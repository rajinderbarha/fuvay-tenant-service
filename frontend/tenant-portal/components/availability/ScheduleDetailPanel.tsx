"use client";
/** Right-hand technician detail panel. Every section renders only what the
 * backend can actually prove:
 *  - Weekly pattern: aggregated from the real week's effective_schedules.
 *  - Capacity: real daily_capacity/concurrent_capacity from the resolver.
 *  - Date overrides: GET /v1/provider/team/{id}/overrides
 *  - Upcoming time off: GET /v1/provider/team/{id}/time-off?upcoming_only=true
 *  - Service capability: real supported_services from the team-overview
 *    endpoint (GET /v1/tenant/home-services/team/{id}/overview).
 *
 * The override and time-off sections used to be a disclosure line saying no
 * such tables existed. Migration 242 created both and the resolver reads
 * them, so they are real sections now -- an empty one says "none", which is a
 * fact, not a gap. */
import React from "react";
import { X, AlertTriangle, ExternalLink, Trash2 } from "lucide-react";
import { Btn } from "../shared/ui";

export interface WeeklyPatternLine { label: string; value: string; }

export interface DateOverride {
  id: string; override_date: string; start_time: string | null; end_time: string | null;
  full_day_closed: boolean; reason: string | null;
}
export interface TimeOffEntry {
  id: string; start_date: string; end_date: string; all_day: boolean;
  start_time: string | null; end_time: string | null; reason: string | null; status: string;
}
export interface ConflictDetail {
  dateLabel: string;
  jobNumbers: string[];
  peak: number | null;
  limit: number | null;
  dispatchHref: string | null;
}
/** Today's real state for this technician, straight from the resolver's reasons --
 *  not a decorative label. */
export interface ReadinessState { label: string; tone: "ok" | "warn" | "bad" | "muted"; }

/** "09:00" -> "9:00 AM". The panel reads as a schedule a person would write out,
 *  where the grid stays 24-hour because its cells are too narrow for the suffix. */
export function to12h(t: string | null | undefined): string | null {
  if (!t) return null;
  const [hRaw, m] = t.slice(0, 5).split(":");
  const h = Number(hRaw);
  if (Number.isNaN(h)) return t;
  const suffix = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${m} ${suffix}`;
}
function range12h(a: string | null, b: string | null): string {
  const s = to12h(a), e = to12h(b);
  return s && e ? `${s} – ${e}` : s ?? e ?? "—";
}
/** "1 job", not "1 jobs" -- a limit of one is the common case for a solo technician. */
function jobsUnit(n: number | null): string {
  if (n == null) return "Not configured";
  return `${n} ${n === 1 ? "job" : "jobs"}`;
}
function fmtDate(iso: string): string {
  return new Date(iso + "T00:00:00").toLocaleDateString("en-IN", {
    weekday: "short", day: "2-digit", month: "short", year: "numeric",
  });
}

const TONE_COLOR: Record<ReadinessState["tone"], string> = {
  ok: "#22C55E", warn: "#F59E0B", bad: "#EF4444", muted: "#94A3B8",
};

export function ScheduleDetailPanel({
  staffName, isActive, readiness, weeklyPattern, breakLine, maxJobsPerDay, maxConcurrentJobs,
  serviceCapability, capabilityLoading, conflict, generatedAt, onClose, onEditAvailability,
  overrides, overridesLoading, overridesError,
  timeOff, timeOffLoading, timeOffError, onAddTimeOff,
  onCancelTimeOff, onRemoveOverride, mutating,
}: {
  staffName: string; isActive: boolean; readiness: ReadinessState;
  weeklyPattern: WeeklyPatternLine[]; breakLine: string | null;
  maxJobsPerDay: number | null; maxConcurrentJobs: number | null;
  serviceCapability: string[] | null; capabilityLoading: boolean;
  conflict: ConflictDetail | null;
  generatedAt: string | null;
  onClose: () => void; onEditAvailability: () => void;
  overrides: DateOverride[] | null; overridesLoading: boolean; overridesError: string | null;
  timeOff: TimeOffEntry[] | null; timeOffLoading: boolean; timeOffError: string | null;
  onAddTimeOff: () => void;
  onCancelTimeOff: (id: string) => void;
  onRemoveOverride: (date: string) => void;
  mutating: boolean;
}) {
  return (
    <>
      {/* Real change made here: this used to render as a sticky inline
          sidebar card next to the roster/grid, competing for the same
          horizontal space -- the requested behavior is a slide-over drawer,
          same pattern already used for the Bookings & Jobs job panel. */}
      <div onClick={onClose} style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", zIndex: 899, backdropFilter: "blur(1px)",
      }}/>
      <div style={{
        position: "fixed", top: 0, right: 0, width: 380, height: "100vh",
        background: "var(--surface)", borderLeft: "1px solid var(--border)",
        zIndex: 900, boxShadow: "-8px 0 24px rgba(0,0,0,0.2)",
        animation: "slideInAvailDrawer 0.2s cubic-bezier(0.4,0,0.2,1)",
      }}>
        <style>{`@keyframes slideInAvailDrawer { from { transform: translateX(100%) } to { transform: translateX(0) } }`}</style>
        <div style={{ padding: "18px 18px 24px", height: "100%", overflowY: "auto", boxSizing: "border-box" }}>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
            <h3 style={{ fontSize: 14.5, fontWeight: 700, color: "var(--text-primary)", margin: 0, lineHeight: 1.3 }}>
              Schedule details — {staffName}
            </h3>
            <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
              {/* Outlined, not filled: this is a state, and a solid chip here competes
                  with the primary action further down. */}
              <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 9px", borderRadius: 6,
                border: `1px solid ${isActive ? "#22C55E" : "var(--border)"}`,
                color: isActive ? "#22C55E" : "var(--text-tertiary)" }}>
                {isActive ? "Active" : "Inactive"}
              </span>
              <button onClick={onClose} aria-label="Close"
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", padding: 0, display: "flex" }}>
                <X size={16}/>
              </button>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6, fontSize: 12,
            color: TONE_COLOR[readiness.tone] }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: TONE_COLOR[readiness.tone] }}/>
            {readiness.label}
          </div>

          <Section title="Weekly pattern" first>
            {weeklyPattern.map(l => <KV key={l.label} label={l.label} value={l.value}/>)}
            {breakLine && <KV label="Break" value={breakLine}/>}
          </Section>

          <Section title="Capacity">
            <KV label="Max jobs per day" value={jobsUnit(maxJobsPerDay)}/>
            <KV label="Max concurrent jobs" value={jobsUnit(maxConcurrentJobs)}/>
          </Section>

          <Section title="Date overrides">
            {overridesLoading ? (
              <Muted>Loading…</Muted>
            ) : overridesError ? (
              // "None" and "we could not ask" are different answers, and only one of
              // them is safe to schedule against.
              <Failed>{overridesError}</Failed>
            ) : !overrides || overrides.length === 0 ? (
              <Muted>None. This technician works their weekly pattern.</Muted>
            ) : overrides.map(o => (
              <Row
                key={o.id}
                dot="#F59E0B"
                label={fmtDate(o.override_date)}
                value={o.full_day_closed ? "Not working" : range12h(o.start_time, o.end_time)}
                hint={o.reason}
                onRemove={mutating ? undefined : () => onRemoveOverride(o.override_date)}
                removeTitle="Remove this override and return the day to the weekly pattern"
              />
            ))}
          </Section>

          <Section title="Upcoming time off">
            {timeOffLoading ? (
              <Muted>Loading…</Muted>
            ) : timeOffError ? (
              <Failed>{timeOffError}</Failed>
            ) : !timeOff || timeOff.length === 0 ? (
              <Muted>None scheduled.</Muted>
            ) : timeOff.map(t => (
              <Row
                key={t.id}
                dot="#94A3B8"
                label={t.start_date === t.end_date
                  ? fmtDate(t.start_date)
                  : `${fmtDate(t.start_date)} – ${fmtDate(t.end_date)}`}
                value={t.all_day ? "All day" : range12h(t.start_time, t.end_time)}
                hint={t.reason}
                onRemove={mutating ? undefined : () => onCancelTimeOff(t.id)}
                removeTitle="Cancel this time off"
              />
            ))}
          </Section>

          <Section title="Service capability">
            {capabilityLoading ? (
              <Muted>Loading…</Muted>
            ) : serviceCapability && serviceCapability.length > 0 ? (
              <p style={{ fontSize: 12.5, color: "var(--text-primary)", margin: 0, lineHeight: 1.5 }}>
                {serviceCapability.join(", ")}
              </p>
            ) : (
              <Muted>No services assigned yet.</Muted>
            )}
          </Section>

          <div style={{ display: "flex", gap: 8, margin: "18px 0 16px" }}>
            {/* "Edit availability" implied this changed what customers could book. It
                did not -- that is business hours. This edits one date for one person. */}
            <div style={{ flex: 1 }}><Btn variant="primary" fullWidth onClick={onEditAvailability}>Override date</Btn></div>
            <div style={{ flex: 1 }}><Btn variant="secondary" fullWidth onClick={onAddTimeOff}>Add time off</Btn></div>
          </div>

          {conflict && (
            <div style={{ padding: "11px 13px", borderRadius: 10, background: "var(--danger-bg)",
              border: "1px solid var(--danger-border)", marginBottom: 16 }}>
              <div style={{ display: "flex", gap: 7, alignItems: "flex-start" }}>
                <AlertTriangle size={13} style={{ color: "var(--danger-text)", marginTop: 2, flexShrink: 0 }}/>
                <div style={{ minWidth: 0 }}>
                  <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
                    {conflict.jobNumbers.length || 1} assignment conflict{conflict.jobNumbers.length === 1 ? "" : "s"} on{" "}
                    <span style={{ color: "var(--danger-text)" }}>{conflict.dateLabel}</span>
                  </p>
                  <p style={{ fontSize: 11.5, color: "var(--text-secondary)", margin: "4px 0 0" }}>
                    {conflict.peak != null && conflict.limit != null
                      ? `${conflict.peak} jobs overlap at once, above the limit of ${conflict.limit}.`
                      : "Overlapping assigned jobs exceed capacity."}
                  </p>
                  {conflict.jobNumbers.length > 0 && (
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "3px 0 0" }}>
                      {conflict.jobNumbers.join(", ")}
                    </p>
                  )}
                  {conflict.dispatchHref && (
                    <a href={conflict.dispatchHref} style={{ display: "inline-flex", alignItems: "center", gap: 4,
                      fontSize: 11.5, fontWeight: 600, color: "var(--brand)", marginTop: 8, textDecoration: "none" }}>
                      Open in Dispatch <ExternalLink size={11}/>
                    </a>
                  )}
                </div>
              </div>
            </div>
          )}

          {generatedAt && (
            <p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: 0, lineHeight: 1.5 }}>
              {/* No "version v4 / updated by Owner" line: the schedule tables carry no
                  version counter and no updated-by attribution, so those would be
                  invented. The resolve timestamp is the one thing that is true. */}
              Resolved {new Date(generatedAt).toLocaleString("en-IN", {
                day: "2-digit", month: "short", year: "numeric",
                hour: "2-digit", minute: "2-digit",
              })}
            </p>
          )}
        </div>
      </div>
    </>
  );
}

function Section({ title, children, first }: { title: string; children: React.ReactNode; first?: boolean }) {
  return (
    <div style={{
      marginTop: first ? 18 : 0, paddingTop: first ? 0 : 14, paddingBottom: 14,
      borderTop: first ? "none" : "1px solid var(--border)",
    }}>
      <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 9px" }}>{title}</p>
      {children}
    </div>
  );
}

function Muted({ children }: { children: React.ReactNode }) {
  return <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>{children}</p>;
}

function Failed({ children }: { children: React.ReactNode }) {
  return (
    <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>
      Couldn&apos;t load — {children}
    </p>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 10, fontSize: 12.5, padding: "3px 0" }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span style={{ color: "var(--text-primary)" }}>{value}</span>
    </div>
  );
}

function Row({ dot, label, value, hint, onRemove, removeTitle }: {
  dot: string; label: string; value: string; hint?: string | null;
  onRemove?: () => void; removeTitle?: string;
}) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, padding: "4px 0" }}>
      <div style={{ display: "flex", gap: 7, alignItems: "flex-start", minWidth: 0 }}>
        <span style={{ width: 7, height: 7, borderRadius: "50%", background: dot, marginTop: 5, flexShrink: 0 }}/>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 12.5, color: "var(--text-primary)" }}>{label}</div>
          {hint && <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{hint}</div>}
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
        <span style={{ fontSize: 12.5, color: "var(--text-primary)" }}>{value}</span>
        {onRemove && (
          <button onClick={onRemove} title={removeTitle}
            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", padding: 2, display: "flex" }}>
            <Trash2 size={12}/>
          </button>
        )}
      </div>
    </div>
  );
}
