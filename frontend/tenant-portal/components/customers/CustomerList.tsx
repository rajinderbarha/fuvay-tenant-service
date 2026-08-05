"use client";
import React from "react";
import { Card, Badge } from "../shared/ui";
import type { HsCustomerListItem } from "../../lib/api";

function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const days = Math.floor((Date.now() - d.getTime()) / 86400000);
  if (days <= 0) return "Today";
  if (days === 1) return "1 day ago";
  if (days < 7) return `${days} days ago`;
  if (days < 30) return `${Math.floor(days / 7)} week${Math.floor(days / 7) > 1 ? "s" : ""} ago`;
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export function CustomerList({ items, selectedId, onSelect }: {
  items: HsCustomerListItem[]; selectedId: string | null; onSelect: (id: string) => void;
}) {
  return (
    <Card padding={0} style={{ width: 460, flexShrink: 0 }}>
      <div style={{ maxHeight: 640, overflowY: "auto" }}>
        {items.length === 0 && (
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", padding: 16 }}>No customers match this view.</p>
        )}
        {items.map(c => (
          <button key={c.customer_id} onClick={() => onSelect(c.customer_id)} style={{
            display: "block", width: "100%", textAlign: "left", padding: "14px 16px",
            background: selectedId === c.customer_id ? "var(--accent-muted)" : "transparent",
            border: "none", borderLeft: selectedId === c.customer_id ? "3px solid var(--brand)" : "3px solid transparent",
            borderBottom: "1px solid var(--border)", cursor: "pointer",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
                <div style={{ width: 34, height: 34, borderRadius: "50%", background: "var(--accent-muted)",
                  display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                  fontSize: 13, fontWeight: 700, color: "var(--accent)" }}>
                  {c.alias.replace("Customer ", "").slice(0, 2)}
                </div>
                <div style={{ minWidth: 0 }}>
                  <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 2px" }}>{c.alias}</p>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
                    Last activity {timeAgo(c.last_activity_at)}
                  </p>
                </div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, flexShrink: 0 }}>
                <Badge variant={c.repeat_status === "repeat" ? "success" : c.is_active ? "info" : "muted"} size="sm">
                  {c.repeat_status === "repeat" ? "Repeat" : c.repeat_status === "one_time" ? "One-time" : "New"}
                </Badge>
                {c.open_complaints > 0 && <Badge variant="danger" size="sm">{c.open_complaints} complaint{c.open_complaints > 1 ? "s" : ""}</Badge>}
              </div>
            </div>
            <div style={{ display: "flex", gap: 16, marginTop: 8, fontSize: 11.5, color: "var(--text-secondary)" }}>
              <span>{c.completed_jobs} completed job{c.completed_jobs === 1 ? "" : "s"}</span>
              <span>{c.services_used_count} service{c.services_used_count === 1 ? "" : "s"} used</span>
            </div>
          </button>
        ))}
      </div>
    </Card>
  );
}
