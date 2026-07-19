"use client";
/**
 * DESIGN PHASE UX-03 — shared setup-wizard pattern. Backs the first-time
 * business setup flow AND the multi-service setup wizard (both use the
 * same step/progress/save-resume shape). Canonical stages for business
 * setup: account created -> business profile -> registration/tax ->
 * owner info -> address -> service categories -> service areas -> team
 * setup -> package/deposit requirements -> review summary -> submit ->
 * under review -> approved/rejected/changes-requested.
 */
import React, { useState } from "react";
import { PageHeader } from "@serviceos/design-system";

export interface WizardStep {
  id: string;
  label: string;
  optional?: boolean;
  blocked?: boolean; // e.g. depends on an earlier step / backend gate not ready
  render: (ctx: { goNext: () => void; goBack: () => void }) => React.ReactNode;
}

export function SetupWizard({
  title,
  description,
  steps,
  initialStepIndex = 0,
  onSaveDraft,
}: {
  title: string;
  description?: string;
  steps: WizardStep[];
  initialStepIndex?: number;
  onSaveDraft?: (stepId: string) => void;
}) {
  const [index, setIndex] = useState(initialStepIndex);
  const step = steps[index];
  const pct = Math.round(((index + 1) / steps.length) * 100);

  function goNext() {
    onSaveDraft?.(step.id);
    setIndex((i) => Math.min(i + 1, steps.length - 1));
  }
  function goBack() {
    setIndex((i) => Math.max(i - 1, 0));
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <PageHeader title={title} description={description} />
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
        <div style={{ flex: 1, height: 6, borderRadius: "var(--radius-full)", background: "var(--neutral-bg)", overflow: "hidden" }}>
          <div style={{ width: `${pct}%`, height: "100%", background: "var(--brand)" }} />
        </div>
        <span className="ds-text-body" style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
          Step {index + 1} of {steps.length} ({pct}%)
        </span>
      </div>
      <nav aria-label="Setup steps" style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        {steps.map((s, i) => (
          <button
            key={s.id}
            type="button"
            disabled={s.blocked}
            onClick={() => setIndex(i)}
            aria-current={i === index ? "step" : undefined}
            style={{
              fontSize: "0.75rem",
              padding: "0.25rem 0.625rem",
              borderRadius: "var(--radius-full)",
              border: `1px solid ${i === index ? "var(--brand)" : "var(--border)"}`,
              background: i === index ? "var(--accent-muted)" : "transparent",
              color: s.blocked ? "var(--text-secondary)" : i === index ? "var(--brand)" : "var(--text-primary)",
              cursor: s.blocked ? "not-allowed" : "pointer",
            }}
          >
            {s.label}{s.optional ? " (optional)" : ""}
          </button>
        ))}
      </nav>
      <div>{step.render({ goNext, goBack })}</div>
    </div>
  );
}
