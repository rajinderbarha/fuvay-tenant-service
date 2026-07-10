"use client";
import React from "react";
export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string; error?: string; hint?: string; rows?: number;
}
export function Textarea({ label, error, hint, rows = 4, style, id, ...props }: TextareaProps) {
  const uid = id || label?.toLowerCase().replace(/\s+/g,"-");
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:5 }}>
      {label && <label htmlFor={uid} style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-medium)",
        color:"var(--color-text-secondary)", letterSpacing:"0.02em" }}>{label}</label>}
      <textarea id={uid} rows={rows} {...props}
        style={{ width:"100%", padding:"10px 12px", fontSize:"var(--text-base)",
          fontFamily:"var(--font-sans)", background:"var(--input-bg)",
          border:`1px solid ${error ? "var(--color-danger)" : "var(--input-border)"}`,
          borderRadius:"var(--radius-md)", color:"var(--color-text-primary)",
          resize:"vertical", outline:"none", lineHeight:1.5,
          transition:"border-color 0.15s, box-shadow 0.15s", boxSizing:"border-box" as const, ...style }}
        onFocus={e => {
          e.currentTarget.style.borderColor = error ? "var(--color-danger)" : "var(--color-border-focus)";
          e.currentTarget.style.boxShadow = "0 0 0 3px " + (error ? "rgba(220,38,38,0.1)" : "rgba(46,134,171,0.12)");
        }}
        onBlur={e => {
          e.currentTarget.style.borderColor = error ? "var(--color-danger)" : "var(--input-border)";
          e.currentTarget.style.boxShadow = "none";
        }}
      />
      {error && <p style={{ fontSize:"var(--text-sm)", color:"var(--color-danger-text)", margin:0 }}>{error}</p>}
      {hint && !error && <p style={{ fontSize:"var(--text-sm)", color:"var(--color-text-tertiary)", margin:0 }}>{hint}</p>}
    </div>
  );
}
