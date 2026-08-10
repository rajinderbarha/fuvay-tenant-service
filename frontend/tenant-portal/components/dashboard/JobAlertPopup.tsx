"use client";
import React from "react";
import { PartyPopper, AlertTriangle, ArrowRight, X } from "lucide-react";
import type { DashboardAlert } from "../../lib/api";
import { playAlertTone } from "../../lib/alertTone";

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

/** Lower sorts first: the most serious alert leads, and its tone is the one that sounds. */
function toneWeight(tone: DashboardAlert["tone"]): number {
  return tone === "critical" ? 0 : tone === "warning" ? 1 : 2;
}

export function JobAlertPopup({
  alerts, newTotal, delayedTotal, onDismiss, onOpenJob, onSeeAllDelayed,
}: JobAlertPopupProps) {
  const leadTone = alerts.length > 0
    ? [...alerts].sort((a, b) => toneWeight(a.tone) - toneWeight(b.tone))[0].tone
    : null;

  /**
   * Sounds once per popup, matched to the severity: rising for a new job, falling for a
   * delay. The point is that a provider can tell WHICH arrived without looking up --
   * a single generic ping would only say "something happened".
   *
   * Keyed on the tone so a delay arriving while a celebration is on screen re-sounds
   * with the right one, and does not sound again on an unrelated re-render.
   */
  React.useEffect(() => {
    if (leadTone) playAlertTone(leadTone);
  }, [leadTone]);

  if (alerts.length === 0) return null;

  // Worst first. `tone` decides, not list order, so this holds however the caller
  // assembled the array.
  const ordered = [...alerts].sort((a, b) => toneWeight(a.tone) - toneWeight(b.tone));
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
        background: "rgba(2,6,23,0.6)", padding: 16,
      }}
      onClick={onDismiss}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: "100%", maxWidth: 480, background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg, 14px)", overflow: "hidden",
          boxShadow: "0 24px 60px rgba(2,6,23,0.45)",
          // A single hairline of the tone colour. A 4px bar PLUS a tinted header PLUS a
          // coloured button was three statements of the same thing.
          borderTop: `3px solid ${tone.accent}`,
        }}
      >
        <div style={{ padding: "18px 20px", display: "flex", gap: 14, alignItems: "flex-start" }}>
          <div
            style={{
              width: 38, height: 38, borderRadius: 10, flexShrink: 0,
              // The tint lives on the icon tile only, so the tone reads at a glance
              // without washing the whole panel in colour.
              background: tone.surface,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            <tone.Icon size={20} color={tone.accent} />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <h2 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "var(--text-primary)" }}>
              {lead.title}
            </h2>
            <p style={{ margin: "5px 0 0", fontSize: 13, lineHeight: 1.5, color: "var(--text-secondary)" }}>
              {lead.message}
            </p>
            {/* The slot itself, for a delay: "how late" means little without knowing
                what was promised. */}
            {isDelay && lead.scheduled_date ? (
              <p
                style={{
                  margin: "10px 0 0", fontSize: 12, color: "var(--text-secondary)",
                  padding: "6px 8px", borderRadius: 6,
                  background: "var(--surface-raised, rgba(255,255,255,0.05))",
                  display: "inline-block",
                }}
              >
                {`Committed slot: ${lead.scheduled_date}`}
                {lead.scheduled_time_window ? ` · ${lead.scheduled_time_window}` : ""}
                {lead.city ? ` · ${lead.city}` : ""}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss"
            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)", height: 24 }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Everything else waiting, named rather than counted: "and 4 more" tells a
            provider nothing about whether to keep reading. */}
        {rest.length > 0 ? (
          <ul
            style={{
              margin: 0, padding: "6px 12px 10px", listStyle: "none",
              borderTop: "1px solid var(--border)",
            }}
          >
            {rest.map(alert => {
              const t = toneOf(alert.tone);
              return (
                <li key={alert.job_id}>
                  <button
                    type="button"
                    onClick={() => onOpenJob(alert.job_id)}
                    style={{
                      display: "flex", alignItems: "center", gap: 10, width: "100%",
                      background: "none", border: "none", cursor: "pointer",
                      padding: "8px", borderRadius: 8, textAlign: "left",
                      fontSize: 13, color: "var(--text-primary)",
                    }}
                  >
                    <t.Icon size={14} color={t.accent} style={{ flexShrink: 0 }} />
                    <span
                      style={{
                        flex: 1, minWidth: 0, overflow: "hidden",
                        textOverflow: "ellipsis", whiteSpace: "nowrap",
                      }}
                    >
                      {alert.label}
                    </span>
                    {/* Right-aligned so the delays line up and can be compared down the
                        column, instead of being read one sentence at a time. */}
                    {alert.lateness_label ? (
                      <span style={{ fontSize: 12, color: t.accent, flexShrink: 0 }}>
                        {alert.lateness_label}
                      </span>
                    ) : null}
                  </button>
                </li>
              );
            })}
          </ul>
        ) : null}

        <div
          style={{
            padding: "14px 20px", borderTop: "1px solid var(--border)",
            background: "var(--surface-raised, rgba(255,255,255,0.03))",
            display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12,
          }}
        >
          <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
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
                  background: "none", border: "1px solid var(--border)", borderRadius: 8,
                  padding: "8px 12px", fontSize: 13, cursor: "pointer",
                  color: "var(--text-primary)",
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
