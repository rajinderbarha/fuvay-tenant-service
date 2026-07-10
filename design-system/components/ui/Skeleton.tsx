/**
 * Skeleton — loading placeholder with shimmer animation.
 * Supports circle (avatar), text lines, and block variants.
 */
"use client";
import React from "react";

export interface SkeletonProps {
  width?:    number | string;
  height?:   number | string;
  circle?:   boolean;
  rounded?:  boolean;
  lines?:    number;   // render N stacked text lines
  className?: string;
}

const SHIMMER: React.CSSProperties = {
  background: "linear-gradient(90deg, var(--color-border) 25%, var(--color-surface-sunken) 50%, var(--color-border) 75%)",
  backgroundSize: "200% 100%",
  animation: "shimmer 1.5s infinite",
};

export function Skeleton({ width, height, circle, rounded, lines, className }: SkeletonProps) {
  if (lines && lines > 1) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {Array.from({ length: lines }).map((_, i) => (
          <div key={i} style={{
            ...SHIMMER,
            height: height ?? 14,
            width: i === lines - 1 ? "65%" : width ?? "100%",
            borderRadius: "var(--radius-sm)",
          }} className={className} />
        ))}
      </div>
    );
  }

  return (
    <div
      style={{
        ...SHIMMER,
        width:        width  ?? (circle ? 40 : "100%"),
        height:       height ?? (circle ? 40 : 14),
        borderRadius: circle ? "var(--radius-full)"
                    : rounded ? "var(--radius-full)"
                    : "var(--radius-sm)",
        flexShrink: 0,
      }}
      aria-hidden="true"
      className={className}
    />
  );
}

/** Pre-composed card skeleton — matches KpiCard/StatCard shape */
export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div style={{
      background: "var(--color-surface-base)", border: "1px solid var(--color-border)",
      borderRadius: "var(--radius-lg)", padding: "20px", display: "flex",
      flexDirection: "column", gap: 12, boxShadow: "var(--shadow-sm)",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <Skeleton width={80} height={12} />
        <Skeleton circle width={32} height={32} />
      </div>
      <Skeleton width={120} height={32} />
      <Skeleton lines={lines} height={12} />
    </div>
  );
}

/** Pre-composed table row skeleton */
export function SkeletonRow({ columns = 5 }: { columns?: number }) {
  return (
    <div style={{ display: "flex", gap: 16, alignItems: "center", padding: "12px 0", borderBottom: "1px solid var(--color-border)" }}>
      {Array.from({ length: columns }).map((_, i) => (
        <Skeleton key={i} width={i === 0 ? 120 : i === columns - 1 ? 60 : "100%"} height={14} />
      ))}
    </div>
  );
}
