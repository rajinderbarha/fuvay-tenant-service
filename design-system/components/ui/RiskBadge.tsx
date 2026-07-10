"use client";
import React from "react";
export type RiskLevel = "low" | "medium" | "high" | "critical";
const RISK: Record<RiskLevel, { bg:string; text:string; border:string; label:string }> = {
  low:      { bg:"var(--color-success-bg)",     text:"var(--color-success-text)",     border:"var(--color-success-border)",   label:"Low Risk"      },
  medium:   { bg:"var(--color-warning-bg)",     text:"var(--color-warning-text)",     border:"var(--color-warning-border)",   label:"Medium Risk"   },
  high:     { bg:"var(--color-danger-bg)",      text:"var(--color-danger-text)",      border:"var(--color-danger-border)",    label:"High Risk"     },
  critical: { bg:"var(--color-danger-bg)",      text:"var(--color-danger-text)",      border:"var(--color-danger-border)",    label:"Critical Risk" },
};
export interface RiskBadgeProps { level: RiskLevel; showLabel?: boolean; }
export function RiskBadge({ level, showLabel = true }: RiskBadgeProps) {
  const c = RISK[level];
  return (
    <span style={{ display:"inline-flex", alignItems:"center", gap:5,
      borderRadius:"var(--radius-full)", fontWeight:700, fontSize:"var(--text-xs)",
      padding:"3px 9px", background:c.bg, color:c.text, border:`1px solid ${c.border}` }}>
      <span style={{ width:5, height:5, borderRadius:"50%", background:c.text }}/>
      {showLabel && c.label}
    </span>
  );
}
