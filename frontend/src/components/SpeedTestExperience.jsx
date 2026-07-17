import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import {
  completeSpeedTest,
  fetchRecommendation,
  measureLatencyPhase,
  measureServerPhase,
  streamDownloadPhase,
  streamUploadPhase,
} from "../api/client";
import Speedometer from "./Speedometer";
import TestStageProgress, { TEST_STAGES } from "./TestStageProgress";

const SETTLE_MS = 2800;
const MIN_INIT_MS = 1200;
const MIN_SERVER_MS = 1800;

function wait(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

async function waitMin(startedAt, minMs) {
  const remaining = minMs - (Date.now() - startedAt);
  if (remaining > 0) await wait(remaining);
}

function assertActive(runId, runIdRef) {
  if (runIdRef.current !== runId) {
    const err = new Error("cancelled");
    err.name = "AbortError";
    throw err;
  }
}

/**
 * Phased speed-test experience driven by real backend measurements.
 * Order: init → server → download → upload → latency → jitter → analysis.
 */
export default function SpeedTestExperience({
  idleValue = 0,
  onComplete,
  onError,
  autoStart = false,
}) {
  const [phase, setPhase] = useState(autoStart ? "init" : "idle");
  const [gaugeValue, setGaugeValue] = useState(autoStart ? 0 : idleValue);
  const [gaugeMax, setGaugeMax] = useState(500);
  const [pingMs, setPingMs] = useState(null);
  const [jitterMs, setJitterMs] = useState(null);
  const [packetLossPct, setPacketLossPct] = useState(null);
  const [elapsedSec, setElapsedSec] = useState(0);
  const timersRef = useRef([]);
  const runIdRef = useRef(0);
  const abortRef = useRef(null);
  const startedAtRef = useRef(0);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onCompleteRef.current = onComplete;
    onErrorRef.current = onError;
  }, [onComplete, onError]);

  useEffect(() => {
    if (phase === "idle") {
      setGaugeValue(idleValue || 0);
      setGaugeMax(idleValue > 500 ? 1000 : 500);
    }
  }, [idleValue, phase]);

  const clearTimers = () => {
    timersRef.current.forEach((id) => {
      window.clearTimeout(id);
      window.clearInterval(id);
    });
    timersRef.current = [];
    abortRef.current?.abort();
    abortRef.current = null;
  };

  const startTest = async (runId) => {
    clearTimers();
    abortRef.current = new AbortController();
    const { signal } = abortRef.current;

    startedAtRef.current = Date.now();
    setPhase("init");
    setGaugeValue(0);
    setGaugeMax(500);
    setPingMs(null);
    setJitterMs(null);
    setPacketLossPct(null);
    setElapsedSec(0);
    onErrorRef.current?.(null);

    const elapsedTimer = window.setInterval(() => {
      if (runIdRef.current !== runId) return;
      setElapsedSec(Math.floor((Date.now() - startedAtRef.current) / 1000));
    }, 250);
    timersRef.current.push(elapsedTimer);

    const accum = {
      download_mbps: null,
      upload_mbps: null,
      ping_ms: null,
      jitter_ms: null,
      packet_loss_pct: null,
      dns_lookup_ms: null,
      http_response_ms: null,
      ipv4_ok: false,
      ipv6_ok: false,
      public_ip: null,
      isp_name: null,
      as_info: null,
      server_label: "cloudflare",
      errors: [],
    };

    try {
      const initStart = Date.now();
      await waitMin(initStart, MIN_INIT_MS);
      assertActive(runId, runIdRef);

      setPhase("server");
      const serverStart = Date.now();
      const server = await measureServerPhase();
      assertActive(runId, runIdRef);
      Object.assign(accum, {
        dns_lookup_ms: server.dns_lookup_ms,
        http_response_ms: server.http_response_ms,
        ipv4_ok: server.ipv4_ok,
        ipv6_ok: server.ipv6_ok,
        public_ip: server.public_ip,
        isp_name: server.isp_name,
        as_info: server.as_info,
        server_label: server.server_label,
      });
      accum.errors.push(...(server.errors ?? []));
      await waitMin(serverStart, MIN_SERVER_MS);
      assertActive(runId, runIdRef);

      setPhase("download");
      setGaugeValue(0);
      setGaugeMax(500);
      const downloadFinal = await streamDownloadPhase(
        (event) => {
          if (event.mbps != null) {
            setGaugeValue(event.mbps);
            if (event.mbps > 450) setGaugeMax(1000);
          }
        },
        { signal, quick: false }
      );
      assertActive(runId, runIdRef);
      const downloadMbps = downloadFinal?.download_mbps ?? downloadFinal?.mbps ?? 0;
      accum.download_mbps = downloadMbps;
      accum.errors.push(...(downloadFinal?.errors ?? []));
      setGaugeValue(downloadMbps);
      if (downloadMbps > 500) setGaugeMax(1000);
      await wait(SETTLE_MS);
      assertActive(runId, runIdRef);

      setPhase("upload");
      setGaugeValue(0);
      const uploadFinal = await streamUploadPhase(
        (event) => {
          if (event.mbps != null) setGaugeValue(event.mbps);
        },
        { signal, quick: false }
      );
      assertActive(runId, runIdRef);
      const uploadMbps = uploadFinal?.upload_mbps ?? uploadFinal?.mbps ?? 0;
      accum.upload_mbps = uploadMbps;
      accum.errors.push(...(uploadFinal?.errors ?? []));
      setGaugeValue(uploadMbps);
      await wait(SETTLE_MS);
      assertActive(runId, runIdRef);

      setPhase("ping");
      setGaugeMax(100);
      const latency = await measureLatencyPhase(false);
      assertActive(runId, runIdRef);
      accum.ping_ms = latency.ping_ms;
      accum.jitter_ms = latency.jitter_ms;
      accum.packet_loss_pct = latency.packet_loss_pct;
      accum.errors.push(...(latency.errors ?? []));
      setPingMs(latency.ping_ms);
      setJitterMs(latency.jitter_ms);
      setPacketLossPct(latency.packet_loss_pct);
      setGaugeValue(latency.ping_ms ?? 0);
      await wait(SETTLE_MS);
      assertActive(runId, runIdRef);

      setPhase("jitter");
      setGaugeMax(Math.max(20, Math.ceil((latency.jitter_ms ?? 10) * 1.5)));
      setGaugeValue(latency.jitter_ms ?? 0);
      await wait(SETTLE_MS);
      assertActive(runId, runIdRef);

      setPhase("ai");
      setGaugeMax(downloadMbps > 500 ? 1000 : 500);
      setGaugeValue(downloadMbps);

      const speedTest = await completeSpeedTest(accum);
      assertActive(runId, runIdRef);

      let recommendation = null;
      try {
        recommendation = await fetchRecommendation();
      } catch {
        recommendation = null;
      }
      assertActive(runId, runIdRef);

      setPhase("done");
      onCompleteRef.current?.({ speedTest, recommendation });
    } catch (err) {
      if (runIdRef.current !== runId || err?.name === "AbortError") return;
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
      if (runIdRef.current === runId) runIdRef.current += 1;
      clearTimers();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoStart]);

  const handleGo = () => {
    const runId = ++runIdRef.current;
    startTest(runId);
  };

  const stageId = normalizeStage(phase);

  return (
    <div className="sq-test-experience premium">
      <AnimatePresence mode="wait">
        <motion.div
          key="gauge"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          className="sq-test-layout premium"
        >
          <Speedometer
            value={gaugeValue}
            max={gaugeMax}
            phase={phase}
            onGo={handleGo}
            disabled={phase !== "idle" && phase !== "done"}
            pingMs={pingMs}
            jitterMs={jitterMs}
            packetLossPct={packetLossPct}
            elapsedSec={elapsedSec}
          />
          <TestStageProgress
            currentStageId={
              phase === "idle" ? "init" : phase === "done" ? "ai" : stageId
            }
          />
        </motion.div>
      </AnimatePresence>
      {(phase === "idle" || phase === "done") && (
        <p className="sq-test-hint">
          Tap GO to run a full SmartQoS measurement (typically 45–90 seconds).
        </p>
      )}
      {phase !== "idle" && phase !== "done" && (
        <p className="sq-stage-caption">
          {TEST_STAGES.find((s) => s.id === stageId)?.label || "Testing"}
        </p>
      )}
    </div>
  );
}

function normalizeStage(phase) {
  if (phase === "calculate" || phase === "results" || phase === "done") return "ai";
  return phase;
}
