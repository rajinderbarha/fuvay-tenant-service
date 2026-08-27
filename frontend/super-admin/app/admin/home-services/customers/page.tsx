"use client";
/**
 * Home Services Customers — canonical, vertically-scoped customer directory.
 *
 * Audit finding: the prior page showed only Total/Active Customers and an
 * empty list (no customer-directory backend existed). This is a genuine
 * build on top of HomeServicesCustomerDirectoryService, which computes
 * Total/Active/New/Repeat/Returning-Rate from ONE shared per-customer
 * aggregate over ServiceBooking/ServiceJob -- summary and table can never
 * disagree, the exact bug class already found and fixed for the Provider
 * Directory.
 *
 * Payment Reliability is derived from canonical direct-payment
 * reconciliation records. Pending confirmations are neutral; unresolved
 * mismatches and disputes are the only records that enter Payment Review.
 */
import { useCallback, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Download, Info, RefreshCw } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Input, DataTable, Skeleton, Modal, Pagination, SummaryCard, KpiGrid, SectionHeader } from "../../../../components/shared/ui";
import { hsCustomerDirectoryApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

function dt(v?: string | null) {
  return v ? new Date(v).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—";
}
function money(v?: string | number | null) {
  return `₹${Number(v ?? 0).toLocaleString("en-IN")}`;
}

export default function HomeServicesCustomersPage() {
  return (
    <Suspense fallback={<Skeleton height={400} />}>
      <HomeServicesCustomersWorkspace />
    </Suspense>
  );
}

function HomeServicesCustomersWorkspace() {
  const router = useRouter();
  const params = useSearchParams();
  const q = params.get("q") || "";
  const activity = (params.get("activity") as "active" | "inactive" | null) || undefined;
  const repeatStatus = params.get("repeat_status") || undefined;
  const page = Number(params.get("page") || "1");
  const [defsOpen, setDefsOpen] = useState(false);

  function setListState(next: { q?: string; activity?: string; repeat_status?: string; page?: number }) {
    const sp = new URLSearchParams(params.toString());
    if (next.q !== undefined) { if (next.q) sp.set("q", next.q); else sp.delete("q"); }
    if (next.activity !== undefined) { if (next.activity) sp.set("activity", next.activity); else sp.delete("activity"); }
    if (next.repeat_status !== undefined) { if (next.repeat_status) sp.set("repeat_status", next.repeat_status); else sp.delete("repeat_status"); }
    if (next.page !== undefined) sp.set("page", String(next.page));
    router.replace(`/admin/home-services/customers?${sp.toString()}`);
  }

  const summary = useApi(useCallback(() => hsCustomerDirectoryApi.getSummary(), []));
  const customers = useApi(useCallback(
    () => hsCustomerDirectoryApi.list({ q: q || undefined, activity, repeatStatus, page, pageSize: 20 }),
    [q, activity, repeatStatus, page]));
  const s = summary.data as Record<string, unknown> | undefined;

  return (
    <AdminLayout activeNav="home_services-customers">
      <SectionHeader
        eyebrow="Home Services operations"
        context="Customers"
        title="Home Services Customers"
        subtitle="Understand customer activity, repeat usage, service diversity and payment-confirmation reliability."
        actions={<>
          <Badge variant="info">Home Services only</Badge>
          <Btn variant="ghost" icon={<Info size={14} />} onClick={() => setDefsOpen(true)}>View Definitions</Btn>
          <Btn variant="ghost" icon={<RefreshCw size={14} />} onClick={() => { summary.refetch(); customers.refetch(); }}>Refresh</Btn>
          <Btn variant="ghost" icon={<Download size={14} />} onClick={async () => {
            const data = await hsCustomerDirectoryApi.list({ pageSize: 5000 });
            if (data.items.length === 0) { alert("Nothing to export."); return; }
            const headers = Object.keys(data.items[0]);
            const csv = [headers.join(","), ...data.items.map(r => headers.map(h => JSON.stringify(r[h] ?? "")).join(","))].join("\n");
            const blob = new Blob([csv], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url; a.download = "home-services-customers.csv"; a.click();
            URL.revokeObjectURL(url);
          }}>Export</Btn>
        </>}
      />

      <Card padding={12} style={{ background: "var(--surface-sunken)", marginBottom: 16 }}>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
          Active = qualifying Home Services activity in the last {s?.active_window_days as number ?? 90} days.
          Customer payments are made directly to providers.
        </p>
      </Card>

      {summary.error && (
        <Card padding={12} style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)", marginBottom: 12 }}>
          <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>
            Summary metrics failed to load ({summary.error}).
            <Btn variant="ghost" size="sm" onClick={summary.refetch} style={{ marginLeft: 8 }}>Retry</Btn>
          </p>
        </Card>
      )}

      <KpiGrid minCardWidth={170} style={{ marginBottom: "var(--space-3)" }}>
        <SummaryCard label="Total Customers" value={s?.total_customers as number} onClick={() => setListState({ activity: undefined, page: 1 })} />
        <SummaryCard label={`Active · ${s?.active_window_days ?? 90} days`} value={s?.active_customers as number} tone="success" onClick={() => setListState({ activity: "active", page: 1 })} />
        <SummaryCard label={`New · ${s?.new_customer_window_days ?? 30} days`} value={s?.new_customers as number} />
        <SummaryCard label="Repeat Customers" value={s?.repeat_customers as number} onClick={() => setListState({ repeat_status: "repeat", page: 1 })} />
        <SummaryCard label="Returning Rate" value={s ? `${s.returning_rate}%` : undefined} />
        <SummaryCard label="Inactive" value={s?.inactive_customers as number} tone="warning" onClick={() => setListState({ activity: "inactive", page: 1 })} />
        <SummaryCard label="Payment Review" value={s?.payment_review_available ? (s.payment_review as number) : "N/A"} tone="warning" />
        <SummaryCard label="Open Complaints" value={s?.open_complaints as number} tone="danger" />
      </KpiGrid>

      <KpiGrid minCardWidth={170} style={{ marginBottom: "var(--space-4)" }}>
        <SummaryCard label="Completed-job Customers" value={String(s?.completed_job_customers ?? "—")} />
        <SummaryCard label="Multi-service Customers" value={String(s?.multi_service_customers ?? "—")} />
        <SummaryCard label="Multi-provider Customers" value={String(s?.multi_provider_customers ?? "—")} />
        <SummaryCard label="Avg Completed Jobs" value={String(s?.average_completed_jobs ?? "—")} />
        <SummaryCard label="Confirmed Job Value" value={money(s?.confirmed_job_value as string)} sub="Not platform collection" />
      </KpiGrid>

      <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
        <div style={{ flex: 1, maxWidth: 360 }}>
          <Input placeholder="Search name, phone, email or customer ID..." value={q}
            onChange={v => setListState({ q: v, page: 1 })} />
        </div>
        {(activity || repeatStatus) && (
          <Btn variant="ghost" onClick={() => setListState({ activity: undefined, repeat_status: undefined, page: 1 })}>
            Clear filters ×
          </Btn>
        )}
      </div>

      {customers.error ? (
        <Card padding={24} style={{ textAlign: "center" }}>
          <p style={{ color: "var(--danger-text)", fontSize: 13, margin: "0 0 8px" }}>
            Could not load Home Services customers: {customers.error}
          </p>
          {customers.requestId && (
            <p style={{ color: "var(--text-tertiary)", fontSize: 11, margin: "0 0 8px" }}>Request ID: {customers.requestId}</p>
          )}
          <Btn variant="ghost" onClick={customers.refetch}>Retry</Btn>
        </Card>
      ) : (
        <>
          <DataTable
            loading={customers.loading}
            rows={(customers.data?.items ?? []) as unknown as Record<string, unknown>[]}
            emptyText="No Home Services customers match this view."
            onRowClick={row => router.push(`/admin/home-services/customers/${(row as Record<string, unknown>).customer_id}`)}
            columns={[
              { key: "name", label: "Customer", render: (v, row) => v ? String(v) : String((row as Record<string, unknown>).customer_id).slice(0, 8) },
              { key: "is_active", label: "Activity", render: v => <Badge variant={v ? "success" : "default"}>{v ? "Active" : "Inactive"}</Badge> },
              { key: "completed_jobs", label: "Completed Jobs" },
              { key: "services_used_count", label: "Services Used" },
              { key: "providers_used_count", label: "Providers Used" },
              { key: "payment_reliability", label: "Payment Reliability", render: v => (
                <Badge variant={v === "reliable" ? "success" : v === "needs_review" ? "warning" : "default"}>
                  {String(v).replace(/_/g, " ")}
                </Badge>
              ) },
              { key: "repeat_status", label: "Repeat Status", render: v => <Badge variant={v === "repeat" ? "success" : "default"}>{String(v).replace(/_/g, " ")}</Badge> },
              { key: "last_activity_at", label: "Last Activity", render: v => dt(v as string) },
              { key: "customer_id", label: "Actions", render: v => (
                <span onClick={e => e.stopPropagation()}>
                  <Btn variant="ghost" onClick={() => router.push(`/admin/home-services/customers/${v}`)}>View 360°</Btn>
                </span>
              ) },
            ]}
          />
          <Pagination page={page} total={customers.data?.total ?? 0} pageSize={20} onPage={p => setListState({ page: p })} />
        </>
      )}

      <Modal open={defsOpen} onClose={() => setDefsOpen(false)} title="Metric Definitions" size="lg">
        <DefinitionsPanel />
      </Modal>
    </AdminLayout>
  );
}

function DefinitionsPanel() {
  const defs = useApi(useCallback(() => hsCustomerDirectoryApi.getMetricDefinitions(), []));
  if (defs.loading) return <Skeleton height={200} />;
  const d = defs.data as Record<string, unknown> | undefined;
  if (!d) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 12 }}>
      {Object.entries(d).map(([key, value]) => (
        <div key={key}>
          <div style={{ fontWeight: 700, textTransform: "uppercase", fontSize: 10, color: "var(--text-tertiary)" }}>{key.replace(/_/g, " ")}</div>
          <div>{String(value)}</div>
        </div>
      ))}
    </div>
  );
}
