"use client";
import React from "react";
import {
  AlertTriangle, BriefcaseBusiness, Clock3, MapPin, PartyPopper, X,
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
    <aside
      role="dialog"
      aria-modal="false"
      aria-live={isDelay ? "assertive" : "polite"}
      aria-labelledby="job-alert-title"
      aria-describedby="job-alert-message"
      className="job-alert-popup"
      style={{
        "--job-alert-accent": tone.accent,
        "--job-alert-tint": tone.surface,
      } as React.CSSProperties}
    >
      <style>{`
        .job-alert-popup{position:fixed;z-index:80;top:74px;right:24px;width:min(440px,calc(100vw - 32px));max-height:calc(100vh - 96px);overflow:auto;background:var(--surface);border:1px solid var(--border);border-top:3px solid var(--job-alert-accent);border-radius:16px;box-shadow:0 24px 72px rgba(2,6,23,.34),0 4px 14px rgba(2,6,23,.18);animation:job-alert-enter .2s ease-out}.job-alert-head{display:grid;grid-template-columns:44px minmax(0,1fr) 36px;gap:12px;padding:16px 16px 14px;align-items:start}.job-alert-icon{width:44px;height:44px;border-radius:12px;display:grid;place-items:center;background:var(--job-alert-tint);color:var(--job-alert-accent)}.job-alert-eyebrow{margin:0 0 4px;color:var(--job-alert-accent);font-size:10px;line-height:1.2;font-weight:750;letter-spacing:.08em;text-transform:uppercase}.job-alert-title{margin:0;color:var(--text-primary);font-size:16px;line-height:1.3;font-weight:700}.job-alert-message{margin:5px 0 0;color:var(--text-secondary);font-size:12px;line-height:1.5}.job-alert-dismiss{width:36px;height:36px;border:0;border-radius:10px;display:grid;place-items:center;background:transparent;color:var(--text-tertiary);cursor:pointer}.job-alert-dismiss:hover{background:var(--surface-raised);color:var(--text-primary)}.job-alert-meta{display:flex;flex-wrap:wrap;gap:6px;padding:0 16px 14px}.job-alert-chip{display:inline-flex;align-items:center;gap:5px;min-height:26px;padding:4px 8px;border-radius:8px;background:var(--surface-sunken);color:var(--text-secondary);font-size:11px}.job-alert-list{margin:0;padding:7px 9px;list-style:none;border-top:1px solid var(--border)}.job-alert-list-button{display:grid;grid-template-columns:24px minmax(0,1fr) auto;gap:9px;align-items:center;width:100%;padding:9px 7px;border:0;border-radius:10px;background:transparent;color:var(--text-primary);font:inherit;text-align:left;cursor:pointer}.job-alert-list-button:hover{background:var(--surface-sunken)}.job-alert-list-icon{width:24px;height:24px;border-radius:7px;display:grid;place-items:center;background:var(--row-tone-surface);color:var(--row-tone-accent)}.job-alert-list-label{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;font-weight:600}.job-alert-late{color:var(--row-tone-accent);font-size:11px;font-weight:650;white-space:nowrap}.job-alert-footer{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 16px;border-top:1px solid var(--border);background:var(--surface-raised)}.job-alert-total{color:var(--text-tertiary);font-size:11px}.job-alert-actions{display:flex;gap:8px}.job-alert-button{min-height:36px;padding:8px 12px;border-radius:9px;font:inherit;font-size:12px;font-weight:650;cursor:pointer}.job-alert-button-secondary{border:1px solid var(--border);background:transparent;color:var(--text-primary)}.job-alert-button-primary{border:1px solid transparent;background:var(--job-alert-accent);color:#fff}.job-alert-button:focus-visible,.job-alert-dismiss:focus-visible,.job-alert-list-button:focus-visible{outline:2px solid var(--focus-ring,var(--brand));outline-offset:2px}@keyframes job-alert-enter{from{opacity:0;transform:translateY(-8px) scale(.985)}to{opacity:1;transform:none}}@media(max-width:700px){.job-alert-popup{top:auto;right:12px;bottom:12px;width:calc(100vw - 24px);max-height:min(72vh,620px);border-radius:16px}.job-alert-head{grid-template-columns:40px minmax(0,1fr) 36px;padding:14px 14px 12px}.job-alert-icon{width:40px;height:40px}.job-alert-meta{padding:0 14px 12px}.job-alert-footer{align-items:stretch;flex-direction:column;padding:12px 14px}.job-alert-actions{display:grid;grid-template-columns:1fr 1fr}.job-alert-button:only-child{grid-column:1/-1}.job-alert-button{width:100%}}@media(prefers-reduced-motion:reduce){.job-alert-popup{animation:none}}
      `}</style>

      <div className="job-alert-head">
        <div className="job-alert-icon" aria-hidden="true"><tone.Icon size={21} /></div>
        <div>
          <p className="job-alert-eyebrow">{tone.eyebrow}</p>
          <h2 id="job-alert-title" className="job-alert-title">{lead.title}</h2>
          <p id="job-alert-message" className="job-alert-message">{lead.message}</p>
        </div>
        <button type="button" onClick={onDismiss} aria-label="Dismiss job alert" className="job-alert-dismiss">
          <X size={18} />
        </button>
      </div>

      {(lead.scheduled_date || lead.scheduled_time_window || lead.city) && (
        <div className="job-alert-meta" aria-label="Job details">
          {lead.scheduled_date && <span className="job-alert-chip"><Clock3 size={12} />{lead.scheduled_date}</span>}
          {lead.scheduled_time_window && <span className="job-alert-chip"><Clock3 size={12} />{lead.scheduled_time_window}</span>}
          {lead.city && <span className="job-alert-chip"><MapPin size={12} />{lead.city}</span>}
        </div>
      )}

      {rest.length > 0 && (
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
                <span className="job-alert-list-icon" aria-hidden="true"><rowTone.Icon size={13} /></span>
                <span className="job-alert-list-label">{alert.label}</span>
                {alert.lateness_label && <span className="job-alert-late">{alert.lateness_label}</span>}
              </button>
            </li>;
          })}
        </ul>
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
            {tone.action}
          </button>
        </div>
      </div>
    </aside>
  );
}
