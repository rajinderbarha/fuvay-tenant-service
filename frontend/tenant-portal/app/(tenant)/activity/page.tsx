'use client';
import { TableSurface } from "@serviceos/design-system";
/**
 * Tenant "Activity & Audit Log".
 *
 * Two real bugs fixed here (found in the admin<->tenant connectivity audit):
 *  1. The page called `/v1/provider/activity`, a route that exists in NO
 *     engine -- so this page was a permanent error state for every tenant.
 *     It now uses the real, already-mounted `/v1/provider/audit-logs`
 *     (see tenantSetupApi.getActivity), which reads the same
 *     PlatformAuditLogService the super-admin audit-logs page uses, scoped
 *     to the caller's tenant.
 *  2. The table rendered `entry.actor`, `entry.target`, `entry.resource`
 *     and `entry.reason` -- none of which exist in the real payload
 *     (audit_service.py::_to_dict emits actor_role/actor_id,
 *     resource_type/resource_id, and no reason at all), so even with a
 *     working endpoint every one of those cells would have shown "—".
 *     Columns now match the actual contract, and the JSON before/after
 *     snapshots are stringified rather than rendered as "[object Object]".
 */
import { useCallback, useState } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { tenantSetupApi, type ProviderAuditLogEntry } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import { PageHeader, Card, Skeleton, Alert, EmptyState, Pagination } from "@serviceos/design-system";

const PAGE_SIZE = 50;

/** old_value/new_value are arbitrary JSON snapshots -- render compactly
 * instead of letting String() produce "[object Object]". */
function snapshot(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return v || "—";
  try {
    const s = JSON.stringify(v);
    return s === "{}" ? "—" : s;
  } catch {
    return "—";
  }
}

const TH: React.CSSProperties = {
  padding: "10px 14px", textAlign: "left", fontSize: "0.75rem",
  color: "var(--text-secondary)", fontWeight: 600, whiteSpace: "nowrap",
};
const TD: React.CSSProperties = {
  padding: "10px 14px", fontSize: "0.875rem", color: "var(--text-secondary)",
};
const TD_CLIP: React.CSSProperties = {
  ...TD, maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
};

export default function ActivityPage() {
  const [page, setPage] = useState(1);
  const { data, loading, error } = useApi(
    useCallback(() => tenantSetupApi.getActivity(page, PAGE_SIZE), [page]),
    [page],
  );

  const entries: ProviderAuditLogEntry[] = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <TenantLayout activeNav="activity">
      <div style={{ padding: "var(--space-6)" }}>
        <div style={{ marginBottom: 24 }}>
          <PageHeader title="Activity & Audit Log" description="Track all actions and changes made in your provider account." />
        </div>

        {error && <Alert tone="danger">Could not load your activity log: {error}</Alert>}

        {!error && (
          loading ? (
            <Skeleton height="300px" radius="12px"/>
          ) : entries.length === 0 ? (
            <Card padding="lg">
              <EmptyState title="No activity recorded yet." />
            </Card>
          ) : (
            <>
              <Card padding="none">
                <div style={{ overflowX: "auto" }}>
                  <TableSurface style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ background: "var(--surface-sunken)" }}>
                        {["Action", "Actor", "Resource", "Before", "After", "Request ID", "Date"].map(col => (
                          <th key={col} style={TH}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {entries.map(entry => (
                        <tr key={entry.id} style={{ borderTop: "1px solid var(--border)" }}>
                          <td style={{ ...TD, color: "var(--text-primary)" }}>
                            {entry.action ?? "—"}
                            {entry.is_high_risk ? (
                              <span style={{ marginLeft: 6, fontSize: "0.6875rem", color: "var(--danger-text)", fontWeight: 600 }}>
                                HIGH RISK
                              </span>
                            ) : null}
                          </td>
                          <td style={TD}>{entry.actor_role ?? "—"}</td>
                          <td style={TD}>
                            {entry.resource_type ?? "—"}
                            {entry.resource_id ? (
                              <span style={{ color: "var(--text-tertiary)", fontFamily: "monospace", fontSize: "0.75rem" }}>
                                {" "}{entry.resource_id.slice(0, 8)}
                              </span>
                            ) : null}
                          </td>
                          <td style={TD_CLIP} title={snapshot(entry.old_value)}>{snapshot(entry.old_value)}</td>
                          <td style={TD_CLIP} title={snapshot(entry.new_value)}>{snapshot(entry.new_value)}</td>
                          <td style={{ ...TD, fontSize: "0.75rem", color: "var(--text-tertiary)", fontFamily: "monospace" }}>
                            {entry.request_id ?? "—"}
                          </td>
                          <td style={TD}>{new Date(entry.created_at).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </TableSurface>
                </div>
              </Card>
              <Pagination page={page} pageSize={PAGE_SIZE} total={total} pageCount={totalPages} onPage={setPage} itemLabel="entries" />
            </>
          )
        )}
      </div>
    </TenantLayout>
  );
}
