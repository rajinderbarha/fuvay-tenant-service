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
  const tone = presentation(health);
  const score = safeScore(health.score);
  const payment = safeScore(health.signals?.payment_reliability ?? score);
  const behaviour = safeScore(health.signals?.customer_behavior ?? score);
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
          <span style={{ display: "block", color: "var(--text-tertiary)", fontSize: 10 }}>Payment reliability · 80%</span>
          <strong style={{ display: "block", marginTop: 3, color: payment < 60 ? "var(--danger-text)" : "var(--text-primary)", fontSize: 13 }}>{payment}/100</strong>
          <small style={{ color: "var(--text-secondary)", fontSize: 10 }}>{signalLabel(payment, "payment history")}</small>
        </div>
        <div style={{ padding: 9, borderRadius: 9, background: "var(--surface)" }}>
          <span style={{ display: "block", color: "var(--text-tertiary)", fontSize: 10 }}>Customer behaviour · 20%</span>
          <strong style={{ display: "block", marginTop: 3, color: behaviour < 60 ? "var(--warning-text)" : "var(--text-primary)", fontSize: 13 }}>{behaviour}/100</strong>
          <small style={{ color: "var(--text-secondary)", fontSize: 10 }}>{signalLabel(behaviour, "behaviour")}</small>
        </div>
      </div>
      {advance > 0 && <strong style={{ color: tone.color, fontSize: 11.5 }}>
        Payment protection: collect {advance}% advance before service.
      </strong>}
    </section>
  );
}
