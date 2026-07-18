import { motion } from "framer-motion";

/** Elegant pulse / spinner loader for async states. */
export default function LoadingPulse({ label = "Loading…", compact = false }) {
  return (
    <div className={`ui-loader ${compact ? "compact" : ""}`} role="status" aria-live="polite">
      <div className="ui-loader-ring" aria-hidden="true">
        <motion.span
          className="ui-loader-orb"
          animate={{ rotate: 360 }}
          transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
        />
      </div>
      {label && <p className="ui-loader-label">{label}</p>}
    </div>
  );
}

/** Skeleton placeholders for cards while dashboard data loads. */
export function SkeletonCards({ count = 5 }) {
  return (
    <div className="ui-skeleton-grid">
      {Array.from({ length: count }).map((_, i) => (
        <motion.div
          key={i}
          className="ui-skeleton-card"
          initial={{ opacity: 0.4 }}
          animate={{ opacity: [0.4, 0.75, 0.4] }}
          transition={{ duration: 1.6, repeat: Infinity, delay: i * 0.08 }}
        />
      ))}
    </div>
  );
}
