'use client';
import { useCallback } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { tenantSetupApi } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";

export default function ActivityPage() {
  const { data, loading, error } = useApi(useCallback(() => tenantSetupApi.getActivity(1), []));

  const d = data as Record<string, unknown> | null;
  const entries: Record<string, unknown>[] = Array.isArray(d?.items ?? d?.entries ?? d)
    ? (d?.items ?? d?.entries ?? d ?? []) as Record<string, unknown>[]
    : [];

  return (
    <TenantLayout activeNav="activity">
      <div style={{ padding: "var(--space-6)" }}>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.75rem", margin: "0 0 4px" }}>Tenant Portal &rsaquo; Activity</p>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Activity &amp; Audit Log</h1>
        <p style={{ color: "var(--text-secondary)", margin: "0 0 24px" }}>Track all actions and changes made in your provider account.</p>

        {error && (
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>
            Activity log endpoint unavailable. Contact your administrator to view activity history.
          </div>
        )}

        {!error && (
          loading ? (
            <div style={{ height: 300, background: "var(--surface-sunken)", borderRadius: 12 }} />
          ) : entries.length === 0 ? (
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 48, textAlign: "center", color: "var(--text-secondary)" }}>
              No activity recorded yet.
            </div>
          ) : (
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, overflow: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "var(--surface-sunken)" }}>
                    {["Action", "Actor", "Target", "Old Value", "New Value", "Reason", "Request ID", "Date"].map(col => (
                      <th key={col} style={{ padding: "10px 14px", textAlign: "left", fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600, whiteSpace: "nowrap" }}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry, i) => (
                    <tr key={i} style={{ borderTop: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 14px", fontSize: "0.875rem", color: "var(--text-primary)" }}>{String(entry.action ?? "—")}</td>
                      <td style={{ padding: "10px 14px", fontSize: "0.875rem", color: "var(--text-secondary)" }}>{String(entry.actor ?? entry.user ?? "—")}</td>
                      <td style={{ padding: "10px 14px", fontSize: "0.875rem", color: "var(--text-secondary)" }}>{String(entry.target ?? entry.resource ?? "—")}</td>
                      <td style={{ padding: "10px 14px", fontSize: "0.875rem", color: "var(--text-secondary)", maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{String(entry.old_value ?? "—")}</td>
                      <td style={{ padding: "10px 14px", fontSize: "0.875rem", color: "var(--text-secondary)", maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{String(entry.new_value ?? "—")}</td>
                      <td style={{ padding: "10px 14px", fontSize: "0.875rem", color: "var(--text-secondary)" }}>{String(entry.reason ?? "—")}</td>
                      <td style={{ padding: "10px 14px", fontSize: "0.75rem", color: "var(--text-tertiary)", fontFamily: "monospace" }}>{String(entry.request_id ?? "—")}</td>
                      <td style={{ padding: "10px 14px", fontSize: "0.875rem", color: "var(--text-secondary)" }}>
                        {entry.created_at ? new Date(entry.created_at as string).toLocaleDateString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </div>
    </TenantLayout>
  );
}
