import { formatDateTime, formatNumber, ratingClass } from "../utils/format";
import GlassCard from "./ui/GlassCard";
import PanelHeader from "./ui/PanelHeader";

export default function HistoryTable({ history }) {
  const rows = Array.isArray(history) ? [...history].reverse() : [];

  return (
    <GlassCard className="iq-panel" delay={0.16}>
      <PanelHeader title="Measurement History" subtitle="Stored speed test results" />
      {rows.length === 0 ? (
        <p className="iq-empty">No history yet.</p>
      ) : (
        <div className="iq-table-wrap">
          <table className="iq-table">
            <thead>
              <tr>
                <th>When</th>
                <th>Down</th>
                <th>Up</th>
                <th>Ping</th>
                <th>Loss</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>{formatDateTime(row.timestamp)}</td>
                  <td className="mono">{formatNumber(row.download_mbps)}</td>
                  <td className="mono">{formatNumber(row.upload_mbps)}</td>
                  <td className="mono">{formatNumber(row.ping_ms)}</td>
                  <td className="mono">{formatNumber(row.packet_loss_pct, 2)}%</td>
                  <td>
                    <span className={`iq-pill ${ratingClass(row.overall_rating)}`}>
                      {row.overall_score ?? "—"} {row.overall_rating || ""}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </GlassCard>
  );
}
