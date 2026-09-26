"use client";

import React from "react";
import type { HsDispatchJobSummary } from "../../lib/api";

type CustomerHealth = NonNullable<HsDispatchJobSummary["customer_health"]>;

function presentation(health: CustomerHealth) {
  const band = (health.band || "").toLowerCase();
  if (!health.can_book || band === "blocked" || band === "restricted") {
    return {
      label: health.can_book ? "High-risk customer" : "Booking blocked",
      color: "var(--danger-text)", border: "var(--danger-border)", background: "var(--danger-bg)",
    };
  }
  if (band === "cautious") {
    return {
      label: "Payment caution",
      color: "var(--warning-text)", border: "var(--warning-border)", background: "var(--warning-bg)",
    };
  }
  if (band === "trusted") {
    return {
      label: "Excellent customer",
      color: "var(--success-text)", border: "var(--success-border)", background: "var(--success-bg)",
    };
  }
  return {
    label: "Good customer",
    color: "var(--info-text)", border: "var(--info-border)", background: "var(--info-bg)",
  };
}

function signalLabel(score: number, riskLabel: string) {
  if (score >= 80) return `Reliable ${riskLabel}`;
  if (score >= 60) return `Generally good ${riskLabel}`;
  if (score >= 40) return `${riskLabel} needs caution`;
  return `Poor ${riskLabel}`;
}

function safeScore(value: unknown) {
  return Math.max(0, Math.min(100, Math.round(Number(value) || 0)));
}

export function CustomerHealthCard({ health }: { health: CustomerHealth }) {
  if (health.assessment_status === "unassessed" || health.score == null || health.band === "new_customer") {
    const required = Math.max(1, Number(health.minimum_evidence_events) || 1);
    return (
      <section
        aria-label="Customer health"
        style={{
          padding: 13, border: "1px solid var(--info-border)", borderRadius: 12,
          background: "var(--info-bg)", display: "grid", gap: 8,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
          <div>
            <span style={{ color: "var(--text-tertiary)", fontSize: 10.5, fontWeight: 700, letterSpacing: ".06em", textTransform: "uppercase" }}>
              Customer history
            </span>
            <strong style={{ display: "block", marginTop: 3, color: "var(--info-text)", fontSize: 16 }}>New customer</strong>
          </div>
          <span style={{ padding: "5px 9px", borderRadius: 999, background: "var(--surface)", color: "var(--info-text)", fontSize: 11, fontWeight: 750 }}>
            Not yet rated
          </span>
        </div>
        <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: 11.5, lineHeight: 1.5 }}>
          No completed payment or post-job behaviour evidence exists yet. Treat this booking normally; a health score appears after {required === 1 ? "the first verified outcome" : `${required} verified outcomes`}.
        </p>
      </section>
    );
  }

  const tone = presentation(health);
  const score = safeScore(health.score);
  const payment = safeScore(health.signals?.payment_reliability ?? score);
  const behaviour = safeScore(health.signals?.customer_behavior ?? score);
  const paymentWeight = safeScore(health.weights?.payment_reliability ?? 80);
  const behaviourWeight = safeScore(health.weights?.customer_behavior ?? (100 - paymentWeight));
  const paymentOutcomes = Math.max(0, Number(health.evidence?.payment_outcomes) || 0);
  const behaviourAssessments = Math.max(0, Number(health.evidence?.behavior_assessments) || 0);
  const advance = Math.max(0, Math.round(Number(health.advance_required_pct) || 0));
  return (
    <section
      aria-label="Customer health"
      style={{
        padding: 13, border: `1px solid ${tone.border}`, borderRadius: 12,
        background: tone.background, display: "grid", gap: 11,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <div>
          <span style={{ color: "var(--text-tertiary)", fontSize: 10.5, fontWeight: 700, letterSpacing: ".06em", textTransform: "uppercase" }}>
            Customer health
          </span>
          <strong style={{ display: "block", marginTop: 3, color: tone.color, fontSize: 15 }}>{tone.label}</strong>
        </div>
        <strong style={{ color: tone.color, fontSize: 25, lineHeight: 1 }}>{score}<small style={{ fontSize: 11 }}>/100</small></strong>
      </div>
      <div aria-hidden="true" style={{ height: 7, overflow: "hidden", borderRadius: 999, background: "var(--surface)" }}>
        <div style={{ width: `${score}%`, height: "100%", borderRadius: 999, background: tone.color }} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
        <div style={{ padding: 9, borderRadius: 9, background: "var(--surface)" }}>
          <span style={{ display: "block", color: "var(--text-tertiary)", fontSize: 10 }}>Payment reliability · {paymentWeight}%</span>
          <strong style={{ display: "block", marginTop: 3, color: payment < 60 ? "var(--danger-text)" : "var(--text-primary)", fontSize: 13 }}>{payment}/100</strong>
          <small style={{ color: "var(--text-secondary)", fontSize: 10 }}>{signalLabel(payment, "payment history")} · {paymentOutcomes} outcome{paymentOutcomes === 1 ? "" : "s"}</small>
        </div>
        <div style={{ padding: 9, borderRadius: 9, background: "var(--surface)" }}>
          <span style={{ display: "block", color: "var(--text-tertiary)", fontSize: 10 }}>Customer behaviour · {behaviourWeight}%</span>
          <strong style={{ display: "block", marginTop: 3, color: behaviour < 60 ? "var(--warning-text)" : "var(--text-primary)", fontSize: 13 }}>{behaviour}/100</strong>
          <small style={{ color: "var(--text-secondary)", fontSize: 10 }}>{signalLabel(behaviour, "behaviour")} · {behaviourAssessments} report{behaviourAssessments === 1 ? "" : "s"}</small>
        </div>
      </div>
      {advance > 0 && <strong style={{ color: tone.color, fontSize: 11.5 }}>
        Payment protection: collect {advance}% advance before service.
      </strong>}
    </section>
  );
}
