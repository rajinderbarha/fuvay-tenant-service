"use client";
import { TableSurface } from "@serviceos/design-system";
/**
 * Operational Exceptions — real, read-only view of service_jobs that ended
 * abnormally (force_closed by an admin override, or voided). This is
 * deliberately NOT a resolution engine: there is no "resolve"/"retry" action
 * here, only the same real data ServiceJob already stores (status,
 * failure_reason, timestamps), surfaced from the canonical
 * /v1/provider/my-records/jobs endpoint (serviceJobsApi — service_jobs table,
 * not the legacy field_ops pipeline).
 *
 * Scope note: an admin can force-close or void a job via
 * app/engines/execution/home_service_router.py's admin_router
 * (/status-override, /force-close, /void), which sets ServiceJob.status and
 * (per that router) can attach a reason — but ServiceJob has only a single
 * `failure_reason` text column, not a structured escalation/owner/next-step
 * model. So "escalation" here means: show what's known (status + reason +
 * when), not fabricate an assignee or SLA countdown the backend doesn't
 * track. See docs/workflow-rearchitecture/tenant-portal-missing-workflows/backend-tickets.md
 * for the richer model this page would need to grow real escalation actions.
 */
import React, { useCallback, useMemo } from "react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { JobStatusBadge } from "../../../../components/shared/ui";
import { serviceJobsApi, getUserRole } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import type { ServiceJobRecord } from "../../../../lib/api";
import { AlertTriangle, RefreshCw } from "lucide-react";
import ReadOnlyBanner from "../../../../components/shared/ReadOnlyBanner";
import { PageHeader, Card, Button, Skeleton, EmptyState, StatusBadge as DsStatusBadge, Alert } from "@serviceos/design-system";

const shortId = (id?: string | null) => (id ? `${id.slice(0, 8)}…` : "—");

export default function OperationalExceptionsPage() {
  const forceClosed = useApi(useCallback(() => serviceJobsApi.list({ status: "force_closed", limit: 50 }), []));
  const voided = useApi(useCallback(() => serviceJobsApi.list({ status: "voided", limit: 50 }), []));

  const loading = forceClosed.loading || voided.loading;
  const error = forceClosed.error || voided.error;

  const items: (ServiceJobRecord & { exception_kind: "force_closed" | "voided" })[] = useMemo(() => {
    const fc = (forceClosed.data?.items ?? []).map((j) => ({ ...j, exception_kind: "force_closed" as const }));
    const vo = (voided.data?.items ?? []).map((j) => ({ ...j, exception_kind: "voided" as const }));
    return [...fc, ...vo].sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? ""));
  }, [forceClosed.data, voided.data]);

  const refetchAll = () => {
    forceClosed.refetch();
    voided.refetch();
  };

  return (
    <TenantLayout activeNav="operational-exceptions">
      <ReadOnlyBanner role={getUserRole()} />
      <div style={{ marginBottom: 16 }}>
        <PageHeader
          title="Operational Exceptions"
          description={loading ? "Loading..." : `${items.length} job(s) closed outside the normal completion flow`}
          actions={<Button variant="secondary" size="sm" leftIcon={<RefreshCw size={14}/>} onClick={refetchAll}>Refresh</Button>}
        />
      </div>

      <div style={{ marginBottom: 16 }}>
        <Card padding="md" style={{ background: "var(--surface-sunken)" }}>
          <p style={{ fontSize: 12.5, color: "var(--text-secondary)", margin: 0, lineHeight: 1.6 }}>
            This is a read-only explanation view — it does not resolve exceptions. Force-closed jobs were
            ended by an admin status override; voided jobs were cancelled without completion. Use the
            reason shown (when recorded) to decide whether follow-up with the customer or staff is needed.
          </p>
        </Card>
      </div>

      {error && (
        <div style={{ marginBottom: 16 }}>
          <Alert tone="danger">{error}</Alert>
        </div>
      )}

      <Card padding="none">
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
                  <EmptyState title="No operational exceptions"
                    description="No jobs have been force-closed or voided. This queue only shows jobs that ended outside the normal completion flow." />
                </td></tr>
              ) : items.map((j, i) => (
                <tr key={j.id} onClick={() => window.location.href = `/jobs/${j.id}`}
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
