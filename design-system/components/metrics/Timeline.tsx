"use client";
import React from "react";
export interface TimelineItem { id:string; title:string; description?:string; time?:string; icon?:React.ReactNode; variant?:"default"|"success"|"warning"|"danger"|"info"; }
const TV: Record<string,string> = { default:"var(--color-border-strong)", success:"var(--color-success)", warning:"var(--color-warning)", danger:"var(--color-danger)", info:"var(--color-info)" };
export interface TimelineProps { items: TimelineItem[]; compact?: boolean; }
export function Timeline({ items, compact }: TimelineProps) {
  return (
    <div role="list">
      {items.map((item, i) => (
        <div key={item.id} role="listitem"
          style={{ display:"flex", gap: compact ? 10 : 14,
            paddingBottom: i < items.length-1 ? (compact ? 12 : 20) : 0 }}>
          {/* Line + dot */}
          <div style={{ display:"flex", flexDirection:"column", alignItems:"center", flexShrink:0 }}>
            <div style={{ width: compact ? 24 : 32, height: compact ? 24 : 32,
              borderRadius:"var(--radius-full)",
              background: item.icon ? "var(--color-surface-sunken)" : TV[item.variant??"default"]+"22",
              border:`2px solid ${TV[item.variant??"default"]}`,
              display:"flex", alignItems:"center", justifyContent:"center",
              fontSize: compact ? 11 : 14, color:TV[item.variant??"default"], flexShrink:0 }}>
              {item.icon ?? "●"}
            </div>
            {i < items.length-1 && (
              <div style={{ width:2, flex:1, marginTop:4,
                background:"var(--color-border)", borderRadius:"var(--radius-full)" }}/>
            )}
          </div>
          {/* Content */}
          <div style={{ paddingTop: compact ? 3 : 5, flex:1, minWidth:0 }}>
            <div style={{ display:"flex", alignItems:"baseline", justifyContent:"space-between", gap:8 }}>
              <p style={{ fontSize: compact ? "var(--text-sm)" : "var(--text-base)",
                fontWeight:"var(--font-semibold)", color:"var(--color-text-primary)",
                margin:"0 0 3px" }}>{item.title}</p>
              {item.time && <span style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)",
                whiteSpace:"nowrap", flexShrink:0 }}>{item.time}</span>}
            </div>
            {item.description && <p style={{ fontSize:"var(--text-sm)", color:"var(--color-text-secondary)",
              margin:0, lineHeight:1.5 }}>{item.description}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}
