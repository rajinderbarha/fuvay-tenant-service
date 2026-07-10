"use client";
import React, { useEffect } from "react";
export interface RightDrawerProps { open: boolean; onClose: ()=>void; title?: string; subtitle?: string; width?: number; children: React.ReactNode; footer?: React.ReactNode; }
export function RightDrawer({ open, onClose, title, subtitle, width = 480, children, footer }: RightDrawerProps) {
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div style={{ position:"fixed", inset:0, zIndex:"var(--z-modal)" as unknown as number,
      display:"flex", justifyContent:"flex-end" }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ position:"absolute", inset:0, background:"rgba(0,0,0,0.45)",
        backdropFilter:"blur(3px)", animation:"fadeIn 0.15s ease" }} onClick={onClose}/>
      <div role="dialog" aria-modal style={{ position:"relative", width, maxWidth:"100%",
        height:"100%", background:"var(--color-surface-elevated)",
        borderLeft:"1px solid var(--color-border)", boxShadow:"var(--shadow-xl)",
        display:"flex", flexDirection:"column", animation:"slideIn 0.25s ease" }}>
        {/* Header */}
        <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between",
          padding:"20px 24px", borderBottom:"1px solid var(--color-border)", flexShrink:0 }}>
          <div>
            {title && <h2 style={{ fontSize:"var(--text-xl)", fontWeight:"var(--font-semibold)",
              color:"var(--color-text-primary)", margin:0 }}>{title}</h2>}
            {subtitle && <p style={{ fontSize:"var(--text-sm)", color:"var(--color-text-secondary)",
              margin:"4px 0 0" }}>{subtitle}</p>}
          </div>
          <button onClick={onClose} aria-label="Close drawer"
            style={{ width:32, height:32, borderRadius:"var(--radius-sm)",
              border:"1px solid var(--color-border)", background:"transparent",
              display:"flex", alignItems:"center", justifyContent:"center",
              cursor:"pointer", color:"var(--color-text-tertiary)", fontSize:14, flexShrink:0 }}>✕</button>
        </div>
        {/* Body */}
        <div style={{ flex:1, overflowY:"auto", padding:"20px 24px" }}>{children}</div>
        {/* Footer */}
        {footer && (
          <div style={{ padding:"16px 24px", borderTop:"1px solid var(--color-border)",
            background:"var(--color-surface-sunken)", flexShrink:0 }}>{footer}</div>
        )}
      </div>
    </div>
  );
}
