"use client";
import React, { useState } from "react";
export interface CopyButtonProps { value: string; size?: "sm"|"md"; label?: string; successLabel?: string; }
export function CopyButton({ value, size = "sm", label = "Copy", successLabel = "Copied!" }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try { await navigator.clipboard.writeText(value); } catch { const t=document.createElement("textarea"); t.value=value; document.body.appendChild(t); t.select(); document.execCommand("copy"); document.body.removeChild(t); }
    setCopied(true); setTimeout(() => setCopied(false), 1500);
  }
  const S = { sm: { fontSize:"var(--text-xs)", padding:"3px 9px", height:26 }, md: { fontSize:"var(--text-sm)", padding:"5px 12px", height:32 } };
  return (
    <button onClick={copy} aria-label={`Copy ${value}`}
      style={{ display:"inline-flex", alignItems:"center", gap:5, borderRadius:"var(--radius-sm)",
        border:`1px solid ${copied ? "var(--color-success-border)" : "var(--color-border)"}`,
        background: copied ? "var(--color-success-bg)" : "var(--color-surface-base)",
        color: copied ? "var(--color-success-text)" : "var(--color-text-secondary)",
        cursor:"pointer", fontFamily:"var(--font-sans)", fontWeight:"var(--font-medium)",
        transition:"all 0.15s", ...S[size] }}>
      {copied ? "✓" : "⎘"} {copied ? successLabel : label}
    </button>
  );
}
