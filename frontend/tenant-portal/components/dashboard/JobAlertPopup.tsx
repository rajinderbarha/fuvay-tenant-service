"use client";
import React from "react";
import {
  AlertTriangle, ArrowRight, BriefcaseBusiness, CalendarDays, Clock3, MapPin, PartyPopper, X,
} from "lucide-react";
import type { DashboardAlert } from "../../lib/api";
import { playAlertTone } from "../../lib/alertTone";

export interface JobAlertPopupProps {
  alerts: DashboardAlert[];
  /** Real totals can exceed the four alerts shown in this compact interruption. */
  newTotal: number;
  delayedTotal: number;
  onDismiss: () => void;
  onOpenJob: (jobId: string) => void;
  onSeeAllDelayed: () => void;
}

const TONES = {
  success: {
    accent: "var(--success, #10b981)", surface: "rgba(16,185,129,0.12)",
    Icon: PartyPopper, eyebrow: "New booking", action: "Assign technician",
  },
  warning: {
    accent: "var(--warning, #f59e0b)", surface: "rgba(245,158,11,0.13)",
    Icon: AlertTriangle, eyebrow: "Needs attention", action: "Open job",
  },
  critical: {
    accent: "var(--danger, #ef4444)", surface: "rgba(239,68,68,0.13)",
    Icon: AlertTriangle, eyebrow: "Urgent action", action: "Open job",
  },
  info: {
    accent: "var(--brand, #4f46e5)", surface: "rgba(79,70,229,0.11)",
    Icon: BriefcaseBusiness, eyebrow: "Job update", action: "Open job",
  },
} as const;

function toneOf(tone: DashboardAlert["tone"]) {
  return TONES[tone] ?? TONES.info;
}

/** The most time-sensitive customer commitment always leads. */
function toneWeight(tone: DashboardAlert["tone"]): number {
  return tone === "critical" ? 0 : tone === "warning" ? 1 : tone === "success" ? 2 : 3;
}

function totalLabel(newTotal: number, delayedTotal: number, hiddenAlerts: number): string {
  const parts: string[] = [];
  if (delayedTotal > 0) parts.push(`${delayedTotal} past slot`);
  if (newTotal > 0) parts.push(`${newTotal} new`);
  if (hiddenAlerts > 0) parts.push(`${hiddenAlerts} more`);
  return parts.join(" · ");
}

export function JobAlertPopup({
  alerts, newTotal, delayedTotal, onDismiss, onOpenJob, onSeeAllDelayed,
}: JobAlertPopupProps) {
  const ordered = React.useMemo(
    () => [...alerts].sort((a, b) => toneWeight(a.tone) - toneWeight(b.tone)),
    [alerts],
  );
  const lead = ordered[0];
  const leadTone = lead?.tone ?? null;

  React.useEffect(() => {
    if (leadTone) playAlertTone(leadTone);
  }, [leadTone]);

  if (!lead) return null;

  const visible = ordered.slice(0, 4);
  const rest = visible.slice(1);
  const tone = toneOf(lead.tone);
  const isDelay = lead.tone === "warning" || lead.tone === "critical";
  const hiddenAlerts = Math.max(0, newTotal + delayedTotal - visible.length);

  return (
    <div className="job-alert-backdrop" onClick={onDismiss}>
      <style>{`
        .job-alert-backdrop{position:fixed;inset:0;z-index:1300;display:flex;align-items:center;justify-content:center;padding:24px;background:rgba(20,18,15,.4);backdrop-filter:blur(2px);animation:job-alert-backdrop-enter .18s ease-out}.job-alert-popup{width:min(420px,94vw);max-height:calc(100vh - 48px);overflow:auto;background:var(--surface);border:1px solid color-mix(in srgb,var(--border) 78%,transparent);border-radius:22px;box-shadow:0 40px 90px -20px rgba(0,0,0,.45);animation:job-alert-enter .22s ease-out}.job-alert-head{position:relative;display:flex;flex-direction:column;gap:14px;padding:22px 22px 18px;background:linear-gradient(150deg,var(--job-alert-tint),var(--surface) 65%)}.job-alert-icon{display:grid;width:48px;height:48px;place-items:center;border-radius:14px;background:var(--job-alert-accent);color:#fff;box-shadow:0 10px 22px -8px color-mix(in srgb,var(--job-alert-accent) 62%,transparent)}.job-alert-copy{display:flex;flex-direction:column;gap:5px;padding-right:16px}.job-alert-eyebrow{display:flex;align-items:center;gap:5px;margin:0;color:var(--job-alert-accent);font:700 10px/1 "IBM Plex Mono",var(--font-family-mono),monospace;letter-spacing:.1em;text-transform:uppercase}.job-alert-title{margin:0;color:var(--text-primary);font-size:19px;line-height:1.25;font-weight:700}.job-alert-message{margin:0;color:var(--text-secondary);font-size:13px;line-height:1.5}.job-alert-dismiss{position:absolute;top:16px;right:16px;display:grid;width:28px;height:28px;place-items:center;border:0;border-radius:9px;background:color-mix(in srgb,var(--surface) 65%,transparent);color:var(--text-tertiary);cursor:pointer}.job-alert-dismiss:hover{background:var(--surface);color:var(--text-primary)}.job-alert-list-wrap{display:flex;flex-direction:column;gap:9px;padding:14px 22px}.job-alert-list-title{margin:0;color:var(--text-tertiary);font:600 11px/1 "IBM Plex Mono",var(--font-family-mono),monospace;letter-spacing:.08em;text-transform:uppercase}.job-alert-list{display:flex;flex-direction:column;gap:4px;margin:0;padding:0;list-style:none}.job-alert-list-button{display:grid;grid-template-columns:30px minmax(0,1fr) auto;gap:10px;align-items:center;width:100%;padding:9px 8px;border:0;border-radius:11px;background:transparent;color:var(--text-primary);font:inherit;text-align:left;cursor:pointer}.job-alert-list-button:hover{background:var(--surface-sunken)}.job-alert-list-icon{display:grid;width:30px;height:30px;place-items:center;border-radius:9px;background:var(--row-tone-surface);color:var(--row-tone-accent)}.job-alert-list-copy{display:flex;min-width:0;flex-direction:column;gap:3px}.job-alert-list-label{overflow:hidden;color:var(--text-primary);font:600 13px/1.2 "IBM Plex Mono",var(--font-family-mono),monospace;text-overflow:ellipsis;white-space:nowrap}.job-alert-list-meta{display:flex;align-items:center;gap:6px;color:var(--text-tertiary);font-size:11px;line-height:1.3}.job-alert-list-meta span{display:inline-flex;align-items:center;gap:4px}.job-alert-late{padding:5px 7px;border-radius:7px;background:var(--row-tone-surface);color:var(--row-tone-accent);font-size:10px;font-weight:700;white-space:nowrap}.job-alert-footer{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:16px 22px;border-top:1px solid var(--border)}.job-alert-total{color:var(--text-tertiary);font-size:12px;font-weight:500}.job-alert-actions{display:flex;gap:8px}.job-alert-button{display:inline-flex;min-height:40px;align-items:center;justify-content:center;gap:6px;padding:0 15px;border-radius:11px;font:600 13px/1 inherit;cursor:pointer}.job-alert-button-secondary{border:1px solid var(--border);background:var(--surface);color:var(--text-secondary)}.job-alert-button-primary{border:1px solid transparent;background:var(--job-alert-accent);color:#fff}.job-alert-button:focus-visible,.job-alert-dismiss:focus-visible,.job-alert-list-button:focus-visible{outline:2px solid var(--focus-ring,var(--brand));outline-offset:2px}@keyframes job-alert-backdrop-enter{from{opacity:0}to{opacity:1}}@keyframes job-alert-enter{from{opacity:0;transform:translateY(10px) scale(.975)}to{opacity:1;transform:none}}@media(max-width:560px){.job-alert-backdrop{align-items:flex-end;padding:12px}.job-alert-popup{width:100%;max-height:calc(100vh - 24px);border-radius:20px}.job-alert-head{padding:20px 18px 16px}.job-alert-list-wrap{padding:14px 18px}.job-alert-footer{align-items:stretch;flex-direction:column;padding:14px 18px}.job-alert-actions{display:grid;grid-template-columns:1fr 1fr}.job-alert-button:only-child{grid-column:1/-1}.job-alert-button{width:100%}}@media(prefers-reduced-motion:reduce){.job-alert-backdrop,.job-alert-popup{animation:none}}
      `}</style>

      <aside
        role="dialog"
        aria-modal="true"
        aria-live={isDelay ? "assertive" : "polite"}
        aria-labelledby="job-alert-title"
        aria-describedby="job-alert-message"
        className="job-alert-popup"
        onClick={event => event.stopPropagation()}
        style={{
          "--job-alert-accent": tone.accent,
          "--job-alert-tint": tone.surface,
        } as React.CSSProperties}
      >
        <div className="job-alert-head">
          <button type="button" onClick={onDismiss} aria-label="Dismiss job alert" className="job-alert-dismiss">
            <X size={15} />
          </button>
          <div className="job-alert-icon" aria-hidden="true"><tone.Icon size={22} /></div>
          <div className="job-alert-copy">
            <p className="job-alert-eyebrow"><span>{tone.eyebrow}</span><span aria-hidden="true">·</span><span>New job alert</span></p>
            <h2 id="job-alert-title" className="job-alert-title">{lead.title}</h2>
            <p id="job-alert-message" className="job-alert-message">{lead.message}</p>
          </div>
        </div>

        {rest.length > 0 && (
          <div className="job-alert-list-wrap">
            <p className="job-alert-list-title">{rest.some(alert => alert.lateness_label) ? "Also past slot" : "More job alerts"}</p>
            <ul className="job-alert-list" aria-label="Other job alerts">
              {rest.map(alert => {
                const rowTone = toneOf(alert.tone);
                return <li key={`${alert.job_id}:${alert.tone}`}>
                  <button
                    type="button"
                    onClick={() => onOpenJob(alert.job_id)}
                    className="job-alert-list-button"
                    style={{
                      "--row-tone-accent": rowTone.accent,
                      "--row-tone-surface": rowTone.surface,
                    } as React.CSSProperties}
                  >
                    <span className="job-alert-list-icon" aria-hidden="true"><rowTone.Icon size={14} /></span>
                    <span className="job-alert-list-copy">
                      <span className="job-alert-list-label">{alert.label}</span>
                      <span className="job-alert-list-meta">
                        {alert.scheduled_date && <span><CalendarDays size={11} />{alert.scheduled_date}</span>}
                        {alert.scheduled_time_window && <span><Clock3 size={11} />{alert.scheduled_time_window}</span>}
                        {!alert.scheduled_date && !alert.scheduled_time_window && alert.city && <span><MapPin size={11} />{alert.city}</span>}
                      </span>
                    </span>
                    {alert.lateness_label && <span className="job-alert-late">{alert.lateness_label}</span>}
                  </button>
                </li>;
              })}
            </ul>
          </div>
        )}

        <div className="job-alert-footer">
          <span className="job-alert-total">{totalLabel(newTotal, delayedTotal, hiddenAlerts)}</span>
          <div className="job-alert-actions">
            {delayedTotal > 1 && (
              <button type="button" onClick={onSeeAllDelayed} className="job-alert-button job-alert-button-secondary">
                See all delayed
              </button>
            )}
            <button type="button" onClick={() => onOpenJob(lead.job_id)} className="job-alert-button job-alert-button-primary">
              {tone.action}<ArrowRight size={13} />
            </button>
          </div>
        </div>
      </aside>
    </div>
  );
}
