"use client";
/**
 * DESIGN PHASE UX-04 — shared status timeline used inside Job Detail and
 * Booking Detail. Model-aware: pass the literal status strings for whichever
 * pipeline the entity belongs to (field_ops.Job vs ServiceJob) — this
 * component never assumes a merged status vocabulary.
 */
import React from "react";

export function JobStatusTimeline({ statuses, current }: { statuses: string[]; current: string }) {
  const currentIdx = statuses.indexOf(current);
  return (
    <ol style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", listStyle: "none", padding: 0, margin: 0 }}>
      {statuses.map((s, i) => {
        const done = currentIdx >= 0 && i < currentIdx;
        const active = i === currentIdx;
        return (
          <li
            key={s}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.375rem",
              fontSize: "0.75rem",
              fontWeight: active ? 700 : 500,
              color: active ? "var(--brand)" : done ? "var(--success-text)" : "var(--text-secondary)",
              border: `1px solid ${active ? "var(--brand)" : "var(--border)"}`,
              borderRadius: "var(--radius-full)",
              padding: "0.125rem 0.625rem",
            }}
            aria-current={active ? "step" : undefined}
          >
            {s.replace(/_/g, " ")}
          </li>
        );
      })}
    </ol>
  );
}
