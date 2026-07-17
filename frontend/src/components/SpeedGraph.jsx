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
        label: "Download (Mbps)",
        data: rows.map((r) => r.download_mbps),
        borderColor: "#38bdf8",
        backgroundColor: "rgba(56, 189, 248, 0.14)",
        tension: 0.3,
        fill: true,
        pointRadius: rows.length > 20 ? 0 : 3,
      },
      {
        label: "Upload (Mbps)",
        data: rows.map((r) => r.upload_mbps),
        borderColor: "#34d399",
        backgroundColor: "rgba(52, 211, 153, 0.1)",
        tension: 0.3,
        fill: false,
        pointRadius: rows.length > 20 ? 0 : 3,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top",
        labels: { color: "#93a4bd", boxWidth: 12, font: { family: "IBM Plex Sans" } },
      },
    },
    scales: {
      x: {
        ticks: { color: "#93a4bd", maxTicksLimit: 8 },
        grid: { color: "rgba(148, 163, 184, 0.12)" },
      },
      y: {
        ticks: { color: "#93a4bd" },
        grid: { color: "rgba(148, 163, 184, 0.12)" },
        title: { display: true, text: "Mbps", color: "#93a4bd" },
      },
    },
  };

  return (
    <section className="iq-panel glass">
      <div className="iq-panel-head">
        <h2>Speed Graph</h2>
        <p>Download and upload across recent tests</p>
      </div>
      <div className="iq-chart">
        {rows.length === 0 ? (
          <p className="iq-empty">Run a speed test to populate the graph.</p>
        ) : (
          <Line data={data} options={options} />
        )}
      </div>
    </section>
  );
}
