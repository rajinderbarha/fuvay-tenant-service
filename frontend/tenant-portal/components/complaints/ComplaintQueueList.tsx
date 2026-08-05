"use client";
import React from "react";
import { Card, Badge } from "../shared/ui";
import type { ComplaintQueueItem } from "../../lib/api";

export function severityVariant(s: string | null): "muted" | "info" | "warning" | "danger" {
  if (s === "critical") return "danger";
  if (s === "high") return "danger";
  if (s === "medium") return "warning";
  return "muted";
}
export function slaVariant(s: string | null): "success" | "warning" | "danger" | "muted" {
  if (s === "breached" || s === "escalated") return "danger";
  if (s === "at_risk") return "warning";
  if (s === "on_time") return "success";
  return "muted";
}
export function statusLabel(s: string | null): string {
  if (!s) return "Not set";
  return s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const mins = Math.floor((Date.now() - d.getTime()) / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function ComplaintQueueList({ items, selectedId, onSelect }: {
  items: ComplaintQueueItem[]; selectedId: string | null; onSelect: (id: string) => void;
}) {
  return (
    <Card padding={0} style={{ width: 480, flexShrink: 0 }}>
      <div style={{ maxHeight: 700, overflowY: "auto" }}>
        {items.length === 0 && (
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", padding: 16 }}>No complaints match this view.</p>
        )}
        {items.map(c => (
          <button key={c.id} onClick={() => onSelect(c.id)} style={{
            display: "block", width: "100%", textAlign: "left", padding: "14px 16px",
            background: selectedId === c.id ? "var(--accent-muted)" : "transparent",
            border: "none", borderLeft: selectedId === c.id ? "3px solid var(--brand)" : "3px solid transparent",
            borderBottom: "1px solid var(--border)", cursor: "pointer",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10 }}>
              <div style={{ minWidth: 0 }}>
                <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 2px" }}>
                  {c.complaint_number} — {c.title ?? c.complaint_type.replace(/_/g, " ")}
                </p>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
                  {c.customer_alias} {c.job_number ? `· ${c.job_number}` : ""} {c.master_service_name ? `· ${c.master_service_name}` : ""}
                </p>
              </div>
              <Badge variant={severityVariant(c.severity)} size="sm">{c.severity}</Badge>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
              <Badge variant={slaVariant(c.sla_status)} size="sm">{statusLabel(c.sla_status)}</Badge>
              <Badge variant="info" size="sm">{statusLabel(c.status)}</Badge>
              <span style={{ fontSize: 11, color: "var(--text-tertiary)", marginLeft: "auto" }}>{timeAgo(c.updated_at)}</span>
            </div>
          </button>
        ))}
      </div>
    </Card>
  );
}
