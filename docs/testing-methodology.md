# Testing Methodology

## Simulator Testing

Purpose: Verify that generated QoS data behaves like realistic broadband measurements.

Tests:

- Confirm normal scenario values remain within expected ranges.
- Confirm congestion increases utilisation, latency, jitter, and packet loss.
- Confirm bandwidth limitation reduces throughput below service tier.
- Confirm outage scenarios reduce availability.
- Confirm generated ground-truth labels match active scenarios.

## Backend Testing

Purpose: Verify reliable ingestion, persistence, and querying.

Tests:

- `GET /health` returns healthy status.
- `POST /api/measurements` validates required fields.
- Invalid QoS values are rejected.
- Valid measurements are stored in PostgreSQL.
- Latest metrics endpoint returns the newest sample per node.
- Historical metrics endpoint respects node, metric, and time range filters.

## ML Testing

Purpose: Evaluate anomaly detection quality.

Metrics:

- Precision
- Recall
- F1-score
- False positive rate
- Detection delay

Evaluation method:

1. Generate labelled datasets using simulator scenarios.
2. Train or fit the anomaly detection model on mostly normal samples.
3. Run the model on mixed normal and degraded samples.
4. Compare predicted anomalies with simulator ground truth.
5. Report results by scenario type.

## AI Testing

Purpose: Verify that generated explanations are useful, consistent, and technically reasonable.

Tests:

- AI output mentions the affected QoS metrics.
- AI output identifies likely causes that match the scenario.
- AI recommendations are relevant to telecom operations.
- Offline fallback produces deterministic explanations for demonstrations.

## Frontend Testing

Purpose: Verify that the dashboard correctly presents live and historical network state.

Tests:

- Health cards display latest QoS values.
- Charts render historical data correctly.
- Incident panel displays detected anomalies.
- Recommendation panel displays AI output.
- Layout remains usable on laptop and mobile screen widths.

## Dissertation Evaluation Evidence

The final report should include:

- Screenshots of normal and degraded network states.
- Graphs comparing QoS metrics across scenarios.
- ML confusion matrix and evaluation metrics.
- Example AI explanations and recommendations.
- Discussion of limitations due to simulation-based data.
