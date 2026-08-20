-- SmartQoS Phase 3 — Supabase / Postgres schema for traceable speed_tests
-- Run in the Supabase SQL Editor (or via psql against the project DB).
-- FastAPI still owns writes through SQLAlchemy; these objects document the store
-- and provide SQL-side aggregations for dissertation evidence.

CREATE TABLE IF NOT EXISTS speed_tests (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    download_mbps DOUBLE PRECISION,
    upload_mbps DOUBLE PRECISION,
    ping_ms DOUBLE PRECISION,
    jitter_ms DOUBLE PRECISION,
    packet_loss_pct DOUBLE PRECISION,
    dns_lookup_ms DOUBLE PRECISION,
    http_response_ms DOUBLE PRECISION,
    ipv4_ok BOOLEAN NOT NULL DEFAULT FALSE,
    ipv6_ok BOOLEAN NOT NULL DEFAULT FALSE,
    public_ip VARCHAR(64),
    client_hash VARCHAR(64),
    isp_name VARCHAR(200),
    as_info VARCHAR(200),
    internet_package VARCHAR(120),
    detected_region VARCHAR(120),
    detected_city VARCHAR(120),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    server_id VARCHAR(80),
    server_label VARCHAR(80) NOT NULL DEFAULT 'cloudflare',
    server_operator VARCHAR(120),
    server_location VARCHAR(120),
    server_type VARCHAR(120),
    selection_mode VARCHAR(20),
    selection_score DOUBLE PRECISION,
    test_date VARCHAR(10),
    day_of_week INTEGER,
    hour_utc INTEGER,
    ping_min_ms DOUBLE PRECISION,
    ping_max_ms DOUBLE PRECISION,
    ping_median_ms DOUBLE PRECISION,
    packets_sent INTEGER,
    packets_received INTEGER,
    packets_lost INTEGER,
    latency_samples_json TEXT,
    download_bytes INTEGER,
    download_duration_s DOUBLE PRECISION,
    download_connections INTEGER,
    download_peak_mbps DOUBLE PRECISION,
    upload_bytes INTEGER,
    upload_duration_s DOUBLE PRECISION,
    upload_connections INTEGER,
    upload_peak_mbps DOUBLE PRECISION,
    dns_ok BOOLEAN,
    dns_resolver VARCHAR(80),
    tcp_connect_ms DOUBLE PRECISION,
    tls_handshake_ms DOUBLE PRECISION,
    http_ok BOOLEAN,
    measurement_config_version VARCHAR(20),
    overall_score INTEGER,
    overall_rating VARCHAR(40),
    errors_json TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Additive upgrades when the table already exists (safe to re-run).
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS client_hash VARCHAR(64);
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS internet_package VARCHAR(120);
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS server_operator VARCHAR(120);
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS server_location VARCHAR(120);
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS server_type VARCHAR(120);
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS test_date VARCHAR(10);
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS day_of_week INTEGER;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS hour_utc INTEGER;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS ping_min_ms DOUBLE PRECISION;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS ping_max_ms DOUBLE PRECISION;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS ping_median_ms DOUBLE PRECISION;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS packets_sent INTEGER;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS packets_received INTEGER;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS packets_lost INTEGER;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS latency_samples_json TEXT;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS download_bytes INTEGER;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS download_duration_s DOUBLE PRECISION;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS download_connections INTEGER;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS download_peak_mbps DOUBLE PRECISION;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS upload_bytes INTEGER;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS upload_duration_s DOUBLE PRECISION;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS upload_connections INTEGER;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS upload_peak_mbps DOUBLE PRECISION;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS dns_ok BOOLEAN;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS dns_resolver VARCHAR(80);
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS tcp_connect_ms DOUBLE PRECISION;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS tls_handshake_ms DOUBLE PRECISION;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS http_ok BOOLEAN;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS measurement_config_version VARCHAR(20);
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS selection_mode VARCHAR(20);
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS selection_score DOUBLE PRECISION;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS detected_region VARCHAR(120);
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS detected_city VARCHAR(120);
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS server_id VARCHAR(80);

CREATE INDEX IF NOT EXISTS idx_speed_tests_timestamp ON speed_tests (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_speed_tests_isp ON speed_tests (isp_name);
CREATE INDEX IF NOT EXISTS idx_speed_tests_package ON speed_tests (internet_package);
CREATE INDEX IF NOT EXISTS idx_speed_tests_region ON speed_tests (detected_region);
CREATE INDEX IF NOT EXISTS idx_speed_tests_server ON speed_tests (server_id);
CREATE INDEX IF NOT EXISTS idx_speed_tests_client_hash ON speed_tests (client_hash);
CREATE INDEX IF NOT EXISTS idx_speed_tests_test_date ON speed_tests (test_date);
CREATE INDEX IF NOT EXISTS idx_speed_tests_dow ON speed_tests (day_of_week);
CREATE INDEX IF NOT EXISTS idx_speed_tests_hour ON speed_tests (hour_utc);

-- Backend uses the service role / direct DB URL. Keep anon open access closed.
ALTER TABLE speed_tests ENABLE ROW LEVEL SECURITY;

-- Aggregation views (dissertation-traceable SQL)
CREATE OR REPLACE VIEW agg_by_isp AS
SELECT
    COALESCE(NULLIF(TRIM(isp_name), ''), 'Unknown') AS bucket,
    COUNT(*)::INT AS count,
    ROUND(AVG(download_mbps)::NUMERIC, 2) AS avg_download_mbps,
    ROUND(AVG(upload_mbps)::NUMERIC, 2) AS avg_upload_mbps,
    ROUND(AVG(ping_ms)::NUMERIC, 2) AS avg_ping_ms,
    ROUND(AVG(jitter_ms)::NUMERIC, 2) AS avg_jitter_ms,
    ROUND(AVG(packet_loss_pct)::NUMERIC, 2) AS avg_packet_loss_pct,
    ROUND(AVG(overall_score)::NUMERIC, 2) AS avg_overall_score
FROM speed_tests
GROUP BY 1;

CREATE OR REPLACE VIEW agg_by_package AS
SELECT
    COALESCE(NULLIF(TRIM(internet_package), ''), 'Unknown') AS bucket,
    COUNT(*)::INT AS count,
    ROUND(AVG(download_mbps)::NUMERIC, 2) AS avg_download_mbps,
    ROUND(AVG(upload_mbps)::NUMERIC, 2) AS avg_upload_mbps,
    ROUND(AVG(ping_ms)::NUMERIC, 2) AS avg_ping_ms,
    ROUND(AVG(overall_score)::NUMERIC, 2) AS avg_overall_score
FROM speed_tests
GROUP BY 1;

CREATE OR REPLACE VIEW agg_by_region AS
SELECT
    COALESCE(NULLIF(TRIM(detected_region), ''), 'Unknown') AS bucket,
    COUNT(*)::INT AS count,
    ROUND(AVG(download_mbps)::NUMERIC, 2) AS avg_download_mbps,
    ROUND(AVG(ping_ms)::NUMERIC, 2) AS avg_ping_ms,
    ROUND(AVG(overall_score)::NUMERIC, 2) AS avg_overall_score
FROM speed_tests
GROUP BY 1;

CREATE OR REPLACE VIEW agg_by_date AS
SELECT
    COALESCE(test_date, TO_CHAR(timestamp AT TIME ZONE 'UTC', 'YYYY-MM-DD')) AS bucket,
    COUNT(*)::INT AS count,
    ROUND(AVG(download_mbps)::NUMERIC, 2) AS avg_download_mbps,
    ROUND(AVG(upload_mbps)::NUMERIC, 2) AS avg_upload_mbps,
    ROUND(AVG(ping_ms)::NUMERIC, 2) AS avg_ping_ms,
    ROUND(AVG(overall_score)::NUMERIC, 2) AS avg_overall_score
FROM speed_tests
GROUP BY 1
ORDER BY 1;

CREATE OR REPLACE VIEW agg_by_day_of_week AS
SELECT
    day_of_week AS bucket,
    COUNT(*)::INT AS count,
    ROUND(AVG(download_mbps)::NUMERIC, 2) AS avg_download_mbps,
    ROUND(AVG(ping_ms)::NUMERIC, 2) AS avg_ping_ms,
    ROUND(AVG(overall_score)::NUMERIC, 2) AS avg_overall_score
FROM speed_tests
GROUP BY 1
ORDER BY 1;

CREATE OR REPLACE VIEW agg_by_hour AS
SELECT
    hour_utc AS bucket,
    COUNT(*)::INT AS count,
    ROUND(AVG(download_mbps)::NUMERIC, 2) AS avg_download_mbps,
    ROUND(AVG(ping_ms)::NUMERIC, 2) AS avg_ping_ms,
    ROUND(AVG(overall_score)::NUMERIC, 2) AS avg_overall_score
FROM speed_tests
GROUP BY 1
ORDER BY 1;

CREATE OR REPLACE VIEW agg_by_server AS
SELECT
    COALESCE(server_id, server_label, 'Unknown') AS bucket,
    MAX(server_operator) AS server_operator,
    MAX(server_location) AS server_location,
    MAX(server_type) AS server_type,
    COUNT(*)::INT AS count,
    ROUND(AVG(download_mbps)::NUMERIC, 2) AS avg_download_mbps,
    ROUND(AVG(upload_mbps)::NUMERIC, 2) AS avg_upload_mbps,
    ROUND(AVG(ping_ms)::NUMERIC, 2) AS avg_ping_ms,
    ROUND(AVG(overall_score)::NUMERIC, 2) AS avg_overall_score
FROM speed_tests
GROUP BY 1;

CREATE OR REPLACE VIEW agg_by_metric AS
SELECT
    'download_mbps' AS metric,
    COUNT(download_mbps)::INT AS count,
    ROUND(AVG(download_mbps)::NUMERIC, 2) AS avg,
    ROUND(MIN(download_mbps)::NUMERIC, 2) AS min,
    ROUND(MAX(download_mbps)::NUMERIC, 2) AS max
FROM speed_tests
UNION ALL
SELECT 'upload_mbps', COUNT(upload_mbps)::INT,
       ROUND(AVG(upload_mbps)::NUMERIC, 2), ROUND(MIN(upload_mbps)::NUMERIC, 2), ROUND(MAX(upload_mbps)::NUMERIC, 2)
FROM speed_tests
UNION ALL
SELECT 'ping_ms', COUNT(ping_ms)::INT,
       ROUND(AVG(ping_ms)::NUMERIC, 2), ROUND(MIN(ping_ms)::NUMERIC, 2), ROUND(MAX(ping_ms)::NUMERIC, 2)
FROM speed_tests
UNION ALL
SELECT 'jitter_ms', COUNT(jitter_ms)::INT,
       ROUND(AVG(jitter_ms)::NUMERIC, 2), ROUND(MIN(jitter_ms)::NUMERIC, 2), ROUND(MAX(jitter_ms)::NUMERIC, 2)
FROM speed_tests
UNION ALL
SELECT 'packet_loss_pct', COUNT(packet_loss_pct)::INT,
       ROUND(AVG(packet_loss_pct)::NUMERIC, 2), ROUND(MIN(packet_loss_pct)::NUMERIC, 2), ROUND(MAX(packet_loss_pct)::NUMERIC, 2)
FROM speed_tests
UNION ALL
SELECT 'overall_score', COUNT(overall_score)::INT,
       ROUND(AVG(overall_score)::NUMERIC, 2), ROUND(MIN(overall_score)::NUMERIC, 2), ROUND(MAX(overall_score)::NUMERIC, 2)
FROM speed_tests;
