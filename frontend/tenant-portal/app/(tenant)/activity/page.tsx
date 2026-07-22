'use client';
import { useCallback } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { tenantSetupApi } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import { PageHeader, Card, Skeleton, Alert, EmptyState } from "@serviceos/design-system";

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
        <div style={{ marginBottom: 24 }}>
          <PageHeader title="Activity & Audit Log" description="Track all actions and changes made in your provider account." />
        </div>

        {error && (
          <Alert tone="danger">
            Activity log endpoint unavailable. Contact your administrator to view activity history.
          </Alert>
        )}

        {!error && (
          loading ? (
            <Skeleton height="300px" radius="12px"/>
          ) : entries.length === 0 ? (
            <Card padding="lg">
              <EmptyState title="No activity recorded yet." />
            </Card>
          ) : (
            <Card padding="none">
              <div style={{ overflowX: "auto" }}>
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
            </Card>
          )
        )}
      </div>
    </TenantLayout>
  );
}
