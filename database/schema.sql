CREATE TABLE IF NOT EXISTS network_nodes (
    id SERIAL PRIMARY KEY,
    node_code VARCHAR(50) UNIQUE NOT NULL,
    region VARCHAR(100) NOT NULL,
    access_technology VARCHAR(50) NOT NULL,
    service_tier_mbps NUMERIC(10, 2) NOT NULL,
    subscriber_count INTEGER NOT NULL,
    baseline_latency_ms NUMERIC(10, 2) NOT NULL,
    max_bandwidth_mbps NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS qos_measurements (
    id BIGSERIAL PRIMARY KEY,
    node_id INTEGER NOT NULL REFERENCES network_nodes(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    latency_ms NUMERIC(10, 2) NOT NULL,
    jitter_ms NUMERIC(10, 2) NOT NULL,
    packet_loss_pct NUMERIC(6, 3) NOT NULL,
    throughput_mbps NUMERIC(10, 2) NOT NULL,
    bandwidth_utilisation_pct NUMERIC(6, 2) NOT NULL,
    signal_quality NUMERIC(6, 2),
    availability_pct NUMERIC(6, 2) NOT NULL,
    scenario_label VARCHAR(50) NOT NULL DEFAULT 'normal'
);

CREATE TABLE IF NOT EXISTS network_events (
    id BIGSERIAL PRIMARY KEY,
    node_id INTEGER NOT NULL REFERENCES network_nodes(id) ON DELETE CASCADE,
    event_type VARCHAR(80) NOT NULL,
    severity VARCHAR(30) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS anomaly_results (
    id BIGSERIAL PRIMARY KEY,
    measurement_id BIGINT NOT NULL REFERENCES qos_measurements(id) ON DELETE CASCADE,
    model_name VARCHAR(80) NOT NULL,
    anomaly_score NUMERIC(12, 6) NOT NULL,
    is_anomaly BOOLEAN NOT NULL,
    severity VARCHAR(30) NOT NULL,
    suspected_issue VARCHAR(120),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_recommendations (
    id BIGSERIAL PRIMARY KEY,
    anomaly_id BIGINT NOT NULL REFERENCES anomaly_results(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    likely_causes TEXT NOT NULL,
    recommended_actions TEXT NOT NULL,
    model_provider VARCHAR(80) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_qos_measurements_node_time
    ON qos_measurements (node_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_anomaly_results_status_time
    ON anomaly_results (is_anomaly, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_network_events_node_time
    ON network_events (node_id, start_time DESC, end_time);
