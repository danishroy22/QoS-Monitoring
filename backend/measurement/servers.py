"""Public speed-test server catalog for SmartQoS measurements."""

from __future__ import annotations

from typing import Any

DEFAULT_SERVER_ID = "cloudflare"

# Each server defines download + optional upload endpoints and ping target.
SPEED_SERVERS: dict[str, dict[str, Any]] = {
    "cloudflare": {
        "id": "cloudflare",
        "name": "Cloudflare",
        "location": "Global CDN",
        "download_mode": "bytes",
        "download_base_url": "https://speed.cloudflare.com/__down",
        "upload_url": "https://speed.cloudflare.com/__up",
        "ping_host": "1.1.1.1",
        "dns_host": "cloudflare.com",
        "http_url": "https://www.cloudflare.com/cdn-cgi/trace",
        "supports_upload": True,
    },
    "tele2": {
        "id": "tele2",
        "name": "Tele2",
        "location": "Stockholm, SE",
        "download_mode": "file",
        "download_urls": [
            "https://speedtest.tele2.net/100MB.zip",
            "https://speedtest.tele2.net/100MB.zip",
        ],
        "upload_url": "https://speedtest.tele2.net/upload.php",
        "ping_host": "speedtest.tele2.net",
        "dns_host": "speedtest.tele2.net",
        "http_url": "https://speedtest.tele2.net/",
        "supports_upload": True,
    },
    "hetzner": {
        "id": "hetzner",
        "name": "Hetzner",
        "location": "Falkenstein, DE",
        "download_mode": "file",
        "download_urls": [
            "https://speed.hetzner.de/100MB.bin",
            "https://speed.hetzner.de/100MB.bin",
        ],
        "upload_url": "https://speed.cloudflare.com/__up",
        "ping_host": "speed.hetzner.de",
        "dns_host": "speed.hetzner.de",
        "http_url": "https://speed.hetzner.de/",
        "supports_upload": True,
        "upload_note": "Upload uses Cloudflare endpoint (Hetzner is download-only)",
    },
    "ovh": {
        "id": "ovh",
        "name": "OVH",
        "location": "Gravelines, FR",
        "download_mode": "file",
        "download_urls": [
            "https://proof.ovh.net/files/100Mb.dat",
            "https://proof.ovh.net/files/100Mb.dat",
        ],
        "upload_url": "https://speed.cloudflare.com/__up",
        "ping_host": "proof.ovh.net",
        "dns_host": "proof.ovh.net",
        "http_url": "https://proof.ovh.net/",
        "supports_upload": True,
        "upload_note": "Upload uses Cloudflare endpoint (OVH is download-only)",
    },
    "thinkbroadband": {
        "id": "thinkbroadband",
        "name": "ThinkBroadband",
        "location": "London, UK",
        "download_mode": "file",
        "download_urls": [
            "http://ipv4.download.thinkbroadband.com/100MB.zip",
            "http://ipv4.download.thinkbroadband.com/100MB.zip",
        ],
        "upload_url": "https://speed.cloudflare.com/__up",
        "ping_host": "ipv4.download.thinkbroadband.com",
        "dns_host": "download.thinkbroadband.com",
        "http_url": "http://ipv4.download.thinkbroadband.com/",
        "supports_upload": True,
        "upload_note": "Upload uses Cloudflare endpoint (ThinkBroadband is download-only)",
    },
}


def list_servers() -> list[dict[str, Any]]:
    """Public metadata for the UI server picker."""
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "location": s["location"],
            "supports_upload": bool(s.get("supports_upload", False)),
            "upload_note": s.get("upload_note"),
        }
        for s in SPEED_SERVERS.values()
    ]


def get_server(server_id: str | None) -> dict[str, Any]:
    if not server_id or server_id not in SPEED_SERVERS:
        return SPEED_SERVERS[DEFAULT_SERVER_ID]
    return SPEED_SERVERS[server_id]
