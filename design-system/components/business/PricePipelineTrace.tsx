"use client";
import React from "react";
export interface PriceStage { id:string; label:string; input:number; output:number; delta:number; ruleApplied?:string; ruleType?:"base"|"surcharge"|"discount"|"tax"; }
export interface PricePipelineTraceProps { stages:PriceStage[]; finalPrice:number; currency?:string; }
export function PricePipelineTrace({ stages, finalPrice, currency="₹" }: PricePipelineTraceProps) {
  const fmt = (n:number) => `${currency}${Math.abs(n).toLocaleString("en-IN")}`;
  const TypeColor:Record<string,string> = {
    base:"var(--color-info-text)", surcharge:"var(--color-danger-text)",
    discount:"var(--color-success-text)", tax:"var(--color-warning-text)"
  };
  return (
    <div style={{ background:"var(--color-surface-base)", border:"1px solid var(--color-border)",
      borderRadius:"var(--radius-lg)", overflow:"hidden", boxShadow:"var(--shadow-sm)" }}>
      <div style={{ padding:"12px 16px", borderBottom:"1px solid var(--color-border)",
        background:"var(--color-surface-sunken)" }}>
        <p style={{ fontSize:"var(--text-xs)", fontWeight:"var(--font-bold)", textTransform:"uppercase",
          letterSpacing:"0.06em", color:"var(--color-text-tertiary)", margin:0 }}>Price Pipeline Trace</p>
      </div>
      {stages.map((s,i)=>(
        <div key={s.id} style={{ display:"flex", alignItems:"center", gap:12, padding:"10px 16px",
          borderBottom:i<stages.length-1?"1px solid var(--color-border)":"none" }}>
          <div style={{ width:24, height:24, borderRadius:"var(--radius-sm)",
            background: s.ruleType==="discount"?"var(--color-success-bg)":s.ruleType==="surcharge"||s.ruleType==="tax"?"var(--color-warning-bg)":"var(--color-info-bg)",
            display:"flex", alignItems:"center", justifyContent:"center",
            fontSize:12, flexShrink:0, fontWeight:"var(--font-bold)",
            color: TypeColor[s.ruleType??"base"] }}>
            {s.delta>0?"+":s.delta<0?"-":"="}
          </div>
          <div style={{ flex:1, minWidth:0 }}>
            <p style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-medium)",
              color:"var(--color-text-primary)", margin:0 }}>{s.label}</p>
            {s.ruleApplied && <p style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)",
              margin:0, fontFamily:"var(--font-mono)" }}>{s.ruleApplied}</p>}
          </div>
          <div style={{ textAlign:"right", flexShrink:0 }}>
            <p style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-semibold)",
              color: s.delta>0?"var(--color-danger-text)":s.delta<0?"var(--color-success-text)":"var(--color-text-secondary)",
              margin:0 }}>
              {s.delta!==0?(s.delta>0?"+":"-")+fmt(s.delta):"—"}
            </p>
            <p style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)", margin:0 }}>
              → {fmt(s.output)}
            </p>
          </div>
        </div>
      ))}
      <div style={{ padding:"12px 16px", background:"var(--color-brand-500)",
        display:"flex", alignItems:"center", justifyContent:"space-between" }}>
        <span style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-semibold)", color:"white", opacity:0.85 }}>
          Final Price
        </span>
        <span style={{ fontSize:"var(--text-2xl)", fontWeight:"var(--font-extrabold)", color:"white" }}>
          {fmt(finalPrice)}
        </span>
      </div>
    </div>
  );
}
