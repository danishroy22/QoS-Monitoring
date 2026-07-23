import { animate, motion, useMotionValue, useMotionValueEvent, useTransform } from "framer-motion";
import { useEffect, useId, useMemo, useState } from "react";

/**
 * Premium 270° SmartQoS speedometer (gauge + centre readout + GO only).
 * Dashboard metric cards live outside this component.
 */
const START_ANGLE = 135;
const SWEEP = 270;
const CX = 220;
const CY = 220;
const RADIUS = 168;
const TRACK_WIDTH = 14;
const PROGRESS_WIDTH = 24;
const VIEW = 440;

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
  if (phase === "jitter") return { title: "JITTER", subtitle: "Current Jitter", unit: "ms" };
  if (phase === "ping") return { title: "PING", subtitle: "Current Latency", unit: "ms" };
  if (phase === "upload") return { title: "UPLOAD", subtitle: "Current Speed", unit: "Mbps" };
  if (phase === "download" || phase === "calculate" || phase === "results" || phase === "done") {
    return { title: "DOWNLOAD", subtitle: "Current Speed", unit: "Mbps" };
  }
  if (phase === "ai") return { title: "ANALYSIS", subtitle: "Peak Download", unit: "Mbps" };
  if (phase === "server") return { title: "SERVER", subtitle: "Current Speed", unit: "Mbps" };
  if (phase === "init") return { title: "INITIALIZING", subtitle: "Current Speed", unit: "Mbps" };
  return { title: "DOWNLOAD", subtitle: "Current Speed", unit: "Mbps" };
}

export default function Speedometer({
  value = 0,
  max = 500,
  phase = "idle",
  onGo,
  disabled = false,
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
    const snap = target === 0 || phase === "init" || phase === "server" || phase === "idle";
    if (snap && target === 0) {
      motionValue.set(0);
      return undefined;
    }
    const controls = animate(motionValue, target, {
      type: "spring",
      stiffness: 34,
      damping: 24,
      mass: 1.1,
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
      stiffness: 30,
      damping: 26,
      mass: 1.15,
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
      const inner = major ? RADIUS - 18 : RADIUS - 12;
      const outer = RADIUS - 2;
      const a = polar(CX, CY, inner, angle);
      const b = polar(CX, CY, outer, angle);
      const labelPos = polar(CX, CY, RADIUS + 22, angle);
      items.push({ mark, major, a, b, labelPos });
    }
    return items;
  }, [gaugeMax, isMsGauge]);

  const [needleDeg, setNeedleDeg] = useState(START_ANGLE + 90);
  useMotionValueEvent(progressMV, "change", (p) => {
    setNeedleDeg(START_ANGLE + p * SWEEP + 90);
  });
  const dashOffset = useTransform(progressMV, (p) => arcLength * (1 - p));

  const centreTitle = showGo ? "DOWNLOAD" : mode.title;

  return (
    <div className="sq-speedometer premium" data-phase={phase}>
      <div className="sq-gauge-core centered">
        <div className="sq-gauge-ring">
          <svg
            viewBox={`0 0 ${VIEW} ${VIEW}`}
            className="sq-gauge-svg"
            role="img"
            aria-label={`${centreTitle} ${value} ${mode.unit}`}
          >
            <defs>
              <linearGradient id={`sq-arc-${uid}`} x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#06b6d4" />
                <stop offset="50%" stopColor="#3b82f6" />
                <stop offset="100%" stopColor="#7c3aed" />
              </linearGradient>
              <radialGradient id={`sq-core-${uid}`} cx="50%" cy="48%" r="52%">
                <stop offset="0%" stopColor="rgba(15, 23, 42, 0.15)" />
                <stop offset="100%" stopColor="rgba(5, 8, 22, 0.55)" />
              </radialGradient>
              <filter id={`sq-glow-${uid}`} x="-55%" y="-55%" width="210%" height="210%">
                <feGaussianBlur stdDeviation="6" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            <circle cx={CX} cy={CY} r={RADIUS + 36} fill={`url(#sq-core-${uid})`} />

            <path
              d={trackPath}
              fill="none"
              stroke="rgba(148,163,184,0.2)"
              strokeWidth={TRACK_WIDTH}
              strokeLinecap="round"
            />

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

            {ticks.map((tick) => (
              <line
                key={tick.mark}
                x1={tick.a.x}
                y1={tick.a.y}
                x2={tick.b.x}
                y2={tick.b.y}
                stroke={tick.major ? "rgba(226,232,240,0.7)" : "rgba(148,163,184,0.28)"}
                strokeWidth={tick.major ? 2.2 : 1.1}
                strokeLinecap="round"
              />
            ))}

            {ticks
              .filter((t) => t.major)
              .map((tick) => (
                <text
                  key={`label-${tick.mark}`}
                  x={tick.labelPos.x}
                  y={tick.labelPos.y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="rgba(203,213,225,0.85)"
                  fontSize="12"
                  fontWeight="600"
                  fontFamily="IBM Plex Mono, monospace"
                >
                  {tick.mark}
                </text>
              ))}

            <g transform={`rotate(${needleDeg} ${CX} ${CY})`}>
              <line
                x1={CX}
                y1={CY}
                x2={CX}
                y2={CY - RADIUS + 32}
                stroke="#f8fafc"
                strokeWidth="3.4"
                strokeLinecap="round"
                filter={`url(#sq-glow-${uid})`}
              />
            </g>
          </svg>

          <div className="sq-gauge-readout">
            <motion.p
              key={centreTitle}
              className="sq-gauge-mode"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.28 }}
            >
              {centreTitle}
            </motion.p>
            <p className="sq-gauge-subtitle">{showGo ? "Current Speed" : mode.subtitle}</p>
            <p className="sq-gauge-number">
              <motion.span>{display}</motion.span>
            </p>
            <p className="sq-gauge-unit">{mode.unit}</p>
          </div>
        </div>

        {showGo && (
          <motion.button
            type="button"
            className="sq-go-btn"
            onClick={onGo}
            disabled={disabled}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.96 }}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
          >
            GO
          </motion.button>
        )}
      </div>
    </div>
  );
}
