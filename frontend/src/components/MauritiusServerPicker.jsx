import { Server } from "lucide-react";

/**
 * Compact Mauritius server dropdown — loaded from backend JSON config.
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
    <div className="mu-server-dropdown">
      <label htmlFor="mu-server-select" className="mu-server-dropdown-label">
        <Server size={15} strokeWidth={2} />
        Test server
      </label>
      <div className="mu-server-dropdown-row">
        <select
          id="mu-server-select"
          value={selectedId}
          disabled={disabled}
          onChange={(e) => onSelect(e.target.value)}
        >
          <option value="auto">Auto — Best Mauritius server</option>
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
        {selectedId === "auto" && (
          <span className="mu-server-pill auto">Auto</span>
        )}
      </div>
      {selected && (
        <p className="mu-server-dropdown-meta">
          {selected.type || "ISP Test Server"}
          {selected.distance_km != null ? ` · ~${selected.distance_km} km` : ""}
        </p>
      )}
      {selectedId === "auto" && (
        <p className="mu-server-dropdown-meta">
          Lowest simulated latency will be selected when you press GO
        </p>
      )}
    </div>
  );
}
