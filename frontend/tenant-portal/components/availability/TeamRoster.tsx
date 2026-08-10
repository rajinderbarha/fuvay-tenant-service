"use client";
/** Left-hand team list -- one card per technician with their photo, today's real
 * job count against their capacity, and a status dot. Distinct card from the
 * weekly grid, matching the reference layout (two separate panels, not one
 * merged table).
 *
 * Each row is its own bordered card rather than a divided list row: the
 * selected technician is marked by a brand outline around the whole card,
 * which needs a card to outline. A left-border stripe on a flat list read as
 * a divider at a glance and the selection kept getting lost. */
import React from "react";
import { Users } from "lucide-react";
import { Card } from "../shared/ui";

export interface RosterRow {
  id: string;
  name: string;
  designation: string | null;
  jobsToday: number;
  /** Jobs allowed on this DAY, not concurrently -- the two are different limits and the
   *  roster is answering "how full is their day". */
  dailyLimit: number | null;
  photoUrl: string | null;
  statusLabel: "Available" | "Conflict" | "Setup incomplete" | "On leave" | "Fully booked" | "Unavailable" | "Dispatcher";
}

/** A dot plus a word, not a filled pill. Five pills stacked down a narrow column
 *  compete with the names for attention; the dot carries the colour and the name
 *  stays the thing you read first. */
const STATUS_DOT: Record<RosterRow["statusLabel"], string> = {
  Available: "#22C55E",
  Conflict: "#EF4444",
  "Setup incomplete": "#F59E0B",
  "On leave": "#94A3B8",
  // Amber, not red: a full day is the system working, not a problem to fix.
  "Fully booked": "#F59E0B",
  Unavailable: "#94A3B8",
  Dispatcher: "#3B82F6",
};

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

function Avatar({ name, url }: { name: string; url: string | null }) {
  const [failed, setFailed] = React.useState(false);
  const box: React.CSSProperties = {
    width: 38, height: 38, borderRadius: "50%", flexShrink: 0,
    objectFit: "cover", border: "1px solid var(--border)",
  };
  // Initials rather than a generic silhouette when there is no photo, and also when
  // the photo 404s -- a broken-image icon in a roster looks like the row is broken.
  if (!url || failed) {
    return (
      <span style={{ ...box, background: "var(--surface-sunken)", color: "var(--text-secondary)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 13, fontWeight: 700 }}>
        {initials(name)}
      </span>
    );
  }
  return <img src={url} alt="" style={box} onError={() => setFailed(true)}/>;
}

export function TeamRoster({ rows, selectedId, onSelect, onManageTeam }: {
  rows: RosterRow[]; selectedId: string | null; onSelect: (id: string) => void; onManageTeam?: () => void;
}) {
  return (
    <Card padding={0} style={{ width: 260, flexShrink: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "16px 16px 12px" }}>
        <Users size={15} style={{ color: "var(--text-secondary)" }}/>
        <h3 style={{ fontSize: 14, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>Team</h3>
      </div>

      <div style={{ maxHeight: 620, overflowY: "auto", padding: "0 10px", display: "flex",
        flexDirection: "column", gap: 8 }}>
        {rows.length === 0 && (
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", padding: "0 6px 16px" }}>
            No technicians configured for this tenant.
          </p>
        )}
        {rows.map(r => {
          const selected = selectedId === r.id;
          return (
            <button key={r.id} onClick={() => onSelect(r.id)} aria-pressed={selected} style={{
              display: "block", width: "100%", textAlign: "left", padding: "10px 11px",
              borderRadius: 12, cursor: "pointer", font: "inherit",
              background: selected ? "var(--accent-muted)" : "var(--surface-sunken)",
              border: `1px solid ${selected ? "var(--brand)" : "var(--border)"}`,
              boxShadow: selected ? "0 0 0 1px var(--brand)" : "none",
            }}>
              <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                <Avatar name={r.name} url={r.photoUrl}/>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <p style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)",
                    margin: "0 0 1px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {r.name}
                  </p>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 5px",
                    whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {r.designation ?? "—"}
                  </p>
                  <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, fontWeight: 600,
                    color: STATUS_DOT[r.statusLabel] }}>
                    <span style={{ width: 6, height: 6, borderRadius: "50%",
                      background: STATUS_DOT[r.statusLabel], flexShrink: 0 }}/>
                    {r.statusLabel}
                  </span>
                </div>
                {/* Count over the word, so the number is what scans down the column.
                    An em dash when the technician has no configured capacity -- 0/0
                    would read as "full" rather than "not set up". */}
                <div style={{ flexShrink: 0, textAlign: "right", lineHeight: 1.15 }}>
                  <div style={{ fontSize: 12.5, fontWeight: 700, color: "var(--text-primary)" }}>
                    {r.dailyLimit != null ? `${r.jobsToday}/${r.dailyLimit}` : "—"}
                  </div>
                  <div style={{ fontSize: 10.5, color: "var(--text-tertiary)" }}>jobs</div>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <div style={{ padding: 12, marginTop: 4 }}>
        <button onClick={onManageTeam} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
          width: "100%", padding: "9px 0", borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface)",
          color: "var(--text-secondary)", fontSize: 12.5, fontWeight: 600, cursor: "pointer" }}>
          <Users size={13}/> Manage team
        </button>
      </div>
    </Card>
  );
}
