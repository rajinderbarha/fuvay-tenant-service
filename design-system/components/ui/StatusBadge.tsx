"use client";
/**
 * StatusBadge — generic, driven by STATUS_MAP in tokens.ts.
 * CSS class controls all colours — zero hardcoded hex.
 */
import React from "react";
import { STATUS_MAP, type StatusKey } from "../../tokens/tokens";
export interface StatusBadgeProps { status: string; size?: "sm" | "md" | "lg"; dot?: boolean; }
export function StatusBadge({ status, size = "md", dot }: StatusBadgeProps) {
  const map  = STATUS_MAP[status as StatusKey];
  const css  = map?.cssClass ?? "status--unknown";
  const lbl  = map?.label   ?? status;
  const showDot = dot ?? map?.dot ?? false;
  const S: Record<string, React.CSSProperties> = {
    sm: { fontSize:"var(--text-xs)", padding:"2px 7px" },
    md: { fontSize:"var(--text-xs)", padding:"3px 9px" },
    lg: { fontSize:"var(--text-sm)", padding:"4px 12px" },
  };
  return (
    <span className={css} style={{ display:"inline-flex", alignItems:"center", gap:5,
      borderRadius:"var(--radius-full)", fontWeight:700, letterSpacing:"0.03em",
      background:"var(--st-bg)", color:"var(--st-text)", border:"1px solid var(--st-border)",
      whiteSpace:"nowrap", ...S[size] }}>
      {showDot && <span style={{ width:5, height:5, borderRadius:"50%", background:"var(--st-text)", flexShrink:0 }}/>}
      {lbl}
    </span>
  );
}
