/**
 * SmartQoS API client.
 * Uses VITE_API_BASE when set (recommended), otherwise same-origin / Vite proxy.
 */
const API_BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  let response;
  try {
    response = await fetch(url, {
      headers: {
        Accept: "application/json",
        ...(options.headers ?? {}),
      },
      ...options,
    });
  } catch (err) {
    throw new Error(
      `Cannot reach API at ${url}. Start the backend with: python scripts/run_backend.py`
    );
  }

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // keep status text
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return response.json();
}

export function getApiBase() {
  return API_BASE || "(vite proxy / same origin)";
}

export function fetchHealth() {
  return request("/health");
}

export function fetchDashboard() {
  return request("/dashboard");
}

export function runSpeedTest(quick = false, serverId = null) {
  return request("/speedtest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ quick, server_id: serverId || undefined }),
  });
}

export function fetchSpeedServers() {
  return request("/speedtest/servers");
}

export function findBestServer(ispName = null) {
  const qs = ispName ? `?isp_name=${encodeURIComponent(ispName)}` : "";
  return request(`/speedtest/find-server${qs}`, { method: "POST" });
}

export function identifyConnection() {
  return request("/speedtest/identify", { method: "POST" });
}

export function measureServerPhase(serverId = null) {
  const qs = serverId ? `?server_id=${encodeURIComponent(serverId)}` : "";
  return request(`/speedtest/measure/server${qs}`, { method: "POST" });
}

export function measureLatencyPhase(quick = false, serverId = null) {
  const params = new URLSearchParams({ quick: quick ? "true" : "false" });
  if (serverId) params.set("server_id", serverId);
  return request(`/speedtest/measure/latency?${params}`, {
    method: "POST",
  });
}

export function completeSpeedTest(payload) {
  return request("/speedtest/complete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function consumeSseStream(path, onEvent, { signal, quick = false, serverId = null } = {}) {
  const params = new URLSearchParams();
  if (quick) params.set("quick", "true");
  if (serverId) params.set("server_id", serverId);
  const qs = params.toString() ? `?${params}` : "";
  const url = `${API_BASE}${path}${qs}`;
  let response;
  try {
    response = await fetch(url, {
      signal,
      headers: { Accept: "text/event-stream" },
    });
  } catch (err) {
    if (err?.name === "AbortError") throw err;
    throw new Error(
      `Cannot reach API at ${url}. Start the backend with: python scripts/run_backend.py`
    );
  }

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalEvent = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data: ")) continue;
      const data = JSON.parse(line.slice(6));
      onEvent(data);
      if (data.done) finalEvent = data;
    }
  }

  return finalEvent;
}

export function streamDownloadPhase(onEvent, options = {}) {
  return consumeSseStream("/speedtest/stream/download", onEvent, options);
}

export function streamUploadPhase(onEvent, options = {}) {
  return consumeSseStream("/speedtest/stream/upload", onEvent, options);
}

export function fetchMeasurementConfig() {
  return request("/speedtest/config");
}

export function fetchAggregations(by = "isp", days = 30, metric = null) {
  const params = new URLSearchParams({ by, days: String(days) });
  if (metric) params.set("metric", metric);
  return request(`/aggregations?${params}`);
}

export function fetchHistory(limit = 50) {
  return request(`/history?limit=${limit}`);
}

export function fetchRecommendation() {
  return request("/recommendation");
}

export function fetchIsp() {
  return request("/isp");
}

export function fetchMonitoringStatus() {
  return request("/monitoring/status");
}

export function startMonitoring(payload) {
  return request("/monitoring/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function stopMonitoring() {
  return request("/monitoring/stop", { method: "POST" });
}

export function fetchPackages() {
  return request("/packages");
}

export function fetchAdminPackages(activeOnly = false) {
  return request(`/admin/packages?active_only=${activeOnly ? "true" : "false"}`);
}

export function createAdminPackage(payload) {
  return request("/admin/packages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateAdminPackage(packageId, payload) {
  return request(`/admin/packages/${packageId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function deactivateAdminPackage(packageId) {
  return request(`/admin/packages/${packageId}`, { method: "DELETE" });
}

export function fetchAdminDashboard(days = 90) {
  return request(`/admin/dashboard?days=${days}`);
}

export function fetchAdminIspAnalytics(days = 90) {
  return request(`/admin/isp-analytics?days=${days}`);
}

export function fetchAdminComparison(filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    params.set(key, String(value));
  });
  const qs = params.toString();
  return request(`/admin/comparison${qs ? `?${qs}` : ""}`);
}

export function fetchAdminPeakHours(filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    params.set(key, String(value));
  });
  const qs = params.toString();
  return request(`/admin/peak-hours${qs ? `?${qs}` : ""}`);
}

export function fetchAdminBenchmarks(days = 90, profileId = null) {
  const params = new URLSearchParams({ days: String(days) });
  if (profileId) params.set("profile_id", profileId);
  return request(`/admin/benchmarks?${params}`);
}

export function updateAdminBenchmarks(profile, days = 90) {
  return request(`/admin/benchmarks?days=${days}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
}

export function fetchAdminBenchmarkProfiles() {
  return request("/admin/benchmark-profiles");
}

export function setActiveAdminBenchmarkProfile(profileId) {
  return request(`/admin/benchmark-profiles/active?profile_id=${encodeURIComponent(profileId)}`, {
    method: "PUT",
  });
}

export function updateAdminBenchmarkProfile(profileId, payload) {
  return request(`/admin/benchmark-profiles/${encodeURIComponent(profileId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function fetchAdminHistory(granularity = "daily", days = 90) {
  return request(`/admin/history?granularity=${encodeURIComponent(granularity)}&days=${days}`);
}

export function fetchAdminPackagePerformance(days = 90) {
  return request(`/admin/package-performance?days=${days}`);
}

export function fetchAdminHeatmap(days = 90) {
  return request(`/admin/heatmap?days=${days}`);
}

export function fetchAdminQosMap(filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    params.set(key, String(value));
  });
  const qs = params.toString();
  return request(`/admin/map${qs ? `?${qs}` : ""}`);
}

export function fetchAdminAi(days = 90) {
  return request(`/admin/ai/isp-analysis?days=${days}`);
}

export function fetchAdminAiFacts(days = 90) {
  return request(`/admin/ai/facts?days=${days}`);
}

export function askAdminAi(question, days = 90) {
  return request("/admin/ai/ask?days=" + days, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}

export async function downloadAdminReport(days = 90) {
  const url = `${API_BASE}/admin/report?days=${days}`;
  let response;
  try {
    response = await fetch(url, { headers: { Accept: "application/pdf" } });
  } catch {
    throw new Error(
      `Cannot reach API at ${url}. Start the backend with: python scripts/run_backend.py`
    );
  }
  if (!response.ok) {
    throw new Error(`Report failed: ${response.status} ${response.statusText}`);
  }
  const blob = await response.blob();
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = "SmartQoS-Administrator-QoS-Report.pdf";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(href);
}
