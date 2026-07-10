"use client";
import React from "react";
export interface KpiCardProps {
  label: string; value: string|number; change?: string; trend?: "up"|"down"|"neutral";
  icon?: React.ReactNode; onClick?: ()=>void; alert?: boolean;
  loading?: boolean; id?: string;
  prefix?: string; suffix?: string;
}
export function KpiCard({ label, value, change, trend, icon, onClick, alert, loading, id, prefix, suffix }: KpiCardProps) {
  const [hov, setHov] = React.useState(false);
  const tC = trend === "up" ? "var(--color-success-text)" : trend === "down" ? "var(--color-danger-text)" : "var(--color-text-tertiary)";
  return (
    <div id={id} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)} onClick={onClick}
      style={{ background: alert ? "var(--color-danger-bg)" : "var(--color-surface-base)",
        border:`1px solid ${alert ? "var(--color-danger-border)" : hov && onClick ? "var(--color-border-strong)" : "var(--color-border)"}`,
        borderRadius:"var(--radius-lg)", padding:"18px 20px",
        boxShadow: hov && onClick ? "var(--shadow-md)" : "var(--shadow-sm)",
        display:"flex", flexDirection:"column", gap:10,
        cursor: onClick ? "pointer" : undefined, transition:"all 0.15s ease",
        transform: hov && onClick ? "translateY(-1px)" : "none" }}>
      <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between" }}>
        <p style={{ fontSize:"var(--text-xs)", fontWeight:"var(--font-bold)",
          color: alert ? "var(--color-danger-text)" : "var(--color-text-tertiary)",
          margin:0, textTransform:"uppercase", letterSpacing:"0.06em" }}>{label}</p>
        {icon && <div style={{ width:34, height:34, borderRadius:"var(--radius)",
          background: alert ? "var(--color-danger-border)" : "var(--color-accent-muted)",
          display:"flex", alignItems:"center", justifyContent:"center",
          color: alert ? "var(--color-danger-text)" : "var(--color-accent)", flexShrink:0 }}>{icon}</div>}
      </div>
      {loading ? (
        <div className="skeleton" style={{ height:32, width:80, borderRadius:"var(--radius)" }}/>
      ) : (
        <p style={{ fontSize:"var(--text-5xl)", fontWeight:"var(--font-extrabold)",
          color: alert ? "var(--color-danger-text)" : "var(--color-text-primary)",
          margin:0, lineHeight:1, letterSpacing:"-0.03em" }}>
          {prefix && <span style={{ fontSize:"var(--text-2xl)", fontWeight:"var(--font-semibold)", opacity:0.7 }}>{prefix}</span>}
          {value}
          {suffix && <span style={{ fontSize:"var(--text-2xl)", fontWeight:"var(--font-semibold)", opacity:0.7 }}>{suffix}</span>}
        </p>
      )}
      {change && <p style={{ fontSize:"var(--text-sm)", color:tC, margin:0 }}>
        {trend === "up" ? "↑" : trend === "down" ? "↓" : "→"} {change}
      </p>}
    </div>
  );
}
