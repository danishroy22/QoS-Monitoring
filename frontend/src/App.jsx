import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  AlertCircle,
  ArrowDownToLine,
  ArrowUpFromLine,
  Gauge,
  Wifi,
  Zap,
} from "lucide-react";
import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchDashboard,
  fetchHealth,
  fetchRecommendation,
} from "./api/client";
import AiAssistant from "./components/AiAssistant";
import HistoryTable from "./components/HistoryTable";
import MonitoringView from "./components/MonitoringView";
import SpeedTestExperience from "./components/SpeedTestExperience";
import GlassCard from "./components/ui/GlassCard";
import SoftButton from "./components/ui/SoftButton";
import { SkeletonCards } from "./components/ui/LoadingPulse";
import MetricStatCard from "./components/ui/MetricStatCard";
import PanelHeader from "./components/ui/PanelHeader";
import { ratingClass } from "./utils/format";

const SpeedGraph = lazy(() => import("./components/SpeedGraph"));
const ResultsView = lazy(() => import("./components/ResultsView"));

const PRIMARY_METRICS = [
  {
    key: "download_mbps",
    label: "Download",
    unit: "Mbps",
    healthName: "Download",
    icon: ArrowDownToLine,
    accent: "download",
    higherIsBetter: true,
  },
  {
    key: "upload_mbps",
    label: "Upload",
    unit: "Mbps",
    healthName: "Upload",
    icon: ArrowUpFromLine,
    accent: "upload",
    higherIsBetter: true,
  },
  {
    key: "ping_ms",
    label: "Ping",
    unit: "ms",
    healthName: "Ping",
    icon: Zap,
    accent: "ping",
    higherIsBetter: false,
  },
  {
    key: "jitter_ms",
    label: "Jitter",
    unit: "ms",
    healthName: "Jitter",
    icon: Activity,
    accent: "jitter",
    higherIsBetter: false,
  },
  {
    key: "packet_loss_pct",
    label: "Packet Loss",
    unit: "%",
    healthName: "Packet Loss",
    icon: Wifi,
    accent: "loss",
    higherIsBetter: false,
    digits: 2,
  },
];

function trendFor(metric, latest, previous) {
  if (!latest || !previous) return "flat";
  const a = Number(latest[metric.key]);
  const b = Number(previous[metric.key]);
  if (!Number.isFinite(a) || !Number.isFinite(b) || a === b) return "flat";
  const improved = metric.higherIsBetter ? a > b : a < b;
  return improved ? "up" : "down";
}

export default function App() {
  const [view, setView] = useState("dashboard");
  const [dashboard, setDashboard] = useState(null);
  const [recommendation, setRecommendation] = useState(null);
  const [lastTest, setLastTest] = useState(null);
  const [apiOk, setApiOk] = useState(false);
  const [error, setError] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [bootLoading, setBootLoading] = useState(true);
  const [testKey, setTestKey] = useState(0);
  const [liveSession, setLiveSession] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [dash, health] = await Promise.all([fetchDashboard(), fetchHealth()]);
      setDashboard(dash);
      setApiOk(health?.status === "ok");
      setError(null);
    } catch (err) {
      setApiOk(false);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBootLoading(false);
    }
  }, []);

  const refreshAi = useCallback(async () => {
    setAiLoading(true);
    try {
      const rec = await fetchRecommendation();
      setRecommendation(rec);
    } catch {
      setRecommendation(null);
    } finally {
      setAiLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    refreshAi();
  }, [refresh, refreshAi]);

  const latest = dashboard?.latest;
  const health = dashboard?.health;
  const isp = dashboard?.isp;
  const history = dashboard?.history || [];
  const previous = history.length >= 2 ? history[history.length - 2] : null;
  const score = health?.overall_score ?? latest?.overall_score;
  const rating = health?.overall_rating ?? latest?.overall_rating ?? "—";

  const metricRating = useMemo(() => {
    const map = {};
    (health?.metrics || []).forEach((m) => {
      map[m.name] = m.rating;
    });
    return map;
  }, [health]);

  const handleTestComplete = async ({ speedTest, recommendation: rec }) => {
    setLiveSession(null);
    setLastTest({ speedTest, recommendation: rec });
    if (rec) setRecommendation(rec);
    await refresh();
    setView("results");
  };

  const handleTestError = (message) => {
    setLiveSession(null);
    if (message) setError(message);
  };

  const handleLiveUpdate = useCallback((snapshot) => {
    setLiveSession(snapshot?.active ? snapshot : null);
  }, []);

  const metricSource = liveSession?.active
    ? {
        download_mbps: liveSession.download_mbps,
        upload_mbps: liveSession.upload_mbps,
        ping_ms: liveSession.ping_ms,
        jitter_ms: liveSession.jitter_ms,
        packet_loss_pct: liveSession.packet_loss_pct,
      }
    : latest;

  const livePhase = liveSession?.active ? liveSession.phase : null;

  return (
    <div className="iq-shell dark">
      <div className="iq-bg" aria-hidden="true" />
      <main className="iq-main">
        <header className="iq-top">
          <div>
            <p className="iq-eyebrow">SmartQoS Platform</p>
            <h1>
              {view === "results"
                ? "Network Quality Report"
                : view === "monitoring"
                  ? "Continuous Monitoring"
                  : "Internet Quality Monitor"}
            </h1>
          </div>
          <div className="iq-top-meta">
            {(view === "dashboard" || view === "monitoring") && (
              <nav className="iq-nav" aria-label="Primary">
                <SoftButton
                  variant={view === "dashboard" ? "primary" : "ghost"}
                  className="iq-nav-btn"
                  onClick={() => setView("dashboard")}
                >
                  Dashboard
                </SoftButton>
                <SoftButton
                  variant={view === "monitoring" ? "primary" : "ghost"}
                  className="iq-nav-btn"
                  onClick={() => setView("monitoring")}
                >
                  Monitoring
                </SoftButton>
              </nav>
            )}
            <span className={`iq-status ${apiOk ? "on" : "off"}`}>
              <span
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  background: "currentColor",
                  display: "inline-block",
                }}
              />
              {apiOk ? "API online" : "API offline"}
            </span>
            {isp?.isp_name && view === "dashboard" && (
              <span className="iq-isp">
                <Wifi size={14} strokeWidth={2} />
                {isp.isp_name}
                {isp.public_ip ? ` · ${isp.public_ip}` : ""}
              </span>
            )}
          </div>
        </header>

        {error && (
          <motion.div
            className="iq-banner error"
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <AlertCircle size={18} />
            <span>{error}</span>
          </motion.div>
        )}

        <AnimatePresence mode="wait">
          {view === "dashboard" && (
            <motion.div
              key="dashboard"
              className="sq-view"
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
            >
              <section className="iq-hero iq-hero-speed">
                <GlassCard className="sq-hero-gauge" hover={false} delay={0.05}>
                  <div className="sq-score-strip">
                    <div className="sq-score-strip-inner">
                      <p className="iq-score-label">Overall Network Score</p>
                      <p className={`iq-score-value compact ${ratingClass(rating)}`}>
                        {score != null ? `${score}/100` : "—"}
                      </p>
                      <p className={`iq-score-rating ${ratingClass(rating)}`}>{rating}</p>
                    </div>
                  </div>

                  <SpeedTestExperience
                    key={testKey}
                    autoStart={false}
                    onComplete={handleTestComplete}
                    onError={handleTestError}
                    onLiveUpdate={handleLiveUpdate}
                  />
                </GlassCard>

                {bootLoading ? (
                  <SkeletonCards count={5} />
                ) : (
                  <div className="iq-metric-grid" aria-live="polite">
                    {PRIMARY_METRICS.map((metric, index) => (
                      <MetricStatCard
                        key={metric.key}
                        label={metric.label}
                        value={metricSource?.[metric.key]}
                        unit={metric.unit}
                        rating={
                          liveSession?.active
                            ? null
                            : metricRating[metric.healthName]
                        }
                        icon={metric.icon}
                        accent={metric.accent}
                        trend={
                          liveSession?.active
                            ? "flat"
                            : trendFor(metric, latest, previous)
                        }
                        digits={metric.digits ?? 1}
                        delay={0.08 + index * 0.04}
                        pending={Boolean(liveSession?.active)}
                        live={
                          livePhase === "download" && metric.key === "download_mbps"
                            ? true
                            : livePhase === "upload" && metric.key === "upload_mbps"
                              ? true
                              : livePhase === "ping" && metric.key === "ping_ms"
                                ? true
                                : livePhase === "jitter" && metric.key === "jitter_ms"
                                  ? true
                                  : false
                        }
                      />
                    ))}
                  </div>
                )}
              </section>

              {health?.metrics && (
                <GlassCard className="iq-panel compact" delay={0.12}>
                  <PanelHeader
                    title="QoS Breakdown"
                    subtitle="Per-metric health classification from the latest measurement"
                    action={<Gauge size={18} color="var(--muted)" />}
                  />
                  <div className="iq-breakdown">
                    {health.metrics.map((m) => (
                      <div key={m.name} className="iq-breakdown-row">
                        <span>{m.name}</span>
                        <span className="mono">
                          {m.value == null ? "—" : `${Number(m.value).toFixed(1)} ${m.unit}`}
                        </span>
                        <span className={`iq-pill ${ratingClass(m.rating)}`}>
                          {m.rating} · {m.score}
                        </span>
                      </div>
                    ))}
                  </div>
                </GlassCard>
              )}

              <Suspense fallback={<GlassCard className="iq-panel"><SkeletonCards count={1} /></GlassCard>}>
                <SpeedGraph history={history} />
              </Suspense>

              <div className="iq-lower">
                <HistoryTable history={history} />
                <AiAssistant recommendation={recommendation} loading={aiLoading} />
              </div>
            </motion.div>
          )}

          {view === "monitoring" && (
            <MonitoringView
              key="monitoring"
              onBack={() => {
                setView("dashboard");
                refresh();
              }}
            />
          )}

          {view === "results" && lastTest && (
            <Suspense
              fallback={
                <GlassCard className="iq-panel">
                  <SkeletonCards count={3} />
                </GlassCard>
              }
            >
              <ResultsView
                key="results"
                speedTest={lastTest.speedTest}
                recommendation={lastTest.recommendation || recommendation}
                history={history}
                onBack={() => {
                  setTestKey((k) => k + 1);
                  setView("dashboard");
                }}
                onRetest={() => {
                  setTestKey((k) => k + 1);
                  setView("dashboard");
                }}
              />
            </Suspense>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
