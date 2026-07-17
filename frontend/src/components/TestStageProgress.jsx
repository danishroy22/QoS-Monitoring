import { motion } from "framer-motion";

export const TEST_STAGES = [
  { id: "init", label: "Initializing" },
  { id: "server", label: "Selecting Best Server" },
  { id: "ping", label: "Testing Ping" },
  { id: "download", label: "Testing Download Speed" },
  { id: "upload", label: "Testing Upload Speed" },
  { id: "calculate", label: "Calculating Results" },
  { id: "ai", label: "Generating AI Analysis" },
  { id: "results", label: "Displaying Results" },
];

/**
 * Stage pipeline shown during an active SmartQoS speed test.
 */
export default function TestStageProgress({ currentStageId }) {
  const currentIndex = Math.max(
    0,
    TEST_STAGES.findIndex((s) => s.id === currentStageId)
  );

  return (
    <div className="sq-stages" role="list" aria-label="Speed test stages">
      {TEST_STAGES.map((stage, index) => {
        const state =
          index < currentIndex ? "done" : index === currentIndex ? "active" : "pending";
        return (
          <motion.div
            key={stage.id}
            className={`sq-stage ${state}`}
            role="listitem"
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.04 }}
          >
            <span className="sq-stage-dot">
              {state === "done" ? "✓" : state === "active" ? "" : index + 1}
              {state === "active" && <span className="sq-stage-pulse" />}
            </span>
            <span className="sq-stage-label">{stage.label}</span>
            {state === "active" && (
              <motion.span
                className="sq-stage-bar"
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ duration: 1.1, ease: "easeInOut", repeat: Infinity }}
              />
            )}
          </motion.div>
        );
      })}
    </div>
  );
}
