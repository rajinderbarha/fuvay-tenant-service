"use client";
import React from "react";
import { useRouter } from "next/navigation";
import { Btn } from "../shared/ui";
import { ArrowLeft, X } from "lucide-react";

export const WIZARD_STEPS = ["category", "service", "job-types", "coverage-pricing", "review"] as const;
export type WizardStep = typeof WIZARD_STEPS[number];
export const WIZARD_STEP_LABELS: Record<WizardStep, string> = {
  "category": "Category",
  "service": "Service",
  "job-types": "Job Types",
  "coverage-pricing": "Coverage & Pricing",
  "review": "Review & Publish",
};

/** Full-page wizard shell (not a modal) -- header + stepper + content slot.
 * Schema-driven: step labels/order are fixed platform-wide (not per-vertical),
 * but everything rendered inside a step comes from the backend. */
export function WizardShell({
  currentStep, breadcrumb, saving, lastSavedAt, onSaveAndExit, children,
}: {
  currentStep: WizardStep;
  breadcrumb?: string;
  saving?: "idle" | "saving" | "saved" | "failed";
  lastSavedAt?: string | null;
  onSaveAndExit?: () => void;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const currentIndex = WIZARD_STEPS.indexOf(currentStep);

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-soft, var(--bg))", display: "flex", flexDirection: "column" }}>
      <header style={{
        display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10,
        padding: "14px 24px", borderBottom: "1px solid var(--border)", background: "var(--surface)",
        position: "sticky", top: 0, zIndex: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <button onClick={() => router.push("/services")} aria-label="Back to Services"
            style={{ display: "flex", alignItems: "center", gap: 6, background: "none", border: "none",
              color: "var(--text-secondary)", cursor: "pointer", fontSize: 13, fontFamily: "inherit" }}>
            <ArrowLeft size={15} /> Services
          </button>
          <span style={{ color: "var(--border)" }}>/</span>
          <div>
            <p style={{ margin: 0, fontSize: 14, fontWeight: 700 }}>Set up service</p>
            {breadcrumb && <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)" }}>{breadcrumb}</p>}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
          <AutosaveIndicator status={saving ?? "idle"} lastSavedAt={lastSavedAt} />
          <Btn size="sm" variant="secondary" onClick={onSaveAndExit ?? (() => router.push("/services"))}>
            Save and Exit
          </Btn>
          <button onClick={() => router.push("/services")} aria-label="Close"
            style={{ background: "none", border: "none", color: "var(--text-tertiary)", cursor: "pointer" }}>
            <X size={18} />
          </button>
        </div>
      </header>

      <nav aria-label="Setup steps" style={{
        display: "flex", gap: 4, padding: "12px 24px", background: "var(--surface)",
        borderBottom: "1px solid var(--border)", overflowX: "auto",
      }}>
        {WIZARD_STEPS.map((step, i) => {
          const state = i < currentIndex ? "done" : i === currentIndex ? "active" : "upcoming";
          return (
            <div key={step} aria-current={state === "active" ? "step" : undefined}
              style={{
                display: "flex", alignItems: "center", gap: 8, padding: "6px 12px", borderRadius: 999,
                fontSize: 12, fontWeight: 600, whiteSpace: "nowrap",
                background: state === "active" ? "var(--accent-muted)" : "transparent",
                color: state === "done" ? "var(--success-text)" : state === "active" ? "var(--accent)" : "var(--text-tertiary)",
              }}>
              <span aria-hidden style={{
                width: 18, height: 18, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 10, fontWeight: 700,
                background: state === "done" ? "var(--success-text)" : state === "active" ? "var(--accent)" : "var(--border)",
                color: state === "upcoming" ? "var(--text-tertiary)" : "#fff",
              }}>{state === "done" ? "✓" : i + 1}</span>
              {WIZARD_STEP_LABELS[step]}
            </div>
          );
        })}
      </nav>

      {/* Visually hidden, announces the current step to screen readers on
          every step change (spec section 24). */}
      <p role="status" aria-live="polite" style={{
        position: "absolute", width: 1, height: 1, padding: 0, margin: -1, overflow: "hidden",
        clip: "rect(0,0,0,0)", whiteSpace: "nowrap", border: 0,
      }}>
        Step {currentIndex + 1} of {WIZARD_STEPS.length}: {WIZARD_STEP_LABELS[currentStep]}
      </p>

      <main style={{ flex: 1, padding: "28px 24px", maxWidth: 880, width: "100%", margin: "0 auto" }}>
        {children}
      </main>
    </div>
  );
}

export function AutosaveIndicator({ status, lastSavedAt }: {
  status: "idle" | "saving" | "saved" | "failed"; lastSavedAt?: string | null;
}) {
  if (status === "idle" && !lastSavedAt) return null;
  const label = status === "saving" ? "Saving…" : status === "failed" ? "Save failed" :
    lastSavedAt ? `Saved ${new Date(lastSavedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : "Saved";
  const color = status === "failed" ? "var(--danger-text)" : status === "saving" ? "var(--text-tertiary)" : "var(--success-text)";
  return (
    <span role="status" aria-live="polite" style={{ fontSize: 12, color, fontWeight: 500 }}>{label}</span>
  );
}

export function WizardFooter({ onBack, onContinue, continueLabel = "Continue", continueDisabled, continueLoading }: {
  onBack?: () => void; onContinue?: () => void; continueLabel?: string;
  continueDisabled?: boolean; continueLoading?: boolean;
}) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", marginTop: 28, paddingTop: 20, borderTop: "1px solid var(--border)" }}>
      <Btn variant="ghost" onClick={onBack} disabled={!onBack}>Back</Btn>
      <Btn onClick={onContinue} disabled={continueDisabled} loading={continueLoading}>{continueLabel}</Btn>
    </div>
  );
}
