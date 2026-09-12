"use client";
import React from "react";
import { AlertTriangle, ArrowRight, Bell, CalendarDays, Clock3, MapPin, PartyPopper, X } from "lucide-react";
import type { DashboardAlert } from "../../lib/api";
import { playAlertTone } from "../../lib/alertTone";

export interface JobAlertPopupProps {
  alerts: DashboardAlert[];
  newTotal: number;
  delayedTotal: number;
  onDismiss: () => void;
  onOpenJob: (jobId: string) => void;
  onSeeAllDelayed: () => void;
  onOpenBoard?: () => void;
}

function remaining(deadline: string | undefined, now: number): string | null {
  if (!deadline) return null;
  const seconds = Math.max(0, Math.ceil((new Date(deadline).getTime() - now) / 1000));
  if (!Number.isFinite(seconds)) return null;
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")} left`;
}

function JobMeta({ alert }: { alert: DashboardAlert }) {
  return <span className="job-alert-meta">
    {alert.scheduled_date && <span><CalendarDays size={12} />{alert.scheduled_date}</span>}
    {alert.scheduled_time_window && <span><Clock3 size={12} />{alert.scheduled_time_window}</span>}
    {alert.city && <span><MapPin size={12} />{alert.city}</span>}
  </span>;
}

export function JobAlertPopup({ alerts, newTotal, delayedTotal, onDismiss, onOpenJob, onSeeAllDelayed, onOpenBoard }: JobAlertPopupProps) {
  const [now, setNow] = React.useState(() => Date.now());
  React.useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const offers = alerts.filter(alert => alert.tone === "success");
  const delayed = alerts.filter(alert => alert.tone !== "success");
  const lead = offers[0] ?? delayed[0];
  React.useEffect(() => { if (lead) playAlertTone(lead.tone); }, [lead?.job_id, lead?.tone]);
  if (!lead) return null;
  const rest = [...offers.slice(lead.tone === "success" ? 1 : 0), ...delayed.slice(lead.tone === "success" ? 0 : 1)].slice(0, 4);
  const isOffer = lead.tone === "success";
  const hidden = Math.max(0, newTotal + delayedTotal - 1 - rest.length);

  return <div className="job-alert-backdrop" onClick={onDismiss}>
    <style>{`
      .job-alert-backdrop{position:fixed;inset:0;z-index:1300;display:flex;align-items:center;justify-content:center;padding:24px;background:rgba(18,27,29,.55);backdrop-filter:blur(5px)}
      .job-alert-popup{width:min(880px,96vw);max-height:calc(100vh - 48px);overflow:auto;border-radius:24px;background:#fff;color:#172622;box-shadow:0 38px 100px rgba(0,0,0,.38);font-family:inherit}
      .job-alert-top{display:flex;align-items:center;gap:13px;padding:18px 22px;border-bottom:1px solid #e7ece9}.job-alert-bell{display:grid;place-items:center;width:40px;height:40px;flex:none;border-radius:13px;background:#e9f6f3;color:#0e685f}.job-alert-heading{flex:1;min-width:0}.job-alert-heading h2{margin:0;font-size:18px;line-height:1.2;font-weight:800}.job-alert-heading p{margin:3px 0 0;color:#718078;font-size:12px}.job-alert-close{display:grid;place-items:center;width:34px;height:34px;flex:none;border:1px solid #e8e1d8;border-radius:12px;background:white;color:#69736d;cursor:pointer}
      .job-alert-feature{display:flex;align-items:center;gap:18px;padding:22px;background:#f2faf8}.job-alert-feature-icon{display:grid;place-items:center;width:53px;height:53px;flex:none;border-radius:17px;background:#0d675d;color:#fff;box-shadow:0 8px 17px rgba(13,103,93,.22)}.job-alert-feature-copy{flex:1;min-width:0}.job-alert-eyebrow{margin:0 0 4px;color:#0d675d;font:800 10px/1.2 monospace;letter-spacing:.08em;text-transform:uppercase}.job-alert-feature h3{margin:0 0 8px;font-size:23px;line-height:1.15;font-weight:850;letter-spacing:-.025em}.job-alert-feature p{margin:8px 0 0;color:#57675f;font-size:12px}
      .job-alert-meta{display:flex;flex-wrap:wrap;gap:7px;color:#737c78;font-size:11px}.job-alert-meta>span{display:inline-flex;align-items:center;gap:4px;padding:5px 8px;border:1px solid #e7e4de;border-radius:99px;background:#fff}.job-alert-primary{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:46px;flex:none;padding:0 20px;border:0;border-radius:13px;background:#0d675d;color:#fff;font-size:13px;font-weight:800;cursor:pointer;box-shadow:0 9px 17px rgba(13,103,93,.15)}
      .job-alert-queue{padding:20px 22px 18px}.job-alert-section-label{display:flex;align-items:center;gap:9px;margin:0 0 12px;color:#6a716e;font:800 11px/1.2 monospace;letter-spacing:.06em;text-transform:uppercase}.job-alert-count{display:inline-grid;place-items:center;min-width:20px;height:20px;padding:0 5px;border-radius:50%;background:#f5eadc;color:#76592d}.job-alert-list{display:flex;flex-direction:column;gap:10px;margin:0;padding:0;list-style:none}.job-alert-row{display:flex;align-items:center;gap:12px;padding:11px 12px;border:1px solid #f3c5b1;border-radius:14px;background:#fff6f1}.job-alert-row.offer{border-color:#bfdfd2;background:#f2faf6}.job-alert-row-icon{display:grid;place-items:center;width:29px;height:29px;flex:none;border-radius:9px;background:#fff;color:#bb6842}.job-alert-row.offer .job-alert-row-icon{color:#0e685f}.job-alert-row-copy{flex:1;min-width:0}.job-alert-row-copy strong{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px;font-weight:800}.job-alert-row-copy .job-alert-meta{margin-top:4px}.job-alert-row-copy .job-alert-meta>span{padding:0;border:0;background:none}.job-alert-time{padding:5px 9px;border-radius:99px;background:#fff;color:#a45636;font-size:11px;font-weight:800;white-space:nowrap}.job-alert-row.offer .job-alert-time{color:#0d675d}.job-alert-row-button{min-height:36px;padding:0 15px;border:1px solid #ddd9d2;border-radius:10px;background:#fff;color:#303835;font-size:12px;font-weight:700;cursor:pointer}
      .job-alert-footer{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 22px;border-top:1px solid #ebe9e4}.job-alert-footer span{color:#777e7a;font-size:12px}.job-alert-actions{display:flex;gap:8px}.job-alert-secondary,.job-alert-board{min-height:40px;padding:0 15px;border-radius:11px;font-size:12px;font-weight:700;cursor:pointer}.job-alert-secondary{border:1px solid #e2ddd5;background:#fff;color:#4b5751}.job-alert-board{border:1px solid #292827;background:#292827;color:#fff}.job-alert-popup button:focus-visible{outline:3px solid #67b7ac;outline-offset:2px}
      @media(max-width:700px){.job-alert-backdrop{align-items:flex-end;padding:8px}.job-alert-popup{width:100%;max-height:calc(100vh - 16px);border-radius:20px}.job-alert-feature{align-items:flex-start;flex-wrap:wrap;padding:18px}.job-alert-feature-copy{min-width:calc(100% - 75px)}.job-alert-feature h3{font-size:20px}.job-alert-primary{width:100%}.job-alert-row{flex-wrap:wrap}.job-alert-row-copy{min-width:calc(100% - 50px)}.job-alert-time{margin-left:40px}.job-alert-footer{align-items:stretch;flex-direction:column}.job-alert-actions{display:grid;grid-template-columns:1fr 1fr}}
    `}</style>
    <aside className="job-alert-popup" role="dialog" aria-modal="true" aria-labelledby="job-alert-heading" onClick={event => event.stopPropagation()}>
      <header className="job-alert-top"><span className="job-alert-bell" aria-hidden="true"><Bell size={18} /></span><div className="job-alert-heading"><h2 id="job-alert-heading">Job alerts</h2><p>New bookings and jobs still waiting for a technician</p></div><button className="job-alert-close" type="button" aria-label="Dismiss job alert" onClick={onDismiss}><X size={17} /></button></header>
      <section className="job-alert-feature"><span className="job-alert-feature-icon" aria-hidden="true">{isOffer ? <PartyPopper size={22} /> : <AlertTriangle size={22} />}</span><div className="job-alert-feature-copy"><div className="job-alert-eyebrow">{isOffer ? "Newest booking" : "Needs attention"}</div><h3>{lead.label}</h3><JobMeta alert={lead} /><p>{isOffer ? `Assign a technician before this offer expires${remaining(lead.assignment_deadline_at, now) ? ` · ${remaining(lead.assignment_deadline_at, now)}` : ""}.` : lead.message}</p></div><button className="job-alert-primary" type="button" onClick={() => onOpenJob(lead.job_id)}>{isOffer ? "Assign technician" : "Open job"}<ArrowRight size={16} /></button></section>
      {rest.length > 0 && <section className="job-alert-queue"><h3 className="job-alert-section-label">Waiting for assignment <span className="job-alert-count">{newTotal + delayedTotal - 1}</span></h3><ul className="job-alert-list">{rest.map(alert => <li key={`${alert.job_id}:${alert.tone}`} className={`job-alert-row${alert.tone === "success" ? " offer" : ""}`}><span className="job-alert-row-icon" aria-hidden="true"><AlertTriangle size={15} /></span><span className="job-alert-row-copy"><strong>{alert.label}</strong><JobMeta alert={alert} /></span>{(alert.lateness_label || alert.assignment_deadline_at) && <span className="job-alert-time">{alert.lateness_label || remaining(alert.assignment_deadline_at, now)}</span>}<button className="job-alert-row-button" type="button" onClick={() => onOpenJob(alert.job_id)}>{alert.tone === "success" ? "Assign" : "Open"}</button></li>)}</ul></section>}
      <footer className="job-alert-footer"><span>{hidden > 0 ? `${hidden} more on the bookings board` : isOffer ? "Closing this alert will remind you in 30 seconds while the offer is open." : `${delayedTotal} delayed job${delayedTotal === 1 ? "" : "s"}`}</span><div className="job-alert-actions"><button className="job-alert-secondary" type="button" onClick={onDismiss}>Dismiss</button><button className="job-alert-board" type="button" onClick={onOpenBoard ?? onSeeAllDelayed}>Open bookings board</button></div></footer>
    </aside>
  </div>;
}
