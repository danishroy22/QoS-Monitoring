import { motion } from "framer-motion";
import {
  Activity,
  Clock,
  Gauge,
  Play,
  Square,
  Timer,
  Wifi,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchMonitoringStatus,
  fetchSpeedServers,
  startMonitoring,
  stopMonitoring,
} from "../api/client";
import GlassCard from "./ui/GlassCard";
import SoftButton from "./ui/SoftButton";
import PanelHeader from "./ui/PanelHeader";
import { formatDateTime, formatNumber, ratingClass } from "../utils/format";

const INTERVAL_OPTIONS = [
  { value: "1m", label: "1 minute" },
  { value: "5m", label: "5 minutes" },
  { value: "10m", label: "10 minutes" },
  { value: "30m", label: "30 minutes" },
  { value: "custom", label: "Custom" },
];

function formatDuration(totalSeconds) {
  const s = Math.max(0, Number(totalSeconds) || 0);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}h ${m}m ${sec}s`;
  if (m > 0) return `${m}m ${sec}s`;
  return `${sec}s`;
}

function formatCountdown(iso) {
  if (!iso) return "—";
  const target = new Date(iso).getTime();
  if (!Number.isFinite(target)) return "—";
  const diff = Math.max(0, Math.floor((target - Date.now()) / 1000));
  return formatDuration(diff);
}

/**
 * Continuous QoS Monitoring page (Phase 7).
 * Enable/disable interval-based background measurements.
 */
export default function MonitoringView({ onBack }) {
  const [status, setStatus] = useState(null);
  const [servers, setServers] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [interval, setIntervalPreset] = useState("5m");
  const [customMinutes, setCustomMinutes] = useState(15);
  const [serverId, setServerId] = useState("");
  const [tick, setTick] = useState(0);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchMonitoringStatus();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    refresh();
    fetchSpeedServers()
      .then((payload) => setServers(payload?.servers || []))
      .catch(() => setServers([]));
  }, [refresh]);

  useEffect(() => {
    const id = window.setInterval(() => {
      setTick((t) => t + 1);
      refresh();
    }, 5000);
    return () => window.clearInterval(id);
  }, [refresh]);

  const durationDisplay = useMemo(() => {
    void tick;
    if (!status?.enabled || !status.started_at) {
      return formatDuration(status?.monitoring_duration_seconds || 0);
    }
    const start = new Date(status.started_at).getTime();
    return formatDuration(Math.floor((Date.now() - start) / 1000));
  }, [status, tick]);

  const nextDisplay = useMemo(() => {
    void tick;
    if (!status?.enabled) return "—";
    if (status.running) return "Measuring now…";
    return formatCountdown(status.next_run_at);
  }, [status, tick]);

  const handleStart = async () => {
    setBusy(true);
    setError(null);
    try {
      const payload = {
        interval,
        quick: true,
        server_id: serverId || null,
      };
      if (interval === "custom") {
        payload.custom_seconds = Math.max(1, Number(customMinutes) || 1) * 60;
      }
      const data = await startMonitoring(payload);
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const handleStop = async () => {
    setBusy(true);
    setError(null);
    try {
      const data = await stopMonitoring();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const enabled = Boolean(status?.enabled);
  const last = status?.last_measurement;

  return (
    <motion.div
      className="sq-view mon-view"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
    >
      <GlassCard className="iq-panel" hover={false} delay={0.04}>
        <PanelHeader
          title="Continuous QoS Monitoring"
          subtitle="Automatically measure and store network quality on a schedule"
          action={
            <SoftButton variant="ghost" onClick={onBack}>
              Back to dashboard
            </SoftButton>
          }
        />

        {error && (
          <p className="mon-error" role="alert">
            {error}
          </p>
        )}

        <div className="mon-controls">
          <label className="mon-field">
            <span>Interval</span>
            <select
              value={interval}
              disabled={enabled || busy}
              onChange={(e) => setIntervalPreset(e.target.value)}
            >
              {INTERVAL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          {interval === "custom" && (
            <label className="mon-field">
              <span>Custom (minutes)</span>
              <input
                type="number"
                min={1}
                max={1440}
                value={customMinutes}
                disabled={enabled || busy}
                onChange={(e) => setCustomMinutes(e.target.value)}
              />
            </label>
          )}

          <label className="mon-field">
            <span>Server</span>
            <select
              value={serverId}
              disabled={enabled || busy}
              onChange={(e) => setServerId(e.target.value)}
            >
              <option value="">Default / Auto</option>
              {servers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} · {s.location}
                </option>
              ))}
            </select>
          </label>

          <div className="mon-actions">
            {!enabled ? (
              <SoftButton onClick={handleStart} loading={busy} disabled={busy}>
                <Play size={16} strokeWidth={2.25} />
                Start monitoring
              </SoftButton>
            ) : (
              <SoftButton variant="ghost" onClick={handleStop} loading={busy} disabled={busy}>
                <Square size={16} strokeWidth={2.25} />
                Stop monitoring
              </SoftButton>
            )}
          </div>
        </div>
      </GlassCard>

      <div className="mon-status-grid">
        <GlassCard className="mon-stat" delay={0.06}>
          <span className="mon-stat-icon" aria-hidden="true">
            <Activity size={18} />
          </span>
          <p className="mon-stat-label">Monitoring Status</p>
          <p className={`mon-stat-value ${enabled ? "on" : "off"}`}>
            {enabled ? (status?.running ? "Measuring" : "Active") : "Stopped"}
          </p>
        </GlassCard>

        <GlassCard className="mon-stat" delay={0.08}>
          <span className="mon-stat-icon" aria-hidden="true">
            <Clock size={18} />
          </span>
          <p className="mon-stat-label">Last Measurement</p>
          <p className="mon-stat-value compact">
            {last?.timestamp ? formatDateTime(last.timestamp) : "—"}
          </p>
        </GlassCard>

        <GlassCard className="mon-stat" delay={0.1}>
          <span className="mon-stat-icon" aria-hidden="true">
            <Timer size={18} />
          </span>
          <p className="mon-stat-label">Next Measurement</p>
          <p className="mon-stat-value compact">{nextDisplay}</p>
        </GlassCard>

        <GlassCard className="mon-stat" delay={0.12}>
          <span className="mon-stat-icon" aria-hidden="true">
            <Gauge size={18} />
          </span>
          <p className="mon-stat-label">Monitoring Duration</p>
          <p className="mon-stat-value compact">{durationDisplay}</p>
        </GlassCard>

        <GlassCard className="mon-stat" delay={0.14}>
          <span className="mon-stat-icon" aria-hidden="true">
            <Wifi size={18} />
          </span>
          <p className="mon-stat-label">Number of Measurements</p>
          <p className="mon-stat-value">{status?.measurement_count ?? 0}</p>
        </GlassCard>
      </div>

      {last && (
        <GlassCard className="iq-panel compact" delay={0.16}>
          <PanelHeader
            title="Latest monitoring sample"
            subtitle={
              status?.interval
                ? `Interval · ${status.interval} (${status.interval_seconds}s)`
                : "Most recent stored result"
            }
          />
          <div className="mon-last-grid">
            <div>
              <span>Download</span>
              <strong>
                {last.download_mbps != null
                  ? `${formatNumber(last.download_mbps, 1)} Mbps`
                  : "—"}
              </strong>
            </div>
            <div>
              <span>Upload</span>
              <strong>
                {last.upload_mbps != null
                  ? `${formatNumber(last.upload_mbps, 1)} Mbps`
                  : "—"}
              </strong>
            </div>
            <div>
              <span>Ping</span>
              <strong>
                {last.ping_ms != null ? `${formatNumber(last.ping_ms, 0)} ms` : "—"}
              </strong>
            </div>
            <div>
              <span>Jitter</span>
              <strong>
                {last.jitter_ms != null
                  ? `${formatNumber(last.jitter_ms, 1)} ms`
                  : "—"}
              </strong>
            </div>
            <div>
              <span>Loss</span>
              <strong>
                {last.packet_loss_pct != null
                  ? `${formatNumber(last.packet_loss_pct, 2)} %`
                  : "—"}
              </strong>
            </div>
            <div>
              <span>Score</span>
              <strong className={ratingClass(last.overall_rating)}>
                {last.overall_score != null
                  ? `${last.overall_score}/100 · ${last.overall_rating || "—"}`
                  : "—"}
              </strong>
            </div>
          </div>
          {status?.last_error && (
            <p className="mon-error" role="status">
              Last error: {status.last_error}
            </p>
          )}
        </GlassCard>
      )}
    </motion.div>
  );
}
