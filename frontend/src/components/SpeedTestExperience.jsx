import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import {
  completeSpeedTest,
  fetchRecommendation,
  fetchSpeedServers,
  findBestServer,
  identifyConnection,
  measureLatencyPhase,
  measureServerPhase,
  streamDownloadPhase,
  streamUploadPhase,
} from "../api/client";
import FindServerPanel from "./FindServerPanel";
import MauritiusServerPicker from "./MauritiusServerPicker";
import Speedometer from "./Speedometer";
import TestStageProgress from "./TestStageProgress";

const SETTLE_MS = 2800;
const SERVER_STORAGE_KEY = "smartqos_mu_server_id";
const AUTO_ID = "auto";

function wait(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function assertActive(runId, runIdRef) {
  if (runIdRef.current !== runId) {
    const err = new Error("cancelled");
    err.name = "AbortError";
    throw err;
  }
}

/**
 * Mauritius-focused speed-test experience.
 * On GO: blank live cards, then populate them as readings arrive.
 */
export default function SpeedTestExperience({
  onComplete,
  onError,
  onLiveUpdate,
  autoStart = false,
}) {
  const [phase, setPhase] = useState(autoStart ? "init" : "idle");
  const [gaugeValue, setGaugeValue] = useState(0);
  const [gaugeMax, setGaugeMax] = useState(500);
  const [downloadMbps, setDownloadMbps] = useState(null);
  const [uploadMbps, setUploadMbps] = useState(null);
  const [pingMs, setPingMs] = useState(null);
  const [jitterMs, setJitterMs] = useState(null);
  const [packetLossPct, setPacketLossPct] = useState(null);
  const [servers, setServers] = useState([]);
  const [preferredServerId, setPreferredServerId] = useState(
    () => localStorage.getItem(SERVER_STORAGE_KEY) || AUTO_ID
  );
  const [activeServer, setActiveServer] = useState(null);
  const [ispName, setIspName] = useState(null);
  const [publicIp, setPublicIp] = useState(null);
  const [findProbes, setFindProbes] = useState([]);
  const [findSelected, setFindSelected] = useState(null);
  const [showFindPanel, setShowFindPanel] = useState(false);
  const [identity, setIdentity] = useState(null);
  const [identityReady, setIdentityReady] = useState(false);
  const [sessionActive, setSessionActive] = useState(false);

  const timersRef = useRef([]);
  const runIdRef = useRef(0);
  const abortRef = useRef(null);
  const startedAtRef = useRef(0);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);
  const onLiveUpdateRef = useRef(onLiveUpdate);

  useEffect(() => {
    onCompleteRef.current = onComplete;
    onErrorRef.current = onError;
    onLiveUpdateRef.current = onLiveUpdate;
  }, [onComplete, onError, onLiveUpdate]);

  useEffect(() => {
    onLiveUpdateRef.current?.({
      active: sessionActive,
      phase,
      download_mbps: downloadMbps,
      upload_mbps: uploadMbps,
      ping_ms: pingMs,
      jitter_ms: jitterMs,
      packet_loss_pct: packetLossPct,
      isp_name: ispName,
      public_ip: publicIp,
      server_name: activeServer?.name ?? null,
      server_location: activeServer?.location ?? null,
    });
  }, [
    sessionActive,
    phase,
    downloadMbps,
    uploadMbps,
    pingMs,
    jitterMs,
    packetLossPct,
    ispName,
    publicIp,
    activeServer,
  ]);

  useEffect(() => {
    let cancelled = false;
    fetchSpeedServers()
      .then((payload) => {
        if (cancelled) return;
        const list = payload?.servers || [];
        setServers(list);
        const saved = localStorage.getItem(SERVER_STORAGE_KEY) || AUTO_ID;
        const valid = saved === AUTO_ID || list.some((s) => s.id === saved);
        setPreferredServerId(valid ? saved : AUTO_ID);
      })
      .catch(() => {
        if (!cancelled) setServers([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    localStorage.setItem(SERVER_STORAGE_KEY, preferredServerId);
  }, [preferredServerId]);

  const clearTimers = () => {
    timersRef.current.forEach((id) => {
      window.clearTimeout(id);
      window.clearInterval(id);
    });
    timersRef.current = [];
    abortRef.current?.abort();
    abortRef.current = null;
  };

  const resetSessionCards = () => {
    setDownloadMbps(null);
    setUploadMbps(null);
    setPingMs(null);
    setJitterMs(null);
    setPacketLossPct(null);
    setIspName(null);
    setPublicIp(null);
    setActiveServer(null);
    setFindProbes([]);
    setFindSelected(null);
    setIdentity(null);
    setIdentityReady(false);
  };

  const startTest = async (runId) => {
    clearTimers();
    abortRef.current = new AbortController();
    const { signal } = abortRef.current;

    // New session: blank cards immediately, then fill in real time.
    startedAtRef.current = Date.now();
    setSessionActive(true);
    setPhase("init");
    setGaugeValue(0);
    setGaugeMax(500);
    resetSessionCards();
    setShowFindPanel(true);
    onErrorRef.current?.(null);

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
      detected_region: null,
      detected_city: null,
      latitude: null,
      longitude: null,
      server_label: "Mauritius",
      server_id: null,
      selection_mode: preferredServerId === AUTO_ID ? "auto" : "manual",
      selection_score: null,
      errors: [],
    };

    try {
      setPhase("init");
      setGaugeValue(0);

      let identified = null;
      try {
        identified = await identifyConnection();
      } catch {
        identified = null;
      }
      assertActive(runId, runIdRef);
      setIdentity(identified);
      setIdentityReady(true);
      if (identified?.isp_name) setIspName(identified.isp_name);
      if (identified?.public_ip) setPublicIp(identified.public_ip);
      Object.assign(accum, {
        public_ip: identified?.public_ip ?? null,
        isp_name: identified?.isp_name ?? null,
        as_info: identified?.as_info ?? null,
        detected_region: identified?.detected_region ?? null,
        detected_city: identified?.detected_city ?? null,
        latitude: identified?.latitude ?? null,
        longitude: identified?.longitude ?? null,
      });
      await wait(700);
      assertActive(runId, runIdRef);

      setPhase("server");
      const probeResult = await findBestServer(identified?.isp_name || null);
      assertActive(runId, runIdRef);
      const probes = probeResult?.probes || [];
      setFindProbes(probes);
      await wait(Math.min(1400, 400 + probes.length * 40));
      assertActive(runId, runIdRef);

      const manual =
        preferredServerId !== AUTO_ID
          ? probes.find((p) => p.id === preferredServerId)
          : null;
      const chosen =
        manual ||
        probeResult?.best_server ||
        probes[0] ||
        servers.find((s) => s.id === preferredServerId) ||
        servers[0];

      if (!chosen) {
        throw new Error("No Mauritius test servers are configured.");
      }

      const chosenWithLatency = {
        ...chosen,
        latency_ms:
          chosen.latency_ms ??
          probes.find((p) => p.id === chosen.id)?.latency_ms ??
          null,
      };
      setFindSelected(chosenWithLatency);
      setActiveServer(chosenWithLatency);
      accum.selection_score = chosenWithLatency.score ?? probeResult?.best_server?.score ?? null;
      await wait(1100);
      assertActive(runId, runIdRef);
      setShowFindPanel(false);

      const selectedServerId = chosenWithLatency.id;
      accum.server_id = selectedServerId;
      accum.server_label = `${chosenWithLatency.name} · ${chosenWithLatency.location}`;

      const server = await measureServerPhase(selectedServerId);
      assertActive(runId, runIdRef);
      Object.assign(accum, {
        dns_lookup_ms: server.dns_lookup_ms,
        http_response_ms: server.http_response_ms,
        ipv4_ok: server.ipv4_ok,
        ipv6_ok: server.ipv6_ok,
        public_ip: server.public_ip || accum.public_ip,
        isp_name: server.isp_name || accum.isp_name,
        as_info: server.as_info || accum.as_info,
        detected_region: server.detected_region || accum.detected_region,
        detected_city: server.detected_city || accum.detected_city,
        latitude: server.latitude ?? accum.latitude,
        longitude: server.longitude ?? accum.longitude,
        server_label: `${chosenWithLatency.name} · ${chosenWithLatency.location}`,
        server_id: selectedServerId,
      });
      accum.errors.push(...(server.errors ?? []));
      setIspName(server.isp_name || null);
      setPublicIp(server.public_ip || null);

      setPhase("download");
      setGaugeValue(0);
      setGaugeMax(500);
      const downloadFinal = await streamDownloadPhase(
        (event) => {
          if (event.mbps != null) {
            setGaugeValue(event.mbps);
            setDownloadMbps(event.mbps);
            if (event.mbps > 450) setGaugeMax(1000);
          }
        },
        { signal, quick: false, serverId: selectedServerId }
      );
      assertActive(runId, runIdRef);
      const down = downloadFinal?.download_mbps ?? downloadFinal?.mbps ?? 0;
      accum.download_mbps = down;
      accum.errors.push(...(downloadFinal?.errors ?? []));
      setDownloadMbps(down);
      setGaugeValue(down);
      if (down > 500) setGaugeMax(1000);
      await wait(SETTLE_MS);
      assertActive(runId, runIdRef);

      setPhase("upload");
      setGaugeValue(0);
      const uploadFinal = await streamUploadPhase(
        (event) => {
          if (event.mbps != null) {
            setGaugeValue(event.mbps);
            setUploadMbps(event.mbps);
          }
        },
        { signal, quick: false, serverId: selectedServerId }
      );
      assertActive(runId, runIdRef);
      const up = uploadFinal?.upload_mbps ?? uploadFinal?.mbps ?? 0;
      accum.upload_mbps = up;
      accum.errors.push(...(uploadFinal?.errors ?? []));
      setUploadMbps(up);
      setGaugeValue(up);
      await wait(SETTLE_MS);
      assertActive(runId, runIdRef);

      setPhase("ping");
      setGaugeMax(100);
      setGaugeValue(0);
      const latency = await measureLatencyPhase(false, selectedServerId);
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
      setGaugeMax(down > 500 ? 1000 : 500);
      setGaugeValue(down);

      const speedTest = await completeSpeedTest(accum);
      assertActive(runId, runIdRef);

      let recommendation = null;
      try {
        recommendation = await fetchRecommendation();
      } catch {
        recommendation = null;
      }
      assertActive(runId, runIdRef);

      setSessionActive(false);
      setPhase("done");
      onCompleteRef.current?.({ speedTest, recommendation });
    } catch (err) {
      if (runIdRef.current !== runId || err?.name === "AbortError") return;
      clearTimers();
      setShowFindPanel(false);
      setSessionActive(false);
      setPhase("idle");
      setGaugeValue(0);
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
  const busy = phase !== "idle" && phase !== "done";

  return (
    <div className="sq-test-experience premium mu-ecosystem">
      <MauritiusServerPicker
        servers={servers}
        selectedId={preferredServerId}
        onSelect={setPreferredServerId}
        disabled={busy}
      />

      <AnimatePresence>
        {showFindPanel && (
          <FindServerPanel
            visible
            identity={identity}
            identityReady={identityReady}
            probes={findProbes}
            selected={findSelected}
          />
        )}
      </AnimatePresence>

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
            disabled={busy}
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
          Tap GO. SmartQoS identifies your connection and chooses a test server.
          Use Advanced Settings for a manual server.
        </p>
      )}
    </div>
  );
}

function normalizeStage(phase) {
  if (phase === "jitter") return "ping";
  if (phase === "calculate" || phase === "results" || phase === "done") return "ai";
  return phase;
}
