import { formatTime } from "../utils/format";

export default function Header({ health, updatedAt, connected }) {
  const dbOk = health?.database === "connected";

  return (
    <header className="noc-header">
      <div className="brand-block">
        <p className="brand-eyebrow">Telecommunications Operations</p>
        <h1 className="brand-title">Broadband QoS NOC</h1>
        <p className="brand-sub">
          AI-driven monitoring · live metrics · anomaly awareness
        </p>
      </div>

      <div className="header-meta">
        <div className={`link-pill ${connected ? "ok" : "crit"}`}>
          <span className="pulse-dot" aria-hidden="true" />
          {connected ? "API online" : "API offline"}
        </div>
        <div className={`link-pill ${dbOk ? "ok" : "warn"}`}>
          DB {dbOk ? "connected" : health?.database ?? "unknown"}
        </div>
        <div className="link-pill neutral">
          Updated {updatedAt ? formatTime(updatedAt.toISOString()) : "—"}
        </div>
      </div>
    </header>
  );
}
