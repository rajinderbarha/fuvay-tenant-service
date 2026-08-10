"use client";
import React from "react";
import { PartyPopper, AlertTriangle, ArrowRight, X } from "lucide-react";
import type { DashboardAlert } from "../../lib/api";

/**
 * The dashboard's interruption: a new job to celebrate, or a job past its slot to fix.
 *
 * The tone comes from the SERVER (`alert.tone`, the notification registry's own severity
 * vocabulary), and it drives everything a provider reads at a glance -- the colour, the
 * icon, the heading and the button. That is the point: someone should know within a
 * second whether this popup is worth stopping for, without reading a word of it. A single
 * neutral dialog for both would train them to dismiss all of it, and the delay alerts are
 * the ones that cost money.
 *
 * Delays come FIRST when both are waiting. Good news can be a moment later; a customer
 * standing in their kitchen cannot.
 */

export interface JobAlertPopupProps {
  alerts: DashboardAlert[];
  /** Real totals, which can exceed the alerts shown -- the list is capped for a popup. */
  newTotal: number;
  delayedTotal: number;
  onDismiss: () => void;
  onOpenJob: (jobId: string) => void;
  onSeeAllDelayed: () => void;
}

const TONES = {
  success: {
    accent: "var(--success, #10b981)",
    surface: "rgba(16,185,129,0.08)",
    Icon: PartyPopper,
    action: "Assign a technician",
  },
  warning: {
    accent: "var(--warning, #f59e0b)",
    surface: "rgba(245,158,11,0.10)",
    Icon: AlertTriangle,
    action: "Open the job",
  },
  critical: {
    accent: "var(--danger, #ef4444)",
    surface: "rgba(239,68,68,0.10)",
    Icon: AlertTriangle,
    action: "Open the job",
  },
  info: {
    accent: "var(--brand, #4f46e5)",
    surface: "rgba(79,70,229,0.08)",
    Icon: ArrowRight,
    action: "Open the job",
  },
} as const;

function toneOf(tone: DashboardAlert["tone"]) {
  return TONES[tone] ?? TONES.info;
}

export function JobAlertPopup({
  alerts, newTotal, delayedTotal, onDismiss, onOpenJob, onSeeAllDelayed,
}: JobAlertPopupProps) {
  if (alerts.length === 0) return null;

  // Worst first. `tone` decides, not list order, so this holds however the caller
  // assembled the array.
  const ordered = [...alerts].sort((a, b) => {
    const weight = (t: DashboardAlert["tone"]) => (t === "critical" ? 0 : t === "warning" ? 1 : 2);
    return weight(a.tone) - weight(b.tone);
  });
  const lead = ordered[0];
  const rest = ordered.slice(1);
  const tone = toneOf(lead.tone);
  const isDelay = lead.tone === "warning" || lead.tone === "critical";
  const hiddenDelays = Math.max(0, delayedTotal - alerts.filter(a => a.tone !== "success").length);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={lead.title}
      style={{
        position: "fixed", inset: 0, zIndex: 1000,
        display: "flex", alignItems: "center", justifyContent: "center",
        background: "rgba(15,23,42,0.45)", padding: 16,
      }}
      onClick={onDismiss}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: "100%", maxWidth: 460, background: "var(--surface, #fff)",
          borderRadius: "var(--radius-lg, 14px)", overflow: "hidden",
          boxShadow: "0 20px 50px rgba(15,23,42,0.25)",
          borderTop: `4px solid ${tone.accent}`,
        }}
      >
        <div style={{ padding: 20, background: tone.surface, display: "flex", gap: 14 }}>
          <div
            style={{
              width: 40, height: 40, borderRadius: 999, flexShrink: 0,
              background: "var(--surface, #fff)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            <tone.Icon size={20} color={tone.accent} />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: "#111827" }}>
              {lead.title}
            </h2>
            <p style={{ margin: "4px 0 0", fontSize: 13, color: "#4b5563" }}>{lead.message}</p>
            {/* The slot itself, for a delay: "how late" means little without knowing
                what was promised. */}
            {isDelay && lead.scheduled_date ? (
              <p style={{ margin: "6px 0 0", fontSize: 12, color: "#6b7280" }}>
                Committed slot: {lead.scheduled_date}
                {lead.scheduled_time_window ? ` · ${lead.scheduled_time_window}` : ""}
                {lead.city ? ` · ${lead.city}` : ""}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss"
            style={{ background: "none", border: "none", cursor: "pointer", color: "#6b7280", height: 24 }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Everything else waiting, named rather than counted: "and 4 more" tells a
            provider nothing about whether to keep reading. */}
        {rest.length > 0 ? (
          <ul style={{ margin: 0, padding: "12px 20px", listStyle: "none", borderTop: "1px solid #eef2f7" }}>
            {rest.map(alert => {
              const t = toneOf(alert.tone);
              return (
                <li key={alert.job_id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 0" }}>
                  <t.Icon size={14} color={t.accent} />
                  <button
                    type="button"
                    onClick={() => onOpenJob(alert.job_id)}
                    style={{
                      background: "none", border: "none", padding: 0, cursor: "pointer",
                      fontSize: 13, color: "#374151", textAlign: "left",
                    }}
                  >
                    {alert.label}
                    {alert.lateness_label ? ` — ${alert.lateness_label}` : ""}
                  </button>
                </li>
              );
            })}
          </ul>
        ) : null}

        <div
          style={{
            padding: 16, borderTop: "1px solid #eef2f7",
            display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12,
          }}
        >
          <span style={{ fontSize: 12, color: "#6b7280" }}>
            {/* Real totals, so a capped list never quietly understates the problem. */}
            {delayedTotal > 0
              ? `${delayedTotal} past their slot${newTotal > 0 ? ` · ${newTotal} new` : ""}`
              : `${newTotal} new job${newTotal === 1 ? "" : "s"}`}
            {hiddenDelays > 0 ? ` (${hiddenDelays} not shown)` : ""}
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            {delayedTotal > 1 ? (
              <button
                type="button"
                onClick={onSeeAllDelayed}
                style={{
                  background: "none", border: "1px solid #d1d5db", borderRadius: 8,
                  padding: "8px 12px", fontSize: 13, cursor: "pointer", color: "#374151",
                }}
              >
                See all
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => onOpenJob(lead.job_id)}
              style={{
                background: tone.accent, color: "#fff", border: "none", borderRadius: 8,
                padding: "8px 14px", fontSize: 13, fontWeight: 600, cursor: "pointer",
              }}
            >
              {tone.action}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
