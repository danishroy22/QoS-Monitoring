export function formatNumber(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  return Number(value).toFixed(digits);
}

export function formatTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDateTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ratingClass(rating) {
  const key = String(rating || "").toLowerCase();
  if (key === "excellent") return "excellent";
  if (key === "good") return "good";
  if (key === "fair") return "fair";
  if (key === "poor") return "poor";
  if (key === "critical") return "critical";
  return "neutral";
}
