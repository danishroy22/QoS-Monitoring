import { motion } from "framer-motion";
import {
  Activity,
  ArrowDownToLine,
  ArrowUpFromLine,
  RotateCcw,
  ShieldCheck,
  Wifi,
  Zap,
} from "lucide-react";
import { formatDateTime, formatNumber, ratingClass } from "../utils/format";
import AiAssistant from "./AiAssistant";
import GlassCard from "./ui/GlassCard";
import PanelHeader from "./ui/PanelHeader";
import SoftButton from "./ui/SoftButton";

const CARD_META = [
  {
    label: "Download Speed",
    key: "download_mbps",
    unit: "Mbps",
    accent: "down",
    icon: ArrowDownToLine,
  },
  {
    label: "Upload Speed",
    key: "upload_mbps",
    unit: "Mbps",
    accent: "up",
    icon: ArrowUpFromLine,
  },
  { label: "Ping", key: "ping_ms", unit: "ms", accent: "ping", icon: Zap },
  { label: "Jitter", key: "jitter_ms", unit: "ms", accent: "jitter", icon: Activity },
  {
    label: "Packet Loss",
    key: "packet_loss_pct",
    unit: "%",
    accent: "loss",
    icon: Wifi,
    digits: 2,
  },
];

/**
 * Post-test professional network quality report.
 */
export default function ResultsView({
  speedTest,
  recommendation,
  history = [],
  onBack,
  onRetest,
}) {
  const result = speedTest?.result;
  const health = speedTest?.health;
  const score = health?.overall_score ?? result?.overall_score;
  const rating = health?.overall_rating ?? result?.overall_rating ?? "—";
  const recent = Array.isArray(history) ? [...history].reverse().slice(0, 5) : [];

  return (
    <motion.section
      className="sq-results"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="sq-results-head">
        <div>
          <p className="iq-eyebrow">SmartQoS Report</p>
          <h2>Test Complete</h2>
        </div>
        <div className="sq-results-actions">
          <SoftButton variant="ghost" onClick={onBack}>
            Dashboard
          </SoftButton>
          <SoftButton variant="primary" onClick={onRetest}>
            <RotateCcw size={16} />
            Run Again
          </SoftButton>
        </div>
      </div>

      <GlassCard className="sq-score-hero" hover={false} delay={0.05}>
        <p className="iq-score-label">Overall Network Score</p>
        <motion.p
          className={`iq-score-value ${ratingClass(rating)}`}
          initial={{ scale: 0.88, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 120, damping: 14 }}
        >
          {score != null ? `${score}/100` : "—"}
        </motion.p>
        <span className={`sq-quality-badge ${ratingClass(rating)}`}>
          <ShieldCheck size={16} />
          Connection Quality · {rating}
        </span>
        {(result?.isp_name || result?.public_ip) && (
          <p className="sq-results-isp">
            {[result?.isp_name, result?.public_ip].filter(Boolean).join(" · ")}
          </p>
        )}
      </GlassCard>

      <div className="sq-result-grid">
        {CARD_META.map((card, index) => {
          const Icon = card.icon;
          return (
            <GlassCard
              key={card.label}
              as="article"
              className={`sq-result-card accent-${card.accent}`}
              delay={0.08 + index * 0.04}
            >
              <div className="sq-result-card-icon">
                <Icon size={16} strokeWidth={1.85} />
              </div>
              <p className="iq-metric-label">{card.label}</p>
              <p className="iq-metric-value">
                {formatNumber(result?.[card.key], card.digits ?? 1)}
                <span>{card.unit}</span>
              </p>
            </GlassCard>
          );
        })}
      </div>

      {health?.metrics && (
        <GlassCard className="iq-panel compact" delay={0.2}>
          <PanelHeader title="QoS Breakdown" subtitle="Per-metric quality rating" />
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
        </GlassCard>
      )}

      <AiAssistant recommendation={recommendation} loading={false} />

      {recent.length > 0 && (
        <GlassCard className="iq-panel" delay={0.28}>
          <PanelHeader
            title="Recent History"
            subtitle="Latest stored measurements for comparison"
          />
          <div className="sq-history-preview">
            {recent.map((row) => (
              <div key={row.id} className="sq-history-row">
                <span>{formatDateTime(row.timestamp)}</span>
                <span className="mono">{formatNumber(row.download_mbps)} ↓</span>
                <span className="mono">{formatNumber(row.upload_mbps)} ↑</span>
                <span className="mono">{formatNumber(row.ping_ms)} ms</span>
                <span className={`iq-pill ${ratingClass(row.overall_rating)}`}>
                  {row.overall_score ?? "—"}
                </span>
              </div>
            ))}
          </div>
        </GlassCard>
      )}
    </motion.section>
  );
}
