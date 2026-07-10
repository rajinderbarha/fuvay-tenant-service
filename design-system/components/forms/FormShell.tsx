"use client";
import React from "react";
export interface FormSection { title?: string; description?: string; fields: React.ReactNode; cols?: 1|2; }
export interface FormShellProps {
  sections: FormSection[]; onSubmit?: (e: React.FormEvent)=>void;
  submitLabel?: string; cancelLabel?: string; onCancel?: ()=>void;
  loading?: boolean; title?: string; subtitle?: string;
  error?: string; success?: string;
}
export function FormShell({ sections, onSubmit, submitLabel = "Save changes", cancelLabel = "Cancel", onCancel, loading, title, subtitle, error, success }: FormShellProps) {
  return (
    <form onSubmit={onSubmit} noValidate style={{ display:"flex", flexDirection:"column", gap:0 }}>
      {(title || subtitle) && (
        <div style={{ marginBottom:24 }}>
          {title    && <h2 style={{ fontSize:"var(--text-2xl)", fontWeight:"var(--font-bold)", color:"var(--color-text-primary)", margin:"0 0 6px" }}>{title}</h2>}
          {subtitle && <p  style={{ fontSize:"var(--text-base)", color:"var(--color-text-secondary)", margin:0 }}>{subtitle}</p>}
        </div>
      )}
      {error && (
        <div style={{ padding:"12px 14px", borderRadius:"var(--radius-md)", marginBottom:20,
          background:"var(--color-danger-bg)", border:"1px solid var(--color-danger-border)",
          color:"var(--color-danger-text)", fontSize:"var(--text-sm)" }}>{error}</div>
      )}
      {success && (
        <div style={{ padding:"12px 14px", borderRadius:"var(--radius-md)", marginBottom:20,
          background:"var(--color-success-bg)", border:"1px solid var(--color-success-border)",
          color:"var(--color-success-text)", fontSize:"var(--text-sm)" }}>✓ {success}</div>
      )}
      {sections.map((sec, i) => (
        <div key={i} style={{ paddingBottom:28, marginBottom:28,
          borderBottom: i < sections.length-1 ? "1px solid var(--color-border)" : "none" }}>
          {(sec.title || sec.description) && (
            <div style={{ marginBottom:18 }}>
              {sec.title       && <h3 style={{ fontSize:"var(--text-lg)", fontWeight:"var(--font-semibold)", color:"var(--color-text-primary)", margin:"0 0 4px" }}>{sec.title}</h3>}
              {sec.description && <p  style={{ fontSize:"var(--text-sm)", color:"var(--color-text-secondary)", margin:0 }}>{sec.description}</p>}
            </div>
          )}
          <div style={{ display:"grid", gridTemplateColumns: sec.cols === 2 ? "repeat(2,1fr)" : "1fr",
            gap:16 }}>
            {sec.fields}
          </div>
        </div>
      ))}
      <div style={{ display:"flex", gap:10, justifyContent:"flex-end", paddingTop:8 }}>
        {onCancel && (
          <button type="button" onClick={onCancel} disabled={loading}
            style={{ padding:"9px 20px", borderRadius:"var(--radius-md)",
              border:"1px solid var(--color-border)", background:"transparent",
              color:"var(--color-text-secondary)", cursor:"pointer",
              fontSize:"var(--text-sm)", fontFamily:"var(--font-sans)",
              fontWeight:"var(--font-medium)" }}>
            {cancelLabel}
          </button>
        )}
        <button type="submit" disabled={loading}
          style={{ padding:"9px 20px", borderRadius:"var(--radius-md)", border:"none",
            background: loading ? "var(--color-surface-sunken)" : "var(--color-brand-500)",
            color: loading ? "var(--color-text-tertiary)" : "white",
            cursor: loading ? "not-allowed" : "pointer",
            fontSize:"var(--text-sm)", fontFamily:"var(--font-sans)",
            fontWeight:"var(--font-semibold)", opacity: loading ? 0.6 : 1,
            minWidth:120, transition:"all 0.15s" }}>
          {loading ? "Saving…" : submitLabel}
        </button>
      </div>
    </form>
  );
}
