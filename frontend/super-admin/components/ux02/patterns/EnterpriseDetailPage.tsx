"use client";
import React, { useState } from "react";
import { PageHeader } from "@serviceos/design-system";
import { ReadinessTag } from "../widgets/ReadinessTag";
import type { ReadinessState } from "../../../lib/ux02/types";

/**
 * Reusable enterprise detail-page pattern (UX-02).
 * Used by: Tenant 360, Compliance Case Detail.
 * Sticky section nav on desktop; a <select> section-jump on mobile.
 */
export interface DetailSection { id: string; label: string; content: React.ReactNode; }

export function EnterpriseDetailPage({
  title, subtitle, readiness, sections, headerActions,
}: {
  title: string;
  subtitle?: string;
  readiness: ReadinessState;
  sections: DetailSection[];
  headerActions?: React.ReactNode;
}) {
  const [active, setActive] = useState(sections[0]?.id);
  const current = sections.find((s) => s.id === active) ?? sections[0];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <PageHeader title={title} description={subtitle} actions={<>{headerActions}<ReadinessTag readiness={readiness} /></>} />

      {/* Mobile section selector */}
      <div className="ux02-mobile-only" style={{ display: "none" }}>
        <select aria-label="Jump to section" value={active} onChange={(e) => setActive(e.target.value)} style={{ width: "100%", padding: "0.5rem", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
          {sections.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
      </div>

      <div style={{ display: "flex", gap: "1.5rem", alignItems: "flex-start" }}>
        <nav aria-label="Detail sections" className="ux02-desktop-only" style={{ position: "sticky", top: "1rem", display: "flex", flexDirection: "column", gap: "0.25rem", minWidth: "180px" }}>
          {sections.map((s) => (
            <button
              key={s.id}
              onClick={() => setActive(s.id)}
              aria-current={active === s.id ? "true" : undefined}
              style={{
                textAlign: "left", padding: "0.5rem 0.75rem", borderRadius: "var(--radius-md)", border: "none", cursor: "pointer",
                background: active === s.id ? "var(--accent-muted)" : "transparent",
                color: active === s.id ? "var(--brand)" : "var(--text-secondary)",
                fontWeight: active === s.id ? 600 : 400,
              }}
            >
              {s.label}
            </button>
          ))}
        </nav>
        <div style={{ flex: 1, minWidth: 0 }}>{current?.content}</div>
      </div>
      <style>{`
        @media (max-width: 768px) {
          .ux02-mobile-only { display: block !important; }
          .ux02-desktop-only { display: none !important; }
        }
      `}</style>
    </div>
  );
}
