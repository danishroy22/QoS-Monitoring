import { Check } from "lucide-react";
import { motion } from "framer-motion";

/** Horizontal stage rail under the premium speedometer. */
export const TEST_STAGES = [
  { id: "init", label: "Initializing" },
  { id: "server", label: "Finding Best Server" },
  { id: "download", label: "Download" },
  { id: "upload", label: "Upload" },
  { id: "ping", label: "Ping" },
  { id: "ai", label: "AI Analysis" },
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
          transition={{ type: "spring", stiffness: 55, damping: 20 }}
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
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.045, duration: 0.35 }}
            >
              <span className="sq-stage-dot" aria-hidden="true">
                {state === "done" ? <Check size={14} strokeWidth={2.5} /> : null}
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
