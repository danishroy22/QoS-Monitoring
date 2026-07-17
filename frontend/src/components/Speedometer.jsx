import { animate, motion, useMotionValue, useTransform } from "framer-motion";
import { useEffect, useId } from "react";

/**
 * Premium animated SmartQoS speedometer.
 * Always-visible semicircle gauge with needle, progress arc, and GO control.
 */
export default function Speedometer({
  value = 0,
  max = 200,
  label = "Mbps",
  phase = "idle",
  onGo,
  disabled = false,
}) {
  const uid = useId().replace(/:/g, "");
  const motionValue = useMotionValue(0);
  const rounded = useTransform(motionValue, (latest) =>
    Number.isFinite(latest) ? latest.toFixed(1) : "0.0"
  );

  useEffect(() => {
    const controls = animate(motionValue, Number(value) || 0, {
      duration: 0.8,
      ease: "easeOut",
    });
    return controls.stop;
  }, [value, motionValue]);

  const clamped = Math.max(0, Math.min(Number(value) || 0, max));
  const progress = clamped / max;
  const needleAngle = -120 + progress * 240;

  // Semicircle path length approximation for stroke-dash progress
  const arcLength = 345;
  const dashOffset = arcLength * (1 - Math.max(progress, 0.02));

  const busy = phase !== "idle" && phase !== "done";
  const showGo = !busy;

  return (
    <div className="sq-speedometer" data-phase={phase}>
      <svg
        viewBox="0 0 320 240"
        className="sq-gauge-svg"
        role="img"
        aria-label={`Speedometer ${value} ${label}`}
      >
        <defs>
          <linearGradient id={`sq-ring-${uid}`} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#22d3ee" />
            <stop offset="50%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="#818cf8" />
          </linearGradient>
          <filter id={`sq-glow-${uid}`} x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Background plate */}
        <circle cx="160" cy="150" r="118" fill="rgba(15,23,42,0.55)" stroke="rgba(148,163,184,0.25)" strokeWidth="1" />

        {/* Track — upper semicircle (clearly visible) */}
        <path
          d="M 42 168 A 118 118 0 0 1 278 168"
          fill="none"
          stroke="rgba(148,163,184,0.35)"
          strokeWidth="16"
          strokeLinecap="round"
        />

        {/* Progress */}
        <path
          d="M 42 168 A 118 118 0 0 1 278 168"
          fill="none"
          stroke={`url(#sq-ring-${uid})`}
          strokeWidth="16"
          strokeLinecap="round"
          strokeDasharray={arcLength}
          strokeDashoffset={dashOffset}
          filter={`url(#sq-glow-${uid})`}
          style={{ transition: "stroke-dashoffset 0.45s ease-out" }}
        />

        {/* Ticks */}
        {Array.from({ length: 9 }).map((_, i) => {
          const deg = -120 + (i / 8) * 240;
          const rad = (deg * Math.PI) / 180;
          const x1 = 160 + Math.cos(rad) * 92;
          const y1 = 150 + Math.sin(rad) * 92;
          const x2 = 160 + Math.cos(rad) * 104;
          const y2 = 150 + Math.sin(rad) * 104;
          return (
            <line
              key={i}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="rgba(226,232,240,0.55)"
              strokeWidth={i % 2 === 0 ? 2.5 : 1.5}
            />
          );
        })}

        {/* Needle */}
        <g transform={`rotate(${needleAngle} 160 150)`}>
          <line
            x1="160"
            y1="150"
            x2="160"
            y2="48"
            stroke="#f8fafc"
            strokeWidth="3.5"
            strokeLinecap="round"
            filter={`url(#sq-glow-${uid})`}
          />
          <circle cx="160" cy="150" r="10" fill="#e2e8f0" />
          <circle cx="160" cy="150" r="5" fill="#0ea5e9" />
        </g>
      </svg>

      <div className="sq-gauge-readout">
        <p className="sq-gauge-number">
          <motion.span>{rounded}</motion.span>
        </p>
        <p className="sq-gauge-unit">{label}</p>

        {showGo ? (
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
        ) : (
          <p className="sq-phase-chip">{phaseLabel(phase)}</p>
        )}
      </div>
    </div>
  );
}

function phaseLabel(phase) {
  const map = {
    init: "Initializing",
    server: "Selecting server",
    ping: "Testing ping",
    download: "Download",
    upload: "Upload",
    calculate: "Calculating",
    ai: "AI analysis",
    results: "Complete",
  };
  return map[phase] || phase;
}
