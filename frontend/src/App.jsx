import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchAnomalies,
  fetchHealth,
  fetchLatestMetrics,
  fetchRecommendations,
} from "./api/client";
import AiPanel from "./components/AiPanel";
import Header from "./components/Header";
import IssuesPanel from "./components/IssuesPanel";
import MetricChart from "./components/MetricChart";
import NodeHealthGrid from "./components/NodeHealthGrid";
import StatusBar from "./components/StatusBar";
import { usePolling } from "./hooks/usePolling";

export default function App() {
  const [selectedNode, setSelectedNode] = useState(null);
  const [health, setHealth] = useState(null);

  const fetchLatest = useCallback(() => fetchLatestMetrics(), []);
  const {
    data: metrics,
    error: metricsError,
    loading,
    updatedAt,
  } = usePolling(fetchLatest, 4000, true);

  const fetchIssues = useCallback(() => fetchAnomalies({ activeOnly: true }), []);
  const { data: anomalies } = usePolling(fetchIssues, 8000, true);

  const fetchAi = useCallback(() => fetchRecommendations(10), []);
  const { data: recommendations } = usePolling(fetchAi, 12000, true);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const result = await fetchHealth();
        if (!cancelled) setHealth(result);
      } catch {
        if (!cancelled) setHealth(null);
      }
    };
    check();
    const timer = window.setInterval(check, 10000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (!selectedNode && Array.isArray(metrics) && metrics.length > 0) {
      setSelectedNode(metrics[0].node_code);
    }
  }, [metrics, selectedNode]);

  const connected = Boolean(health?.status === "ok");

  const pageMessage = useMemo(() => {
    if (metricsError) return metricsError;
    if (loading && !metrics) return "Connecting to monitoring API…";
    return null;
  }, [loading, metrics, metricsError]);

  return (
    <div className="noc-shell">
      <div className="noc-atmosphere" aria-hidden="true" />
      <div className="noc-content">
        <Header health={health} updatedAt={updatedAt} connected={connected} />
        <StatusBar metrics={metrics} />

        {pageMessage && (
          <div className={`banner ${metricsError ? "error" : "info"}`}>
            {pageMessage}
            {metricsError ? (
              <span>
                {" "}
                Start the backend with <code>python scripts/run_backend.py</code>.
              </span>
            ) : null}
          </div>
        )}

        <NodeHealthGrid
          metrics={metrics}
          selectedNode={selectedNode}
          onSelect={setSelectedNode}
        />

        <div className="lower-grid">
          <MetricChart nodeCode={selectedNode} />
          <div className="side-stack">
            <IssuesPanel metrics={metrics} anomalies={anomalies} />
            <AiPanel metrics={metrics} recommendations={recommendations} />
          </div>
        </div>
      </div>
    </div>
  );
}
