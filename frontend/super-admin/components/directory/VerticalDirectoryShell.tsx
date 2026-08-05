"use client";
import React, { useState } from "react";
import { AdminLayout } from "../layout/AdminLayout";
import { Card, Badge, Btn } from "../shared/ui";
import { Search } from "lucide-react";

// VERTICAL-DIRECTORY-FRAMEWORK: the one shared shell reused by every
// domain (Providers/Staff/Customers/Complaints) across every Business
// Vertical. Domain-specific data/columns/actions are passed in as props --
// this component owns only layout, never fetches vertical-specific data
// itself.

export interface DirectoryMetric { label: string; value: number | string | undefined }
export interface DirectoryColumn<T> { key: string; label: string; render: (row: T) => React.ReactNode }

export function VerticalDirectoryShell<T extends { [k: string]: unknown }>({
  verticalLabel, domainTitle, description, metrics, search, onSearchChange,
  columns, rows, loading, error, onRetry, onRowClick, rowKey, detail,
}: {
  verticalLabel: string; domainTitle: string; description: string;
  metrics: DirectoryMetric[]; search: string; onSearchChange: (v: string) => void;
  columns: DirectoryColumn<T>[]; rows: T[]; loading: boolean; error: string | null;
  onRetry: () => void; onRowClick?: (row: T) => void; rowKey: (row: T) => string;
  detail?: React.ReactNode;
}) {
  return (
    <AdminLayout>
      <div style={{ padding: "0 4px", display: "flex", gap: 16 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 4px" }}>{verticalLabel}</p>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 4px", color: "var(--text-primary)" }}>{domainTitle}</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 16px" }}>{description}</p>

          <div style={{ display: "grid", gridTemplateColumns: `repeat(${metrics.length}, minmax(110px, 1fr))`, gap: 10, marginBottom: 16 }}>
            {metrics.map(m => (
              <div key={m.label} style={{ padding: "10px 12px", borderRadius: "var(--radius-lg)", border: "1px solid var(--border)", background: "var(--surface)" }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>{m.value ?? "—"}</div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{m.label}</div>
              </div>
            ))}
          </div>

          <div style={{ position: "relative", marginBottom: 12, maxWidth: 320 }}>
            <Search size={13} style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
            <input value={search} onChange={e => onSearchChange(e.target.value)} placeholder="Search…"
              style={{ width: "100%", padding: "7px 10px 7px 28px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
                background: "var(--bg)", color: "var(--text-primary)", fontSize: 13 }}/>
          </div>

          <Card style={{ padding: 0 }}>
            {error ? (
              <div style={{ padding: 24, textAlign: "center" }}>
                <p style={{ color: "var(--danger-text)", fontSize: 13 }}>{error}</p>
                <Btn variant="ghost" size="sm" onClick={onRetry}>Retry</Btn>
              </div>
            ) : loading ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</div>
            ) : rows.length === 0 ? (
              <div style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No records match this view.</div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                      {columns.map(c => (
                        <th key={c.key} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{c.label}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map(row => (
                      <tr key={rowKey(row)} onClick={() => onRowClick?.(row)}
                        style={{ borderBottom: "1px solid var(--border)", cursor: onRowClick ? "pointer" : "default" }}>
                        {columns.map(c => <td key={c.key} style={{ padding: "9px 14px" }}>{c.render(row)}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
        {detail && <div style={{ width: 340, flexShrink: 0 }}>{detail}</div>}
      </div>
    </AdminLayout>
  );
}

export function StatusBadge({ value }: { value: string }) {
  const variant = value === "active" ? "success" : value === "suspended" ? "danger" : value === "open" ? "warning" : "muted";
  return <Badge variant={variant as "success" | "danger" | "warning" | "muted"} size="sm">{value.replace(/_/g, " ")}</Badge>;
}
