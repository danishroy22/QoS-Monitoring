/**
 * API client for the FastAPI QoS monitoring backend.
 * Uses the Vite proxy in development (/api -> localhost:8000).
 */

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      Accept: "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // keep status text
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return null;
  }
  return response.json();
}

export function fetchHealth() {
  return request("/health");
}

export function fetchLatestMetrics() {
  return request("/api/metrics/latest");
}

export function fetchHistory(nodeCode, metric = "latency_ms", limit = 120) {
  const params = new URLSearchParams({
    node_code: nodeCode,
    metric,
    limit: String(limit),
  });
  return request(`/api/metrics/history?${params}`);
}

export function fetchAnomalies({ activeOnly = true, limit = 50 } = {}) {
  const params = new URLSearchParams({
    active_only: String(activeOnly),
    limit: String(limit),
  });
  return request(`/api/anomalies?${params}`);
}

export function fetchRecommendations(limit = 20) {
  const params = new URLSearchParams({ limit: String(limit) });
  return request(`/api/recommendations?${params}`);
}

export function fetchNodes() {
  return request("/api/nodes");
}

export function runAnalysis({ anomalyId, nodeCode, includeRecentHistory = true } = {}) {
  const body = {
    include_recent_history: includeRecentHistory,
  };
  if (anomalyId != null) body.anomaly_id = anomalyId;
  if (nodeCode) body.node_code = nodeCode;
  return request("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function runAnomalyDetection(limit = 500) {
  const params = new URLSearchParams({
    limit: String(limit),
    only_unscored: "true",
  });
  return request(`/api/anomalies/run?${params}`, { method: "POST" });
}
