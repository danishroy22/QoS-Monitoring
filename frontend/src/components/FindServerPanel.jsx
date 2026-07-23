import { AnimatePresence, motion } from "framer-motion";
import { Check, Radar } from "lucide-react";

/**
 * Short “Finding Best Server” animation for Mauritius server probes.
 */
export default function FindServerPanel({
  visible,
  probes = [],
  selected = null,
  title = "Finding Best Server…",
}) {
  if (!visible) return null;

  return (
    <motion.div
      className="mu-find-panel"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.35 }}
    >
      <div className="mu-find-head">
        <Radar size={18} className="mu-find-spin" />
        <p>{title}</p>
      </div>

      <div className="mu-find-list">
        <AnimatePresence>
          {probes.map((probe, index) => (
            <motion.div
              key={probe.id}
              className="mu-find-row"
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.18 }}
            >
              <Check size={15} strokeWidth={2.5} className="mu-find-check" />
              <span className="mu-find-name">{probe.name}</span>
              <span className="mu-find-latency">{probe.latency_ms} ms</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {selected && (
        <motion.div
          className="mu-find-selected"
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.15 }}
        >
          <p className="mu-find-selected-label">Selected</p>
          <p className="mu-find-selected-name">{selected.name}</p>
          <p className="mu-find-selected-meta">
            {selected.location}
            {selected.latency_ms != null ? ` · ${selected.latency_ms} ms` : ""}
          </p>
        </motion.div>
      )}
    </motion.div>
  );
}
