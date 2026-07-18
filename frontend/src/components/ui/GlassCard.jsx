import { motion } from "framer-motion";

/**
 * Premium glassmorphic card shell used across the dashboard.
 */
export default function GlassCard({
  children,
  className = "",
  as = "section",
  hover = true,
  delay = 0,
  ...rest
}) {
  const MotionTag = motion[as] || motion.section;
  return (
    <MotionTag
      className={`ui-card glass ${hover ? "ui-card-hover" : ""} ${className}`.trim()}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1], delay }}
      {...rest}
    >
      {children}
    </MotionTag>
  );
}
