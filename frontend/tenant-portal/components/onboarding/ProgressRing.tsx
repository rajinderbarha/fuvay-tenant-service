"use client";
import React from "react";

/**
 * Circular progress indicator used in every onboarding step's right rail
 * (readiness/completion percentage). Previously each page rendered its
 * percentage as plain text -- the reference design uses a ring everywhere,
 * so this is the one shared implementation rather than a per-page redraw.
 */
export function ProgressRing({
  pct, size = 96, stroke = 9, label, sublabel, tone = "brand",
}: {
  pct: number; size?: number; stroke?: number;
  label?: string; sublabel?: string;
  tone?: "brand" | "success" | "warning";
}) {
  const clamped = Math.max(0, Math.min(100, pct));
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (clamped / 100) * c;
  const color = tone === "success" ? "var(--success)" : tone === "warning" ? "var(--warning)" : "var(--brand)";

  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 16 }}>
      <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
        <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth={stroke} />
          <circle
            cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
            strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.4s ease" }}
          />
        </svg>
        <div style={{
          position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: size >= 90 ? 24 : 18, fontWeight: 800, color: "var(--text-primary)",
        }}>
          {Math.round(clamped)}%
        </div>
      </div>
      {(label || sublabel) && (
        <div>
          {label && <p style={{ margin: 0, fontSize: 15, fontWeight: 800, color: "var(--text-primary)" }}>{label}</p>}
          {sublabel && <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--text-tertiary)" }}>{sublabel}</p>}
        </div>
      )}
    </div>
  );
}
