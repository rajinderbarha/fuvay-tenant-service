"use client";
import React, { useState } from "react";
export interface CopyableIdProps { id: string; prefix?: string; truncate?: number; size?: "sm"|"md"; }
export function CopyableId({ id, prefix, truncate = 8, size = "sm" }: CopyableIdProps) {
  const [copied, setCopied] = useState(false);
  async function copy(e: React.MouseEvent) {
    e.stopPropagation();
    try { await navigator.clipboard.writeText(id); } catch { /**/ }
    setCopied(true); setTimeout(() => setCopied(false), 1500);
  }
  const display = truncate && id.length > truncate + 3 ? `${id.slice(0,truncate)}…` : id;
  const FS = size === "sm" ? "var(--text-xs)" : "var(--text-sm)";
  return (
    <button onClick={copy} title={`Copy ${id}`} aria-label={`Copy ID: ${id}`}
      style={{ display:"inline-flex", alignItems:"center", gap:4,
        padding:"2px 7px", borderRadius:"var(--radius-sm)",
        border:`1px solid ${copied ? "var(--color-success-border)" : "var(--color-border)"}`,
        background: copied ? "var(--color-success-bg)" : "var(--color-surface-sunken)",
        color: copied ? "var(--color-success-text)" : "var(--color-text-tertiary)",
        fontSize:FS, fontFamily:"var(--font-mono)", cursor:"pointer",
        transition:"all 0.15s", whiteSpace:"nowrap" }}>
      {prefix && <span style={{ opacity:0.6 }}>{prefix}</span>}
      {display}
      <span style={{ opacity:0.5, fontSize:10 }}>{copied ? "✓" : "⎘"}</span>
    </button>
  );
}
