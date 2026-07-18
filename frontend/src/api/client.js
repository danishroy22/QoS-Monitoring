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

export function fetchHistory(limit = 50) {
  return request(`/history?limit=${limit}`);
}

export function fetchRecommendation() {
  return request("/recommendation");
}

export function fetchIsp() {
  return request("/isp");
}
