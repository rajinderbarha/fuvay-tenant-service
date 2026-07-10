"use client";
import React from "react";
import { KpiCard, type KpiCardProps } from "./KpiCard";
export interface MetricGridProps { metrics: KpiCardProps[]; columns?: 2|3|4|5|6; gap?: number; }
export function MetricGrid({ metrics, columns = 4, gap = 14 }: MetricGridProps) {
  return (
    <div style={{ display:"grid", fontFamily:"var(--font-sans)",
      gridTemplateColumns:`repeat(auto-fill, minmax(${Math.floor(1200/columns)-gap}px, 1fr))`,
      gap }}>
      {metrics.map((m, i) => <KpiCard key={i} {...m}/>)}
    </div>
  );
}
