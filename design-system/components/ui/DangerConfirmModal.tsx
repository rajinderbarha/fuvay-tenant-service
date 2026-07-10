"use client";
import React, { useState } from "react";
export interface DangerConfirmModalProps {
  open: boolean; onClose: () => void; onConfirm: () => void;
  title: string; description?: string;
  confirmPhrase: string;
  confirmLabel?: string; loading?: boolean;
}
export function DangerConfirmModal({ open, onClose, onConfirm, title, description, confirmPhrase, confirmLabel = "Delete permanently", loading }: DangerConfirmModalProps) {
  const [typed, setTyped] = useState("");
  if (!open) return null;
  const match = typed === confirmPhrase;
  function handleConfirm() { if (!match) return; onConfirm(); }
  return (
    <div role="dialog" aria-modal onClick={e => e.target === e.currentTarget && onClose()}
      style={{ position:"fixed", inset:0, zIndex:"var(--z-modal)" as unknown as number,
        display:"flex", alignItems:"center", justifyContent:"center",
        background:"rgba(0,0,0,0.5)", backdropFilter:"blur(4px)", animation:"fadeIn 0.15s ease" }}>
      <div style={{ background:"var(--color-surface-elevated)", borderRadius:"var(--radius-xl)",
        boxShadow:"var(--shadow-xl)", border:"1px solid var(--color-danger-border)",
        padding:"24px 28px", maxWidth:480, width:"90%",
        animation:"scaleIn 0.2s ease" }}>
        <div style={{ width:40, height:40, borderRadius:"var(--radius-lg)",
          background:"var(--color-danger-bg)", display:"flex", alignItems:"center",
          justifyContent:"center", marginBottom:16, fontSize:20 }}>⚠</div>
        <h2 style={{ fontSize:"var(--text-xl)", fontWeight:"var(--font-bold)",
          color:"var(--color-text-primary)", margin:"0 0 8px" }}>{title}</h2>
        {description && <p style={{ fontSize:"var(--text-sm)", color:"var(--color-text-secondary)",
          margin:"0 0 20px", lineHeight:1.6 }}>{description}</p>}
        <div style={{ padding:"12px 14px", borderRadius:"var(--radius-md)",
          background:"var(--color-danger-bg)", border:"1px solid var(--color-danger-border)",
          marginBottom:16 }}>
          <p style={{ fontSize:"var(--text-sm)", color:"var(--color-danger-text)", margin:0 }}>
            Type <code style={{ fontFamily:"var(--font-mono)", background:"rgba(0,0,0,0.1)",
              padding:"1px 5px", borderRadius:3 }}>{confirmPhrase}</code> to confirm.
          </p>
        </div>
        <input value={typed} onChange={e => setTyped(e.target.value)}
          placeholder={`Type "${confirmPhrase}" to enable`}
          style={{ width:"100%", height:38, padding:"0 12px", fontSize:"var(--text-sm)",
            fontFamily:"var(--font-mono)", background:"var(--input-bg)",
            border:`1px solid ${match ? "var(--color-success)" : "var(--color-danger-border)"}`,
            borderRadius:"var(--radius-md)", color:"var(--color-text-primary)",
            outline:"none", marginBottom:20, boxSizing:"border-box" as const }}
        />
        <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
          <button onClick={onClose} style={{ padding:"8px 18px", borderRadius:"var(--radius-md)",
            border:"1px solid var(--color-border)", background:"transparent",
            color:"var(--color-text-secondary)", cursor:"pointer",
            fontSize:"var(--text-sm)", fontFamily:"var(--font-sans)" }}>
            Cancel
          </button>
          <button onClick={handleConfirm} disabled={!match || loading}
            style={{ padding:"8px 18px", borderRadius:"var(--radius-md)", border:"none",
              background:"var(--color-danger)", color:"white",
              cursor: !match || loading ? "not-allowed" : "pointer",
              fontSize:"var(--text-sm)", fontFamily:"var(--font-sans)", fontWeight:"var(--font-semibold)",
              opacity: !match ? 0.5 : 1, transition:"opacity 0.15s" }}>
            {loading ? "Deleting…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
