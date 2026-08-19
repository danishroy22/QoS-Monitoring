"""Real network measurement engine for Internet Quality testing.

Measures download/upload throughput, latency, jitter, packet loss, DNS lookup,
HTTP response time, IP version reachability, public IP, and ISP identity.
"""

from __future__ import annotations

import json
import logging
import platform
import re
import socket
import ssl
import statistics
import threading
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout, as_completed
from typing import Any
from urllib.parse import urlparse

from measurement.config import load_version, profile as measurement_profile, rtt_stats, throughput_mbps
from measurement.servers import get_server

logger = logging.getLogger(__name__)

DEFAULT_PING_HOST = "1.1.1.1"
DEFAULT_DNS_HOST = "cloudflare.com"
DEFAULT_HTTP_URL = "https://www.cloudflare.com/cdn-cgi/trace"
DEFAULT_DOWNLOAD_URL = "https://speed.cloudflare.com/__down?bytes=5000000"
DEFAULT_UPLOAD_URL = "https://speed.cloudflare.com/__up"
DEFAULT_IPINFO_URL = (
    "http://ip-api.com/json/?fields=status,message,query,isp,org,as,"
    "country,regionName,city,lat,lon"
)

DOWNLOAD_CHUNK_BYTES = 512 * 1024
DOWNLOAD_PASS_BYTES_FULL = 25_000_000
DOWNLOAD_PASSES_FULL = 2
DOWNLOAD_PASS_BYTES_QUICK = 3_000_000
DOWNLOAD_PASSES_QUICK = 1

UPLOAD_CHUNK_BYTES = 2_000_000
UPLOAD_TOTAL_BYTES_FULL = 20_000_000
UPLOAD_TOTAL_BYTES_QUICK = 2_000_000

PING_COUNT_FULL = 12
PING_COUNT_QUICK = 4


@dataclass
class MeasurementResult:
    """Full result of one Internet quality test run."""

    timestamp: datetime
    download_mbps: float | None = None
    upload_mbps: float | None = None
    ping_ms: float | None = None
    jitter_ms: float | None = None
    packet_loss_pct: float | None = None
    dns_lookup_ms: float | None = None
    http_response_ms: float | None = None
    ipv4_ok: bool = False
    ipv6_ok: bool = False
    public_ip: str | None = None
    isp_name: str | None = None
    as_info: str | None = None
    detected_region: str | None = None
    detected_city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    server_id: str | None = None
    server_label: str = "cloudflare"
    selection_mode: str | None = None
    selection_score: float | None = None
    ping_min_ms: float | None = None
    ping_max_ms: float | None = None
    ping_median_ms: float | None = None
    packets_sent: int | None = None
    packets_received: int | None = None
    packets_lost: int | None = None
    latency_samples_json: str | None = None
    download_bytes: int | None = None
    download_duration_s: float | None = None
    download_connections: int | None = None
    download_peak_mbps: float | None = None
    upload_bytes: int | None = None
    upload_duration_s: float | None = None
    upload_connections: int | None = None
    upload_peak_mbps: float | None = None
    dns_ok: bool | None = None
    dns_resolver: str | None = None
    tcp_connect_ms: float | None = None
    tls_handshake_ms: float | None = None
    http_ok: bool | None = None
    measurement_config_version: str | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return payload


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _http_get(url: str, timeout: float = 20.0) -> tuple[bytes, float]:
    started = time.perf_counter()
    request = urllib.request.Request(url, headers={"User-Agent": "FYP-InternetQuality/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return data, elapsed_ms


def _http_post(url: str, body: bytes, timeout: float = 30.0) -> float:
    started = time.perf_counter()
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "User-Agent": "FYP-InternetQuality/1.0",
            "Content-Type": "application/octet-stream",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response.read()
    return (time.perf_counter() - started) * 1000.0


def measure_dns_lookup(hostname: str = DEFAULT_DNS_HOST) -> float:
    started = time.perf_counter()
    socket.getaddrinfo(hostname, 443, proto=socket.IPPROTO_TCP)
    return (time.perf_counter() - started) * 1000.0


def measure_http_breakdown(url: str = DEFAULT_HTTP_URL, timeout: float = 15.0) -> dict[str, Any]:
    """Split DNS / TCP / TLS / HTTP timings. Total is stored as http_response_ms."""
    parsed = urlparse(url)
    host = parsed.hostname or DEFAULT_DNS_HOST
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    errors: list[str] = []
    dns_ms = tcp_ms = tls_ms = http_ms = None
    dns_ok = http_ok = False

    t0 = time.perf_counter()
    try:
        socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        dns_ms = (time.perf_counter() - t0) * 1000.0
        dns_ok = True
    except (OSError, socket.gaierror, ValueError) as exc:
        errors.append(f"dns: {exc}")
        dns_ms = (time.perf_counter() - t0) * 1000.0

    sock = None
    t1 = time.perf_counter()
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        tcp_ms = (time.perf_counter() - t1) * 1000.0
    except OSError as exc:
        errors.append(f"tcp: {exc}")
        tcp_ms = (time.perf_counter() - t1) * 1000.0

    t2 = time.perf_counter()
    wrapped = sock
    try:
        if sock is not None and parsed.scheme == "https":
            ctx = ssl.create_default_context()
            wrapped = ctx.wrap_socket(sock, server_hostname=host)
            tls_ms = (time.perf_counter() - t2) * 1000.0
        elif sock is not None:
            tls_ms = 0.0
    except (ssl.SSLError, OSError) as exc:
        errors.append(f"tls: {exc}")
        tls_ms = (time.perf_counter() - t2) * 1000.0
        wrapped = sock

    t3 = time.perf_counter()
    try:
        if wrapped is not None:
            path = parsed.path or "/"
            if parsed.query:
                path = f"{path}?{parsed.query}"
            req = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\nUser-Agent: FYP-InternetQuality/1.0\r\n\r\n"
            wrapped.settimeout(timeout)
            wrapped.sendall(req.encode("ascii"))
            wrapped.recv(1024)
            http_ms = (time.perf_counter() - t3) * 1000.0
            http_ok = True
    except OSError as exc:
        errors.append(f"http: {exc}")
        http_ms = (time.perf_counter() - t3) * 1000.0
    finally:
        try:
            if wrapped is not None:
                wrapped.close()
        except OSError:
            pass

    parts = [x for x in (dns_ms, tcp_ms, tls_ms, http_ms) if x is not None]
    total = sum(parts) if parts else None
    return {
        "dns_lookup_ms": round(dns_ms, 2) if dns_ms is not None else None,
        "tcp_connect_ms": round(tcp_ms, 2) if tcp_ms is not None else None,
        "tls_handshake_ms": round(tls_ms, 2) if tls_ms is not None else None,
        "http_wait_ms": round(http_ms, 2) if http_ms is not None else None,
        "http_response_ms": round(total, 2) if total is not None else None,
        "dns_ok": dns_ok,
        "http_ok": http_ok,
        "dns_resolver": "os-getaddrinfo",
        "errors": errors,
    }


def measure_http_response(url: str = DEFAULT_HTTP_URL) -> float:
    payload = measure_http_breakdown(url)
    return float(payload.get("http_response_ms") or 0.0)


def measure_download_speed(url: str = DEFAULT_DOWNLOAD_URL) -> float:
    data, elapsed_ms = _http_get(url, timeout=120.0)
    seconds = max(elapsed_ms / 1000.0, 0.001)
    megabits = (len(data) * 8) / 1_000_000.0
    return megabits / seconds


def measure_download_speed_multi(
    *,
    bytes_per_pass: int | None = None,
    passes: int | None = None,
    download_base_url: str | None = None,
    server_id: str | None = None,
    quick: bool = False,
) -> float:
    """Average throughput from the duration-window downloader."""
    del bytes_per_pass, passes, download_base_url
    for event in iter_download_progress(server_id=server_id, quick=quick):
        if event.get("done") and event.get("download_mbps") is not None:
            return float(event["download_mbps"])
        if event.get("done") and event.get("mbps") is not None:
            return float(event["mbps"])
    return 0.0


def _download_url_for_pass(server: dict[str, Any], pass_idx: int, bytes_per_pass: int) -> str:
    if server.get("download_mode") == "bytes":
        base = server.get("download_base_url") or "https://speed.cloudflare.com/__down"
        return f"{base}?bytes={bytes_per_pass}"
    urls = server.get("download_urls") or []
    if not urls:
        return f"https://speed.cloudflare.com/__down?bytes={bytes_per_pass}"
    return urls[pass_idx % len(urls)]


class _ByteMeter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.total = 0
        self.warmup_total = 0

    def add(self, n: int) -> None:
        with self._lock:
            self.total += n

    def snapshot(self) -> int:
        with self._lock:
            return self.total

    def mark_warmup(self) -> None:
        with self._lock:
            self.warmup_total = self.total


def iter_download_progress(
    *,
    bytes_per_pass: int | None = None,
    passes: int | None = None,
    download_base_url: str = "https://speed.cloudflare.com/__down",
    server_id: str | None = None,
    quick: bool = False,
):
    """Yield live download Mbps, then a final duration-window result.

    Extra kwargs `bytes_per_pass` / `passes` are ignored in duration mode and
    kept so older callers do not break.
    """
    del bytes_per_pass, passes, download_base_url
    params = measurement_profile(quick)
    server = get_server(server_id)
    duration = float(params["download_duration"])
    warmup = float(params["warmup_duration"])
    interval = float(params["measurement_interval"])
    connections = max(1, int(params["download_connections"]))
    chunk = int(params["download_chunk_bytes"])
    timeout = float(params["timeout"])
    retries = max(0, int(params["retry_count"]))
    request_bytes = 200_000_000
    url = _download_url_for_pass(server, 0, request_bytes)
    meter = _ByteMeter()
    errors: list[str] = []
    peak = 0.0
    stop_flag = threading.Event()

    def worker() -> None:
        attempts = 0
        while not stop_flag.is_set():
            try:
                request = urllib.request.Request(
                    url, headers={"User-Agent": "FYP-InternetQuality/1.0"}
                )
                with urllib.request.urlopen(request, timeout=min(timeout, 4.0)) as response:
                    while not stop_flag.is_set():
                        piece = response.read(chunk)
                        if not piece:
                            break
                        meter.add(len(piece))
                attempts = 0
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                attempts += 1
                errors.append(f"download: {exc}")
                if attempts > retries:
                    time.sleep(0.15)

    started = time.perf_counter()
    warmup_end = started + warmup
    measure_end = warmup_end + duration
    with ThreadPoolExecutor(max_workers=connections) as pool:
        futures = [pool.submit(worker) for _ in range(connections)]
        last_emit = started
        warmup_marked = False
        while time.perf_counter() < measure_end:
            now = time.perf_counter()
            if not warmup_marked and now >= warmup_end:
                meter.mark_warmup()
                warmup_marked = True
            if now - last_emit >= interval:
                elapsed_meas = max(now - warmup_end, 0.001) if warmup_marked else max(now - started, 0.001)
                counted = meter.snapshot() - (meter.warmup_total if warmup_marked else 0)
                current = throughput_mbps(counted, elapsed_meas)
                if warmup_marked:
                    peak = max(peak, current)
                yield {
                    "phase": "download",
                    "bytes": meter.snapshot(),
                    "mbps": round(current, 2),
                    "done": False,
                    "server_id": server["id"],
                }
                last_emit = now
            time.sleep(min(0.05, interval / 2))
        if not warmup_marked:
            meter.mark_warmup()
        stop_flag.set()
        try:
            for fut in as_completed(futures, timeout=3):
                _ = fut.exception()
        except FuturesTimeout:
            pass

    measured_bytes = max(0, meter.snapshot() - meter.warmup_total)
    avg = round(throughput_mbps(measured_bytes, duration), 2) if measured_bytes else None
    yield {
        "phase": "download",
        "mbps": avg,
        "download_mbps": avg,
        "done": True,
        "errors": errors[:8],
        "server_id": server["id"],
        "bytes_transferred": measured_bytes,
        "duration_s": duration,
        "warmup_s": warmup,
        "connections": connections,
        "peak_mbps": round(peak, 2) if peak else avg,
        "config_version": load_version(),
    }


def measure_upload_speed(url: str = DEFAULT_UPLOAD_URL, size_bytes: int = 1_000_000) -> float:
    payload = b"0" * size_bytes
    elapsed_ms = _http_post(url, payload, timeout=120.0)
    seconds = max(elapsed_ms / 1000.0, 0.001)
    megabits = (size_bytes * 8) / 1_000_000.0
    return megabits / seconds


def iter_upload_progress(
    *,
    total_bytes: int | None = None,
    chunk_bytes: int | None = None,
    upload_url: str = DEFAULT_UPLOAD_URL,
    server_id: str | None = None,
    quick: bool = False,
):
    """Yield live upload Mbps for a configured duration window."""
    del total_bytes, chunk_bytes
    params = measurement_profile(quick)
    server = get_server(server_id)
    target_url = server.get("upload_url") or upload_url or DEFAULT_UPLOAD_URL
    duration = float(params["upload_duration"])
    warmup = float(params["warmup_duration"])
    interval = float(params["measurement_interval"])
    connections = max(1, int(params["upload_connections"]))
    chunk = int(params["upload_chunk_bytes"])
    timeout = float(params["timeout"])
    retries = max(0, int(params["retry_count"]))
    meter = _ByteMeter()
    errors: list[str] = []
    peak = 0.0
    stop_flag = threading.Event()
    payload = b"0" * chunk

    def worker() -> None:
        attempts = 0
        while not stop_flag.is_set():
            try:
                _http_post(target_url, payload, timeout=min(timeout, 4.0))
                meter.add(len(payload))
                attempts = 0
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                attempts += 1
                errors.append(f"upload: {exc}")
                if attempts > retries:
                    time.sleep(0.15)

    started = time.perf_counter()
    warmup_end = started + warmup
    measure_end = warmup_end + duration
    with ThreadPoolExecutor(max_workers=connections) as pool:
        futures = [pool.submit(worker) for _ in range(connections)]
        last_emit = started
        warmup_marked = False
        while time.perf_counter() < measure_end:
            now = time.perf_counter()
            if not warmup_marked and now >= warmup_end:
                meter.mark_warmup()
                warmup_marked = True
            if now - last_emit >= interval:
                elapsed_meas = max(now - warmup_end, 0.001) if warmup_marked else max(now - started, 0.001)
                counted = meter.snapshot() - (meter.warmup_total if warmup_marked else 0)
                current = throughput_mbps(counted, elapsed_meas)
                if warmup_marked:
                    peak = max(peak, current)
                yield {
                    "phase": "upload",
                    "bytes": meter.snapshot(),
                    "mbps": round(current, 2),
                    "done": False,
                    "server_id": server["id"],
                }
                last_emit = now
            time.sleep(min(0.05, interval / 2))
        if not warmup_marked:
            meter.mark_warmup()
        stop_flag.set()
        try:
            for fut in as_completed(futures, timeout=3):
                _ = fut.exception()
        except FuturesTimeout:
            pass

    measured_bytes = max(0, meter.snapshot() - meter.warmup_total)
    avg = round(throughput_mbps(measured_bytes, duration), 2) if measured_bytes else None
    yield {
        "phase": "upload",
        "mbps": avg,
        "upload_mbps": avg,
        "done": True,
        "errors": errors[:8],
        "server_id": server["id"],
        "bytes_transferred": measured_bytes,
        "duration_s": duration,
        "warmup_s": warmup,
        "connections": connections,
        "peak_mbps": round(peak, 2) if peak else avg,
        "config_version": load_version(),
    }


def run_server_probe(*, server_id: str | None = None) -> dict[str, Any]:
    """DNS, HTTP, IP version, and ISP lookup for the 'Finding Server' phase."""
    server = get_server(server_id)
    errors: list[str] = []
    dns_lookup_ms: float | None = None
    http_response_ms: float | None = None
    ipv4_ok = False
    ipv6_ok = False
    public_ip: str | None = None
    isp_name: str | None = None
    as_info: str | None = None
    detected_region: str | None = None
    detected_city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    tcp_connect_ms: float | None = None
    tls_handshake_ms: float | None = None
    dns_ok: bool | None = None
    http_ok: bool | None = None
    dns_resolver: str | None = None

    try:
        dns_lookup_ms = round(measure_dns_lookup(server.get("dns_host") or DEFAULT_DNS_HOST), 2)
    except (OSError, socket.gaierror, ValueError) as exc:
        errors.append(f"dns: {exc}")

    try:
        http = measure_http_breakdown(server.get("http_url") or DEFAULT_HTTP_URL)
        http_response_ms = http.get("http_response_ms")
        if http.get("dns_lookup_ms") is not None and dns_lookup_ms is None:
            dns_lookup_ms = http.get("dns_lookup_ms")
        errors.extend(http.get("errors") or [])
        tcp_connect_ms = http.get("tcp_connect_ms")
        tls_handshake_ms = http.get("tls_handshake_ms")
        dns_ok = http.get("dns_ok")
        http_ok = http.get("http_ok")
        dns_resolver = http.get("dns_resolver")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        errors.append(f"http: {exc}")
        tcp_connect_ms = tls_handshake_ms = None
        dns_ok = http_ok = None
        dns_resolver = None

    try:
        ipv4_ok, ipv6_ok = check_ip_version_support()
    except OSError as exc:
        errors.append(f"ip_version: {exc}")

    try:
        info = lookup_public_ip_and_isp()
        public_ip = info.get("public_ip")
        isp_name = info.get("isp_name")
        as_info = info.get("as_info")
        detected_region = info.get("detected_region")
        detected_city = info.get("detected_city")
        latitude = info.get("latitude")
        longitude = info.get("longitude")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        errors.append(f"isp: {exc}")

    label = f"{server['name']} · {server['location']}"
    return {
        "dns_lookup_ms": dns_lookup_ms,
        "http_response_ms": http_response_ms,
        "ipv4_ok": ipv4_ok,
        "ipv6_ok": ipv6_ok,
        "public_ip": public_ip,
        "isp_name": isp_name,
        "as_info": as_info,
        "detected_region": detected_region,
        "detected_city": detected_city,
        "latitude": latitude,
        "longitude": longitude,
        "server_label": label,
        "server_id": server["id"],
        "tcp_connect_ms": tcp_connect_ms,
        "tls_handshake_ms": tls_handshake_ms,
        "dns_ok": dns_ok,
        "http_ok": http_ok,
        "dns_resolver": dns_resolver,
        "errors": errors,
    }


def run_latency_probe(
    *,
    ping_host: str | None = None,
    count: int | None = None,
    server_id: str | None = None,
    quick: bool = False,
) -> dict[str, Any]:
    """Ping, jitter, and packet loss for the latency phase."""
    server = get_server(server_id)
    host = ping_host or server.get("ping_host") or DEFAULT_PING_HOST
    errors: list[str] = []
    stats: dict[str, Any] = {}
    try:
        stats = measure_ping(host, count=count, quick=quick)
    except (OSError, ValueError, statistics.StatisticsError) as exc:
        errors.append(f"ping: {exc}")
        stats = rtt_stats([], sent=count or 0, received=0)
    stats["errors"] = errors
    stats["server_id"] = server["id"]
    stats["latency_samples"] = stats.get("samples") or []
    return stats


def check_ip_version_support() -> tuple[bool, bool]:
    ipv4_ok = False
    ipv6_ok = False
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=3.0).close()
        ipv4_ok = True
    except OSError:
        pass
    try:
        socket.create_connection(("2606:4700:4700::1111", 443), timeout=3.0).close()
        ipv6_ok = True
    except OSError:
        pass
    return ipv4_ok, ipv6_ok


def lookup_public_ip_and_isp(url: str = DEFAULT_IPINFO_URL) -> dict[str, Any]:
    """Approximate network identity from a public IP lookup.

    ISP/ASN/region are contextual only — they are not ground-truth operator
    records and must not be treated as perfectly accurate.
    """
    empty = {
        "public_ip": None,
        "isp_name": None,
        "as_info": None,
        "detected_region": None,
        "detected_city": None,
        "country": None,
        "latitude": None,
        "longitude": None,
    }
    try:
        data, _ = _http_get(url, timeout=10.0)
        payload = json.loads(data.decode("utf-8"))
        if payload.get("status") == "fail":
            return empty
        lat = payload.get("lat")
        lon = payload.get("lon")
        return {
            "public_ip": payload.get("query"),
            "isp_name": payload.get("isp") or payload.get("org"),
            "as_info": payload.get("as"),
            "detected_region": payload.get("regionName") or payload.get("city"),
            "detected_city": payload.get("city"),
            "country": payload.get("country"),
            "latitude": float(lat) if lat is not None else None,
            "longitude": float(lon) if lon is not None else None,
        }
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError):
        return empty


def measure_ping(
    host: str = DEFAULT_PING_HOST,
    count: int | None = None,
    timeout: float | None = None,
    packet_size: int | None = None,
    quick: bool = False,
) -> dict[str, Any]:
    """ICMP echo via OS ping; TCP connect fallback. Returns a stats dict."""
    params = measurement_profile(quick)
    count = int(count if count is not None else params["latency_packet_count"])
    timeout = float(timeout if timeout is not None else params["latency_timeout"])
    packet_size = int(packet_size if packet_size is not None else params["latency_packet_size"])
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", str(count), "-w", str(int(timeout * 1000)), "-l", str(packet_size), host]
    else:
        cmd = ["ping", "-c", str(count), "-W", str(max(1, int(timeout))), "-s", str(packet_size), host]

    import subprocess

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(30, count * (timeout + 1) + 10),
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.warning("Ping failed: %s", exc)
        stats = rtt_stats([], sent=count, received=0)
        stats["probe_method"] = "icmp_failed"
        stats["latency_packet_size"] = packet_size
        return stats

    output = completed.stdout + "\n" + completed.stderr
    rtts = [float(x) for x in re.findall(r"(?:time[=<]|time=)(\d+(?:\.\d+)?)\s*ms", output, flags=re.I)]
    if not rtts:
        samples: list[float] = []
        failures = 0
        for _ in range(count):
            started = time.perf_counter()
            try:
                socket.create_connection((host, 443), timeout=timeout).close()
                samples.append((time.perf_counter() - started) * 1000.0)
            except OSError:
                failures += 1
        stats = rtt_stats(samples, sent=count, received=len(samples))
        stats["probe_method"] = "tcp_fallback"
        stats["latency_packet_size"] = packet_size
        return stats

    sent_match = re.search(r"Sent\s*=\s*(\d+).*Received\s*=\s*(\d+)", output, flags=re.I | re.S)
    if not sent_match:
        sent_match = re.search(r"(\d+)\s+packets transmitted.*?(\d+)\s+received", output, flags=re.I | re.S)
    if sent_match:
        sent = int(sent_match.group(1))
        received = int(sent_match.group(2))
    else:
        sent = count
        received = len(rtts)
    stats = rtt_stats(rtts, sent=sent, received=received)
    stats["probe_method"] = "icmp"
    stats["latency_packet_size"] = packet_size
    return stats


class NetworkMeasurementEngine:
    """Runs a full Internet quality measurement suite and returns structured results."""

    def __init__(
        self,
        *,
        ping_host: str | None = None,
        download_url: str = DEFAULT_DOWNLOAD_URL,
        upload_url: str | None = None,
        upload_bytes: int | None = None,
        quick: bool = False,
        server_id: str | None = None,
    ) -> None:
        del upload_bytes
        self.server = get_server(server_id)
        self.server_id = self.server["id"]
        self.ping_host = ping_host or self.server.get("ping_host") or DEFAULT_PING_HOST
        self.upload_url = upload_url or self.server.get("upload_url") or DEFAULT_UPLOAD_URL
        self.quick = quick
        self.params = measurement_profile(quick)
        self.download_url = download_url

    def run(self) -> MeasurementResult:
        result = MeasurementResult(timestamp=_now())
        result.server_id = self.server_id
        result.server_label = f"{self.server['name']} · {self.server['location']}"
        result.measurement_config_version = load_version()

        try:
            http = measure_http_breakdown(self.server.get("http_url") or DEFAULT_HTTP_URL)
            result.dns_lookup_ms = http.get("dns_lookup_ms")
            result.http_response_ms = http.get("http_response_ms")
            result.tcp_connect_ms = http.get("tcp_connect_ms")
            result.tls_handshake_ms = http.get("tls_handshake_ms")
            result.dns_ok = http.get("dns_ok")
            result.http_ok = http.get("http_ok")
            result.dns_resolver = http.get("dns_resolver")
            result.errors.extend(http.get("errors") or [])
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"http: {exc}")

        try:
            down_event = None
            for event in iter_download_progress(server_id=self.server_id, quick=self.quick):
                if event.get("done"):
                    down_event = event
            if down_event:
                result.download_mbps = down_event.get("download_mbps")
                result.download_bytes = down_event.get("bytes_transferred")
                result.download_duration_s = down_event.get("duration_s")
                result.download_connections = down_event.get("connections")
                result.download_peak_mbps = down_event.get("peak_mbps")
                result.errors.extend(down_event.get("errors") or [])
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"download: {exc}")

        try:
            up_event = None
            for event in iter_upload_progress(
                upload_url=self.upload_url,
                server_id=self.server_id,
                quick=self.quick,
            ):
                if event.get("done"):
                    up_event = event
            if up_event:
                result.upload_mbps = up_event.get("upload_mbps")
                result.upload_bytes = up_event.get("bytes_transferred")
                result.upload_duration_s = up_event.get("duration_s")
                result.upload_connections = up_event.get("connections")
                result.upload_peak_mbps = up_event.get("peak_mbps")
                result.errors.extend(up_event.get("errors") or [])
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"upload: {exc}")

        try:
            stats = measure_ping(self.ping_host, quick=self.quick)
            result.ping_ms = stats.get("ping_ms")
            result.ping_min_ms = stats.get("ping_min_ms")
            result.ping_max_ms = stats.get("ping_max_ms")
            result.ping_median_ms = stats.get("ping_median_ms")
            result.jitter_ms = stats.get("jitter_ms")
            result.packet_loss_pct = stats.get("packet_loss_pct")
            result.packets_sent = stats.get("packets_sent")
            result.packets_received = stats.get("packets_received")
            result.packets_lost = stats.get("packets_lost")
            result.latency_samples_json = json.dumps(stats.get("samples") or [])
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"ping: {exc}")

        try:
            result.ipv4_ok, result.ipv6_ok = check_ip_version_support()
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"ip_version: {exc}")

        try:
            info = lookup_public_ip_and_isp()
            result.public_ip = info.get("public_ip")
            result.isp_name = info.get("isp_name")
            result.as_info = info.get("as_info")
            result.detected_region = info.get("detected_region")
            result.detected_city = info.get("detected_city")
            result.latitude = info.get("latitude")
            result.longitude = info.get("longitude")
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"isp: {exc}")

        return result
