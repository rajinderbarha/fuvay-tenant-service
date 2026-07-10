/** Tabs — segmented navigation. */
import React, { useState } from "react";

export interface Tab { id: string; label: string; icon?: React.ReactNode; count?: number; }

export function Tabs({ tabs, activeId, onTabChange, style }:{
  tabs: Tab[]; activeId: string; onTabChange: (id:string)=>void; style?: React.CSSProperties;
}) {
  return (
    <div style={{
      display: "flex", gap: "2px", padding: "4px",
      background: "var(--color-surface-sunken)",
      borderRadius: "12px", border: "1px solid var(--color-border)",
      ...style,
    }}>
      {tabs.map(tab => {
        const active = tab.id === activeId;
        return (
          <button key={tab.id} onClick={() => onTabChange(tab.id)} style={{
            display: "flex", alignItems: "center", gap: "6px",
            padding: "7px 14px", borderRadius: "9px", border: "none",
            background: active ? "var(--color-surface-base)" : "transparent",
            color: active ? "var(--color-text-primary)" : "var(--color-text-secondary)",
            fontWeight: active ? 600 : 400, fontSize: "13px",
            cursor: "pointer", transition: "all 0.15s ease",
            boxShadow: active ? "var(--shadow-sm)" : "none",
          }}>
            {tab.icon}
            {tab.label}
            {tab.count != null && (
              <span style={{
                background: active ? "var(--color-accent-muted)" : "var(--color-border)",
                color: active ? "var(--color-accent)" : "var(--color-text-tertiary)",
                borderRadius: "999px", padding: "1px 7px", fontSize: "11px", fontWeight: 600,
              }}>{tab.count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
