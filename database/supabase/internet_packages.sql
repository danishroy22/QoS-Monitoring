-- Phase 4 — ISP internet packages + fulfilment columns (Supabase)
-- Run after database/supabase/speed_tests.sql (or alongside it).

CREATE TABLE IF NOT EXISTS internet_packages (
    id BIGSERIAL PRIMARY KEY,
    isp_name VARCHAR(120) NOT NULL,
    package_name VARCHAR(120) NOT NULL,
    advertised_download_mbps DOUBLE PRECISION NOT NULL,
    advertised_upload_mbps DOUBLE PRECISION NOT NULL,
    notes TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_package_isp_name UNIQUE (isp_name, package_name)
);

CREATE INDEX IF NOT EXISTS idx_internet_packages_isp ON internet_packages (isp_name);
CREATE INDEX IF NOT EXISTS idx_internet_packages_active ON internet_packages (active);

ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS package_id INTEGER;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS advertised_download_mbps DOUBLE PRECISION;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS advertised_upload_mbps DOUBLE PRECISION;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS download_fulfilment_pct DOUBLE PRECISION;
ALTER TABLE speed_tests ADD COLUMN IF NOT EXISTS upload_fulfilment_pct DOUBLE PRECISION;

CREATE INDEX IF NOT EXISTS idx_speed_tests_package_id ON speed_tests (package_id);

-- No seed rows: commercial packages must be entered by an administrator.
