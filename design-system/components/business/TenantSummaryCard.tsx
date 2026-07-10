"use client";
import React from "react";
export interface TenantSummaryCardProps {
  name:string; vertical:string; city:string; plan_type:string; status:string;
  health_score:number; jobs_today?:number; commission_today?:number; wallet_balance?:number;
  onClick?: ()=>void; compact?: boolean;
}
export function TenantSummaryCard({ name, vertical, city, plan_type, status, health_score, jobs_today, commission_today, wallet_balance, onClick, compact }: TenantSummaryCardProps) {
  const [hov, setHov] = React.useState(false);
  const bandColor = health_score>=90?"var(--color-success)":health_score>=75?"var(--color-warning)":health_score>=55?"var(--color-text-tertiary)":health_score>=35?"var(--color-warning-text)":health_score>=15?"var(--color-warning)":"var(--color-danger)";
  const statusBg = status==="active"?"var(--color-success-bg)":status==="suspended"?"var(--color-danger-bg)":"var(--color-surface-sunken)";
  const statusText = status==="active"?"var(--color-success-text)":status==="suspended"?"var(--color-danger-text)":"var(--color-text-tertiary)";
  return (
    <div onMouseEnter={()=>setHov(true)} onMouseLeave={()=>setHov(false)} onClick={onClick}
      style={{ background:"var(--color-surface-base)", border:"1px solid var(--color-border)",
        borderRadius:"var(--radius-lg)", padding: compact ? "14px 16px" : "20px",
        boxShadow: hov&&onClick ? "var(--shadow-md)" : "var(--shadow-sm)",
        cursor: onClick ? "pointer" : undefined, transition:"all 0.15s",
        transform: hov&&onClick ? "translateY(-1px)" : "none" }}>
      <div style={{ display:"flex", alignItems:"center", gap:12, marginBottom:compact?10:16 }}>
        <div style={{ width: compact?36:44, height: compact?36:44, borderRadius:"var(--radius-md)",
          background:"var(--color-brand-500)", display:"flex", alignItems:"center",
          justifyContent:"center", color:"white", fontWeight:"var(--font-extrabold)",
          fontSize: compact?"var(--text-lg)":"var(--text-2xl)", flexShrink:0 }}>{name[0]}</div>
        <div style={{ flex:1, minWidth:0 }}>
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <p style={{ fontSize: compact?"var(--text-base)":"var(--text-lg)",
              fontWeight:"var(--font-semibold)", color:"var(--color-text-primary)",
              margin:0, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{name}</p>
            <span style={{ fontSize:"var(--text-xs)", padding:"2px 7px", borderRadius:"var(--radius-full)",
              background:statusBg, color:statusText, fontWeight:"var(--font-bold)", flexShrink:0 }}>{status}</span>
          </div>
          <p style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)", margin:"2px 0 0",
            textTransform:"uppercase", letterSpacing:"0.05em" }}>
            {vertical.replace(/_/g," ")} · {city} · {plan_type}
          </p>
        </div>
      </div>
      <div style={{ marginBottom:compact?10:14 }}>
        <div style={{ display:"flex", justifyContent:"space-between", marginBottom:5 }}>
          <span style={{ fontSize:"var(--text-xs)", fontWeight:"var(--font-semibold)",
            color:"var(--color-text-tertiary)", textTransform:"uppercase", letterSpacing:"0.05em" }}>
            Health Score
          </span>
          <span style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-bold)", color:bandColor }}>
            {health_score}
          </span>
        </div>
        <div style={{ height:6, background:"var(--color-border)", borderRadius:"var(--radius-full)", overflow:"hidden" }}>
          <div style={{ height:"100%", width:`${health_score}%`, background:bandColor,
            borderRadius:"var(--radius-full)", transition:"width 0.5s ease" }}/>
        </div>
      </div>
      {!compact && (jobs_today!=null||commission_today!=null||wallet_balance!=null) && (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:8 }}>
          {[
            { label:"Jobs Today",     v: jobs_today ?? 0 },
            { label:"Commission",     v: commission_today != null ? `₹${commission_today.toLocaleString("en-IN")}` : "—" },
            { label:"Wallet",         v: wallet_balance   != null ? `₹${(wallet_balance/1000).toFixed(1)}K` : "—" },
          ].map(m=>(
            <div key={m.label} style={{ padding:"8px 10px", borderRadius:"var(--radius-sm)",
              background:"var(--color-surface-sunken)", textAlign:"center" }}>
              <p style={{ fontSize:10, color:"var(--color-text-tertiary)", margin:"0 0 2px",
                textTransform:"uppercase", letterSpacing:"0.05em" }}>{m.label}</p>
              <p style={{ fontSize:"var(--text-base)", fontWeight:"var(--font-bold)",
                color:"var(--color-text-primary)", margin:0 }}>{String(m.v)}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
