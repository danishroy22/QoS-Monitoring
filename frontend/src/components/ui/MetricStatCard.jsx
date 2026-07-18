import { motion } from "framer-motion";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { formatNumber, ratingClass } from "../../utils/format";

const TREND = {
  up: { Icon: ArrowUpRight, className: "trend-up" },
  down: { Icon: ArrowDownRight, className: "trend-down" },
  flat: { Icon: Minus, className: "trend-flat" },
};

/**
 * Dashboard statistic card: icon, large value, label, rating, optional trend.
 */
export default function MetricStatCard({
  label,
  value,
  unit,
  rating,
  icon: Icon,
  accent = "primary",
  trend = "flat",
  digits = 1,
  delay = 0,
}) {
  const { Icon: TrendIcon, className: trendClass } = TREND[trend] || TREND.flat;

  return (
    <motion.article
      className={`metric-stat glass ui-card-hover accent-${accent}`}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -4 }}
    >
      <div className="metric-stat-top">
        {Icon && (
          <span className="metric-stat-icon" aria-hidden="true">
            <Icon size={18} strokeWidth={1.75} />
          </span>
        )}
        <span className={`metric-stat-trend ${trendClass}`} aria-hidden="true">
          <TrendIcon size={14} strokeWidth={2.25} />
        </span>
      </div>
      <p className="metric-stat-label">{label}</p>
      <p className="metric-stat-value">
        {formatNumber(value, digits)}
        <span>{unit}</span>
      </p>
      <p className={`metric-stat-rating ${ratingClass(rating)}`}>{rating || "—"}</p>
    </motion.article>
  );
}
