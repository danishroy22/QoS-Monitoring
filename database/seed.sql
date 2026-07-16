INSERT INTO network_nodes (
    node_code,
    region,
    access_technology,
    service_tier_mbps,
    subscriber_count,
    baseline_latency_ms,
    max_bandwidth_mbps
) VALUES
    ('BNG-DXB-001', 'Dubai North', 'FTTH', 100.00, 250, 22.00, 1000.00),
    ('BNG-DXB-002', 'Dubai South', 'FTTH', 250.00, 180, 18.00, 1500.00),
    ('DSL-SHJ-001', 'Sharjah Central', 'DSL', 50.00, 320, 35.00, 500.00),
    ('FWA-AUH-001', 'Abu Dhabi Suburban', 'Fixed Wireless', 100.00, 140, 28.00, 700.00)
ON CONFLICT (node_code) DO NOTHING;
