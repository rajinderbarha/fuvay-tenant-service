"use client";
import React from "react";
import { SLA_BANDS } from "../../tokens/tokens";
export interface JobSlaBadgeProps { minutesOverdue: number; slaMinutes?: number; }
export function JobSlaBadge({ minutesOverdue, slaMinutes }: JobSlaBadgeProps) {
  const band = SLA_BANDS.find(b => minutesOverdue <= b.maxMinutes) ?? SLA_BANDS[SLA_BANDS.length-1];
  const styles: Record<string,React.CSSProperties> = {
    ok:       { background:"var(--color-success-bg)", color:"var(--color-success-text)", border:"1px solid var(--color-success-border)" },
    warning:  { background:"var(--color-warning-bg)", color:"var(--color-warning-text)", border:"1px solid var(--color-warning-border)" },
    danger:   { background:"var(--color-danger-bg)",  color:"var(--color-danger-text)",  border:"1px solid var(--color-danger-border)"  },
    critical: { background:"var(--color-danger-bg)",  color:"var(--color-danger-text)",  border:"2px solid var(--color-danger)"         },
  };
  const mins = Math.abs(minutesOverdue);
  const label = mins > 0 ? `${band.label} · ${mins}m` : band.label;
  return (
    <span style={{ display:"inline-flex", alignItems:"center", gap:5, fontSize:"var(--text-xs)",
      fontWeight:700, padding:"3px 9px", borderRadius:"var(--radius-full)",
      letterSpacing:"0.03em", ...styles[band.severity] }}>
      {band.severity !== "ok" && <span style={{ animation:"pulse 1.5s infinite" }}>●</span>}
      {label}
      {slaMinutes && band.severity === "ok" && ` / ${slaMinutes}m SLA`}
    </span>
  );
}
