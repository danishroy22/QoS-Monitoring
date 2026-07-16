# Broadband QoS Simulator

## Purpose

Generate realistic synthetic broadband QoS measurements that behave like ISP monitoring telemetry. The simulator supports:

- Normal operation
- Peak-hour congestion
- High latency
- Packet loss
- Bandwidth limitation
- Outage / availability degradation

Every sample includes a `scenario_label` ground-truth field for ML evaluation.

## Package layout

| File | Role |
|------|------|
| `models.py` | `NetworkNode`, `QoSMeasurement`, `NetworkEvent`, scenario enums |
| `nodes.py` | Default UAE-region virtual broadband nodes |
| `scenarios.py` | Metric profiles for each degradation type |
| `engine.py` | Scenario scheduling and ground-truth events |
| `generator.py` | Core measurement generator (`QoSSimulator`) |
| `publishers.py` | CSV export and FastAPI POST publisher |
| `cli.py` | Command-line entry point |

## Quick start

From the repository root (`d:\FYP`):

```bash
# Historical dataset for ML training (CSV)
python -m backend.simulator --mode batch --samples 120 --seed 42

# Live simulation for 20 ticks
python -m backend.simulator --mode live --ticks 20 --interval 2 --print-json

# Force a congestion demo
python -m backend.simulator --mode batch --samples 50 --force-scenario congestion

# Live publish to backend (Phase 3) with dry-run until API exists
python -m backend.simulator --mode live --ticks 10 --dry-run-api
```

Output files are written to `data/simulator/`:

- `qos_measurements.csv`
- `network_events.csv`

## Metrics generated

- `latency_ms`
- `jitter_ms`
- `packet_loss_pct`
- `throughput_mbps`
- `bandwidth_utilisation_pct`
- `signal_quality`
- `availability_pct`
- `scenario_label`
