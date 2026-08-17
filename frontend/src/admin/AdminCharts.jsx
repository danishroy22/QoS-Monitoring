import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import { Bar, Line } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler
);

const TICK = {
  color: "#94a3b8",
  font: { family: "Plus Jakarta Sans", size: 11, weight: "600" },
};

const GRID = { color: "rgba(148, 163, 184, 0.12)", drawBorder: false };

export const ADMIN_PALETTE = [
  "#3b82f6",
  "#06b6d4",
  "#22c55e",
  "#a78bfa",
  "#f59e0b",
  "#f43f5e",
  "#38bdf8",
  "#94a3b8",
];

export function chartOptions({ stacked = false, yTitle = "" } = {}) {
  return {
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
          padding: 14,
          font: { family: "Plus Jakarta Sans", size: 12, weight: "600" },
        },
      },
      tooltip: {
        backgroundColor: "rgba(5, 8, 22, 0.92)",
        titleColor: "#eef2ff",
        bodyColor: "#c7d2fe",
        borderColor: "rgba(148, 163, 184, 0.2)",
        borderWidth: 1,
        padding: 10,
      },
    },
    scales: {
      x: { stacked, ticks: TICK, grid: { display: false } },
      y: {
        stacked,
        ticks: TICK,
        grid: GRID,
        title: yTitle
          ? { display: true, text: yTitle, color: "#94a3b8", font: { size: 11, weight: "600" } }
          : undefined,
      },
    },
  };
}

export function AdminBarChart({ labels, datasets, yTitle }) {
  return (
    <Bar
      data={{ labels, datasets }}
      options={chartOptions({ yTitle })}
    />
  );
}

export function AdminLineChart({ labels, datasets, yTitle }) {
  return (
    <Line
      data={{ labels, datasets }}
      options={chartOptions({ yTitle })}
    />
  );
}

export function metricDataset(label, data, color, { fill = false, line = false } = {}) {
  return {
    label,
    data,
    borderColor: color,
    backgroundColor: hexAlpha(color, fill || line ? 0.16 : 0.78),
    borderWidth: line ? 2.25 : 1.5,
    borderRadius: line ? 0 : 8,
    tension: 0.35,
    fill: Boolean(fill),
    pointRadius: line ? (data.length > 20 ? 0 : 3) : 0,
    pointHoverRadius: 5,
    pointBackgroundColor: color,
    maxBarThickness: 42,
  };
}

function hexAlpha(hex, alpha) {
  const clean = hex.replace("#", "");
  const bigint = parseInt(clean, 16);
  const r = (bigint >> 16) & 255;
  const g = (bigint >> 8) & 255;
  const b = bigint & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
