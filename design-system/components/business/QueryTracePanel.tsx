"use client";
import React, { useState } from "react";
export interface QuerySpan { id:string; operation:string; table?:string; engine?:string; durationMs:number; rows?:number; index?:string; isSlow?:boolean; plan?:string; }
export interface QueryTracePanelProps { spans:QuerySpan[]; totalMs:number; endpoint?:string; requestId?:string; }
export function QueryTracePanel({ spans, totalMs, endpoint, requestId }: QueryTracePanelProps) {
  const [expanded, setExpanded] = useState<string|null>(null);
  const maxDur = Math.max(...spans.map(s=>s.durationMs), 1);
  const slowCount = spans.filter(s=>s.isSlow||s.durationMs>100).length;
  return (
    <div style={{ background:"var(--color-surface-base)", border:"1px solid var(--color-border)",
      borderRadius:"var(--radius-lg)", overflow:"hidden", fontFamily:"var(--font-mono)",
      boxShadow:"var(--shadow-sm)" }}>
      {/* Header */}
      <div style={{ padding:"12px 16px", borderBottom:"1px solid var(--color-border)",
        background:"var(--color-surface-sunken)",
        display:"flex", alignItems:"center", justifyContent:"space-between", gap:12, flexWrap:"wrap" }}>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <span style={{ fontSize:"var(--text-xs)", fontWeight:"var(--font-bold)",
            color:"var(--color-text-primary)" }}>QUERY TRACE</span>
          {endpoint && <code style={{ fontSize:"var(--text-xs)", color:"var(--color-accent)",
            background:"var(--color-accent-muted)", padding:"1px 6px", borderRadius:3 }}>
            {endpoint}
          </code>}
        </div>
        <div style={{ display:"flex", gap:12 }}>
          <span style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)" }}>
            {spans.length} queries
          </span>
          {slowCount > 0 && <span style={{ fontSize:"var(--text-xs)", color:"var(--color-warning-text)",
            background:"var(--color-warning-bg)", padding:"2px 7px", borderRadius:"var(--radius-sm)",
            border:"1px solid var(--color-warning-border)", fontWeight:"var(--font-bold)" }}>
            {slowCount} slow
          </span>}
          <span style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-bold)",
            color: totalMs>500?"var(--color-danger-text)":totalMs>200?"var(--color-warning-text)":"var(--color-success-text)" }}>
            {totalMs}ms total
          </span>
        </div>
      </div>
      {/* Spans */}
      {spans.map(span => (
        <div key={span.id}>
          <div onClick={() => setExpanded(expanded===span.id?null:span.id)}
            style={{ display:"flex", alignItems:"center", gap:10, padding:"9px 16px",
              borderBottom:"1px solid var(--color-border)",
              background: span.isSlow||span.durationMs>100 ? "var(--color-warning-bg)" : "transparent",
              cursor:span.plan?"pointer":"default" }}
            onMouseEnter={e=>(e.currentTarget as HTMLDivElement).style.background=span.isSlow||span.durationMs>100?"var(--color-warning-bg)":"var(--color-surface-sunken)"}
            onMouseLeave={e=>(e.currentTarget as HTMLDivElement).style.background=span.isSlow||span.durationMs>100?"var(--color-warning-bg)":"transparent"}>
            {/* Bar */}
            <div style={{ width:80, flexShrink:0 }}>
              <div style={{ height:5, background:"var(--color-border)", borderRadius:99, overflow:"hidden" }}>
                <div style={{ height:"100%", width:`${(span.durationMs/maxDur)*100}%`,
                  background: span.durationMs>100?"var(--color-warning)":"var(--color-accent)",
                  borderRadius:99 }}/>
              </div>
            </div>
            <code style={{ fontSize:"var(--text-xs)", color:"var(--color-accent)",
              minWidth:50, flexShrink:0 }}>{span.durationMs}ms</code>
            <code style={{ fontSize:"var(--text-xs)", color:"var(--color-text-primary)",
              flex:1, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
              {span.operation}{span.table?` → ${span.table}`:""}
            </code>
            {span.engine && <code style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)",
              flexShrink:0 }}>{span.engine}</code>}
            {span.rows!=null && <code style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)",
              flexShrink:0 }}>{span.rows} rows</code>}
            {span.index && <code style={{ fontSize:"var(--text-xs)", color:"var(--color-success-text)",
              flexShrink:0 }}>idx:{span.index}</code>}
            {(span.isSlow||span.durationMs>100) && <span style={{ fontSize:"var(--text-xs)",
              color:"var(--color-warning-text)", flexShrink:0 }}>⚠ SLOW</span>}
            {span.plan && <span style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)", flexShrink:0 }}>
              {expanded===span.id?"▲":"▼"}
            </span>}
          </div>
          {expanded===span.id && span.plan && (
            <pre style={{ margin:0, padding:"10px 16px",
              background:"var(--color-surface-sunken)",
              borderBottom:"1px solid var(--color-border)",
              fontSize:"var(--text-xs)", color:"var(--color-text-secondary)",
              overflow:"auto", maxHeight:200, fontFamily:"var(--font-mono)" }}>
              {span.plan}
            </pre>
          )}
        </div>
      ))}
      {requestId && (
        <div style={{ padding:"8px 16px", background:"var(--color-surface-sunken)",
          borderTop:"1px solid var(--color-border)" }}>
          <span style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)" }}>
            request_id: {requestId}
          </span>
        </div>
      )}
    </div>
  );
}
