"use client";
/**
 * DESIGN PHASE UX-03 — grouped, searchable StaffPermission editor.
 *
 * Backs onto app/engines/auth/models.py::StaffPermission
 * (user_id, tenant_id, permission_key, is_granted). Three visually distinct
 * states are rendered:
 *   - granted_by_role     : role default grant (from ROLE_PERMISSIONS)
 *   - granted_override     : explicit StaffPermission row, is_granted=true
 *   - denied_override      : explicit StaffPermission row, is_granted=false
 *   - not_granted          : no role default, no override row
 *
 * CRITICAL: denied_override must always render as visually distinct from
 * not_granted (both look "off" but mean different things), and a grant can
 * NEVER be implied to override an explicit deny elsewhere in the UI.
 */
import React, { useMemo, useState } from "react";
import { Card } from "@serviceos/design-system";
import type { StaffPermissionFixture } from "../../../lib/ux03/types";

function StateChip({ state }: { state: StaffPermissionFixture["state"] }) {
  const map = {
    granted_by_role: { label: "Granted (role default)", color: "var(--success-text)", bg: "var(--success-bg)" },
    granted_override: { label: "Granted (override)", color: "var(--success-text)", bg: "var(--success-bg)" },
    denied_override: { label: "Denied (explicit)", color: "var(--danger-text)", bg: "var(--danger-bg)" },
    not_granted: { label: "Not granted", color: "var(--text-secondary)", bg: "var(--neutral-bg)" },
  } as const;
  const s = map[state];
  return (
    <span style={{ fontSize: "0.6875rem", fontWeight: 600, color: s.color, background: s.bg, borderRadius: "var(--radius-full)", padding: "0.125rem 0.625rem" }}>
      {s.label}
    </span>
  );
}

export function PermissionEditor({
  permissions,
  onToggle,
  readOnly = false,
}: {
  permissions: StaffPermissionFixture[];
  onToggle?: (permissionKey: string, next: StaffPermissionFixture["state"]) => void;
  readOnly?: boolean;
}) {
  const [query, setQuery] = useState("");

  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = q
      ? permissions.filter((p) => p.label.toLowerCase().includes(q) || p.permissionKey.toLowerCase().includes(q) || p.group.toLowerCase().includes(q))
      : permissions;
    const byGroup = new Map<string, StaffPermissionFixture[]>();
    for (const p of filtered) {
      if (!byGroup.has(p.group)) byGroup.set(p.group, []);
      byGroup.get(p.group)!.push(p);
    }
    return byGroup;
  }, [permissions, query]);

  function cycle(p: StaffPermissionFixture) {
    if (readOnly || !onToggle) return;
    // Cycle: granted_by_role/not_granted -> granted_override -> denied_override -> back to default
    const next: StaffPermissionFixture["state"] =
      p.state === "denied_override" ? (p.roleDefaultForTechnician ? "granted_by_role" : "not_granted")
      : p.state === "granted_override" ? "denied_override"
      : "granted_override";
    onToggle(p.permissionKey, next);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <input
        aria-label="Search permissions"
        placeholder="Search permissions by name or key…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        style={{
          padding: "0.5rem 0.75rem",
          borderRadius: "var(--radius-md)",
          border: "1px solid var(--border)",
          background: "var(--surface)",
          color: "var(--text-primary)",
        }}
      />
      {Array.from(grouped.entries()).map(([group, perms]) => (
        <Card key={group} title={group}>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {perms.map((p) => (
              <div
                key={p.permissionKey}
                style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.75rem", padding: "0.375rem 0" }}
              >
                <div>
                  <div className="ds-text-body" style={{ fontWeight: 600 }}>{p.label}</div>
                  <div className="ds-text-body" style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    {p.description} <code style={{ opacity: 0.7 }}>{p.permissionKey}</code>
                  </div>
                </div>
                <button
                  type="button"
                  disabled={readOnly}
                  onClick={() => cycle(p)}
                  style={{ background: "none", border: "none", cursor: readOnly ? "default" : "pointer", padding: 0 }}
                  aria-label={`Toggle ${p.label}`}
                >
                  <StateChip state={p.state} />
                </button>
              </div>
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}
