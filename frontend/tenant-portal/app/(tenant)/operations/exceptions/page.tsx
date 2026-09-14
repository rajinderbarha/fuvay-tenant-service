"use client";
import { TableSurface } from "@serviceos/design-system";
/**
 * Operational Exceptions combines the dashboard's canonical active action
 * queue with historical service_jobs that ended abnormally. Active rows drill
 * into their owning workspace; force-closed and voided records remain below
 * as read-only closure history.
 */
import React, { useCallback, useMemo } from "react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { Badge, JobStatusBadge } from "../../../../components/shared/ui";
import {
  serviceJobsApi, getUserRole, homeServicesDashboardApi,
  type HomeServicesDashboardAttentionItem,
} from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import type { ServiceJobRecord } from "../../../../lib/api";
import { AlertTriangle, ArrowRight, Clock3, RefreshCw } from "lucide-react";
import ReadOnlyBanner from "../../../../components/shared/ReadOnlyBanner";
import { PageHeader, Card, Button, Skeleton, EmptyState, Alert } from "@serviceos/design-system";

const shortId = (id?: string | null) => (id ? `${id.slice(0, 8)}…` : "—");

export default function OperationalExceptionsPage() {
  const dashboard = useApi(useCallback(() => homeServicesDashboardApi.get(), []));
  const forceClosed = useApi(useCallback(() => serviceJobsApi.list({ status: "force_closed", limit: 50 }), []));
  const voided = useApi(useCallback(() => serviceJobsApi.list({ status: "voided", limit: 50 }), []));

  const loading = dashboard.loading || forceClosed.loading || voided.loading;
  const error = dashboard.error || forceClosed.error || voided.error;
  const activeItems = dashboard.data?.attention_queue ?? [];
  const activeTotal = activeItems.reduce((total, item) => total + item.count, 0);

  const items: (ServiceJobRecord & { exception_kind: "force_closed" | "voided" })[] = useMemo(() => {
    const fc = (forceClosed.data?.items ?? []).map((j) => ({ ...j, exception_kind: "force_closed" as const }));
    const vo = (voided.data?.items ?? []).map((j) => ({ ...j, exception_kind: "voided" as const }));
    return [...fc, ...vo].sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? ""));
  }, [forceClosed.data, voided.data]);

  const refetchAll = () => {
    dashboard.refetch();
    forceClosed.refetch();
    voided.refetch();
  };

  return (
    <TenantLayout activeNav="operational-exceptions">
      <ReadOnlyBanner role={getUserRole()} />
      <div style={{ marginBottom: 16 }}>
        <PageHeader
          title="Operational Exceptions"
          description={loading ? "Loading..." : `${activeTotal} active action(s) · ${items.length} unusually closed job(s)`}
          actions={<Button variant="secondary" size="sm" leftIcon={<RefreshCw size={14}/>} onClick={refetchAll}>Refresh</Button>}
        />
      </div>

      <div style={{ marginBottom: 16 }}>
        <Card padding="md" style={{ background: "var(--surface-sunken)" }}>
          <p style={{ fontSize: 12.5, color: "var(--text-secondary)", margin: 0, lineHeight: 1.6 }}>
            Active exceptions use the same live action queue as your dashboard. Open a queue to resolve
            its underlying work. The history below separately records jobs force-closed by an admin or
            voided without normal completion.
          </p>
        </Card>
      </div>

      {error && (
        <div style={{ marginBottom: 16 }}>
          <Alert tone="danger">{error}</Alert>
        </div>
      )}

      <Card title="Active attention" padding="none" style={{ marginBottom: 16 }}>
        {dashboard.loading && !dashboard.data ? <div style={{ padding: 16 }}><Skeleton height={92} /></div>
          : activeItems.length === 0 ? <EmptyState title="No active exceptions" description="No operational actions currently need attention." />
          : <div style={{ display: "grid" }}>{activeItems.map((item, index) => <AttentionItem key={item.key} item={item} last={index === activeItems.length - 1} />)}</div>}
      </Card>

      <Card title="Exceptional closure history" padding="none">
        <div style={{ overflowX: "auto" }}>
          <TableSurface style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                {["Job", "Exception", "Status", "Reason", "Staff", "Closed"].map((h) => (
                  <th key={h} style={{ padding: "11px 16px", textAlign: "left", fontSize: 11,
                    fontWeight: 700, color: "var(--text-tertiary)", letterSpacing: "0.06em",
                    textTransform: "uppercase" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? [...Array(4)].map((_, i) => (
                <tr key={i}><td colSpan={6} style={{ padding: "10px 16px" }}><Skeleton height="1.125rem" /></td></tr>
              )) : items.length === 0 ? (
                <tr><td colSpan={6} style={{ padding: 0 }}>
                  <EmptyState title="No exceptional closures"
                    description="No jobs have been force-closed or voided." />
                </td></tr>
              ) : items.map((j, i) => (
                <tr key={j.id} onClick={() => window.location.href = `/home-services/bookings-jobs?job_id=${j.id}`}
                  style={{ borderBottom: i < items.length - 1 ? "1px solid var(--border)" : "none", cursor: "pointer" }}
                  onMouseEnter={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "var(--surface-sunken)"}
                  onMouseLeave={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "transparent"}>
                  <td style={{ padding: "11px 16px", fontSize: 12, fontWeight: 600, color: "var(--text-link)" }}>
                    {j.job_number}
                  </td>
                  <td style={{ padding: "11px 16px" }}>
                    <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 9px", borderRadius: 999,
                      background: j.exception_kind === "force_closed" ? "var(--warning-bg)" : "var(--surface-sunken)",
                      color: j.exception_kind === "force_closed" ? "var(--warning-text)" : "var(--text-secondary)",
                      border: `1px solid ${j.exception_kind === "force_closed" ? "var(--warning-border)" : "var(--border)"}` }}>
                      {j.exception_kind === "force_closed" ? "Force-closed" : "Voided"}
                    </span>
                  </td>
                  <td style={{ padding: "11px 16px" }}><JobStatusBadge status={j.status} /></td>
                  <td style={{ padding: "11px 16px", fontSize: 12, color: "var(--text-secondary)", maxWidth: 320 }}>
                    {j.failure_reason ?? <span style={{ color: "var(--text-tertiary)" }}>Not recorded</span>}
                  </td>
                  <td style={{ padding: "11px 16px", fontSize: 12, color: "var(--text-secondary)" }}>
                    {shortId(j.assigned_staff_id)}
                  </td>
                  <td style={{ padding: "11px 16px", fontSize: 12, color: "var(--text-tertiary)" }}>
                    {j.updated_at ? new Date(j.updated_at).toLocaleString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </TableSurface>
        </div>
      </Card>
    </TenantLayout>
  );
}

function AttentionItem({ item, last }: { item: HomeServicesDashboardAttentionItem; last: boolean }) {
  const tone = item.severity === "danger" ? "danger" : item.severity === "warning" ? "warning" : "info";
  return <button type="button" onClick={() => { window.location.href = item.destination; }} style={{
    display: "flex", alignItems: "center", gap: 12, width: "100%", padding: "14px 16px",
    border: 0, borderBottom: last ? 0 : "1px solid var(--border)", background: "transparent",
    color: "var(--text-primary)", cursor: "pointer", textAlign: "left", font: "inherit",
  }}>
    <span style={{ display: "grid", placeItems: "center", width: 38, height: 38, flex: "none", borderRadius: 11,
      background: tone === "danger" ? "var(--danger-bg)" : tone === "warning" ? "var(--warning-bg)" : "var(--info-bg)",
      color: tone === "danger" ? "var(--danger-text)" : tone === "warning" ? "var(--warning-text)" : "var(--info-text)" }}>
      {item.key === "SLA_ATTENTION" ? <Clock3 size={17} /> : <AlertTriangle size={17} />}
    </span>
    <span style={{ minWidth: 0, flex: 1 }}><strong style={{ display: "block", fontSize: 13 }}>{item.label}</strong>
      <span style={{ display: "block", marginTop: 3, color: "var(--text-tertiary)", fontSize: 11 }}>
        {item.oldest_age_hours == null ? "Open the queue for details" : `Oldest item ${item.oldest_age_hours}h`}
      </span></span>
    <Badge variant={tone} size="sm">{item.count}</Badge><ArrowRight size={15} color="var(--text-tertiary)" />
  </button>;
}
