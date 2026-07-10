"use client";
import React from "react";
export type ProgressVariant = "default"|"success"|"warning"|"danger"|"info";
export interface ProgressBarProps { value: number; max?: number; label?: string; showPercent?: boolean; variant?: ProgressVariant; height?: number; animated?: boolean; }
const PV: Record<ProgressVariant, string> = {
  default: "var(--color-accent)",
  success: "var(--color-success)",
  warning: "var(--color-warning)",
  danger:  "var(--color-danger)",
  info:    "var(--color-info)",
};
export function ProgressBar({ value, max = 100, label, showPercent, variant = "default", height = 8, animated }: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const vv = variant === "default" && pct >= 90 ? "danger" : variant === "default" && pct >= 70 ? "warning" : variant;
  return (
    <div>
      {(label || showPercent) && (
        <div style={{ display:"flex", justifyContent:"space-between", marginBottom:5 }}>
          {label && <span style={{ fontSize:"var(--text-sm)", color:"var(--color-text-secondary)" }}>{label}</span>}
          {showPercent && <span style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-semibold)",
            color:"var(--color-text-primary)" }}>{pct.toFixed(0)}%</span>}
        </div>
      )}
      <div role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={max}
        style={{ height, background:"var(--color-border)", borderRadius:"var(--radius-full)", overflow:"hidden" }}>
        <div style={{ height:"100%", width:`${pct}%`, background:PV[vv],
          borderRadius:"var(--radius-full)", transition:"width 0.6s cubic-bezier(0.4,0,0.2,1)",
          ...(animated ? { backgroundImage:`linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.25) 50%, transparent 100%)`, backgroundSize:"200% 100%", animation:"shimmer 1.5s linear infinite" } : {}) }}/>
      </div>
    </div>
  );
}
