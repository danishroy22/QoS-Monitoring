import { motion } from "framer-motion";

/** Horizontal stage rail under the premium speedometer. */
export const TEST_STAGES = [
  { id: "init", label: "Initializing" },
  { id: "server", label: "Finding Server" },
  { id: "download", label: "Download" },
  { id: "upload", label: "Upload" },
  { id: "ping", label: "Latency" },
  { id: "jitter", label: "Jitter" },
  { id: "ai", label: "Analysis" },
];

export default function TestStageProgress({ currentStageId }) {
  const currentIndex = Math.max(
    0,
    TEST_STAGES.findIndex((s) => s.id === currentStageId)
  );

  return (
    <div className="sq-stage-rail" role="list" aria-label="Speed test stages">
      <div className="sq-stage-track">
        <motion.div
          className="sq-stage-fill"
          initial={false}
          animate={{
            width: `${(currentIndex / Math.max(TEST_STAGES.length - 1, 1)) * 100}%`,
          }}
          transition={{ type: "spring", stiffness: 60, damping: 18 }}
        />
      </div>
      <div className="sq-stage-steps">
        {TEST_STAGES.map((stage, index) => {
          const state =
            index < currentIndex ? "done" : index === currentIndex ? "active" : "pending";
          return (
            <motion.div
              key={stage.id}
              className={`sq-stage-step ${state}`}
              role="listitem"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.04 }}
            >
              <span className="sq-stage-dot">
                {state === "done" ? "✓" : index + 1}
                {state === "active" && <span className="sq-stage-pulse" />}
              </span>
              <span className="sq-stage-label">{stage.label}</span>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
