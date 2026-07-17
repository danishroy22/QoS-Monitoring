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

logger = logging.getLogger(__name__)

DEFAULT_PING_HOST = "1.1.1.1"
DEFAULT_DNS_HOST = "cloudflare.com"
DEFAULT_HTTP_URL = "https://www.cloudflare.com/cdn-cgi/trace"
DEFAULT_DOWNLOAD_URL = "https://speed.cloudflare.com/__down?bytes=5000000"
DEFAULT_UPLOAD_URL = "https://speed.cloudflare.com/__up"
DEFAULT_IPINFO_URL = "http://ip-api.com/json/?fields=status,message,query,isp,org,as,mobile,proxy,hosting"


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
    data, elapsed_ms = _http_get(url, timeout=45.0)
    seconds = max(elapsed_ms / 1000.0, 0.001)
    megabits = (len(data) * 8) / 1_000_000.0
    return megabits / seconds


def measure_upload_speed(url: str = DEFAULT_UPLOAD_URL, size_bytes: int = 1_000_000) -> float:
    payload = b"0" * size_bytes
    elapsed_ms = _http_post(url, payload, timeout=45.0)
    seconds = max(elapsed_ms / 1000.0, 0.001)
    megabits = (size_bytes * 8) / 1_000_000.0
    return megabits / seconds


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
            timeout=20,
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
        ping_host: str = DEFAULT_PING_HOST,
        download_url: str = DEFAULT_DOWNLOAD_URL,
        upload_url: str = DEFAULT_UPLOAD_URL,
        upload_bytes: int = 1_000_000,
        quick: bool = False,
    ) -> None:
        self.ping_host = ping_host
        self.download_url = download_url
        self.upload_url = upload_url
        self.upload_bytes = 500_000 if quick else upload_bytes
        self.ping_count = 4 if quick else 6
        if quick:
            self.download_url = "https://speed.cloudflare.com/__down?bytes=1500000"

    def run(self) -> MeasurementResult:
        result = MeasurementResult(timestamp=_now())

        try:
            result.ping_ms, result.jitter_ms, result.packet_loss_pct = measure_ping(
                self.ping_host, count=self.ping_count
            )
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"ping: {exc}")

        try:
            result.dns_lookup_ms = round(measure_dns_lookup(), 2)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"dns: {exc}")

        try:
            result.http_response_ms = round(measure_http_response(), 2)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"http: {exc}")

        try:
            result.download_mbps = round(measure_download_speed(self.download_url), 2)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"download: {exc}")

        try:
            result.upload_mbps = round(
                measure_upload_speed(self.upload_url, size_bytes=self.upload_bytes), 2
            )
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"upload: {exc}")

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
