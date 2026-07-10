"use client";
import React from "react";
import { tokens, type HealthBand } from "../../tokens/tokens";
export interface HealthBadgeProps { band: HealthBand | string; score?: number; size?: "sm" | "md"; }
export function HealthBadge({ band, score, size = "md" }: HealthBadgeProps) {
  const c = tokens.colors.health[band as HealthBand] ?? tokens.colors.health.critical;
  return (
    <span style={{ display:"inline-flex", alignItems:"center", gap:5,
      borderRadius:"var(--radius-full)", fontWeight:700, letterSpacing:"0.04em",
      fontSize: size === "sm" ? "var(--text-xs)" : "var(--text-xs)",
      padding: size === "sm" ? "2px 7px" : "3px 10px",
      background:c.bg, color:c.text, border:`1px solid ${c.border}`, whiteSpace:"nowrap" }}>
      <span style={{ width:6, height:6, borderRadius:"50%", background:c.icon, flexShrink:0 }}/>
      {band.replace(/_/g," ")}
      {score != null && <span style={{ opacity:0.75 }}>· {score}</span>}
    </span>
  );
}
