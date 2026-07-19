"use client";
import React from "react";
import type { OperationalExceptionView } from "../../lib/ux04/types";

/** DESIGN PHASE UX-04 — read-only operational exception explanation. This is
 * NOT an active Booking Exception Resolution engine (that stays blocked
 * product-side) — it only explains the exception, lists safe actions, and
 * an escalation path. */
export function OperationalRiskBanner({ exception }: { exception: OperationalExceptionView }) {
  return (
    <div style={{ border: "1px solid var(--warning-text)", borderRadius: "var(--radius-md)", padding: "0.75rem 1rem", background: "var(--warning-bg, transparent)" }}>
      <p style={{ margin: 0, fontWeight: 600, color: "var(--warning-text)" }}>{exception.kind.replace(/_/g, " ")}</p>
      <p style={{ fontSize: "0.8125rem", margin: "0.25rem 0" }}>{exception.explanation}</p>
      <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Affects: {exception.affectedWorkflow}</p>
      {exception.safeActions.length > 0 && (
        <ul style={{ fontSize: "0.75rem", margin: "0.25rem 0", paddingLeft: "1rem" }}>
          {exception.safeActions.map((a) => (
            <li key={a}>{a}</li>
          ))}
        </ul>
      )}
      {exception.escalationPath && <p style={{ fontSize: "0.75rem", color: "var(--info-text)" }}>Escalation: {exception.escalationPath}</p>}
    </div>
  );
}
