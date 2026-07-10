"use client";
import React from "react";
export interface SeparatorProps { orientation?: "horizontal"|"vertical"; label?: string; spacing?: number; }
export function Separator({ orientation = "horizontal", label, spacing = 16 }: SeparatorProps) {
  if (orientation === "vertical") return (
    <div style={{ width:1, background:"var(--color-border)", alignSelf:"stretch", flexShrink:0,
      margin:`0 ${spacing}px` }}/>
  );
  if (label) return (
    <div style={{ display:"flex", alignItems:"center", gap:12, margin:`${spacing}px 0` }}>
      <div style={{ flex:1, height:1, background:"var(--color-border)" }}/>
      <span style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)",
        fontWeight:"var(--font-semibold)", textTransform:"uppercase", letterSpacing:"0.08em" }}>
        {label}
      </span>
      <div style={{ flex:1, height:1, background:"var(--color-border)" }}/>
    </div>
  );
  return <div style={{ height:1, background:"var(--color-border)", margin:`${spacing}px 0` }}/>;
}
