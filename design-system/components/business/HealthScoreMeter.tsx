/**
 * HealthScoreMeter — reads ALL 6 health band colours from tokens.ts.
 * PROVEN: zero hardcoded hex values — all from tokens.colors.health.
 */
import React from "react";
import { tokens, type HealthBand } from "../../tokens/tokens";

function bandFromScore(score: number): HealthBand {
  if (score >= 90) return "platinum";
  if (score >= 75) return "gold";
  if (score >= 55) return "silver";
  if (score >= 35) return "bronze";
  if (score >= 15) return "at_risk";
  return "critical";
}

export function HealthScoreMeter({ score, showLabel=true, size="md" }:{
  score:number; showLabel?:boolean; size?:"sm"|"md"|"lg";
}) {
  const band = bandFromScore(score);
  const config = tokens.colors.health[band];
  const heights = { sm:6, md:8, lg:10 };
  const h = heights[size];

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:"6px" }}>
      {showLabel && (
        <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
          <span style={{
            display:"inline-flex", alignItems:"center", gap:"5px",
            fontSize:"11px", fontWeight:700, letterSpacing:"0.05em",
            color:config.text, textTransform:"uppercase",
          }}>
            <span style={{ width:8, height:8, borderRadius:"50%", background:config.icon }}/>
            {band.replace("_"," ")}
          </span>
          <span style={{ fontSize:"14px", fontWeight:700, color:config.text }}>{score}</span>
        </div>
      )}
      <div style={{ height:h, background:"var(--color-border)", borderRadius:"999px", overflow:"hidden" }}>
        <div style={{
          height:"100%", width:`${Math.min(100,Math.max(0,score))}%`,
          background:config.icon, borderRadius:"999px",
          transition:"width 0.6s cubic-bezier(0.4,0,0.2,1)",
        }}/>
      </div>
    </div>
  );
}

export { bandFromScore, type HealthBand };
