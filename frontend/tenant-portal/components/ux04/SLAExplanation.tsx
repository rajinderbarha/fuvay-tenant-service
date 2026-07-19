"use client";
/**
 * DESIGN PHASE UX-04A — expanded SLA/risk explanation panel, complementing
 * the compact SLAIndicator badge. Used on a dedicated SLA-risk gallery
 * page to enumerate all 9 SLAState values with their explanations.
 */
import React from "react";
import { SLAIndicator } from "./SLAIndicator";
import type { SLAStateView } from "../../lib/ux04/types";

export function SLAExplanation({ sla }: { sla: SLAStateView }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "0.75rem 1rem" }}>
      <SLAIndicator sla={sla} />
      <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", margin: "0.375rem 0 0" }}>{sla.explanation}</p>
      {sla.deadlineAt && <p style={{ fontSize: "0.6875rem", color: "var(--text-secondary)" }}>Deadline: {sla.deadlineAt}</p>}
    </div>
  );
}
