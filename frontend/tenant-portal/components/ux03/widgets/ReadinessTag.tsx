"use client";
/**
 * DESIGN PHASE UX-03 — dev-only readiness indicator. NEVER render this in a
 * production/customer-facing surface; it is metadata for engineers/design
 * review only (see readiness-state-registry.csv).
 */
import React from "react";
import type { ReadinessState } from "../../../lib/ux03/types";

const LABEL: Record<ReadinessState, string> = {
  PRODUCTION_READY: "Production Ready",
  READ_ONLY_READY: "Read-Only Ready",
  MOCK_DESIGN_ONLY: "Mock / Design Only",
  API_CONTRACT_REQUIRED: "API Contract Required",
  SECURITY_CONTRACT_PENDING: "Security Contract Pending",
  PRODUCT_DECISION_REQUIRED: "Product Decision Required",
  DEPRECATED: "Deprecated",
  NOT_APPLICABLE: "Not Applicable",
};

const COLOR: Record<ReadinessState, string> = {
  PRODUCTION_READY: "var(--success-text)",
  READ_ONLY_READY: "var(--info-text)",
  MOCK_DESIGN_ONLY: "var(--neutral-text)",
  API_CONTRACT_REQUIRED: "var(--warning-text)",
  SECURITY_CONTRACT_PENDING: "var(--danger-text)",
  PRODUCT_DECISION_REQUIRED: "var(--warning-text)",
  DEPRECATED: "var(--danger-text)",
  NOT_APPLICABLE: "var(--neutral-text)",
};

export function ReadinessTag({ state }: { state: ReadinessState }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        fontSize: "0.625rem",
        fontWeight: 600,
        letterSpacing: "0.02em",
        textTransform: "uppercase",
        color: COLOR[state],
        border: `1px solid ${COLOR[state]}`,
        borderRadius: "var(--radius-full)",
        padding: "0.0625rem 0.5rem",
      }}
      title="Dev-only metadata — never shown to real users"
    >
      {LABEL[state]}
    </span>
  );
}
