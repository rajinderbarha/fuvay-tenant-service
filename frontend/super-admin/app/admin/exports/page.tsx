"use client";
/**
 * FINAL-L5-05AB — Export Job History.
 *
 * Real /v1/enterprise/exports job list, retry, cancel and download. This
 * page did not exist before this sprint despite being referenced by 4
 * existing page flows (Commission Records, Payments, Refund Requests,
 * Service Jobs) via an `alert("...check /admin/exports.")` message that
 * pointed at a dead route -- jobs were created server-side but never
 * visible, retryable, cancellable or downloadable anywhere in the UI.
 *
 * Backend already scopes `GET /v1/enterprise/exports` to the requesting
 * user's own jobs (`list_export_jobs(db, u.user_id)`), so no client-side
 * tenant/role filtering is needed here -- an actor simply never sees a
 * job they didn't create, which also means Admin Read Only (who has no
 * export-create permission anywhere) naturally sees an empty history.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { RefreshCw, Download, RotateCcw, XCircle, AlertTriangle } from "lucide-react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader } from "../../../components/shared/ui";
import { useApi, useAction } from "../../../hooks/useApi";
import { enterpriseApi, ServiceOSError } from "../../../lib/api";
import type { EnterpriseExportJob } from "../../../lib/api";

// Backend statuses (app/engines/enterprise_grid/constants.py) -> canonical
// UI presentation. Never render the raw backend string directly.
const STATUS_META: Record<string, { label: string; variant: "success" | "warning" | "danger" | "muted" | "info" }> = {
  pending:    { label: "Queued",     variant: "info" },
  processing: { label: "Running",    variant: "warning" },
  completed:  { label: "Completed",  variant: "success" },
  failed:     { label: "Failed",     variant: "danger" },
  cancelled:  { label: "Cancelled",  variant: "muted" },
  expired:    { label: "Expired",    variant: "muted" },
};

const RESOURCE_LABELS: Record<string, string> = {
  admin_commission_records: "Commission Records",
  admin_payments:           "Payments",
  admin_refund_requests:    "Refund Requests",
  admin_service_jobs:       "Service Jobs",
};

// Non-terminal statuses -- while any job is in one of these, the list
// keeps polling (bounded: fixed 5s interval, stops entirely once none
// remain, matching "polling is bounded" / "terminal jobs stop polling").
const NON_TERMINAL = new Set(["pending", "processing"]);

function StatusBadge({ status }: { status: string }) {
  const meta = STATUS_META[status] ?? { label: status, variant: "muted" as const };
  return <Badge variant={meta.variant}>{meta.label}</Badge>;
}

function formatBytes(n?: number | null): string {
  if (!n) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ExportJobHistoryPage() {
  const jobs = useApi(useCallback(() => enterpriseApi.listExports(), []));
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const retry = useAction((id: string) => enterpriseApi.retryExport(id));
  const cancel = useAction((id: string) => enterpriseApi.cancelExport(id));

  // Bounded polling: only while at least one listed job is non-terminal.
  useEffect(() => {
    const hasActive = (jobs.data ?? []).some((j) => NON_TERMINAL.has(j.status));
    if (hasActive && !pollRef.current) {
      pollRef.current = setInterval(() => jobs.refetch(), 5000);
    } else if (!hasActive && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobs.data]);

  const handleRetry = async (id: string) => {
    if (busyId) return; // duplicate-tap safe
    setBusyId(id); setActionError(null);
    try { await retry.execute(id); jobs.refetch(); }
    catch (e) { setActionError(e instanceof ServiceOSError ? e.message : "Retry failed."); }
    finally { setBusyId(null); }
  };

  const handleCancel = async (id: string) => {
    if (busyId) return;
    if (!window.confirm("Cancel this export job? This cannot be undone.")) return;
    setBusyId(id); setActionError(null);
    try { await cancel.execute(id); jobs.refetch(); }
    catch (e) { setActionError(e instanceof ServiceOSError ? e.message : "Cancel failed."); }
    finally { setBusyId(null); }
  };

  const handleDownload = async (job: EnterpriseExportJob) => {
    if (busyId) return;
    setBusyId(job.id); setActionError(null);
    try {
      const label = RESOURCE_LABELS[job.resource_key] ?? job.resource_key;
      const ext = (job.export_format || "csv").toLowerCase();
      const filename = `${label.replace(/\s+/g, "-").toLowerCase()}-${job.id.slice(0, 8)}.${ext}`;
      const blob = await enterpriseApi.downloadExport(job.id, filename);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setActionError(e instanceof ServiceOSError ? e.message : "Download failed.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <AdminLayout>
      <SectionHeader
        title="Export Job History"
        subtitle="Exports you have created. Files are private, expire automatically, and are only downloadable while status is Completed."
        actions={<Btn variant="secondary" onClick={() => jobs.refetch()}><RefreshCw size={14} /> Refresh</Btn>}
      />

      {actionError && (
        <Card style={{ marginBottom: 16, borderColor: "var(--color-danger, #dc2626)" }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", color: "var(--color-danger, #dc2626)" }}>
            <AlertTriangle size={16} /> {actionError}
          </div>
        </Card>
      )}

      <Card>
        {jobs.loading && !jobs.data && <div style={{ padding: 24 }}>Loading export history…</div>}
        {jobs.error && (
          <div style={{ padding: 24, color: "var(--color-danger, #dc2626)" }}>
            {jobs.error}{jobs.requestId ? ` (request ${jobs.requestId})` : ""}
          </div>
        )}
        {jobs.data && jobs.data.length === 0 && (
          <div style={{ padding: 24, textAlign: "center", color: "var(--color-muted, #6b7280)" }}>
            No export jobs yet. Use an Export button on a supported page to create one.
          </div>
        )}
        {jobs.data && jobs.data.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <thead>
                <tr style={{ textAlign: "left", borderBottom: "1px solid var(--color-border, #e5e7eb)" }}>
                  <th style={{ padding: "8px 12px" }}>Resource</th>
                  <th style={{ padding: "8px 12px" }}>Format</th>
                  <th style={{ padding: "8px 12px" }}>Status</th>
                  <th style={{ padding: "8px 12px" }}>Rows</th>
                  <th style={{ padding: "8px 12px" }}>Size</th>
                  <th style={{ padding: "8px 12px" }}>Created</th>
                  <th style={{ padding: "8px 12px" }}>Expires</th>
                  <th style={{ padding: "8px 12px" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.data.map((job) => {
                  const isBusy = busyId === job.id;
                  const canRetry = job.status === "failed" || job.status === "expired";
                  const canCancel = NON_TERMINAL.has(job.status);
                  const canDownload = job.status === "completed";
                  return (
                    <tr key={job.id} style={{ borderBottom: "1px solid var(--color-border, #f0f0f0)" }}>
                      <td style={{ padding: "8px 12px" }}>{RESOURCE_LABELS[job.resource_key] ?? job.resource_key}</td>
                      <td style={{ padding: "8px 12px" }}>{(job.export_format || "csv").toUpperCase()}</td>
                      <td style={{ padding: "8px 12px" }}><StatusBadge status={job.status} /></td>
                      <td style={{ padding: "8px 12px" }}>{job.row_count ?? "—"}</td>
                      <td style={{ padding: "8px 12px" }}>{formatBytes((job as unknown as { file_size?: number }).file_size)}</td>
                      <td style={{ padding: "8px 12px" }}>{job.created_at ? new Date(job.created_at).toLocaleString() : "—"}</td>
                      <td style={{ padding: "8px 12px" }}>{job.expires_at ? new Date(job.expires_at).toLocaleString() : "—"}</td>
                      <td style={{ padding: "8px 12px", display: "flex", gap: 6 }}>
                        {canDownload && (
                          <Btn variant="secondary" disabled={isBusy} onClick={() => handleDownload(job)}>
                            <Download size={14} /> Download
                          </Btn>
                        )}
                        {canRetry && (
                          <Btn variant="secondary" disabled={isBusy} onClick={() => handleRetry(job.id)}>
                            <RotateCcw size={14} /> Retry
                          </Btn>
                        )}
                        {canCancel && (
                          <Btn variant="secondary" disabled={isBusy} onClick={() => handleCancel(job.id)}>
                            <XCircle size={14} /> Cancel
                          </Btn>
                        )}
                        {job.status === "failed" && job.failure_reason && (
                          <span style={{ fontSize: 12, color: "var(--color-muted, #6b7280)", alignSelf: "center" }}>{job.failure_reason}</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </AdminLayout>
  );
}
