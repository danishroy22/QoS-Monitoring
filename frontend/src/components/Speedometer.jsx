import { animate, motion, useMotionValue, useMotionValueEvent, useTransform } from "framer-motion";
import { useEffect, useId, useMemo, useState } from "react";

/**
 * Premium 270° SmartQoS speedometer.
 * Original SVG + Framer Motion design for a commercial broadband test look.
 */
const START_ANGLE = 135; // deg, SVG math coords (0 = east)
const SWEEP = 270;
const CX = 200;
const CY = 200;
const RADIUS = 152;
const TRACK_WIDTH = 16;
const PROGRESS_WIDTH = 22;

function polar(cx, cy, r, angleDeg) {
  const rad = (angleDeg * Math.PI) / 180;
  return {
    x: cx + r * Math.cos(rad),
    y: cy + r * Math.sin(rad),
  };
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polar(cx, cy, r, startAngle);
  const end = polar(cx, cy, r, endAngle);
  const delta = ((endAngle - startAngle) % 360 + 360) % 360;
  const largeArc = delta > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}

function phaseMode(phase) {
  if (phase === "jitter") return { title: "JITTER", unit: "ms" };
  if (phase === "ping") return { title: "PING", unit: "ms" };
  if (phase === "upload") return { title: "UPLOAD", unit: "Mbps" };
  if (phase === "download" || phase === "calculate" || phase === "results" || phase === "done") {
    return { title: "DOWNLOAD", unit: "Mbps" };
  }
  if (phase === "ai") return { title: "ANALYSIS", unit: "Mbps" };
  if (phase === "server" || phase === "init" || phase === "idle") {
    return { title: phase === "idle" ? "READY" : phase === "init" ? "INITIALIZING" : "SERVER", unit: "Mbps" };
  }
  return { title: "DOWNLOAD", unit: "Mbps" };
}

export default function Speedometer({
  value = 0,
  max = 500,
  phase = "idle",
  onGo,
  disabled = false,
  pingMs = null,
  jitterMs = null,
  packetLossPct = null,
  elapsedSec = null,
}) {
  const uid = useId().replace(/:/g, "");
  const mode = phaseMode(phase);
  const isMsGauge = mode.unit === "ms";
  const gaugeMax = isMsGauge ? Math.max(20, max) : Math.max(100, max);
  const busy = phase !== "idle" && phase !== "done";
  const showGo = !busy;

  const motionValue = useMotionValue(0);
  const display = useTransform(motionValue, (v) =>
    Number.isFinite(v) ? (mode.unit === "ms" ? v.toFixed(0) : v.toFixed(2)) : "0.00"
  );
  const progressMV = useMotionValue(0.001);

  useEffect(() => {
    const target = Math.max(0, Number(value) || 0);
    // Snap to zero during init / server discovery so the needle does not linger.
    const snap = target === 0 || phase === "init" || phase === "server" || phase === "idle";
    if (snap && target === 0) {
      motionValue.set(0);
      return undefined;
    }
    const controls = animate(motionValue, target, {
      type: "spring",
      stiffness: 36,
      damping: 22,
      mass: 1.05,
    });
    return controls.stop;
  }, [value, motionValue, phase]);

  useEffect(() => {
    const ratio = Math.min(1, Math.max(0, (Number(value) || 0) / gaugeMax));
    const snap = ratio <= 0.001 || phase === "init" || phase === "server" || phase === "idle";
    if (snap && ratio <= 0.001) {
      progressMV.set(0.001);
      return undefined;
    }
    const controls = animate(progressMV, Math.max(0.001, ratio), {
      type: "spring",
      stiffness: 32,
      damping: 24,
      mass: 1.1,
    });
    return controls.stop;
  }, [value, gaugeMax, progressMV, phase]);

  const arcLength = useMemo(() => (SWEEP * Math.PI * RADIUS) / 180, []);
  const trackPath = useMemo(
    () => describeArc(CX, CY, RADIUS, START_ANGLE, START_ANGLE + SWEEP),
    []
  );

  const ticks = useMemo(() => {
    const items = [];
    const step = isMsGauge ? Math.max(5, Math.round(gaugeMax / 10)) : 10;
    for (let mark = 0; mark <= gaugeMax; mark += step) {
      const t = mark / gaugeMax;
      const angle = START_ANGLE + t * SWEEP;
      const major = isMsGauge ? mark % (step * 2) === 0 : mark % 100 === 0;
      const inner = major ? RADIUS - 22 : RADIUS - 14;
      const outer = RADIUS - 4;
      const a = polar(CX, CY, inner, angle);
      const b = polar(CX, CY, outer, angle);
      items.push({ mark, major, a, b, angle });
    }
    return items;
  }, [gaugeMax, isMsGauge]);

  const [needleDeg, setNeedleDeg] = useState(START_ANGLE + 90);
  useMotionValueEvent(progressMV, "change", (p) => {
    setNeedleDeg(START_ANGLE + p * SWEEP + 90);
  });
  const dashOffset = useTransform(progressMV, (p) => arcLength * (1 - p));

  const fmt = (n, digits = 1) =>
    n == null || Number.isNaN(Number(n)) ? "—" : Number(n).toFixed(digits);

  return (
    <div className="sq-speedometer premium" data-phase={phase}>
      <div className="sq-gauge-glass">
        <div className="sq-corner sq-corner-tl">
          <span>Ping</span>
          <strong>{fmt(pingMs, 0)}<small> ms</small></strong>
        </div>
        <div className="sq-corner sq-corner-tr">
          <span>Jitter</span>
          <strong>{fmt(jitterMs, 1)}<small> ms</small></strong>
        </div>
        <div className="sq-corner sq-corner-bl">
          <span>Packet Loss</span>
          <strong>{fmt(packetLossPct, 2)}<small> %</small></strong>
        </div>
        <div className="sq-corner sq-corner-br">
          <span>Elapsed Time</span>
          <strong>{fmt(elapsedSec, 0)}<small> s</small></strong>
        </div>

        <svg
          viewBox="0 0 400 400"
          className="sq-gauge-svg"
          role="img"
          aria-label={`${mode.title} ${value} ${mode.unit}`}
        >
          <defs>
            <linearGradient id={`sq-arc-${uid}`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#22d3ee" />
              <stop offset="45%" stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#a855f7" />
            </linearGradient>
            <radialGradient id={`sq-core-${uid}`} cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="rgba(56,189,248,0.18)" />
              <stop offset="70%" stopColor="rgba(5,8,22,0.2)" />
              <stop offset="100%" stopColor="rgba(5,8,22,0.65)" />
            </radialGradient>
            <filter id={`sq-glow-${uid}`} x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="5.5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          <circle cx={CX} cy={CY} r="178" fill={`url(#sq-core-${uid})`} />
          <circle
            cx={CX}
            cy={CY}
            r="178"
            fill="none"
            stroke="rgba(148,163,184,0.16)"
            strokeWidth="1"
          />

          {/* Thin background arc */}
          <path
            d={trackPath}
            fill="none"
            stroke="rgba(148,163,184,0.22)"
            strokeWidth={TRACK_WIDTH}
            strokeLinecap="round"
          />

          {/* Thick gradient progress arc */}
          <motion.path
            d={trackPath}
            fill="none"
            stroke={`url(#sq-arc-${uid})`}
            strokeWidth={PROGRESS_WIDTH}
            strokeLinecap="round"
            strokeDasharray={arcLength}
            style={{ strokeDashoffset: dashOffset }}
            filter={`url(#sq-glow-${uid})`}
          />

          {/* Tick marks */}
          {ticks.map((tick) => (
            <line
              key={tick.mark}
              x1={tick.a.x}
              y1={tick.a.y}
              x2={tick.b.x}
              y2={tick.b.y}
              stroke={tick.major ? "rgba(226,232,240,0.75)" : "rgba(148,163,184,0.35)"}
              strokeWidth={tick.major ? 2.4 : 1.2}
              strokeLinecap="round"
            />
          ))}

          {ticks
            .filter((t) => t.major)
            .map((tick) => {
              const labelPos = polar(CX, CY, RADIUS - 36, tick.angle);
              return (
                <text
                  key={`label-${tick.mark}`}
                  x={labelPos.x}
                  y={labelPos.y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="sq-tick-label"
                  fill="rgba(148,163,184,0.7)"
                  fontSize="11"
                  fontFamily="IBM Plex Mono, monospace"
                >
                  {tick.mark}
                </text>
              );
            })}

          {/* Needle — SVG rotate around gauge centre for reliable easing */}
          <g transform={`rotate(${needleDeg} ${CX} ${CY})`}>
            <line
              x1={CX}
              y1={CY}
              x2={CX}
              y2={CY - RADIUS + 28}
              stroke="#f8fafc"
              strokeWidth="3.2"
              strokeLinecap="round"
              filter={`url(#sq-glow-${uid})`}
            />
            <circle cx={CX} cy={CY} r="11" fill="#e2e8f0" />
            <circle cx={CX} cy={CY} r="5.5" fill="#38bdf8" />
          </g>
        </svg>

        <div className="sq-gauge-readout">
          <motion.p
            key={mode.title}
            className="sq-gauge-mode"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {showGo ? "SMARTQOS" : mode.title}
          </motion.p>
          <p className="sq-gauge-number">
            <motion.span>{display}</motion.span>
          </p>
          <p className="sq-gauge-unit">{mode.unit}</p>

          {showGo && (
            <motion.button
              type="button"
              className="sq-go-btn"
              onClick={onGo}
              disabled={disabled}
              whileHover={{ scale: 1.06 }}
              whileTap={{ scale: 0.95 }}
            >
              GO
            </motion.button>
          )}
        </div>
      </div>
    </div>
  );
}
