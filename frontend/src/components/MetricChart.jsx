import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import { useEffect, useMemo, useState } from "react";
import { Line } from "react-chartjs-2";
import { fetchHistory } from "../api/client";
import { formatTime, METRIC_OPTIONS } from "../utils/format";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler
);

export default function MetricChart({ nodeCode }) {
  const [metric, setMetric] = useState("latency_ms");
  const [history, setHistory] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!nodeCode) {
      setHistory(null);
      return undefined;
    }

    let cancelled = false;

    const load = async () => {
      setLoading(true);
      try {
        const data = await fetchHistory(nodeCode, metric, 120);
        if (!cancelled) {
          setHistory(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    const timer = window.setInterval(load, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [nodeCode, metric]);

  const chartData = useMemo(() => {
    const points = history?.points ?? [];
    return {
      labels: points.map((p) => formatTime(p.timestamp)),
      datasets: [
        {
          label: METRIC_OPTIONS.find((m) => m.value === metric)?.label ?? metric,
          data: points.map((p) => p.value),
          borderColor: "#0f766e",
          backgroundColor: "rgba(15, 118, 110, 0.12)",
          borderWidth: 2,
          pointRadius: points.length > 40 ? 0 : 2,
          tension: 0.25,
          fill: true,
        },
      ],
    };
  }, [history, metric]);

  const options = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 350 },
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: "index",
          intersect: false,
        },
      },
      scales: {
        x: {
          grid: { color: "rgba(15, 23, 42, 0.06)" },
          ticks: {
            color: "#64748b",
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 8,
            font: { family: "IBM Plex Mono", size: 10 },
          },
        },
        y: {
          grid: { color: "rgba(15, 23, 42, 0.06)" },
          ticks: {
            color: "#64748b",
            font: { family: "IBM Plex Mono", size: 10 },
          },
        },
      },
    }),
    []
  );

  return (
    <section className="panel chart-panel">
      <div className="panel-head row">
        <div>
          <h2>Historical performance</h2>
          <p>
            {nodeCode
              ? `Node ${nodeCode}`
              : "Select a node to view QoS history"}
          </p>
        </div>
        <label className="metric-select">
          <span>Metric</span>
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
            disabled={!nodeCode}
          >
            {METRIC_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="chart-frame">
        {!nodeCode && (
          <p className="empty-copy centered">Choose an access node above.</p>
        )}
        {nodeCode && loading && !history && (
          <p className="empty-copy centered">Loading history…</p>
        )}
        {nodeCode && error && (
          <p className="empty-copy centered error">{error}</p>
        )}
        {nodeCode && history && history.points.length === 0 && (
          <p className="empty-copy centered">No history points for this metric.</p>
        )}
        {nodeCode && history && history.points.length > 0 && (
          <Line data={chartData} options={options} />
        )}
      </div>
    </section>
  );
}
