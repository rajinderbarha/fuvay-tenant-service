"use client";
/**
 * DESIGN PHASE UX-04 — role-sensitive action queue for the Operations
 * Command Center. Renders the SAME list component for tenant_owner /
 * staff-with-permission / staff-limited / read-only — composition differs
 * only by which `actions` entries are `available`, never by a separate
 * per-role implementation.
 */
import React from "react";
import type { OperationalActionItemView } from "../../lib/ux04/types";
import { SLAIndicator } from "./SLAIndicator";

export function OperationalActionQueue({ items }: { items: OperationalActionItemView[] }) {
  if (items.length === 0) {
    return <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>No items need action right now.</p>;
  }
  return (
    <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
      {items.map((item) => {
        const grantedActions = item.actions.filter((a) => a.available);
        return (
          <li
            key={item.id}
            style={{
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-md)",
              padding: "0.75rem 1rem",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: "1rem",
            }}
          >
            <div>
              <a href={item.entity.href} style={{ fontWeight: 600, fontSize: "0.875rem" }}>
                {item.entity.label}
              </a>
              <p style={{ margin: "0.25rem 0", fontSize: "0.8125rem", color: "var(--text-secondary)" }}>{item.summary}</p>
              <SLAIndicator sla={item.sla} />
            </div>
            <div style={{ textAlign: "right" }}>
              <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", margin: 0 }}>{item.requiredAction}</p>
              {grantedActions.length === 0 && (
                <p style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", fontStyle: "italic" }}>
                  No action available with your current permissions.
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
