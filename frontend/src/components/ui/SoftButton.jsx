import { motion } from "framer-motion";

/**
 * Premium button with soft shadow, hover scale, ripple highlight, and loading state.
 */
export default function SoftButton({
  children,
  variant = "primary",
  loading = false,
  className = "",
  disabled,
  type = "button",
  ...rest
}) {
  const onMove = (event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    event.currentTarget.style.setProperty("--rx", `${event.clientX - rect.left}px`);
    event.currentTarget.style.setProperty("--ry", `${event.clientY - rect.top}px`);
  };

  return (
    <motion.button
      type={type}
      className={`ui-btn ui-btn-${variant} ${loading ? "is-loading" : ""} ${className}`.trim()}
      disabled={disabled || loading}
      whileHover={disabled || loading ? undefined : { scale: 1.03, y: -1 }}
      whileTap={disabled || loading ? undefined : { scale: 0.97 }}
      transition={{ type: "spring", stiffness: 420, damping: 24 }}
      {...rest}
      onMouseMove={onMove}
    >
      <span className="ui-btn-label">{children}</span>
      {loading && <span className="ui-btn-spinner" aria-hidden="true" />}
    </motion.button>
  );
}
