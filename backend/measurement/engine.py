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
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from measurement.servers import get_server

logger = logging.getLogger(__name__)

DEFAULT_PING_HOST = "1.1.1.1"
DEFAULT_DNS_HOST = "cloudflare.com"
DEFAULT_HTTP_URL = "https://www.cloudflare.com/cdn-cgi/trace"
DEFAULT_DOWNLOAD_URL = "https://speed.cloudflare.com/__down?bytes=5000000"
DEFAULT_UPLOAD_URL = "https://speed.cloudflare.com/__up"
DEFAULT_IPINFO_URL = "http://ip-api.com/json/?fields=status,message,query,isp,org,as,mobile,proxy,hosting"

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
    server_label: str = "cloudflare"
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


def measure_http_response(url: str = DEFAULT_HTTP_URL) -> float:
    _, elapsed_ms = _http_get(url, timeout=15.0)
    return elapsed_ms


def measure_download_speed(url: str = DEFAULT_DOWNLOAD_URL) -> float:
    data, elapsed_ms = _http_get(url, timeout=120.0)
    seconds = max(elapsed_ms / 1000.0, 0.001)
    megabits = (len(data) * 8) / 1_000_000.0
    return megabits / seconds


def measure_download_speed_multi(
    *,
    bytes_per_pass: int = DOWNLOAD_PASS_BYTES_FULL,
    passes: int = DOWNLOAD_PASSES_FULL,
    download_base_url: str = "https://speed.cloudflare.com/__down",
    server_id: str | None = None,
) -> float:
    """Average throughput across multiple large download passes."""
    speeds: list[float] = []
    for event in iter_download_progress(
        bytes_per_pass=bytes_per_pass,
        passes=passes,
        download_base_url=download_base_url,
        server_id=server_id,
    ):
        if event.get("done") and event.get("download_mbps") is not None:
            return float(event["download_mbps"])
        if event.get("done") and event.get("mbps") is not None:
            return float(event["mbps"])
    return statistics.mean(speeds) if speeds else 0.0


def _download_url_for_pass(server: dict[str, Any], pass_idx: int, bytes_per_pass: int) -> str:
    if server.get("download_mode") == "bytes":
        base = server.get("download_base_url") or "https://speed.cloudflare.com/__down"
        return f"{base}?bytes={bytes_per_pass}"
    urls = server.get("download_urls") or []
    if not urls:
        return f"https://speed.cloudflare.com/__down?bytes={bytes_per_pass}"
    return urls[pass_idx % len(urls)]


def iter_download_progress(
    *,
    bytes_per_pass: int = DOWNLOAD_PASS_BYTES_FULL,
    passes: int = DOWNLOAD_PASSES_FULL,
    download_base_url: str = "https://speed.cloudflare.com/__down",
    server_id: str | None = None,
):
    """Yield live download Mbps updates, then a final averaged result."""
    server = get_server(server_id)
    if server.get("download_mode") == "bytes" and download_base_url:
        # Allow explicit base override for legacy callers.
        server = {**server, "download_base_url": download_base_url}

    pass_speeds: list[float] = []
    errors: list[str] = []

    for pass_idx in range(passes):
        url = _download_url_for_pass(server, pass_idx, bytes_per_pass)
        request = urllib.request.Request(url, headers={"User-Agent": "FYP-InternetQuality/1.0"})
        started_pass = time.perf_counter()
        total_bytes = 0
        try:
            with urllib.request.urlopen(request, timeout=120.0) as response:
                while total_bytes < bytes_per_pass:
                    chunk = response.read(min(DOWNLOAD_CHUNK_BYTES, bytes_per_pass - total_bytes))
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    elapsed = time.perf_counter() - started_pass
                    current_mbps = (total_bytes * 8 / 1_000_000.0) / max(elapsed, 0.001)
                    yield {
                        "phase": "download",
                        "pass": pass_idx + 1,
                        "passes": passes,
                        "bytes": total_bytes,
                        "mbps": round(current_mbps, 2),
                        "done": False,
                        "server_id": server["id"],
                    }
            pass_elapsed = time.perf_counter() - started_pass
            pass_mbps = (total_bytes * 8 / 1_000_000.0) / max(pass_elapsed, 0.001)
            if total_bytes > 0:
                pass_speeds.append(pass_mbps)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            errors.append(f"download pass {pass_idx + 1}: {exc}")
            logger.warning("Download pass failed: %s", exc)

    final = round(statistics.mean(pass_speeds), 2) if pass_speeds else None
    yield {
        "phase": "download",
        "mbps": final,
        "download_mbps": final,
        "done": True,
        "errors": errors,
        "server_id": server["id"],
    }


def measure_upload_speed(url: str = DEFAULT_UPLOAD_URL, size_bytes: int = 1_000_000) -> float:
    payload = b"0" * size_bytes
    elapsed_ms = _http_post(url, payload, timeout=120.0)
    seconds = max(elapsed_ms / 1000.0, 0.001)
    megabits = (size_bytes * 8) / 1_000_000.0
    return megabits / seconds


def iter_upload_progress(
    *,
    total_bytes: int = UPLOAD_TOTAL_BYTES_FULL,
    chunk_bytes: int = UPLOAD_CHUNK_BYTES,
    upload_url: str = DEFAULT_UPLOAD_URL,
    server_id: str | None = None,
):
    """Yield live upload Mbps updates while sending chunked payloads."""
    server = get_server(server_id)
    target_url = server.get("upload_url") or upload_url or DEFAULT_UPLOAD_URL
    errors: list[str] = []
    sent = 0
    started = time.perf_counter()
    payload_template = b"0" * chunk_bytes

    try:
        while sent < total_bytes:
            chunk_size = min(chunk_bytes, total_bytes - sent)
            payload = payload_template[:chunk_size]
            _http_post(target_url, payload, timeout=120.0)
            sent += chunk_size
            elapsed = time.perf_counter() - started
            current_mbps = (sent * 8 / 1_000_000.0) / max(elapsed, 0.001)
            yield {
                "phase": "upload",
                "bytes": sent,
                "mbps": round(current_mbps, 2),
                "done": False,
                "server_id": server["id"],
            }
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        errors.append(f"upload: {exc}")
        logger.warning("Upload failed: %s", exc)

    elapsed = time.perf_counter() - started
    final = round((sent * 8 / 1_000_000.0) / max(elapsed, 0.001), 2) if sent else None
    yield {
        "phase": "upload",
        "mbps": final,
        "upload_mbps": final,
        "done": True,
        "errors": errors,
        "server_id": server["id"],
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

    try:
        dns_lookup_ms = round(measure_dns_lookup(server.get("dns_host") or DEFAULT_DNS_HOST), 2)
    except (OSError, socket.gaierror, ValueError) as exc:
        errors.append(f"dns: {exc}")

    try:
        http_response_ms = round(
            measure_http_response(server.get("http_url") or DEFAULT_HTTP_URL), 2
        )
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        errors.append(f"http: {exc}")

    try:
        ipv4_ok, ipv6_ok = check_ip_version_support()
    except OSError as exc:
        errors.append(f"ip_version: {exc}")

    try:
        info = lookup_public_ip_and_isp()
        public_ip = info.get("public_ip")
        isp_name = info.get("isp_name")
        as_info = info.get("as_info")
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
        "server_label": label,
        "server_id": server["id"],
        "errors": errors,
    }


def run_latency_probe(
    *,
    ping_host: str | None = None,
    count: int = PING_COUNT_FULL,
    server_id: str | None = None,
) -> dict[str, Any]:
    """Ping, jitter, and packet loss for the latency phase."""
    server = get_server(server_id)
    host = ping_host or server.get("ping_host") or DEFAULT_PING_HOST
    errors: list[str] = []
    ping_ms: float | None = None
    jitter_ms: float | None = None
    packet_loss_pct: float | None = None

    try:
        ping_ms, jitter_ms, packet_loss_pct = measure_ping(host, count=count)
        if ping_ms is not None:
            ping_ms = round(ping_ms, 2)
        if jitter_ms is not None:
            jitter_ms = round(jitter_ms, 2)
        if packet_loss_pct is not None:
            packet_loss_pct = round(packet_loss_pct, 2)
    except (OSError, ValueError, statistics.StatisticsError) as exc:
        errors.append(f"ping: {exc}")

    return {
        "ping_ms": ping_ms,
        "jitter_ms": jitter_ms,
        "packet_loss_pct": packet_loss_pct,
        "errors": errors,
        "server_id": server["id"],
    }


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


def lookup_public_ip_and_isp(url: str = DEFAULT_IPINFO_URL) -> dict[str, str | None]:
    try:
        data, _ = _http_get(url, timeout=10.0)
        payload = json.loads(data.decode("utf-8"))
        if payload.get("status") == "fail":
            return {"public_ip": None, "isp_name": None, "as_info": None}
        return {
            "public_ip": payload.get("query"),
            "isp_name": payload.get("isp") or payload.get("org"),
            "as_info": payload.get("as"),
        }
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError):
        return {"public_ip": None, "isp_name": None, "as_info": None}


def measure_ping(
    host: str = DEFAULT_PING_HOST,
    count: int = 6,
) -> tuple[float | None, float | None, float | None]:
    """Return (avg_ms, jitter_ms, packet_loss_pct) using the OS ping utility."""
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", str(count), host]
    else:
        cmd = ["ping", "-c", str(count), host]

    import subprocess

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(30, count * 5 + 10),
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.warning("Ping failed: %s", exc)
        return None, None, None

    output = completed.stdout + "\n" + completed.stderr
    rtts = [float(x) for x in re.findall(r"(?:time[=<]|time=)(\d+(?:\.\d+)?)\s*ms", output, flags=re.I)]
    if not rtts:
        # Fallback TCP connect timing when ICMP is blocked.
        samples: list[float] = []
        failures = 0
        for _ in range(count):
            started = time.perf_counter()
            try:
                socket.create_connection((host, 443), timeout=2.0).close()
                samples.append((time.perf_counter() - started) * 1000.0)
            except OSError:
                failures += 1
        if not samples:
            return None, None, 100.0
        jitter = statistics.pstdev(samples) if len(samples) > 1 else 0.0
        loss = (failures / count) * 100.0
        return statistics.mean(samples), jitter, loss

    sent_match = re.search(r"Sent\s*=\s*(\d+).*Received\s*=\s*(\d+)", output, flags=re.I | re.S)
    if not sent_match:
        sent_match = re.search(r"(\d+)\s+packets transmitted.*?(\d+)\s+received", output, flags=re.I | re.S)
    if sent_match:
        sent = int(sent_match.group(1))
        received = int(sent_match.group(2))
        loss = ((sent - received) / max(sent, 1)) * 100.0
    else:
        loss = max(0.0, ((count - len(rtts)) / max(count, 1)) * 100.0)

    jitter = statistics.pstdev(rtts) if len(rtts) > 1 else 0.0
    return statistics.mean(rtts), jitter, loss


class NetworkMeasurementEngine:
    """Runs a full Internet quality measurement suite and returns structured results."""

    def __init__(
        self,
        *,
        ping_host: str | None = None,
        download_url: str = DEFAULT_DOWNLOAD_URL,
        upload_url: str | None = None,
        upload_bytes: int = UPLOAD_TOTAL_BYTES_FULL,
        quick: bool = False,
        server_id: str | None = None,
    ) -> None:
        self.server = get_server(server_id)
        self.server_id = self.server["id"]
        self.ping_host = ping_host or self.server.get("ping_host") or DEFAULT_PING_HOST
        self.upload_url = upload_url or self.server.get("upload_url") or DEFAULT_UPLOAD_URL
        self.quick = quick
        if quick:
            self.download_bytes_per_pass = DOWNLOAD_PASS_BYTES_QUICK
            self.download_passes = DOWNLOAD_PASSES_QUICK
            self.upload_total_bytes = UPLOAD_TOTAL_BYTES_QUICK
            self.ping_count = PING_COUNT_QUICK
        else:
            self.download_bytes_per_pass = DOWNLOAD_PASS_BYTES_FULL
            self.download_passes = DOWNLOAD_PASSES_FULL
            self.upload_total_bytes = upload_bytes
            self.ping_count = PING_COUNT_FULL
        self.download_url = download_url

    def run(self) -> MeasurementResult:
        result = MeasurementResult(timestamp=_now())
        result.server_label = f"{self.server['name']} · {self.server['location']}"

        try:
            result.dns_lookup_ms = round(
                measure_dns_lookup(self.server.get("dns_host") or DEFAULT_DNS_HOST), 2
            )
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"dns: {exc}")

        try:
            result.http_response_ms = round(
                measure_http_response(self.server.get("http_url") or DEFAULT_HTTP_URL), 2
            )
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"http: {exc}")

        try:
            result.download_mbps = round(
                measure_download_speed_multi(
                    bytes_per_pass=self.download_bytes_per_pass,
                    passes=self.download_passes,
                    server_id=self.server_id,
                ),
                2,
            )
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"download: {exc}")

        try:
            final_upload: float | None = None
            for event in iter_upload_progress(
                total_bytes=self.upload_total_bytes,
                upload_url=self.upload_url,
                server_id=self.server_id,
            ):
                if event.get("done"):
                    final_upload = event.get("upload_mbps")
            result.upload_mbps = round(final_upload, 2) if final_upload is not None else None
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"upload: {exc}")

        try:
            result.ping_ms, result.jitter_ms, result.packet_loss_pct = measure_ping(
                self.ping_host, count=self.ping_count
            )
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
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"isp: {exc}")

        if result.ping_ms is not None:
            result.ping_ms = round(result.ping_ms, 2)
        if result.jitter_ms is not None:
            result.jitter_ms = round(result.jitter_ms, 2)
        if result.packet_loss_pct is not None:
            result.packet_loss_pct = round(result.packet_loss_pct, 2)

        return result
