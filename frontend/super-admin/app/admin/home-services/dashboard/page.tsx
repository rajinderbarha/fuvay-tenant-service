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
import { Card, Badge, Skeleton, SectionHeader, SummaryCard, KpiGrid } from "../../../../components/shared/ui";
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
      <SectionHeader
        eyebrow="Home Services command center"
        context="Operations"
        title="Home Services Dashboard"
        subtitle="Operational health and customer intelligence for Home Services."
      />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: 0 }}>
          Customer Intelligence
        </h2>
        {customerIntel.error && !isVerticalDisabled(customerIntel.error) && (
          <Badge variant="danger">Unavailable — {customerIntel.error}</Badge>
        )}
      </div>
      {customerIntel.loading ? (
        <KpiGrid minCardWidth={170} style={{ marginBottom: "var(--layout-page-gap)" }}>
          {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} height={126} />)}
        </KpiGrid>
      ) : customerIntel.error && !isVerticalDisabled(customerIntel.error) ? null : (
        <KpiGrid minCardWidth={170} style={{ marginBottom: "var(--layout-page-gap)" }}>
          <SummaryCard label="Total Customers" value={c?.total_customers as number} onClick={() => goCustomers()} />
          <SummaryCard label={`Active · ${c?.active_window_days ?? 90} days`} value={c?.active_customers as number} tone="success" onClick={() => goCustomers("activity=active")} />
          <SummaryCard label={`New · ${c?.new_customer_window_days ?? 30} days`} value={c?.new_customers as number} onClick={() => goCustomers()} />
          <SummaryCard label="Repeat Customers" value={c?.repeat_customers as number} onClick={() => goCustomers("repeat_status=repeat")} />
          <SummaryCard label="Returning Rate" value={c ? `${c.returning_rate}%` : undefined} onClick={() => goCustomers()} />
          <SummaryCard label="Multi-service Customers" value={c?.multi_service_customers as number} onClick={() => goCustomers()} />
          <SummaryCard label="Payment Review" value={c?.payment_review_available ? (c?.payment_review as number) : "N/A"} tone="warning" onClick={() => goCustomers()} />
          <SummaryCard label="Open Complaints" value={c?.open_complaints as number} tone="danger" onClick={() => goCustomers()} />
        </KpiGrid>
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
        <KpiGrid minCardWidth={170}>
          {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} height={126} />)}
        </KpiGrid>
      ) : ops.error && !isVerticalDisabled(ops.error) ? null : (
        <KpiGrid minCardWidth={170}>
          <SummaryCard label="Active Providers" value={o?.active_providers as number} />
          <SummaryCard label="Available Staff" value={o?.available_staff as number} />
          <SummaryCard label="Active Jobs" value={o?.active_jobs as number} />
          <SummaryCard label="Unassigned Jobs" value={o?.unassigned_jobs as number} tone="warning" />
          <SummaryCard label="Jobs At Risk" value={o?.jobs_at_risk_available ? (o?.jobs_at_risk as number) : "N/A"} tone="warning" />
          <SummaryCard label="SLA Breached" value={o?.sla_breached_available ? (o?.sla_breached as number) : "N/A"} tone="danger" />
          <SummaryCard label="Open Complaints" value={o?.open_complaints as number} tone="danger" />
          <SummaryCard label="Pending Quotes" value={o?.pending_quotes as number} />
        </KpiGrid>
      )}
    </AdminLayout>
  );
}
