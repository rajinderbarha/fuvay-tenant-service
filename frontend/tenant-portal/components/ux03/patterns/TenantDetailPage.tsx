"use client";
/**
 * DESIGN PHASE UX-03 — shared detail-page pattern (mirrors UX-02's
 * EnterpriseDetailPage): header, section nav, readiness/permission-aware
 * action area. Reused for Job Detail, Booking Detail, Customer Detail,
 * Compliance item, etc.
 */
import React, { useState } from "react";
import { PageHeader } from "@serviceos/design-system";

export interface DetailSection {
  id: string;
  label: string;
  render: () => React.ReactNode;
}

export function TenantDetailPage({
  title,
  description,
  headerBadges,
  actions,
  sections,
  initialSectionId,
}: {
  title: string;
  description?: string;
  headerBadges?: React.ReactNode;
  actions?: React.ReactNode;
  sections: DetailSection[];
  initialSectionId?: string;
}) {
  const [activeId, setActiveId] = useState(initialSectionId ?? sections[0]?.id);
  const active = sections.find((s) => s.id === activeId) ?? sections[0];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <PageHeader
        title={title}
        description={description}
        actions={actions}
      />
      {headerBadges && <div style={{ display: "flex", gap: "0.5rem" }}>{headerBadges}</div>}
      <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
        <nav aria-label="Detail sections" style={{ display: "flex", flexDirection: "column", gap: "0.25rem", minWidth: "12rem" }}>
          {sections.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setActiveId(s.id)}
              aria-current={s.id === active?.id ? "page" : undefined}
              style={{
                textAlign: "left",
                padding: "0.5rem 0.75rem",
                borderRadius: "var(--radius-md)",
                border: "none",
                cursor: "pointer",
                background: s.id === active?.id ? "var(--accent-muted)" : "transparent",
                color: s.id === active?.id ? "var(--brand)" : "var(--text-primary)",
                fontWeight: s.id === active?.id ? 600 : 400,
              }}
            >
              {s.label}
            </button>
          ))}
        </nav>
        <div style={{ flex: 1, minWidth: "16rem" }}>{active?.render()}</div>
      </div>
    </div>
  );
}
