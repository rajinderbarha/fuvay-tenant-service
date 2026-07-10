"use client";
import React from "react";
export interface DispatchSignal { key:string; label:string; score:number; weight:number; }
export interface DispatchScoreBreakdownProps { staffName:string; totalScore:number; signals:DispatchSignal[]; recommended?:boolean; }
export function DispatchScoreBreakdown({ staffName, totalScore, signals, recommended }: DispatchScoreBreakdownProps) {
  return (
    <div style={{ background:"var(--color-surface-base)", border:`1px solid ${recommended?"var(--color-success-border)":"var(--color-border)"}`,
      borderRadius:"var(--radius-lg)", padding:"16px 18px",
      boxShadow: recommended?"var(--shadow-md)":"var(--shadow-sm)" }}>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:14 }}>
        <div>
          <p style={{ fontSize:"var(--text-base)", fontWeight:"var(--font-semibold)",
            color:"var(--color-text-primary)", margin:"0 0 2px" }}>{staffName}</p>
          {recommended && <span style={{ fontSize:"var(--text-xs)", padding:"2px 7px",
            borderRadius:"var(--radius-full)", background:"var(--color-success-bg)",
            color:"var(--color-success-text)", fontWeight:"var(--font-bold)",
            border:"1px solid var(--color-success-border)" }}>Top Pick</span>}
        </div>
        <div style={{ textAlign:"right" }}>
          <p style={{ fontSize:"var(--text-3xl)", fontWeight:"var(--font-extrabold)",
            color: totalScore>=80?"var(--color-success-text)":totalScore>=60?"var(--color-warning-text)":"var(--color-danger-text)",
            margin:0, lineHeight:1 }}>{totalScore.toFixed(0)}</p>
          <p style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)", margin:0 }}>/ 100</p>
        </div>
      </div>
      <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
        {signals.map(s => (
          <div key={s.key}>
            <div style={{ display:"flex", justifyContent:"space-between", marginBottom:3 }}>
              <span style={{ fontSize:"var(--text-xs)", color:"var(--color-text-secondary)" }}>
                {s.label} <span style={{ opacity:0.5 }}>×{s.weight.toFixed(1)}</span>
              </span>
              <span style={{ fontSize:"var(--text-xs)", fontWeight:"var(--font-bold)",
                color:"var(--color-text-primary)" }}>{s.score.toFixed(0)}</span>
            </div>
            <div style={{ height:5, background:"var(--color-border)", borderRadius:"var(--radius-full)", overflow:"hidden" }}>
              <div style={{ height:"100%", width:`${s.score}%`,
                background: s.score>=80?"var(--color-success)":s.score>=60?"var(--color-warning)":"var(--color-danger)",
                borderRadius:"var(--radius-full)" }}/>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
