"use client";
import React from "react";
export interface DataDeletionRequestCardProps {
  requestId:string; userId:string; status:"pending"|"processing"|"completed"|"failed";
  slaDeadline:string; hoursUntilSla:number; tablesErased?:string[]; tablesExempted?:string[];
  exemptionReasons?:Record<string,string>;
  onProcess?:()=>void; loading?:boolean;
}
export function DataDeletionRequestCard({ requestId, userId, status, slaDeadline, hoursUntilSla, tablesErased=[], tablesExempted=[], exemptionReasons={}, onProcess, loading }: DataDeletionRequestCardProps) {
  const breached = hoursUntilSla < 0;
  const urgent   = !breached && hoursUntilSla < 24;
  const bgColor  = breached?"var(--color-danger-bg)":urgent?"var(--color-warning-bg)":"var(--color-surface-base)";
  const bdColor  = breached?"var(--color-danger-border)":urgent?"var(--color-warning-border)":"var(--color-border)";
  return (
    <div style={{ background:bgColor, border:`1px solid ${bdColor}`,
      borderRadius:"var(--radius-lg)", padding:"18px 20px", boxShadow:"var(--shadow-sm)" }}>
      <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", gap:16, marginBottom:12 }}>
        <div>
          <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:4 }}>
            <span style={{ display:"inline-flex", alignItems:"center", gap:4, fontSize:"var(--text-xs)",
              padding:"2px 8px", borderRadius:"var(--radius-full)", fontWeight:"var(--font-bold)",
              background: status==="completed"?"var(--color-success-bg)":status==="failed"?"var(--color-danger-bg)":breached?"var(--color-danger-bg)":urgent?"var(--color-warning-bg)":"var(--color-info-bg)",
              color: status==="completed"?"var(--color-success-text)":status==="failed"?"var(--color-danger-text)":breached?"var(--color-danger-text)":urgent?"var(--color-warning-text)":"var(--color-info-text)",
              border: `1px solid ${status==="completed"?"var(--color-success-border)":"var(--color-danger-border)"}` }}>
              {status.toUpperCase()}
            </span>
            {breached && <span style={{ fontSize:"var(--text-xs)", padding:"2px 7px", borderRadius:"var(--radius-full)",
              background:"var(--color-danger-bg)", color:"var(--color-danger-text)",
              fontWeight:"var(--font-bold)", border:"1px solid var(--color-danger-border)" }}>SLA BREACHED</span>}
            {urgent && !breached && <span style={{ fontSize:"var(--text-xs)", padding:"2px 7px",
              borderRadius:"var(--radius-full)", background:"var(--color-warning-bg)",
              color:"var(--color-warning-text)", fontWeight:"var(--font-bold)",
              border:"1px solid var(--color-warning-border)" }}>URGENT</span>}
          </div>
          <p style={{ fontSize:"var(--text-sm)", color:"var(--color-text-secondary)", margin:"0 0 3px" }}>
            User: <code style={{ fontFamily:"var(--font-mono)", background:"rgba(0,0,0,0.06)",
              padding:"1px 5px", borderRadius:3, fontSize:"var(--text-xs)" }}>{userId}</code>
          </p>
          <p style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)", margin:0 }}>
            SLA: {new Date(slaDeadline).toLocaleString("en-IN")}
            {status==="pending" && ` · ${Math.abs(hoursUntilSla).toFixed(1)}h ${breached?"overdue":"remaining"}`}
          </p>
        </div>
        {status==="pending" && onProcess && (
          <button onClick={onProcess} disabled={loading}
            style={{ padding:"7px 14px", borderRadius:"var(--radius-md)", border:"none",
              background: breached?"var(--color-danger)":"var(--color-brand-500)",
              color:"white", cursor:loading?"not-allowed":"pointer",
              fontSize:"var(--text-sm)", fontFamily:"var(--font-sans)", fontWeight:"var(--font-semibold)",
              opacity:loading?0.6:1, flexShrink:0 }}>
            {loading?"Processing…":"Process Deletion"}
          </button>
        )}
      </div>
      {tablesErased.length>0 && (
        <p style={{ fontSize:"var(--text-xs)", color:"var(--color-success-text)", margin:"0 0 4px" }}>
          ✓ Erased: {tablesErased.join(", ")}
        </p>
      )}
      {tablesExempted.length>0 && (
        <div>
          <p style={{ fontSize:"var(--text-xs)", color:"var(--color-warning-text)", margin:"0 0 4px" }}>
            ⚠ Exempt (legal):
          </p>
          {tablesExempted.map(t=>(
            <p key={t} style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)", margin:"1px 0", paddingLeft:12 }}>
              {t}: {exemptionReasons[t]??"Legal requirement"}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
