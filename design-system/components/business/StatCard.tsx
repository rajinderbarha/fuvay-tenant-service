/** StatCard — KPI metric card. */
import React from "react";

export function StatCard({ label, value, change, changeLabel, icon, trend, style }:{
  label:string; value:string|number; change?:number;
  changeLabel?:string; icon?:React.ReactNode; trend?:"up"|"down"|"neutral";
  style?:React.CSSProperties;
}) {
  const trendColor = trend === "up"   ? "var(--color-success-text)"
                   : trend === "down" ? "var(--color-danger-text)"
                   : "var(--color-text-tertiary)";
  const trendSign  = change != null && change > 0 ? "↑" : change != null && change < 0 ? "↓" : "";

  return (
    <div style={{
      background:"var(--color-surface-base)", border:"1px solid var(--color-border)",
      borderRadius:"14px", padding:"20px 22px",
      boxShadow:"var(--shadow-sm)", display:"flex", flexDirection:"column", gap:"12px",
      ...style,
    }}>
      <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between" }}>
        <p style={{ fontSize:"12px", fontWeight:500, color:"var(--color-text-secondary)", margin:0, textTransform:"uppercase", letterSpacing:"0.05em" }}>
          {label}
        </p>
        {icon && (
          <div style={{ width:36, height:36, borderRadius:"10px", background:"var(--color-accent-muted)",
            display:"flex", alignItems:"center", justifyContent:"center",
            color:"var(--color-accent)", flexShrink:0 }}>
            {icon}
          </div>
        )}
      </div>
      <p style={{ fontSize:"28px", fontWeight:700, color:"var(--color-text-primary)", margin:0, lineHeight:1 }}>
        {value}
      </p>
      {(change != null || changeLabel) && (
        <p style={{ fontSize:"12px", color:trendColor, margin:0, display:"flex", gap:"4px", alignItems:"center" }}>
          {trendSign}{change != null ? `${Math.abs(change)}%` : ""} {changeLabel}
        </p>
      )}
    </div>
  );
}
