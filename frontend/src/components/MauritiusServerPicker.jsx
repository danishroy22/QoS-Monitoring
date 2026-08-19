import { Server } from "lucide-react";

/**
 * Advanced Settings — Automatic is the default consumer path.
 * Manual catalogue selection remains for testing / administrators.
 */
export default function MauritiusServerPicker({
  servers = [],
  selectedId = "auto",
  onSelect,
  disabled = false,
}) {
  const list = Array.isArray(servers) ? servers : [];
  const selected =
    selectedId === "auto"
      ? null
      : list.find((s) => s.id === selectedId) || null;

  return (
    <details className="mu-advanced" open={selectedId !== "auto"}>
      <summary className="mu-advanced-summary">Advanced Settings</summary>
      <div className="mu-server-dropdown">
        <label htmlFor="mu-server-select" className="mu-server-dropdown-label">
          <Server size={15} strokeWidth={2} />
          Server Selection
        </label>
        <div className="mu-server-dropdown-row">
          <select
            id="mu-server-select"
            value={selectedId}
            disabled={disabled}
            onChange={(e) => onSelect(e.target.value)}
          >
            <option value="auto">Automatic — probe and score Mauritius servers</option>
            {list.map((server) => (
              <option key={server.id} value={server.id}>
                {server.name} — {server.location}
                {server.host ? ` (${server.host})` : ""}
              </option>
            ))}
          </select>
          {selected && (
            <span className={`mu-server-pill ${(selected.status || "Online").toLowerCase()}`}>
              {selected.status || "Online"}
            </span>
          )}
          {selectedId === "auto" && <span className="mu-server-pill auto">Auto</span>}
        </div>
        {selected && (
          <p className="mu-server-dropdown-meta">
            Manual override · {selected.type || "ISP Test Server"}
            {selected.distance_km != null ? ` · ~${selected.distance_km} km` : ""}
          </p>
        )}
        {selectedId === "auto" && (
          <p className="mu-server-dropdown-meta">
            GO identifies your connection, then selects a server from measured latency,
            probe loss, proximity, status, and a small ISP-affinity bonus.
          </p>
        )}
      </div>
    </details>
  );
}
