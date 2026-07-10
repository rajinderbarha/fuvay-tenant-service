"use client";
import React from "react";
import { CITY_TIER_MAP, type CityTier } from "../../tokens/tokens";
export interface CityTierBadgeProps { tier: CityTier | number; city?: string; size?: "sm"|"md"; }
export function CityTierBadge({ tier, city, size="md" }: CityTierBadgeProps) {
  const map = CITY_TIER_MAP[tier as CityTier];
  if (!map) return null;
  return (
    <span className={map.cssClass} title={map.desc}
      style={{ display:"inline-flex", alignItems:"center", gap:5,
        borderRadius:"var(--radius-full)", fontWeight:700,
        fontSize: size==="sm" ? "var(--text-xs)" : "var(--text-xs)",
        padding: size==="sm" ? "2px 7px" : "3px 9px",
        background:"var(--ct-bg)", color:"var(--ct-text)",
        border:"1px solid var(--ct-border)", whiteSpace:"nowrap" }}>
      {map.label}{city && ` · ${city}`}
    </span>
  );
}
