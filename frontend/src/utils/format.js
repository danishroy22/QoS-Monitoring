/** Display helpers for QoS metrics and timestamps. */

export function formatNumber(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  return Number(value).toFixed(digits);
}

export function formatTime(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatDateTime(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function scenarioLabel(label) {
  if (!label) return "Unknown";
  return label
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function healthTone(status) {
  switch (status) {
    case "healthy":
      return "ok";
    case "degraded":
      return "warn";
    case "critical":
      return "crit";
    default:
      return "neutral";
  }
}

export const METRIC_OPTIONS = [
  { value: "latency_ms", label: "Latency (ms)" },
  { value: "jitter_ms", label: "Jitter (ms)" },
  { value: "packet_loss_pct", label: "Packet Loss (%)" },
  { value: "throughput_mbps", label: "Throughput (Mbps)" },
  { value: "bandwidth_utilisation_pct", label: "Utilisation (%)" },
  { value: "signal_quality", label: "Signal Quality" },
  { value: "availability_pct", label: "Availability (%)" },
];
