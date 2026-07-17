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

export function runSpeedTest(quick = false) {
  return request("/speedtest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ quick }),
  });
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
