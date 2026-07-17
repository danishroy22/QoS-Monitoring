import { formatDateTime, formatNumber, ratingClass } from "../utils/format";

export default function HistoryTable({ history }) {
  const rows = Array.isArray(history) ? [...history].reverse() : [];

  return (
    <section className="iq-panel glass">
      <div className="iq-panel-head">
        <h2>History</h2>
        <p>Stored measurement results</p>
      </div>
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
                  <td>{formatNumber(row.download_mbps)} Mbps</td>
                  <td>{formatNumber(row.upload_mbps)} Mbps</td>
                  <td>{formatNumber(row.ping_ms)} ms</td>
                  <td>{formatNumber(row.packet_loss_pct, 2)}%</td>
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
    </section>
  );
}
