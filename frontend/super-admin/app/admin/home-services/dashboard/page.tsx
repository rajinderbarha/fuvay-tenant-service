"use client";
/**
 * Home Services Dashboard — category-specific, NOT a modification of the
 * generic platform /admin/dashboard. Backend-gated by
 * require_vertical_enabled("home_services") -- every card request 403s if
 * Home Services is disabled, and the frontend surfaces that as a distinct
 * "vertical disabled" state, never a fabricated empty dashboard.
 *
 * Customer Intelligence cards reuse HomeServicesCustomerDirectoryService.
 * get_summary() verbatim (same engine, same numbers as /admin/home-services/
 * customers) -- this page never recomputes those metrics independently.
 * Each card deep-links to the exact matching filter on that page.
 */
import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Skeleton } from "../../../../components/shared/ui";
import { hsDashboardApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

export default function HomeServicesDashboardPage() {
  const router = useRouter();
  const customerIntel = useApi(useCallback(() => hsDashboardApi.getCustomerIntelligence(), []));
  const ops = useApi(useCallback(() => hsDashboardApi.getOperationalMetrics(), []));

  const c = customerIntel.data as Record<string, unknown> | undefined;
  const o = ops.data as Record<string, unknown> | undefined;

  function goCustomers(query?: string) {
    router.push(`/admin/home-services/customers${query ? `?${query}` : ""}`);
  }

  // VerticalDisabledException's detail is "This business vertical
  // ('home_services') is currently unavailable." -- matched by message text
  // since useApi only exposes .message, not the structured error_code.
  const isVerticalDisabled = (err: string | null) =>
    !!err && err.toLowerCase().includes("currently unavailable");

  if (isVerticalDisabled(customerIntel.error) || isVerticalDisabled(ops.error)) {
    return (
      <AdminLayout activeNav="home_services-dashboard">
        <Card padding={24}>
          <p style={{ color: "var(--warning-text, #b45309)" }}>
            Home Services is currently disabled. This dashboard is unavailable until it&apos;s re-enabled.
          </p>
        </Card>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout activeNav="home_services-dashboard">
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }}>Home Services Dashboard</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
          Operational health and customer intelligence for Home Services.
        </p>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: 0 }}>
          Customer Intelligence
        </h2>
        {customerIntel.error && !isVerticalDisabled(customerIntel.error) && (
          <Badge variant="danger">Unavailable — {customerIntel.error}</Badge>
        )}
      </div>
      {customerIntel.loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, marginBottom: 24 }}>
          {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} height={70} />)}
        </div>
      ) : customerIntel.error && !isVerticalDisabled(customerIntel.error) ? null : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, marginBottom: 24 }}>
          <DashCard label="Total Customers" value={c?.total_customers as number} onClick={() => goCustomers()} />
          <DashCard label={`Active · ${c?.active_window_days ?? 90} days`} value={c?.active_customers as number} tone="success" onClick={() => goCustomers("activity=active")} />
          <DashCard label={`New · ${c?.new_customer_window_days ?? 30} days`} value={c?.new_customers as number} onClick={() => goCustomers()} />
          <DashCard label="Repeat Customers" value={c?.repeat_customers as number} onClick={() => goCustomers("repeat_status=repeat")} />
          <DashCard label="Returning Rate" value={c ? `${c.returning_rate}%` : undefined} onClick={() => goCustomers()} />
          <DashCard label="Multi-service Customers" value={c?.multi_service_customers as number} onClick={() => goCustomers()} />
          <DashCard label="Payment Review" value={c?.payment_review_available ? (c?.payment_review as number) : "N/A"} tone="warning" onClick={() => goCustomers()} />
          <DashCard label="Open Complaints" value={c?.open_complaints as number} tone="danger" onClick={() => goCustomers()} />
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: 0 }}>
          Operations
        </h2>
        {ops.error && !isVerticalDisabled(ops.error) && (
          <Badge variant="danger">Unavailable — {ops.error}</Badge>
        )}
      </div>
      {ops.loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
          {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} height={70} />)}
        </div>
      ) : ops.error && !isVerticalDisabled(ops.error) ? null : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
          <DashCard label="Active Providers" value={o?.active_providers as number} />
          <DashCard label="Available Staff" value={o?.available_staff as number} />
          <DashCard label="Active Jobs" value={o?.active_jobs as number} />
          <DashCard label="Unassigned Jobs" value={o?.unassigned_jobs as number} tone="warning" />
          <DashCard label="Jobs At Risk" value={o?.jobs_at_risk_available ? (o?.jobs_at_risk as number) : "N/A"} tone="warning" />
          <DashCard label="SLA Breached" value={o?.sla_breached_available ? (o?.sla_breached as number) : "N/A"} tone="danger" />
          <DashCard label="Open Complaints" value={o?.open_complaints as number} tone="danger" />
          <DashCard label="Pending Quotes" value={o?.pending_quotes as number} />
        </div>
      )}
    </AdminLayout>
  );
}

function DashCard({ label, value, tone, onClick }: { label: string; value?: number | string; tone?: "success" | "warning" | "danger"; onClick?: () => void }) {
  const color = tone === "danger" ? "var(--danger-text, #b91c1c)" : tone === "warning" ? "var(--warning-text, #b45309)" : tone === "success" ? "var(--success-text, #0a7c3f)" : "var(--text-primary)";
  return (
    <Card padding={14} onClick={onClick} hover={!!onClick}>
      <div style={{ fontSize: 22, fontWeight: 800, color }}>{value === undefined ? <Skeleton width={40} height={22} /> : value}</div>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>{label}</div>
    </Card>
  );
}
