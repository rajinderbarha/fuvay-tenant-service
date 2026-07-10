/**
 * FRONTEND-CONNECT-01 — Admin API module stubs (super-admin).
 *
 * Thin named wrappers requested by the spec, wired to REAL existing
 * endpoints/methods already in ../api.ts (verified against the actual
 * function names below — nothing fictional). All go through apiFetch
 * internally via the existing typed API objects — no direct fetch().
 */
import {
  catalogApi, dashboardApi, homeServicesCatalogConsoleApi, autoPriceOptionsApi,
  usageCreditsAdminApi, adminTenantApi, platformUsersApi,
} from "../api";

/** No single "overview" endpoint exists yet; composes the two real endpoints
 *  that already back the /admin/home-services/* pages and the executive
 *  dashboard's home-services summary. */
export async function getAdminHomeServicesOverview() {
  const [homeServicesSummary, services] = await Promise.all([
    dashboardApi.getHomeServicesSummary(),
    homeServicesCatalogConsoleApi.listServices(),
  ]);
  return { homeServicesSummary, services };
}

export const getAdminServiceCatalog = () => homeServicesCatalogConsoleApi.listServices();

export const getAdminPricingRules = (params?: { q?: string; vertical_type?: string; status?: string }) =>
  catalogApi.getCategoryOptions(params);

export const getAdminMatchingDiagnostics = (data: Parameters<typeof autoPriceOptionsApi.runMatchingDiagnostics>[0]) =>
  autoPriceOptionsApi.runMatchingDiagnostics(data);

export const getAdminCompletedJobDeductions = (tenantId: string) =>
  usageCreditsAdminApi.getTenantLedger(tenantId);

export const getAdminUsageCredits = (tenantId: string) =>
  usageCreditsAdminApi.getTenantLedger(tenantId);

export const getAdminTenantDetail = (tenantId: string) => adminTenantApi.get(tenantId);

export const getAdminAudit = (params?: { actionType?: string; page?: number; limit?: number }) =>
  platformUsersApi.auditLogs(params?.actionType, params?.page, params?.limit);
