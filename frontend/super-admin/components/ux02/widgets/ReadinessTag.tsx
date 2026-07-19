import React from "react";
import type { ReadinessState } from "../../../lib/ux02/types";

/**
 * Dev-only readiness indicator. Never render this component (or the
 * ReadinessState values it displays) in a production-facing route — it is
 * for /admin/dev/ux-02 showcase pages and internal review only.
 */
export function ReadinessTag({ readiness }: { readiness: ReadinessState }) {
  const color =
    readiness === "PRODUCTION_READY" ? "var(--success-text)" :
    readiness === "READ_ONLY_READY" ? "var(--info-text)" :
    readiness === "DEPRECATED" ? "var(--neutral-text)" :
    "var(--warning-text)";
  return (
    <span
      style={{ fontSize: "0.6875rem", fontWeight: 700, color, border: `1px solid ${color}`, borderRadius: "var(--radius-full)", padding: "0.125rem 0.5rem" }}
      title="Dev-only readiness metadata — never shown to real users"
    >
      {readiness.replace(/_/g, " ")}
    </span>
  );
}
