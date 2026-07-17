import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { fetchRecommendation, runSpeedTest } from "../api/client";
import Speedometer from "./Speedometer";
import TestStageProgress, { TEST_STAGES } from "./TestStageProgress";

/**
 * Refactored speed-test experience.
 * Preserves POST /speedtest + GET /recommendation.
 * Stage UI is choreographed while the real measurement runs.
 */
export default function SpeedTestExperience({
  idleValue = 0,
  onComplete,
  onError,
  autoStart = false,
}) {
  const [phase, setPhase] = useState(autoStart ? "init" : "idle");
  const [gaugeValue, setGaugeValue] = useState(autoStart ? 0 : idleValue);
  const [gaugeLabel, setGaugeLabel] = useState("Mbps");
  const timersRef = useRef([]);
  const runIdRef = useRef(0);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onCompleteRef.current = onComplete;
    onErrorRef.current = onError;
  }, [onComplete, onError]);

  useEffect(() => {
    if (phase === "idle") {
      setGaugeValue(idleValue || 0);
    }
  }, [idleValue, phase]);

  const clearTimers = () => {
    timersRef.current.forEach((id) => {
      window.clearTimeout(id);
      window.clearInterval(id);
    });
    timersRef.current = [];
  };

  const schedule = (fn, ms) => {
    const id = window.setTimeout(fn, ms);
    timersRef.current.push(id);
    return id;
  };

  const startTest = async (runId) => {
    clearTimers();
    setPhase("init");
    setGaugeValue(0);
    setGaugeLabel("Mbps");
    onErrorRef.current?.(null);

    const stagePlan = [
      { id: "init", at: 0 },
      { id: "server", at: 700 },
      { id: "ping", at: 1500 },
      { id: "download", at: 2500 },
      { id: "upload", at: 5000 },
    ];

    stagePlan.forEach(({ id, at }) => {
      schedule(() => {
        if (runIdRef.current !== runId) return;
        setPhase(id);
      }, at);
    });

    const needleTimer = window.setInterval(() => {
      if (runIdRef.current !== runId) return;
      setPhase((current) => {
        if (current === "download") {
          setGaugeLabel("Mbps ↓");
          setGaugeValue((v) => Math.min(180, v + 4 + Math.random() * 9));
        } else if (current === "upload") {
          setGaugeLabel("Mbps ↑");
          setGaugeValue((v) => Math.max(8, v * 0.92 + Math.random() * 6));
        } else if (current === "ping") {
          setGaugeLabel("ms");
          setGaugeValue(8 + Math.random() * 20);
        }
        return current;
      });
    }, 180);
    timersRef.current.push(needleTimer);

    try {
      const result = await runSpeedTest(true);
      if (runIdRef.current !== runId) return;

      window.clearInterval(needleTimer);
      setPhase("calculate");
      setGaugeLabel("Mbps");
      setGaugeValue(result?.result?.download_mbps ?? 0);

      await new Promise((resolve) => schedule(resolve, 600));
      if (runIdRef.current !== runId) return;

      setPhase("ai");
      let recommendation = null;
      try {
        recommendation = await fetchRecommendation();
      } catch {
        recommendation = null;
      }
      if (runIdRef.current !== runId) return;

      setPhase("results");
      await new Promise((resolve) => schedule(resolve, 450));
      if (runIdRef.current !== runId) return;

      setPhase("done");
      onCompleteRef.current?.({
        speedTest: result,
        recommendation,
      });
    } catch (err) {
      if (runIdRef.current !== runId) return;
      clearTimers();
      setPhase("idle");
      onErrorRef.current?.(err instanceof Error ? err.message : String(err));
    }
  };

  useEffect(() => {
    if (!autoStart) return undefined;

    const runId = ++runIdRef.current;
    startTest(runId);

    return () => {
      // Invalidate this run on unmount / StrictMode remount.
      if (runIdRef.current === runId) {
        runIdRef.current += 1;
      }
      clearTimers();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoStart]);

  const handleGo = () => {
    const runId = ++runIdRef.current;
    startTest(runId);
  };

  return (
    <div className="sq-test-experience">
      <AnimatePresence mode="wait">
        <motion.div
          key={phase === "idle" || phase === "done" ? "ready" : "running"}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.35 }}
          className="sq-test-layout"
        >
          <Speedometer
            value={gaugeValue}
            label={gaugeLabel}
            phase={phase}
            onGo={handleGo}
            disabled={phase !== "idle" && phase !== "done"}
          />
          {phase !== "idle" && phase !== "done" && (
            <TestStageProgress currentStageId={normalizeStage(phase)} />
          )}
        </motion.div>
      </AnimatePresence>
      {(phase === "idle" || phase === "done") && (
        <p className="sq-test-hint">
          Tap GO on the speedometer to run a real SmartQoS measurement.
        </p>
      )}
      <p className="sq-stage-caption">
        {TEST_STAGES.find((s) => s.id === normalizeStage(phase))?.label ||
          (phase === "done" ? "Ready for another test" : "Ready when you are")}
      </p>
    </div>
  );
}

function normalizeStage(phase) {
  if (phase === "done") return "results";
  return phase;
}
