import { Package, Server } from "lucide-react";

/**
 * Advanced Settings — Automatic is the default consumer path.
 * Manual catalogue selection remains for testing / administrators.
 * Optional ISP package selection enables advertised-speed fulfilment %.
 */
export default function MauritiusServerPicker({
  servers = [],
  selectedId = "auto",
  onSelect,
  packages = [],
  selectedPackageId = "",
  onSelectPackage,
  disabled = false,
}) {
  const list = Array.isArray(servers) ? servers : [];
  const packageList = Array.isArray(packages) ? packages : [];
  const selected =
    selectedId === "auto"
      ? null
      : list.find((s) => s.id === selectedId) || null;
  const selectedPackage =
    selectedPackageId === "" || selectedPackageId == null
      ? null
      : packageList.find((p) => String(p.id) === String(selectedPackageId)) || null;

  const open = selectedId !== "auto" || Boolean(selectedPackageId);

  return (
    <details className="mu-advanced" open={open}>
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

        <label htmlFor="mu-package-select" className="mu-server-dropdown-label" style={{ marginTop: "1rem" }}>
          <Package size={15} strokeWidth={2} />
          Internet Package (optional)
        </label>
        <div className="mu-server-dropdown-row">
          <select
            id="mu-package-select"
            value={selectedPackageId || ""}
            disabled={disabled || !onSelectPackage}
            onChange={(e) => onSelectPackage?.(e.target.value)}
          >
            <option value="">Not specified — fulfilment % skipped</option>
            {packageList.map((pkg) => (
              <option key={pkg.id} value={String(pkg.id)}>
                {pkg.isp_name} · {pkg.package_name} ({pkg.advertised_download_mbps}/
                {pkg.advertised_upload_mbps} Mbps)
              </option>
            ))}
          </select>
        </div>
        {selectedPackage ? (
          <p className="mu-server-dropdown-meta">
            Fulfilment compares measured speed to advertised{" "}
            {selectedPackage.advertised_download_mbps}↓ / {selectedPackage.advertised_upload_mbps}↑ Mbps.
          </p>
        ) : (
          <p className="mu-server-dropdown-meta">
            Packages are configured in the Admin portal. None are hard-coded.
          </p>
        )}
      </div>
    </details>
  );
}
