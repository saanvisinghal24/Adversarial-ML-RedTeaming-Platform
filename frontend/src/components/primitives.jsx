/** Small shared pieces: severity/status marks, empty + error states, the page reveal. */
import { motion, useReducedMotion } from "framer-motion";

export function Reveal({ children, delay = 0, className = "" }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : { opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}

const SEVERITY_TONE = {
  critical: "text-signal border-signal",
  high: "text-signal border-signal",
  medium: "text-kraft border-kraft",
  low: "text-muted border-rule",
};

export function SeverityTag({ severity }) {
  return (
    <span
      className={`border px-2 py-0.5 text-[10px] uppercase tracking-[0.14em] ${
        SEVERITY_TONE[severity] ?? SEVERITY_TONE.low
      }`}
    >
      {severity}
    </span>
  );
}

const STATUS_COPY = {
  queued: "Queued",
  running: "Running",
  done: "Complete",
  failed: "Failed",
};

export function StatusMark({ status }) {
  const live = status === "queued" || status === "running";
  return (
    <span className="inline-flex items-center gap-2 text-[13px]">
      <span
        className={`h-2 w-2 rounded-full ${
          status === "failed" ? "bg-signal" : status === "done" ? "bg-moss" : "bg-kraft"
        } ${live ? "animate-pulse" : ""}`}
      />
      {STATUS_COPY[status] ?? status}
    </span>
  );
}

export function GradeMark({ grade, score }) {
  const tone = ["A", "B"].includes(grade) ? "text-moss" : grade === "C" ? "text-kraft" : "text-signal";
  return (
    <div className="flex items-end gap-6">
      <span className={`font-display text-[9rem] font-bold leading-[0.72] ${tone}`}>{grade}</span>
      <span className="t-data pb-2 text-4xl font-semibold">
        {score.toFixed(1)}
        <span className="text-base font-normal text-muted"> / 100</span>
      </span>
    </div>
  );
}

export function Notice({ title, children, tone = "neutral", action }) {
  return (
    <div
      className={`border-l-2 py-4 pl-5 ${tone === "error" ? "border-signal" : "border-rule"}`}
      role={tone === "error" ? "alert" : undefined}
    >
      <p className="t-sub mb-1">{title}</p>
      {children ? <p className="max-w-measure text-[15px] text-muted">{children}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function Skeleton({ lines = 3 }) {
  return (
    <div className="space-y-3" aria-hidden>
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-3 w-full animate-pulse bg-panel" style={{ width: `${90 - i * 12}%` }} />
      ))}
    </div>
  );
}
