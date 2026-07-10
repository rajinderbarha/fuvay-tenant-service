"use client";
/**
 * FRONTEND-CONNECT-01 — PART 12 smoke page: Admin Home Services Overview.
 * Spec route: /admin/home-services/overview. No pre-existing equivalent page
 * existed under app/admin/home-services/ (that directory has 10 sibling pages
 * — booking-drafts, pricing-rules, service-catalog, etc. — but no "overview"
 * landing page), so this is a genuinely new route built on the new foundation:
 * central apiFetch (via dashboardApi/homeServicesCatalogConsoleApi), the new
 * getAdminHomeServicesOverview() module stub, ApiLoadingState/ApiErrorState/
 * ApiEmptyState, and safe* normalization. No mock/static runtime data.
 */
import React, { useCallback } from "react";
import Link from "next/link";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { useApi } from "../../../../hooks/useApi";
import { getAdminHomeServicesOverview } from "../../../../lib/api-foundation/admin-modules";
import { ApiLoadingState, ApiErrorState, ApiEmptyState } from "../../../../components/shared/ApiStates";
import { safeNumber, safeText } from "../../../../lib/api-foundation/normalize";
import { SectionHeader, Card, StatCard, Badge } from "../../../../components/shared/ui";
import { Wrench, Layers, MapPin, Gauge, Zap, Wallet } from "lucide-react";

export default function AdminHomeServicesOverviewPage() {
  const overviewApi = useApi(useCallback(() => getAdminHomeServicesOverview(), []));
  const summary = overviewApi.data?.homeServicesSummary ?? null;
  const services = overviewApi.data?.services ?? null;
  const serviceCount = Array.isArray((services as { services?: unknown[] })?.services)
    ? (services as { services: unknown[] }).services.length
    : 0;

  return (
    <AdminLayout>
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <SectionHeader
          icon={<Wrench/>}
          title="Home Services Overview"
          subtitle="Platform-wide health snapshot for the Home Services vertical — catalog, pricing, coverage, and matching readiness."
        />

        {overviewApi.loading && <ApiLoadingState rows={4}/>}

        {overviewApi.error && !overviewApi.loading && (
          <ApiErrorState
            error={{ code: "OVERVIEW_LOAD_FAILED", message: overviewApi.error, request_id: overviewApi.requestId ?? undefined }}
            onRetry={overviewApi.refetch}
          />
        )}

        {!overviewApi.loading && !overviewApi.error && !summary && (
          <ApiEmptyState
            title="No Home Services data available yet"
            description="Once tenants publish services in this vertical, platform-wide metrics will appear here."
          />
        )}

        {summary && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
              <StatCard label="Home Services Providers" value={safeNumber(summary.home_services_providers)} icon={<Layers/>}/>
              <StatCard label="Bookable Providers" value={safeNumber(summary.bookable_providers)} icon={<Zap/>}
                trend={safeNumber(summary.bookable_providers) > 0 ? "up" : "neutral"}/>
              <StatCard label="Not Bookable" value={safeNumber(summary.not_bookable_providers)} icon={<Gauge/>}
                alert={safeNumber(summary.not_bookable_providers) > 0}/>
              <StatCard label="Published Tenant Services" value={safeNumber(summary.published_tenant_services)} icon={<Wallet/>}/>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
              <Card>
                <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", margin: "0 0 8px", textTransform: "uppercase" }}>Service Catalog Health</p>
                <Badge variant={summary.service_catalog_health?.status === "healthy" ? "success" : "warning"}>
                  {safeText(summary.service_catalog_health?.status)}
                </Badge>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "8px 0 0" }}>
                  {safeNumber(summary.service_catalog_health?.active_services)} active services
                  {serviceCount > 0 ? ` (${serviceCount} loaded from catalog console)` : ""}
                </p>
                <Link href="/admin/home-services/service-catalog" style={{ fontSize: 12, color: "var(--accent)" }}>Manage Catalog →</Link>
              </Card>
              <Card>
                <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", margin: "0 0 8px", textTransform: "uppercase" }}>Pricing Rule Health</p>
                <Badge variant={summary.pricing_rule_health?.status === "healthy" ? "success" : "warning"}>
                  {safeText(summary.pricing_rule_health?.status)}
                </Badge>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "8px 0 0" }}>
                  {safeNumber(summary.pricing_rule_health?.active_rules)} active rules
                </p>
                <Link href="/admin/home-services/pricing-rules" style={{ fontSize: 12, color: "var(--accent)" }}>Manage Pricing →</Link>
              </Card>
              <Card>
                <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", margin: "0 0 8px", textTransform: "uppercase" }}>
                  <MapPin size={12} style={{ display: "inline", marginRight: 4 }}/>Service Area Coverage
                </p>
                <Badge variant={summary.service_area_coverage_health?.status === "healthy" ? "success" : "warning"}>
                  {safeText(summary.service_area_coverage_health?.status)}
                </Badge>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "8px 0 0" }}>
                  {safeNumber(summary.service_area_coverage_health?.active_areas)} active areas,{" "}
                  {safeNumber(summary.service_area_coverage_health?.tenants_without_areas)} tenants without coverage
                </p>
                <Link href="/admin/home-services/service-areas" style={{ fontSize: 12, color: "var(--accent)" }}>Manage Areas →</Link>
              </Card>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
              <Card>
                <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", margin: "0 0 8px" }}>Provider Matching</p>
                <p style={{ fontSize: 14, fontWeight: 600 }}>{safeText(summary.provider_matching_health)}</p>
                <Link href="/admin/home-services/matching-diagnostics" style={{ fontSize: 12, color: "var(--accent)" }}>Run Diagnostics →</Link>
              </Card>
              <Card>
                <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", margin: "0 0 8px" }}>Auto Price Options</p>
                <p style={{ fontSize: 14, fontWeight: 600 }}>{safeText(summary.auto_price_options_health)}</p>
                <Link href="/admin/home-services/price-experience" style={{ fontSize: 12, color: "var(--accent)" }}>Preview →</Link>
              </Card>
              <Card>
                <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", margin: "0 0 8px" }}>Completed Job Deduction</p>
                <p style={{ fontSize: 14, fontWeight: 600 }}>{safeText(summary.completed_job_deduction_health)}</p>
                <Link href="/admin/home-services/completed-job-deduction" style={{ fontSize: 12, color: "var(--accent)" }}>View →</Link>
              </Card>
            </div>
          </>
        )}
      </div>
    </AdminLayout>
  );
}
