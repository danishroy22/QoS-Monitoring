import { motion } from "framer-motion";
import { formatNumber, ratingClass } from "../utils/format";
import AiAssistant from "./AiAssistant";

/**
 * Post-test Results view. Reuses AiAssistant for AI Network Analysis.
 */
export default function ResultsView({
  speedTest,
  recommendation,
  onBack,
  onRetest,
}) {
  const result = speedTest?.result;
  const health = speedTest?.health;
  const score = health?.overall_score ?? result?.overall_score;
  const rating = health?.overall_rating ?? result?.overall_rating ?? "—";

  const cards = [
    { label: "Download Speed", value: result?.download_mbps, unit: "Mbps", accent: "down" },
    { label: "Upload Speed", value: result?.upload_mbps, unit: "Mbps", accent: "up" },
    { label: "Ping", value: result?.ping_ms, unit: "ms", accent: "ping" },
    { label: "Jitter", value: result?.jitter_ms, unit: "ms", accent: "jitter" },
    { label: "Packet Loss", value: result?.packet_loss_pct, unit: "%", accent: "loss", digits: 2 },
  ];

  return (
    <motion.section
      className="sq-results"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4 }}
    >
      <div className="sq-results-head">
        <div>
          <p className="iq-eyebrow">SmartQoS Results</p>
          <h2>Test Complete</h2>
        </div>
        <div className="sq-results-actions">
          <button type="button" className="sq-btn ghost" onClick={onBack}>
            Dashboard
          </button>
          <button type="button" className="sq-btn primary" onClick={onRetest}>
            Run Again
          </button>
        </div>
      </div>

      <div className="sq-score-hero glass">
        <p className="iq-score-label">Overall Network Score</p>
        <motion.p
          className={`iq-score-value ${ratingClass(rating)}`}
          initial={{ scale: 0.86, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 120, damping: 12 }}
        >
          {score != null ? `${score}/100` : "—"}
        </motion.p>
        <p className={`iq-score-rating ${ratingClass(rating)}`}>
          Connection Quality · {rating}
        </p>
        {(result?.isp_name || result?.public_ip) && (
          <p className="sq-results-isp">
            {[result?.isp_name, result?.public_ip].filter(Boolean).join(" · ")}
          </p>
        )}
      </div>

      <div className="sq-result-grid">
        {cards.map((card, index) => (
          <motion.article
            key={card.label}
            className={`sq-result-card glass accent-${card.accent}`}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 * index }}
          >
            <p className="iq-metric-label">{card.label}</p>
            <p className="iq-metric-value">
              {formatNumber(card.value, card.digits ?? 1)}
              <span>{card.unit}</span>
            </p>
          </motion.article>
        ))}
      </div>

      {health?.metrics && (
        <div className="iq-panel glass compact">
          <div className="iq-panel-head">
            <h2>QoS Breakdown</h2>
            <p>Per-metric quality rating</p>
          </div>
          <div className="iq-breakdown">
            {health.metrics.map((m) => (
              <div key={m.name} className="iq-breakdown-row">
                <span>{m.name}</span>
                <span className="mono">
                  {m.value == null ? "—" : `${formatNumber(m.value)} ${m.unit}`}
                </span>
                <span className={`iq-pill ${ratingClass(m.rating)}`}>
                  {m.rating} · {m.score}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <AiAssistant recommendation={recommendation} loading={false} />
    </motion.section>
  );
}
