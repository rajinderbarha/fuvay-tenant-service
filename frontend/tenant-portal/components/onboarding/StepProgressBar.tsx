"use client";
import React from "react";

/**
 * Thin horizontal step indicator ("Step N of M") used at the top of every
 * onboarding wizard page, matching the reference design. Previously this
 * was plain text with no visual bar.
 */
export function StepProgressBar({ step, total }: { step: number; total: number }) {
  const pct = Math.round((step / total) * 100);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "8px 0 24px" }}>
      <span style={{ fontSize: 12.5, fontWeight: 700, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
        Step {step} of {total}
      </span>
      <div style={{ flex: 1, height: 5, borderRadius: 999, background: "var(--border)", overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: "var(--brand)", transition: "width 0.25s ease" }} />
      </div>
    </div>
  );
}
