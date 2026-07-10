"use client";
import React from "react";
export interface ConfirmDialogProps {
  open: boolean; onClose: () => void; onConfirm: () => void;
  title: string; description?: string; confirmLabel?: string; cancelLabel?: string;
  variant?: "default" | "danger"; loading?: boolean;
}
export function ConfirmDialog({ open, onClose, onConfirm, title, description, confirmLabel = "Confirm", cancelLabel = "Cancel", variant = "default", loading }: ConfirmDialogProps) {
  if (!open) return null;
  return (
    <div role="dialog" aria-modal onClick={e => e.target === e.currentTarget && onClose()}
      style={{ position:"fixed", inset:0, zIndex:"var(--z-modal)" as unknown as number,
        display:"flex", alignItems:"center", justifyContent:"center",
        background:"rgba(0,0,0,0.45)", backdropFilter:"blur(4px)",
        animation:"fadeIn 0.15s ease" }}>
      <div style={{ background:"var(--color-surface-elevated)", borderRadius:"var(--radius-xl)",
        boxShadow:"var(--shadow-xl)", border:"1px solid var(--color-border)",
        padding:"24px 28px", maxWidth:440, width:"90%",
        animation:"slideUp 0.2s cubic-bezier(0.34,1.56,0.64,1)" }}>
        <h2 style={{ fontSize:"var(--text-lg)", fontWeight:"var(--font-semibold)",
          color:"var(--color-text-primary)", margin:"0 0 10px" }}>{title}</h2>
        {description && <p style={{ fontSize:"var(--text-sm)", color:"var(--color-text-secondary)",
          margin:"0 0 24px", lineHeight:1.6 }}>{description}</p>}
        <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
          <button onClick={onClose} disabled={loading}
            style={{ padding:"8px 18px", borderRadius:"var(--radius-md)", border:"1px solid var(--color-border)",
              background:"transparent", color:"var(--color-text-secondary)", cursor:"pointer",
              fontSize:"var(--text-sm)", fontFamily:"var(--font-sans)", fontWeight:"var(--font-medium)" }}>
            {cancelLabel}
          </button>
          <button onClick={onConfirm} disabled={loading}
            style={{ padding:"8px 18px", borderRadius:"var(--radius-md)", border:"none",
              background: variant === "danger" ? "var(--color-danger)" : "var(--color-brand-500)",
              color:"var(--color-text-on-brand)", cursor: loading ? "not-allowed" : "pointer",
              fontSize:"var(--text-sm)", fontFamily:"var(--font-sans)", fontWeight:"var(--font-semibold)",
              opacity: loading ? 0.6 : 1, transition:"opacity 0.15s" }}>
            {loading ? "Loading…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
