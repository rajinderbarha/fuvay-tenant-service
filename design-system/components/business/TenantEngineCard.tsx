"use client";
import React from "react";
export interface TenantEngineCardProps { engineId:string; name:string; status:"active"|"disabled"|"error"; endpointCount:number; description?:string; version?:string; onToggle?:(enabled:boolean)=>void; }
const StatusDot: Record<string,string> = { active:"var(--color-success)", disabled:"var(--color-text-tertiary)", error:"var(--color-danger)" };
export function TenantEngineCard({ engineId, name, status, endpointCount, description, version, onToggle }: TenantEngineCardProps) {
  return (
    <div style={{ background:"var(--color-surface-base)", border:"1px solid var(--color-border)",
      borderRadius:"var(--radius-lg)", padding:"16px 18px", display:"flex",
      alignItems:"flex-start", gap:14, boxShadow:"var(--shadow-sm)" }}>
      <div style={{ width:42, height:42, borderRadius:"var(--radius-md)",
        background: status==="active"?"var(--color-accent-muted)":"var(--color-surface-sunken)",
        display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0,
        fontSize:20 }}>⚙</div>
      <div style={{ flex:1, minWidth:0 }}>
        <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:3 }}>
          <p style={{ fontSize:"var(--text-base)", fontWeight:"var(--font-semibold)",
            color:"var(--color-text-primary)", margin:0 }}>{name}</p>
          <span style={{ display:"inline-flex", alignItems:"center", gap:4, fontSize:"var(--text-xs)",
            padding:"2px 7px", borderRadius:"var(--radius-full)",
            background: status==="active"?"var(--color-success-bg)":status==="error"?"var(--color-danger-bg)":"var(--color-surface-sunken)",
            color: status==="active"?"var(--color-success-text)":status==="error"?"var(--color-danger-text)":"var(--color-text-tertiary)",
            fontWeight:"var(--font-bold)" }}>
            <span style={{ width:5, height:5, borderRadius:"50%", background:StatusDot[status] }}/>
            {status}
          </span>
        </div>
        <p style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)",
          margin:"0 0 6px", fontFamily:"var(--font-mono)" }}>{engineId}{version?` v${version}`:""}</p>
        {description && <p style={{ fontSize:"var(--text-sm)", color:"var(--color-text-secondary)",
          margin:"0 0 8px", lineHeight:1.4 }}>{description}</p>}
        <span style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)" }}>
          {endpointCount} endpoint{endpointCount!==1?"s":""}
        </span>
      </div>
      {onToggle && (
        <button onClick={() => onToggle(status !== "active")}
          style={{ padding:"5px 12px", borderRadius:"var(--radius-sm)",
            border:"1px solid var(--color-border)", background:"transparent",
            color:"var(--color-text-secondary)", cursor:"pointer",
            fontSize:"var(--text-xs)", fontFamily:"var(--font-sans)",
            fontWeight:"var(--font-medium)", flexShrink:0 }}>
          {status === "active" ? "Disable" : "Enable"}
        </button>
      )}
    </div>
  );
}
