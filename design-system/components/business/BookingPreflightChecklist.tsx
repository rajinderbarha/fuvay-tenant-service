"use client";
import React from "react";
export interface PreflightCheck { id:string; label:string; status:"pass"|"fail"|"pending"|"skip"; detail?:string; }
export interface BookingPreflightChecklistProps { checks:PreflightCheck[]; title?:string; onProceed?:()=>void; onCancel?:()=>void; loading?:boolean; }
export function BookingPreflightChecklist({ checks, title="Booking Preflight", onProceed, onCancel, loading }: BookingPreflightChecklistProps) {
  const all   = checks.every(c => c.status==="pass"||c.status==="skip");
  const anyFail = checks.some(c => c.status==="fail");
  const icons = { pass:"✓", fail:"✕", pending:"○", skip:"–" };
  const colors = { pass:"var(--color-success-text)", fail:"var(--color-danger-text)", pending:"var(--color-text-tertiary)", skip:"var(--color-text-tertiary)" };
  return (
    <div style={{ background:"var(--color-surface-base)", border:"1px solid var(--color-border)",
      borderRadius:"var(--radius-xl)", overflow:"hidden", boxShadow:"var(--shadow-md)" }}>
      <div style={{ padding:"16px 20px", borderBottom:"1px solid var(--color-border)",
        background:"var(--color-surface-sunken)" }}>
        <h3 style={{ fontSize:"var(--text-base)", fontWeight:"var(--font-semibold)",
          color:"var(--color-text-primary)", margin:0 }}>{title}</h3>
      </div>
      <div style={{ padding:"8px 0" }}>
        {checks.map(c=>(
          <div key={c.id} style={{ display:"flex", gap:10, padding:"10px 20px",
            borderBottom:"1px solid var(--color-border)" }}>
            <span style={{ width:20, height:20, borderRadius:"var(--radius-full)", flexShrink:0,
              background: c.status==="pass"?"var(--color-success-bg)":c.status==="fail"?"var(--color-danger-bg)":"var(--color-surface-sunken)",
              display:"flex", alignItems:"center", justifyContent:"center",
              fontSize:12, fontWeight:"var(--font-bold)", color:colors[c.status],
              marginTop:1 }}>{icons[c.status]}</span>
            <div>
              <p style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-medium)",
                color:"var(--color-text-primary)", margin:0 }}>{c.label}</p>
              {c.detail && <p style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)",
                margin:"2px 0 0" }}>{c.detail}</p>}
            </div>
          </div>
        ))}
      </div>
      {(onProceed || onCancel) && (
        <div style={{ display:"flex", gap:10, justifyContent:"flex-end",
          padding:"14px 20px", borderTop:"1px solid var(--color-border)",
          background:"var(--color-surface-sunken)" }}>
          {onCancel && <button onClick={onCancel} style={{ padding:"7px 16px", borderRadius:"var(--radius-md)",
            border:"1px solid var(--color-border)", background:"transparent",
            color:"var(--color-text-secondary)", cursor:"pointer",
            fontSize:"var(--text-sm)", fontFamily:"var(--font-sans)" }}>Cancel</button>}
          {onProceed && <button onClick={onProceed} disabled={!all||loading||anyFail}
            style={{ padding:"7px 16px", borderRadius:"var(--radius-md)", border:"none",
              background: all&&!anyFail?"var(--color-brand-500)":"var(--color-surface-sunken)",
              color: all&&!anyFail?"white":"var(--color-text-tertiary)",
              cursor: !all||anyFail||loading?"not-allowed":"pointer",
              fontSize:"var(--text-sm)", fontFamily:"var(--font-sans)", fontWeight:"var(--font-semibold)" }}>
            {loading?"Checking…":"Proceed →"}
          </button>}
        </div>
      )}
    </div>
  );
}
