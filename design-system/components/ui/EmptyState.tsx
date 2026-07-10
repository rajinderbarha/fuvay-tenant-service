"use client";
import React from "react";
export interface EmptyStateProps { icon?: React.ReactNode; title: string; description?: string; action?: React.ReactNode; compact?: boolean; }
export function EmptyState({ icon, title, description, action, compact = false }: EmptyStateProps) {
  return (
    <div style={{ display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center",
      padding: compact ? "32px 24px" : "64px 32px", textAlign:"center", gap: compact ? 10 : 16 }}>
      {icon && <div style={{ fontSize: compact ? 28 : 40, marginBottom: compact ? 0 : 4,
        color:"var(--color-text-tertiary)" }}>{icon}</div>}
      <h3 style={{ fontSize: compact ? "var(--text-base)" : "var(--text-lg)", fontWeight:"var(--font-semibold)",
        color:"var(--color-text-primary)", margin:0 }}>{title}</h3>
      {description && <p style={{ fontSize:"var(--text-base)", color:"var(--color-text-secondary)",
        margin:0, maxWidth:400, lineHeight:1.6 }}>{description}</p>}
      {action && <div style={{ marginTop: compact ? 8 : 12 }}>{action}</div>}
    </div>
  );
}
