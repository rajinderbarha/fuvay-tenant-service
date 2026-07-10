"use client";
import React from "react";
const TRANSITIONS: Record<string,string[]> = {
  assigned:["accepted","cancelled"],accepted:["en_route","cancelled"],
  en_route:["arrived"],arrived:["in_progress"],in_progress:["parts_required","quality_check","completed"],
  parts_required:["parts_sourced"],parts_sourced:["resumed"],resumed:["quality_check","completed"],
  quality_check:["completed","in_progress"],completed:["invoiced"],
  invoiced:["payment_pending"],payment_pending:["paid"],paid:["closed"],
  disputed:["resolved"],
};
const VARIANT: Record<string,string> = { cancelled:"var(--color-danger)", completed:"var(--color-success)", closed:"var(--color-text-secondary)", paid:"var(--color-success)" };
export interface JobAllowedTransitionsProps { currentStatus:string; onTransition?:(next:string)=>void; loading?:string; }
export function JobAllowedTransitions({ currentStatus, onTransition, loading }: JobAllowedTransitionsProps) {
  const allowed = TRANSITIONS[currentStatus] ?? [];
  if (allowed.length === 0) return <span style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)" }}>No transitions available</span>;
  return (
    <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
      {allowed.map(next => (
        <button key={next} onClick={() => onTransition?.(next)}
          disabled={loading === next}
          style={{ padding:"6px 14px", borderRadius:"var(--radius-sm)",
            border:`1px solid ${VARIANT[next]??"var(--color-border)"}`,
            background:"transparent",
            color: VARIANT[next] ?? "var(--color-text-secondary)",
            cursor: loading === next ? "not-allowed" : "pointer",
            fontSize:"var(--text-xs)", fontFamily:"var(--font-sans)",
            fontWeight:"var(--font-semibold)", opacity: loading===next?0.6:1,
            transition:"all 0.15s" }}>
          → {next.replace(/_/g," ")} {loading===next?"…":""}
        </button>
      ))}
    </div>
  );
}
