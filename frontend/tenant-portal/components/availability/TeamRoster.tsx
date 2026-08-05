"use client";
/** Left-hand team list -- one row per technician with today's real job count,
 * status, and a "Manage team" action. Distinct card from the weekly grid,
 * matching the reference layout (two separate panels, not one merged table). */
import React from "react";
import { Users } from "lucide-react";
import { Card, Badge } from "../shared/ui";

export interface RosterRow {
  id: string;
  name: string;
  designation: string | null;
  jobsToday: number;
  maxConcurrent: number | null;
  statusLabel: "Available" | "Conflict" | "Setup incomplete" | "Unavailable" | "Dispatcher";
}

const STATUS_VARIANT: Record<RosterRow["statusLabel"], "success" | "danger" | "warning" | "muted" | "info"> = {
  Available: "success", Conflict: "danger", "Setup incomplete": "warning", Unavailable: "muted", Dispatcher: "info",
};

export function TeamRoster({ rows, selectedId, onSelect, onManageTeam }: {
  rows: RosterRow[]; selectedId: string | null; onSelect: (id: string) => void; onManageTeam?: () => void;
}) {
  return (
    <Card padding={0} style={{ width: 260, flexShrink: 0 }}>
      <div style={{ padding: "16px 16px 10px" }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>Team</h3>
      </div>
      <div style={{ maxHeight: 620, overflowY: "auto" }}>
        {rows.length === 0 && (
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", padding: 16 }}>No technicians configured for this tenant.</p>
        )}
        {rows.map(r => (
          <button key={r.id} onClick={() => onSelect(r.id)} style={{
            display: "block", width: "100%", textAlign: "left", padding: "12px 16px",
            background: selectedId === r.id ? "var(--accent-muted)" : "transparent",
            border: "none", borderLeft: selectedId === r.id ? "3px solid var(--brand)" : "3px solid transparent",
            borderBottom: "1px solid var(--border)", cursor: "pointer",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
              <div style={{ minWidth: 0 }}>
                <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 2px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{r.name}</p>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 6px" }}>{r.designation ?? "—"}</p>
              </div>
              <span style={{ fontSize: 11.5, fontWeight: 700, color: "var(--text-secondary)", flexShrink: 0 }}>
                {r.jobsToday}/{r.maxConcurrent ?? "—"} jobs
              </span>
            </div>
            <Badge variant={STATUS_VARIANT[r.statusLabel]} size="sm">{r.statusLabel}</Badge>
          </button>
        ))}
      </div>
      <div style={{ padding: 12, borderTop: "1px solid var(--border)" }}>
        <button onClick={onManageTeam} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
          width: "100%", padding: "8px 0", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)",
          color: "var(--text-secondary)", fontSize: 12.5, fontWeight: 600, cursor: "pointer" }}>
          <Users size={13}/> Manage team
        </button>
      </div>
    </Card>
  );
}
