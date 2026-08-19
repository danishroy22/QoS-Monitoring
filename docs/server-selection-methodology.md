# Server selection methodology (Phase 1)

## What we are doing

When the consumer taps **GO** (Automatic mode), SmartQoS:

1. Looks up approximate network identity (public IP, ISP, ASN, city/region).
2. Probes Mauritius catalogue hosts with TCP connect RTT.
3. Scores candidates with documented weights.
4. Uses the winning server for the existing phased speed test.

Manual selection remains under **Advanced Settings**.

## How we are doing it

### Identity

`POST /speedtest/identify` uses ip-api.com fields:

`query, isp, org, as, country, regionName, city, lat, lon`

This is **network identity / context**, not a guaranteed commercial ISP record.

### Probe

Each catalogue `host` (hostname:port) is probed with a short TCP connect
(`samples` and `timeout_seconds` in `backend/measurement/server_selection.json`).

TCP is used instead of ICMP because Windows and many ISPs block ping.

### Score (defaults)

| Factor | Weight | Direction |
|--------|--------|-----------|
| Latency | 0.45 | lower better, capped at 80 ms |
| Probe packet loss | 0.20 | lower better |
| Geographic proximity (`distance_km`) | 0.15 | nearer better, cap 40 km |
| Catalogue status Online | 0.10 | offline → score 0 |
| ISP name overlap | 0.10 | bonus only |

Weights are in `server_selection.json` and can be changed without UI work.

## Why

Consumers should not pick a server. Ranking by **measured RTT** is more honest
than mapping “detected ISP → that ISP’s server”, which can pick a worse path.

## Alternatives considered

| Alternative | Why not default |
|-------------|-----------------|
| Same-ISP server always | Ignores latency; unfair if that host is far or loaded |
| Simulated `base_latency_ms` | Not a measurement (previous behaviour) |
| ICMP-only probes | Often blocked; TCP to the published port is more relevant |

## Limitations

- Throughput is still measured via the existing Cloudflare backend; the selected
  server is the **identity / probe / ping host**, not a full Ookla node.
- Short TCP probes are not a full packet-loss study.
- Catalogue `distance_km` and coordinates are approximate.
- If every probe fails, SmartQoS falls back to the default server id.

Existing APIs `GET /speedtest/servers` and `POST /speedtest/find-server` remain.
`find-server` now performs real probes (optional `?isp_name=`).
