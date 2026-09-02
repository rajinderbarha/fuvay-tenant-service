"use client";
import { TableSurface } from "@serviceos/design-system";
import { useCallback, useState } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader, SummaryCardsRow, Pagination } from "../../../../components/shared/ui";
import { financeApi, TenantPenalty, TenantPenaltySummary } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

const STATUS_VARIANT: Record<string, "success" | "warning" | "danger" | "info" | "muted"> = {
  applied: "danger", pending: "warning", reversed: "muted", failed: "danger", cancelled: "muted",
};
const fmt = (n: number) => `₹${Number(n).toLocaleString("en-IN")}`;

export default function TenantPenaltiesPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");

  const summary = useApi(useCallback(() => financeApi.getPenaltySummary(), []));
  const list = useApi(useCallback(() =>
    financeApi.listPenalties({ page, limit: 50, status: statusFilter || undefined }),
    [page, statusFilter]));

  const s: TenantPenaltySummary | undefined = summary.data;

  return (
    <AdminLayout activeNav="finance">
      <SectionHeader
        title="Tenant Penalties"
        subtitle="Automatic usage-credit deductions for missed service, complaint, refund, and warranty response SLAs."
        actions={<Btn variant="ghost" onClick={() => { summary.refetch(); list.refetch(); }}>Refresh</Btn>}
      />

      {s && (
        <SummaryCardsRow cards={[
          { label: "Total Penalties", value: s.total_penalties },
          { label: "Applied", value: s.applied_penalties, accent: s.applied_penalties > 0 },
          { label: "Pending", value: s.pending_penalties },
          { label: "Reversed", value: s.reversed_penalties },
          { label: "Wallet Deducted", value: fmt(s.wallet_deducted) },
        ]} />
      )}

      <Card padding={0} style={{ marginTop: 20 }}>
        <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)", display: "flex", gap: 10, alignItems: "center" }}>
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
            style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg-input, var(--bg))", fontSize: 13 }}
          >
            <option value="">All statuses</option>
            {["applied","pending","reversed","failed","cancelled"].map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <span style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
            {list.data?.meta.total ?? 0} records
          </span>
        </div>

        <div style={{ overflowX: "auto" }}>
          <TableSurface style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--bg-subtle, var(--bg))" }}>
                {["Penalty #","Status","Type","Source","Amount","Reason","Date"].map(h => (
                  <th key={h} style={{ padding: "10px 12px", textAlign: "left", fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {list.loading && (
                <tr><td colSpan={7} style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)" }}>Loading…</td></tr>
              )}
              {!list.loading && !list.data?.penalties.length && (
                <tr><td colSpan={7} style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)" }}>No penalties found.</td></tr>
              )}
              {list.data?.penalties.map((p: TenantPenalty) => (
                <tr key={p.id} style={{ borderBottom: "1px solid var(--border-subtle, var(--border))" }}>
                  <td style={{ padding: "10px 12px", fontFamily: "monospace", fontSize: 12 }}>{p.penalty_number}</td>
                  <td style={{ padding: "10px 12px" }}>
                    <Badge variant={STATUS_VARIANT[p.status] ?? "muted"}>{p.status}</Badge>
                  </td>
                  <td style={{ padding: "10px 12px", fontSize: 12 }}>{p.penalty_type.replace(/_/g, " ")}</td>
                  <td style={{ padding: "10px 12px", fontSize: 12 }}>{p.source.replace(/_/g, " ")}</td>
                  <td style={{ padding: "10px 12px", fontSize: 13, fontWeight: 700 }}>{fmt(p.amount)}</td>
                  <td style={{ padding: "10px 12px", fontSize: 12, maxWidth: 260 }}>
                    <span title={p.reason} style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {p.reason}
                    </span>
                  </td>
                  <td style={{ padding: "10px 12px", fontSize: 12 }}>
                    {new Date(p.created_at).toLocaleDateString("en-IN")}
                  </td>
                </tr>
              ))}
            </tbody>
          </TableSurface>
        </div>

        {list.data?.meta && <Pagination page={page} pageSize={50} total={list.data.meta.total}
          pageCount={list.data.meta.total_pages} onPage={setPage} itemLabel="penalties" />}
      </Card>
    </AdminLayout>
  );
}
