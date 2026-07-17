import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import {
  fetchDashboard,
  fetchHealth,
  fetchRecommendation,
} from "./api/client";
import AiAssistant from "./components/AiAssistant";
import HistoryTable from "./components/HistoryTable";
import ResultsView from "./components/ResultsView";
import SpeedGraph from "./components/SpeedGraph";
import SpeedTestExperience from "./components/SpeedTestExperience";
import { formatNumber, ratingClass } from "./utils/format";

/**
 * SmartQoS app shell.
 * Speedometer is always visible on the dashboard hero.
 * After a test completes, transitions to the Results view.
 */
const PRIMARY_METRICS = [
  { key: "download_mbps", label: "Download", unit: "Mbps", healthName: "Download" },
  { key: "upload_mbps", label: "Upload", unit: "Mbps", healthName: "Upload" },
  { key: "ping_ms", label: "Ping", unit: "ms", healthName: "Ping" },
  { key: "jitter_ms", label: "Jitter", unit: "ms", healthName: "Jitter" },
  { key: "packet_loss_pct", label: "Packet Loss", unit: "%", healthName: "Packet Loss" },
];

export default function App() {
  const [view, setView] = useState("dashboard");
  const [dashboard, setDashboard] = useState(null);
  const [recommendation, setRecommendation] = useState(null);
  const [lastTest, setLastTest] = useState(null);
  const [apiOk, setApiOk] = useState(false);
  const [error, setError] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [testKey, setTestKey] = useState(0);

  const refresh = useCallback(async () => {
    try {
      const [dash, health] = await Promise.all([fetchDashboard(), fetchHealth()]);
      setDashboard(dash);
      setApiOk(health?.status === "ok");
      setError(null);
    } catch (err) {
      setApiOk(false);
      setError(err instanceof Error ? err.message : String(err));
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
  const score = health?.overall_score ?? latest?.overall_score;
  const rating = health?.overall_rating ?? latest?.overall_rating ?? "—";

  const metricRating = (healthName) => {
    const found = health?.metrics?.find((m) => m.name === healthName);
    return found?.rating || "—";
  };

  const handleTestComplete = async ({ speedTest, recommendation: rec }) => {
    setLastTest({ speedTest, recommendation: rec });
    if (rec) setRecommendation(rec);
    await refresh();
    setView("results");
  };

  const handleTestError = (message) => {
    if (message) setError(message);
  };

  return (
    <div className="iq-shell dark">
      <div className="iq-bg" aria-hidden="true" />
      <main className="iq-main">
        <header className="iq-top">
          <div>
            <p className="iq-eyebrow">SmartQoS</p>
            <h1>{view === "results" ? "Test Results" : "Internet Quality Dashboard"}</h1>
          </div>
          <div className="iq-top-meta">
            <span className={`iq-status ${apiOk ? "on" : "off"}`}>
              {apiOk ? "API online" : "API offline"}
            </span>
            {isp?.isp_name && view === "dashboard" && (
              <span className="iq-isp">
                {isp.isp_name}
                {isp.public_ip ? ` · ${isp.public_ip}` : ""}
              </span>
            )}
          </div>
        </header>

        {error && <div className="iq-banner error">{error}</div>}

        <AnimatePresence mode="wait">
          {view === "dashboard" && (
            <motion.div
              key="dashboard"
              className="sq-view"
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.35 }}
            >
              <section className="iq-hero iq-hero-speed">
                <div className="iq-score-card glass sq-hero-gauge">
                  <div className="sq-score-strip">
                    <div>
                      <p className="iq-score-label">Overall Score</p>
                      <p className={`iq-score-value compact ${ratingClass(rating)}`}>
                        {score != null ? `${score}/100` : "—"}
                      </p>
                      <p className={`iq-score-rating ${ratingClass(rating)}`}>{rating}</p>
                    </div>
                  </div>

                  {/* Speedometer is always mounted here */}
                  <SpeedTestExperience
                    key={testKey}
                    idleValue={latest?.download_mbps || 0}
                    autoStart={false}
                    onComplete={handleTestComplete}
                    onError={handleTestError}
                  />
                </div>

                <div className="iq-metric-grid">
                  {PRIMARY_METRICS.map((metric) => (
                    <article key={metric.key} className="iq-metric glass">
                      <p className="iq-metric-label">{metric.label}</p>
                      <p className="iq-metric-value">
                        {latest
                          ? formatNumber(
                              latest[metric.key],
                              metric.key.includes("loss") ? 2 : 1
                            )
                          : "—"}
                        <span>{metric.unit}</span>
                      </p>
                      <p
                        className={`iq-metric-rating ${ratingClass(
                          metricRating(metric.healthName)
                        )}`}
                      >
                        {metricRating(metric.healthName)}
                      </p>
                    </article>
                  ))}
                </div>
              </section>

              {health?.metrics && (
                <section className="iq-panel glass compact">
                  <div className="iq-panel-head">
                    <h2>QoS Breakdown</h2>
                    <p>Per-metric health classification</p>
                  </div>
                  <div className="iq-breakdown">
                    {health.metrics.map((m) => (
                      <div key={m.name} className="iq-breakdown-row">
                        <span>{m.name}</span>
                        <span className="mono">
                          {m.value == null
                            ? "—"
                            : `${formatNumber(m.value)} ${m.unit}`}
                        </span>
                        <span className={`iq-pill ${ratingClass(m.rating)}`}>
                          {m.rating} · {m.score}
                        </span>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              <SpeedGraph history={dashboard?.history || []} />
              <div className="iq-lower">
                <HistoryTable history={dashboard?.history || []} />
                <AiAssistant recommendation={recommendation} loading={aiLoading} />
              </div>
            </motion.div>
          )}

          {view === "results" && lastTest && (
            <ResultsView
              key="results"
              speedTest={lastTest.speedTest}
              recommendation={lastTest.recommendation || recommendation}
              onBack={() => {
                setTestKey((k) => k + 1);
                setView("dashboard");
              }}
              onRetest={() => {
                setTestKey((k) => k + 1);
                setView("dashboard");
              }}
            />
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
