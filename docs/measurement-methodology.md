# Measurement methodology (Phase 2)

Values in `backend/measurement/measurement_config.json` are **experimental
starting points** so tests are repeatable. They are **not** claimed to be
optimal packet sizes, probe counts, or window lengths.

## What we are doing

Each GO run measures:

1. **Identity / HTTP path** — DNS lookup, TCP connect, TLS handshake, HTTP GET.
2. **Download throughput** — duration-window HTTPS GET after a short warm-up.
3. **Upload throughput** — duration-window HTTPS POST after the same warm-up.
4. **Latency** — ICMP echo (OS ping) with TCP-connect fallback; min / max /
   average / median RTT, jitter, and packet counts.

Parameters live in JSON (`full` and `quick` profiles) and are exposed at
`GET /speedtest/config`. Changing the JSON does not require a UI redesign.

## How we are doing it

### Config keys (both profiles)

| Key | Meaning |
|-----|---------|
| `latency_packet_size` | ICMP payload bytes (`ping -l` / `-s`) |
| `latency_packet_count` | Number of probe packets |
| `latency_timeout` | Per-probe timeout (seconds) |
| `download_duration` | Measurement window after warm-up (seconds) |
| `upload_duration` | Independent uplink window (seconds) |
| `download_connections` | Parallel GET streams (default **1**) |
| `upload_connections` | Parallel POST streams (default **1**) |
| `warmup_duration` | Seconds discarded so TCP slow-start is less dominant |
| `measurement_interval` | How often live Mbps is sampled (SSE + peak) |

Also recorded: `timeout`, `retry_count`, chunk sizes. Version field:
`measurement_config_version` (currently `2.0`).

### Throughput

Mode is **duration**, not a fixed byte budget.

```text
throughput_mbps = bytes_after_warmup * 8 / 1e6 / measurement_duration_s
```

Warm-up bytes are excluded from the average. Peak Mbps is the highest
interval sample during the measurement window. SSE events still send
`phase`, `mbps`, and a final `done` payload (plus `bytes_transferred`,
`duration_s`, `connections`, `peak_mbps`, `config_version`).

Default full windows: **8 s download + 1 s warm-up**, **6 s upload**,
**1 connection**. Quick profile uses shorter windows.

### Latency

Successful RTT samples produce:

- average (`ping_ms`)
- min / max / median
- jitter = **population standard deviation** of successful samples
  (same input the existing QoS engine already uses)
- `packet_loss_pct = packets_lost / packets_sent * 100`
- `packets_sent`, `packets_received`, `packets_lost`
- optional `latency_samples` (JSON on disk)

ICMP uses the configured packet size. If the OS ping yields no RTTs,
SmartQoS falls back to TCP connect timing so Windows / ICMP-blocked
networks still produce a latency phase.

### DNS / HTTP split

`measure_http_breakdown` times, in order:

1. OS `getaddrinfo` (DNS)
2. TCP connect
3. TLS handshake (HTTPS)
4. HTTP GET wait

`http_response_ms` is the **sum** of those parts (existing field).
`dns_ok` / `http_ok` / `dns_resolver` are stored additively.

## Why

- **Documented numbers** let the dissertation defend *what* was measured.
- **Duration windows** stay comparable across line rates; a 25 MB pass
  finishes instantly on fibre and under-samples a slow link.
- **Single connection by default** avoids mixing multi-flow aggregation
  into the consumer score.
- **Warm-up** reduces TCP slow-start bias in the published average.

## Alternatives considered

| Alternative | Why not default |
|-------------|-----------------|
| Fixed-size byte passes | Results depend on line rate; hard to compare |
| Multi-connection Ookla-style | Confounds path capacity with flow aggregation |
| Sample stdev jitter (RFC 3550) | Would change QoS inputs; population stdev kept |
| Claiming “optimal” 32-byte pings | No local study supports that; size is for repeatability |

## Limitations

- Throughput still uses the Cloudflare measurement backend; the Mauritius
  catalogue host is identity / ping / HTTP context (Phase 1).
- ICMP packet size is an OS ping flag, not a custom Ethernet frame.
- Short windows miss long-term buffering and peak-hour congestion
  (later phases).
- DNS resolver identity is `os-getaddrinfo`, not a recursive-resolver probe.
- Defaults are **starting points**, not an ITU / Ookla calibration.

Existing APIs `GET /speedtest/stream/download|upload` and
`POST /speedtest/complete` remain. QoS weights in `qos_analysis.py` are
unchanged.
