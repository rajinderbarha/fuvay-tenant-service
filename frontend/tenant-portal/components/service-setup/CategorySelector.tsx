"use client";
import React from "react";
import { Badge } from "../shared/ui";
import type { MyVerticalEnrollment } from "../../lib/api";
import * as Icons from "lucide-react";
import { Boxes } from "lucide-react";

function VerticalIcon({ name }: { name: string | null }) {
  const Icon = (name && (Icons as unknown as Record<string, React.ComponentType<{ size?: number }>>)[name]) || Boxes;
  return <Icon size={22} />;
}

/** Step 1: Category (business vertical). Schema-driven -- renders only the
 * verticals returned by GET /v1/tenant/vertical-enrollments (platform-
 * enabled AND approved AND active for this tenant). Never hardcodes a
 * vertical name; a suspended/under-review vertical shows its status but
 * is not selectable. */
export function CategorySelector({ verticals, selectedVerticalId, onSelect }: {
  verticals: MyVerticalEnrollment[];
  selectedVerticalId: string | null;
  onSelect: (v: MyVerticalEnrollment) => void;
}) {
  return (
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 800, margin: "0 0 4px" }}>Which business does this belong to?</h1>
      <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 20px" }}>
        Choose the category you want to set up a service for.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px,1fr))", gap: 14 }}>
        {verticals.map(v => {
          const selectable = v.platform_enabled && v.enrollment_status === "active";
          const selected = v.vertical_id === selectedVerticalId;
          return (
            <button key={v.vertical_id} type="button" disabled={!selectable}
              onClick={() => selectable && onSelect(v)}
              aria-pressed={selected}
              style={{
                textAlign: "left", display: "flex", flexDirection: "column", gap: 10,
                padding: "18px 16px", borderRadius: "var(--radius-lg)",
                border: `2px solid ${selected ? "var(--accent)" : "var(--border)"}`,
                background: selected ? "var(--accent-muted)" : "var(--surface)",
                cursor: selectable ? "pointer" : "not-allowed",
                opacity: selectable ? 1 : 0.55,
                fontFamily: "inherit",
              }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: "var(--accent-muted)",
                display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent)" }}>
                <VerticalIcon name={v.icon} />
              </div>
              <div>
                <p style={{ margin: 0, fontWeight: 700, fontSize: 14 }}>{v.vertical_label}</p>
                {!selectable && (
                  <Badge variant="warning" size="sm">
                    {!v.platform_enabled ? "Unavailable" :
                      v.enrollment_status === "suspended" ? "Suspended" :
                      v.enrollment_status === "under_review" || v.enrollment_status === "submitted" ? "Under review" :
                      "Not active"}
                  </Badge>
                )}
              </div>
            </button>
          );
        })}
      </div>
      {verticals.length === 0 && (
        <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
          You don't have any approved business categories yet. Contact your platform admin.
        </p>
      )}
    </div>
  );
}
