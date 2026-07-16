# Database Schema

PostgreSQL is recommended for this project because it is easy to run locally, supports time-indexed queries, and is simpler to document than a full time-series stack. If required, the same design can later be migrated to InfluxDB.

## Tables

### `network_nodes`

Stores simulated broadband access nodes or service areas.

- `id`: Primary key
- `node_code`: Human-readable unique node identifier
- `region`: Simulated geographic area
- `access_technology`: FTTH, DSL, cable, fixed wireless, or similar
- `service_tier_mbps`: Expected maximum service rate
- `subscriber_count`: Number of simulated subscribers
- `baseline_latency_ms`: Normal expected latency
- `max_bandwidth_mbps`: Capacity limit for the node
- `created_at`: Record creation timestamp

### `qos_measurements`

Stores time-series QoS samples.

- `id`: Primary key
- `node_id`: Foreign key to `network_nodes`
- `timestamp`: Measurement time
- `latency_ms`
- `jitter_ms`
- `packet_loss_pct`
- `throughput_mbps`
- `bandwidth_utilisation_pct`
- `signal_quality`
- `availability_pct`
- `scenario_label`: Simulator ground truth, such as `normal` or `congestion`

### `network_events`

Stores simulator events and incident windows.

- `id`: Primary key
- `node_id`: Foreign key to `network_nodes`
- `event_type`
- `severity`
- `start_time`
- `end_time`
- `description`

### `anomaly_results`

Stores ML anomaly detection outputs.

- `id`: Primary key
- `measurement_id`: Foreign key to `qos_measurements`
- `model_name`
- `anomaly_score`
- `is_anomaly`
- `severity`
- `suspected_issue`
- `created_at`

### `ai_recommendations`

Stores generated explanations and corrective actions.

- `id`: Primary key
- `anomaly_id`: Foreign key to `anomaly_results`
- `summary`
- `likely_causes`
- `recommended_actions`
- `model_provider`
- `created_at`

## Indexing Strategy

- Index `qos_measurements(node_id, timestamp)` for historical graph queries.
- Index `anomaly_results(is_anomaly, created_at)` for active issue panels.
- Index `network_events(node_id, start_time, end_time)` for evaluation against simulator ground truth.
