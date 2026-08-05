"use client";
/** Right-hand technician detail panel. Every section renders only what the
 * backend can actually prove:
 *  - Weekly pattern: aggregated from the real week's effective_schedules.
 *  - Capacity: real daily_capacity/concurrent_capacity from the resolver.
 *  - Service capability: real supported_services from the team-overview
 *    endpoint (GET /v1/tenant/home-services/team/{id}/overview).
 *  - Upcoming time off / per-staff date overrides: the backend has no table
 *    for either yet (see availability_resolver.py capability_flags) -- shown
 *    as an honest disclosure line, never a fabricated entry. */
import React from "react";
import { X, AlertTriangle } from "lucide-react";
import { Badge, Btn } from "../shared/ui";

export interface WeeklyPatternLine { label: string; value: string; }

export function ScheduleDetailPanel({
  staffName, isActive, weeklyPattern, breakLine, maxJobsPerDay, maxConcurrentJobs,
  serviceCapability, capabilityLoading, conflict, generatedAt, onClose, onEditAvailability,
}: {
  staffName: string; isActive: boolean;
  weeklyPattern: WeeklyPatternLine[]; breakLine: string | null;
  maxJobsPerDay: number | null; maxConcurrentJobs: number | null;
  serviceCapability: string[] | null; capabilityLoading: boolean;
  conflict: { dateLabel: string } | null;
  generatedAt: string | null;
  onClose: () => void; onEditAvailability: () => void;
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
        <div style={{ padding: 20, height: "100%", overflowY: "auto", boxSizing: "border-box" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Schedule details — {staffName}</h3>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)" }}>
            <X size={16}/>
          </button>
        </div>
        <Badge variant={isActive ? "success" : "muted"} size="sm">{isActive ? "Active" : "Inactive"}</Badge>

        <Section title="Weekly pattern">
          {weeklyPattern.map(l => <KV key={l.label} label={l.label} value={l.value}/>)}
          {breakLine && <KV label="Break" value={breakLine}/>}
        </Section>

        <Section title="Capacity">
          <KV label="Max jobs per day" value={maxJobsPerDay != null ? String(maxJobsPerDay) : "Not configured"}/>
          <KV label="Max concurrent jobs" value={maxConcurrentJobs != null ? String(maxConcurrentJobs) : "Not configured"}/>
        </Section>

        <Section title="Service capability">
          {capabilityLoading ? (
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Loading…</p>
          ) : serviceCapability && serviceCapability.length > 0 ? (
            <p style={{ fontSize: 12.5, color: "var(--text-primary)", margin: 0 }}>{serviceCapability.join(", ")}</p>
          ) : (
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>No services assigned yet.</p>
          )}
        </Section>

        <div style={{ padding: "10px 12px", borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)",
          fontSize: 11, color: "var(--text-tertiary)", margin: "16px 0" }}>
          Per-technician date overrides and time-off tracking aren&apos;t available yet — those tables don&apos;t exist in the
          backend. Overrides shown in the grid reflect tenant-wide schedule exceptions only.
        </div>

        {conflict && (
          <div style={{ padding: "10px 12px", borderRadius: 8, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", marginBottom: 16 }}>
            <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 4 }}>
              <AlertTriangle size={13} style={{ color: "var(--danger-text)" }}/>
              <p style={{ fontSize: 12, fontWeight: 700, color: "var(--danger-text)", margin: 0 }}>Schedule conflict on {conflict.dateLabel}</p>
            </div>
            <p style={{ fontSize: 11.5, color: "var(--danger-text)", margin: 0 }}>Overlapping assigned jobs exceed capacity.</p>
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <Btn variant="primary" onClick={onEditAvailability}>Edit availability</Btn>
          <span title="No time-off table exists in the backend yet.">
            <Btn variant="secondary" disabled fullWidth>Add time off</Btn>
          </span>
        </div>

        {generatedAt && (
          <p style={{ fontSize: 10.5, color: "var(--text-tertiary)", marginTop: 16 }}>
            Data generated {new Date(generatedAt).toLocaleString("en-IN")}
          </p>
        )}
        </div>
      </div>
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ margin: "16px 0" }}>
      <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.04em", margin: "0 0 8px" }}>{title}</p>
      {children}
    </div>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, padding: "4px 0" }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{value}</span>
    </div>
  );
}
