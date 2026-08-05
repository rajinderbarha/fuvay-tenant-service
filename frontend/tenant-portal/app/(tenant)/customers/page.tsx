"use client";
/**
 * Home Services Customers — real directory, not the generic commerce one.
 *
 * Real bug fixed here: this page called `customersApi` (`/v1/commerce/
 * tenants/{tid}/customers`), a health-score/LTV model built for a different
 * commerce vertical that has none of the fields Home Services actually
 * needs (repeat status, completed/cancelled jobs, open complaints, direct-
 * payment behaviour). The real Home Services customer directory
 * (`hsCustomersApi`, /v1/tenant/home-services/customers/*) already existed
 * with exactly those fields -- it just wasn't wired to this page.
 *
 * "Payment attention" and per-row payment-confirmation-mismatch data has NO
 * backend model yet (confirmed via the real /metric-definitions endpoint:
 * `payment_reliability` is explicitly "NOT_IMPLEMENTED... never fabricated
 * as Reliable/Needs Review") -- so this page shows open-complaint-based
 * payment signal only, never an invented reliability score.
 */
import React, { useCallback, useState } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { PageHeader, Card, Skeleton, EmptyState, Input, Select } from "@serviceos/design-system";
import { Badge } from "../../../components/shared/ui";
import { hsCustomersApi } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import { Users2, UserCheck, RefreshCw as RepeatIcon, UserPlus, MessageSquare } from "lucide-react";

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

function typeLabel(status: string | undefined): { label: string; variant: "success" | "info" | "muted" } {
  if (status === "repeat") return { label: "Repeat customer", variant: "success" };
  if (status === "one_time") return { label: "One-time customer", variant: "info" };
  return { label: "New customer", variant: "muted" };
}

export default function CustomersPage() {
  const [search, setSearch] = useState("");
  const [activity, setActivity] = useState("");
  const [repeatStatus, setRepeatStatus] = useState("");
  const [page, setPage] = useState(1);

  const summary = useApi(useCallback(() => hsCustomersApi.summary(), []), []);
  const customers = useApi(useCallback(
    () => hsCustomersApi.list({
      q: search || undefined,
      activity: activity || undefined,
      repeat_status: repeatStatus || undefined,
      page, page_size: 20,
    }),
    [search, activity, repeatStatus, page],
  ), [search, activity, repeatStatus, page]);

  const s = summary.data;
  const rows: Array<Record<string, unknown>> = Array.isArray(customers.data?.items) ? customers.data.items : [];
  const total = Number(customers.data?.total ?? 0);
  const totalPages = Math.max(1, Math.ceil(total / 20));

  return (
    <TenantLayout activeNav="customers">
      <PageHeader
        title="Home Services Customers"
        description="Understand repeat usage, service history, complaints and direct-payment behaviour."
      />

      {/* KPI strip -- every tile from the real backend summary aggregate
          (the same aggregation the list rows are built from), never
          recomputed client-side from one page of results. */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 14, margin: "18px 0 20px" }}>
        {[
          { icon: <Users2 size={18} />, label: "Total customers", value: s?.total_customers },
          { icon: <UserCheck size={18} />, label: "Active", value: s?.active_customers },
          { icon: <RepeatIcon size={18} />, label: "Repeat customers", value: s?.repeat_customers },
          { icon: <UserPlus size={18} />, label: "New customers", value: s?.new_customers },
          { icon: <MessageSquare size={18} />, label: "Open complaints", value: s?.open_complaints },
        ].map(k => (
          <Card key={k.label} style={{ padding: "14px 16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 34, height: 34, borderRadius: "var(--radius-md)", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", background: "var(--accent-muted)", color: "var(--brand)" }}>{k.icon}</div>
              <div>
                <div style={{ fontSize: 19, fontWeight: 800, color: "var(--text-primary)", margin: 0, lineHeight: 1.1 }}>
                  {summary.loading ? <Skeleton width={24} height={19} /> : (k.value ?? "—")}
                </div>
                <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{k.label}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
        <div style={{ flex: "1 1 260px", maxWidth: 360 }}>
          <Input value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search customers…" />
        </div>
        <Select value={activity} onChange={e => { setActivity(e.target.value); setPage(1); }}
          options={[{ value: "", label: "All activity" }, { value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }]} />
        <Select value={repeatStatus} onChange={e => { setRepeatStatus(e.target.value); setPage(1); }}
          options={[
            { value: "", label: "All customer types" },
            { value: "repeat", label: "Repeat" },
            { value: "one_time", label: "One-time" },
            { value: "none", label: "New" },
          ]} />
      </div>

      {customers.loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[...Array(6)].map((_, i) => <Skeleton key={i} height="3.5rem" radius="8px" />)}
        </div>
      ) : rows.length === 0 ? (
        <Card style={{ textAlign: "center" }}>
          <EmptyState title={search ? `No customers matching "${search}"` : "No customers yet"} />
        </Card>
      ) : (
        <>
          <Card padding="none" style={{ overflow: "hidden" }}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                    {["Customer", "Last activity", "Completed jobs", "Services used", "Type", "Complaints"].map(h => (
                      <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", letterSpacing: "0.06em", textTransform: "uppercase", whiteSpace: "nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((c, i) => {
                    const alias = String(c.alias ?? "Customer");
                    const type = typeLabel(c.repeat_status as string | undefined);
                    const complaints = Number(c.open_complaints ?? 0);
                    return (
                      <tr key={String(c.customer_id)}
                        onClick={() => { window.location.href = `/customers/${c.customer_id}`; }}
                        style={{ borderBottom: i < rows.length - 1 ? "1px solid var(--border)" : "none", cursor: "pointer" }}
                        onMouseEnter={e => (e.currentTarget as HTMLTableRowElement).style.background = "var(--surface-sunken)"}
                        onMouseLeave={e => (e.currentTarget as HTMLTableRowElement).style.background = "transparent"}>
                        <td style={{ padding: "12px 16px" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                            <div style={{ width: 32, height: 32, borderRadius: "50%", background: "var(--accent-muted)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 700, color: "var(--accent)", flexShrink: 0 }}>
                              {alias.replace("Customer ", "").slice(0, 1).toUpperCase() || "C"}
                            </div>
                            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{alias}</span>
                          </div>
                        </td>
                        <td style={{ padding: "12px 16px", fontSize: 12, color: "var(--text-secondary)" }}>{fmtDate(c.last_activity_at as string)}</td>
                        <td style={{ padding: "12px 16px", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", textAlign: "center" }}>{Number(c.completed_jobs ?? 0)}</td>
                        <td style={{ padding: "12px 16px", fontSize: 13, color: "var(--text-secondary)", textAlign: "center" }}>{Number(c.services_used_count ?? 0)}</td>
                        <td style={{ padding: "12px 16px" }}>
                          <Badge variant={type.variant} size="sm">{type.label}</Badge>
                        </td>
                        <td style={{ padding: "12px 16px" }}>
                          {complaints > 0
                            ? <Badge variant="danger" size="sm">{complaints} open</Badge>
                            : <Badge variant="success" size="sm">Good history</Badge>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 12, flexWrap: "wrap", gap: 10 }}>
            <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
              Showing {(page - 1) * 20 + 1} to {Math.min(page * 20, total)} of {total} customers
            </span>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <button disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}
                style={{ padding: "6px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", cursor: page <= 1 ? "not-allowed" : "pointer", opacity: page <= 1 ? 0.5 : 1, fontFamily: "inherit", fontSize: 12 }}>← Prev</button>
              <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Page {page} of {totalPages}</span>
              <button disabled={page >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                style={{ padding: "6px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", cursor: page >= totalPages ? "not-allowed" : "pointer", opacity: page >= totalPages ? 0.5 : 1, fontFamily: "inherit", fontSize: 12 }}>Next →</button>
            </div>
          </div>
        </>
      )}
    </TenantLayout>
  );
}
