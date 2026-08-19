import { AnimatePresence, motion } from "framer-motion";
import { Check, Radar } from "lucide-react";

/**
 * Identify-connection + find-best-server overlay for the GO flow.
 */
export default function FindServerPanel({
  visible,
  identity = null,
  identityReady = false,
  probes = [],
  selected = null,
}) {
  if (!visible) return null;

  const ispLabel = identity?.isp_name || "Network operator";
  const regionBits = [identity?.detected_city, identity?.detected_region]
    .filter(Boolean)
    .join(", ");

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
        <p>
          {!identityReady
            ? "Finding your connection…"
            : selected
              ? "Test server selected"
              : "Finding best test server…"}
        </p>
      </div>

      <div className="mu-find-list">
        <div className={`mu-find-row ${identityReady ? "" : "is-pending"}`}>
          {identityReady ? (
            <Check size={15} strokeWidth={2.5} className="mu-find-check" />
          ) : (
            <span className="mu-find-dot" />
          )}
          <span className="mu-find-name">
            {identityReady
              ? identity?.isp_name
                ? `ISP identified — ${ispLabel}`
                : "Connection lookup incomplete"
              : "Identify connection"}
          </span>
          <span className="mu-find-latency">
            {identityReady && identity?.public_ip ? identity.public_ip : ""}
          </span>
        </div>
        {identityReady && regionBits ? (
          <p className="mu-find-note">
            Approximate location: {regionBits}. IP-based ISP is network context, not a
            guaranteed operator record.
          </p>
        ) : null}

        <AnimatePresence>
          {probes.map((probe, index) => (
            <motion.div
              key={probe.id}
              className={`mu-find-row ${probe.reachable === false ? "is-miss" : ""}`}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: Math.min(index * 0.05, 0.4) }}
            >
              <Check size={15} strokeWidth={2.5} className="mu-find-check" />
              <span className="mu-find-name">
                {probe.name}
                {probe.location ? ` — ${probe.location}` : ""}
              </span>
              <span className="mu-find-latency">
                {probe.latency_ms != null ? `${probe.latency_ms} ms` : "unreachable"}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {selected && (
        <motion.div
          className="mu-find-selected"
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
        >
          <p className="mu-find-selected-label">Selected</p>
          <p className="mu-find-selected-name">
            {selected.name}
            {selected.location ? ` — ${selected.location}` : ""}
          </p>
          <p className="mu-find-selected-meta">
            {selected.latency_ms != null ? `${selected.latency_ms} ms` : "fallback"}
            {selected.score != null ? ` · score ${Number(selected.score).toFixed(0)}` : ""}
          </p>
        </motion.div>
      )}
    </motion.div>
  );
}
