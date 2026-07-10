"use client";
import React from "react";
export type AlertVariant = "info" | "success" | "warning" | "danger";
const AV: Record<AlertVariant, React.CSSProperties> = {
  info:    { background:"var(--color-info-bg)",    borderLeftColor:"var(--color-info)",    color:"var(--color-info-text)"    },
  success: { background:"var(--color-success-bg)", borderLeftColor:"var(--color-success)", color:"var(--color-success-text)" },
  warning: { background:"var(--color-warning-bg)", borderLeftColor:"var(--color-warning)", color:"var(--color-warning-text)" },
  danger:  { background:"var(--color-danger-bg)",  borderLeftColor:"var(--color-danger)",  color:"var(--color-danger-text)"  },
};
const AI: Record<AlertVariant, string> = { info:"ℹ", success:"✓", warning:"⚠", danger:"✕" };
export interface AlertProps { variant?: AlertVariant; title?: string; children: React.ReactNode; onClose?: () => void; icon?: React.ReactNode; }
export function Alert({ variant = "info", title, children, onClose, icon }: AlertProps) {
  return (
    <div role="alert" style={{ display:"flex", gap:12, padding:"14px 16px",
      borderRadius:"var(--radius-lg)", borderLeft:"4px solid",
      border:"1px solid", ...AV[variant],
      borderLeftWidth:3, animation:"slideDown 0.2s ease" }}>
      <span style={{ fontSize:16, flexShrink:0, lineHeight:1.4, fontWeight:"var(--font-bold)" }}>
        {icon ?? AI[variant]}
      </span>
      <div style={{ flex:1 }}>
        {title && <p style={{ fontWeight:"var(--font-semibold)", fontSize:"var(--text-base)", margin:"0 0 3px" }}>{title}</p>}
        <div style={{ fontSize:"var(--text-sm)", lineHeight:1.5 }}>{children}</div>
      </div>
      {onClose && <button onClick={onClose} style={{ background:"none", border:"none", cursor:"pointer",
        color:"currentColor", opacity:0.6, fontSize:16, padding:0, lineHeight:1, flexShrink:0 }}>✕</button>}
    </div>
  );
}
