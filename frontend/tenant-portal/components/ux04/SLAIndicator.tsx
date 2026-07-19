"use client";
/**
 * DESIGN PHASE UX-04 — shared SLA/risk badge. Used by list rows, dashboard
 * alerts, and detail-page headers. Values come from SLAStateView only —
 * never computed client-side from invented rules.
 */
import React from "react";
import type { SLAStateView } from "../../lib/ux04/types";

const COLOR: Record<SLAStateView["state"], string> = {
  on_track: "var(--success-text)",
  approaching_deadline: "var(--warning-text)",
  at_risk: "var(--warning-text)",
  breached: "var(--danger-text)",
  blocked: "var(--danger-text)",
  waiting_on_customer: "var(--info-text)",
  waiting_on_provider: "var(--info-text)",
  waiting_on_platform: "var(--info-text)",
  product_decision_blocked: "var(--neutral-text)",
};

export function SLAIndicator({ sla }: { sla: SLAStateView }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.375rem",
        fontSize: "0.75rem",
        fontWeight: 600,
        color: COLOR[sla.state],
      }}
      title={sla.explanation}
    >
      <span
        aria-hidden
        style={{ width: "0.5rem", height: "0.5rem", borderRadius: "var(--radius-full)", background: COLOR[sla.state], display: "inline-block" }}
      />
      {sla.label}
    </span>
  );
}
