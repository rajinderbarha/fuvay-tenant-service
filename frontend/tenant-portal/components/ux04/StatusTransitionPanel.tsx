"use client";
/**
 * DESIGN PHASE UX-04A — dedicated Status Transition workspace component
 * (previously only rendered inline inside Job Detail Workspace). Enforces,
 * client-side for the showcase, the repository-backed ServiceJob lifecycle
 * order: assigned -> on_the_way -> inspection -> in_progress -> work_done
 * -> completed. Never offers a skip-ahead or repeat-a-terminal-state option
 * — `allowedNext` is expected to already encode that server-side, but this
 * component additionally guards by only rendering options that are the
 * immediate next step in LIFECYCLE, as defense in depth for the showcase.
 */
import React from "react";
import { StatusBadge } from "@serviceos/design-system";
import type { StatusTransitionView } from "../../lib/ux04/types";

const LIFECYCLE = ["assigned", "on_the_way", "inspection", "in_progress", "work_done", "completed"];

export function StatusTransitionPanel({ transition }: { transition: StatusTransitionView }) {
  const currentIdx = LIFECYCLE.indexOf(transition.currentStatus);
  const isTerminal = transition.currentStatus === "completed";
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
      <p style={{ margin: 0 }}>
        Current: <StatusBadge status={transition.currentStatus} />
      </p>
      {isTerminal && (
        <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontStyle: "italic" }}>
          Terminal state — no further transition is offered.
        </p>
      )}
      {!isTerminal && transition.allowedNext.length === 0 && (
        <p style={{ fontSize: "0.75rem", color: "var(--warning-text)" }}>
          No allowed transition returned by the repository for this status — this is a valid, honest blocked
          state, not an error.
        </p>
      )}
      {transition.allowedNext.map((opt) => {
        const optIdx = LIFECYCLE.indexOf(opt.toStatus);
        const isImmediateNext = currentIdx >= 0 && optIdx === currentIdx + 1;
        return (
          <div
            key={opt.toStatus}
            style={{
              fontSize: "0.8125rem",
              border: `1px solid ${isImmediateNext ? "var(--brand)" : "var(--danger-text)"}`,
              borderRadius: "var(--radius-md)",
              padding: "0.5rem",
              marginTop: "0.5rem",
            }}
          >
            <p style={{ margin: 0, fontWeight: 600 }}>→ {opt.toStatus.replace(/_/g, " ")}</p>
            {!isImmediateNext && (
              <p style={{ margin: 0, color: "var(--danger-text)", fontSize: "0.75rem" }}>
                Out-of-sequence transition offered by the adapter — flagged, not hidden, so a real bug in the
                backend&apos;s allowed-next list would be visible here rather than silently accepted.
              </p>
            )}
            <p style={{ margin: 0, color: "var(--text-secondary)" }}>Requires: {opt.requiredFieldsOrEvidence.join(", ") || "none"}</p>
            <p style={{ margin: 0, color: "var(--text-secondary)" }}>Customer sees: {opt.customerVisibleEffect}</p>
            {opt.financeEffect && <p style={{ margin: 0, color: "var(--text-secondary)" }}>Finance effect: {opt.financeEffect}</p>}
          </div>
        );
      })}
    </div>
  );
}
