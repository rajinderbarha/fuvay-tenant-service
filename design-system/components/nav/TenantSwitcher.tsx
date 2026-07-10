"use client";
import React, { useState } from "react";
export interface TenantOption { id: string; name: string; vertical: string; city?: string; health_score?: number; logo?: string; }
export interface TenantSwitcherProps { current?: TenantOption; options?: TenantOption[]; onSwitch?: (t: TenantOption) => void; }
export function TenantSwitcher({ current, options = [], onSwitch }: TenantSwitcherProps) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ position:"relative" }}>
      <button onClick={() => setOpen(!open)} aria-expanded={open}
        style={{ display:"flex", alignItems:"center", gap:8, padding:"6px 12px",
          borderRadius:"var(--radius-md)", border:"1px solid var(--color-border)",
          background:"var(--color-surface-base)", cursor:"pointer",
          fontFamily:"var(--font-sans)", transition:"all 0.15s",
          maxWidth:220 }}>
        <div style={{ width:26, height:26, borderRadius:"var(--radius-sm)",
          background:"var(--color-brand-500)", display:"flex", alignItems:"center",
          justifyContent:"center", color:"white", fontWeight:"var(--font-bold)",
          fontSize:"var(--text-sm)", flexShrink:0 }}>
          {current?.name?.[0] ?? "T"}
        </div>
        <div style={{ minWidth:0, textAlign:"left" }}>
          <p style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-semibold)",
            color:"var(--color-text-primary)", margin:0, overflow:"hidden",
            textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{current?.name ?? "Select tenant"}</p>
          {current?.vertical && <p style={{ fontSize:10, color:"var(--color-text-tertiary)",
            margin:0, textTransform:"uppercase", letterSpacing:"0.05em" }}>
            {current.vertical.replace(/_/g," ")}
          </p>}
        </div>
        <span style={{ fontSize:10, color:"var(--color-text-tertiary)", flexShrink:0 }}>⌄</span>
      </button>
      {open && options.length > 0 && (
        <div style={{ position:"absolute", top:"calc(100% + 4px)", left:0, minWidth:260,
          background:"var(--color-surface-elevated)", border:"1px solid var(--color-border)",
          borderRadius:"var(--radius-lg)", boxShadow:"var(--shadow-lg)",
          zIndex:"var(--z-dropdown)" as unknown as number, overflow:"hidden", animation:"slideDown 0.15s ease" }}>
          <p style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)",
            padding:"8px 14px", margin:0, fontWeight:"var(--font-semibold)",
            textTransform:"uppercase", letterSpacing:"0.06em", borderBottom:"1px solid var(--color-border)" }}>
            Switch workspace
          </p>
          {options.map(t => (
            <div key={t.id} onClick={() => { onSwitch?.(t); setOpen(false); }}
              style={{ display:"flex", alignItems:"center", gap:10, padding:"10px 14px",
                cursor:"pointer", background: t.id === current?.id ? "var(--color-surface-sunken)" : "transparent",
                borderBottom:"1px solid var(--color-border)" }}
              onMouseEnter={e=>(e.currentTarget as HTMLDivElement).style.background="var(--color-surface-sunken)"}
              onMouseLeave={e=>(e.currentTarget as HTMLDivElement).style.background=t.id===current?.id?"var(--color-surface-sunken)":"transparent"}>
              <div style={{ width:30, height:30, borderRadius:"var(--radius-sm)",
                background:"var(--color-brand-500)", display:"flex", alignItems:"center",
                justifyContent:"center", color:"white", fontWeight:"var(--font-bold)",
                fontSize:"var(--text-sm)", flexShrink:0 }}>{t.name[0]}</div>
              <div style={{ flex:1, minWidth:0 }}>
                <p style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-medium)",
                  color:"var(--color-text-primary)", margin:0 }}>{t.name}</p>
                <p style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)",
                  margin:0 }}>{t.city ?? t.vertical.replace(/_/g," ")}</p>
              </div>
              {t.id === current?.id && <span style={{ color:"var(--color-accent)", fontSize:14 }}>✓</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
