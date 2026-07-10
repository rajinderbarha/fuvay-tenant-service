"use client";
import React from "react";
export interface TopbarProps {
  title?: string; actions?: React.ReactNode;
  search?: React.ReactNode; left?: React.ReactNode; right?: React.ReactNode;
  height?: number;
}
export function Topbar({ title, actions, search, left, right, height = 60 }: TopbarProps) {
  return (
    <header style={{ height, display:"flex", alignItems:"center", gap:12, padding:"0 24px",
      background:"var(--color-surface-base)", borderBottom:"1px solid var(--color-border)",
      boxShadow:"var(--shadow-sm)", flexShrink:0, position:"sticky", top:0,
      zIndex:"var(--z-sticky)" as unknown as number }}>
      {left}
      {title && <h1 style={{ fontSize:"var(--text-xl)", fontWeight:"var(--font-semibold)",
        color:"var(--color-text-primary)", margin:0, whiteSpace:"nowrap" }}>{title}</h1>}
      {search && <div style={{ flex:1, maxWidth:420 }}>{search}</div>}
      {!search && <div style={{ flex:1 }}/>}
      {actions && <div style={{ display:"flex", alignItems:"center", gap:10 }}>{actions}</div>}
      {right}
    </header>
  );
}
