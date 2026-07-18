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
import { Line } from "react-chartjs-2";
import { formatTime } from "../utils/format";
import GlassCard from "./ui/GlassCard";
import PanelHeader from "./ui/PanelHeader";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler
);

export default function SpeedGraph({ history }) {
  const rows = Array.isArray(history) ? history : [];
  const labels = rows.map((r) => formatTime(r.timestamp));

  const data = {
    labels,
    datasets: [
      {
        label: "Download",
        data: rows.map((r) => r.download_mbps),
        borderColor: "#3B82F6",
        backgroundColor: "rgba(59, 130, 246, 0.12)",
        borderWidth: 2.25,
        tension: 0.35,
        fill: true,
        pointRadius: rows.length > 18 ? 0 : 3,
        pointHoverRadius: 5,
        pointBackgroundColor: "#3B82F6",
      },
      {
        label: "Upload",
        data: rows.map((r) => r.upload_mbps),
        borderColor: "#22C55E",
        backgroundColor: "rgba(34, 197, 94, 0.06)",
        borderWidth: 2.25,
        tension: 0.35,
        fill: false,
        pointRadius: rows.length > 18 ? 0 : 3,
        pointHoverRadius: 5,
        pointBackgroundColor: "#22C55E",
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: {
        position: "top",
        align: "end",
        labels: {
          color: "#94a3b8",
          boxWidth: 10,
          boxHeight: 10,
          usePointStyle: true,
          pointStyle: "circle",
          padding: 16,
          font: { family: "Plus Jakarta Sans", size: 12, weight: "600" },
        },
      },
      tooltip: {
        backgroundColor: "rgba(5, 8, 22, 0.92)",
        titleColor: "#eef2ff",
        bodyColor: "#c7d2fe",
        borderColor: "rgba(148, 163, 184, 0.2)",
        borderWidth: 1,
        padding: 12,
        cornerRadius: 10,
        displayColors: true,
        callbacks: {
          label: (ctx) => ` ${ctx.dataset.label}: ${Number(ctx.parsed.y).toFixed(1)} Mbps`,
        },
      },
    },
    scales: {
      x: {
        ticks: {
          color: "#64748b",
          maxTicksLimit: 8,
          padding: 8,
          font: { family: "Plus Jakarta Sans", size: 11 },
        },
        grid: { color: "rgba(148, 163, 184, 0.08)", drawBorder: false },
      },
      y: {
        ticks: {
          color: "#64748b",
          padding: 10,
          font: { family: "Plus Jakarta Sans", size: 11 },
        },
        grid: { color: "rgba(148, 163, 184, 0.08)", drawBorder: false },
        title: {
          display: true,
          text: "Mbps",
          color: "#64748b",
          font: { family: "Plus Jakarta Sans", size: 11, weight: "600" },
        },
      },
    },
  };

  return (
    <GlassCard className="iq-panel" delay={0.14}>
      <PanelHeader
        title="Speed Trends"
        subtitle="Download and upload across recent tests"
      />
      <div className="iq-chart">
        {rows.length === 0 ? (
          <p className="iq-empty">Run a speed test to populate the graph.</p>
        ) : (
          <Line data={data} options={options} />
        )}
      </div>
    </GlassCard>
  );
}
