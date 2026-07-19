"use client";
/**
 * DESIGN PHASE UX-03 — one centralized profile-completion/review-state
 * banner, reused by the dashboard, business profile, and setup wizard
 * rather than re-implemented per page (see profile-completion-review-states.md).
 */
import React from "react";
import { StatusBadge } from "@serviceos/design-system";
import type { ProfileReviewState } from "../../../lib/ux03/types";

const COPY: Record<ProfileReviewState, { title: string; body: string }> = {
  not_started: { title: "Let's set up your business", body: "Complete the setup wizard to start accepting bookings." },
  in_progress: { title: "Setup in progress", body: "Pick up where you left off — your progress is saved." },
  ready_to_submit: { title: "Ready to submit", body: "All required sections are complete. Submit for review when ready." },
  submitted: { title: "Submitted for review", body: "Your application has been received." },
  under_review: { title: "Under review", body: "Our team is reviewing your business profile." },
  changes_requested: { title: "Changes requested", body: "Please address the items below and resubmit." },
  approved: { title: "Approved", body: "Your business is live on the platform." },
  rejected: { title: "Application rejected", body: "Contact support for next steps." },
  suspended: { title: "Account suspended", body: "Contact support to resolve this." },
};

export function ReviewStateBanner({
  state,
  completionPct,
  changesRequested,
}: {
  state: ProfileReviewState;
  completionPct?: number;
  changesRequested?: string[];
}) {
  const c = COPY[state];
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
        padding: "1rem 1.25rem",
        borderRadius: "var(--radius-lg)",
        border: "1px solid var(--border)",
        background: "var(--surface)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.75rem" }}>
        <div>
          <h3 className="ds-text-card-title" style={{ margin: 0 }}>{c.title}</h3>
          <p className="ds-text-body" style={{ margin: "0.25rem 0 0", color: "var(--text-secondary)" }}>{c.body}</p>
        </div>
        <StatusBadge status={state} />
      </div>
      {typeof completionPct === "number" && (
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <div style={{ flex: 1, height: 6, borderRadius: "var(--radius-full)", background: "var(--neutral-bg)", overflow: "hidden" }}>
            <div style={{ width: `${completionPct}%`, height: "100%", background: "var(--brand)" }} />
          </div>
          <span className="ds-text-body" style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>{completionPct}%</span>
        </div>
      )}
      {changesRequested && changesRequested.length > 0 && (
        <ul style={{ margin: 0, paddingLeft: "1.25rem", color: "var(--warning-text)" }}>
          {changesRequested.map((c, i) => (
            <li key={i} className="ds-text-body">{c}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
