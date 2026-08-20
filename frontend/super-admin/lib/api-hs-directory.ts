// ═══════════════════════════════════════════════════════════════════════════
// Home Services directories + dashboard (admin)
//   /v1/admin/home-services/customers
//   /v1/admin/home-services/providers
//   /v1/admin/home-services/dashboard
//
// Real bug fixed here: the Home Services customer/provider directory pages
// and dashboard have always imported `hsCustomerDirectoryApi`,
// `hsProviderDirectoryApi` and `hsDashboardApi`, but none of them were ever
// implemented -- so those pages could not compile and the super-admin
// production build failed. Routes matched against
// app/engines/tenant_engine/hs_{customer,provider}_directory_router.py and
// hs_dashboard_router.py.
// ═══════════════════════════════════════════════════════════════════════════
import { apiFetch } from "./api";

/**
 * TRADEOFF, deliberately made and worth revisiting:
 *
 * These admin surfaces return large, backend-shaped analytics payloads that
 * differ per tab. The calling pages ALREADY declare and assert their own
 * shapes (e.g. `OverviewData` in the Finance page, `Row` in the directory
 * workspaces) -- so the shape contract lives next to the code that depends
 * on it, which is the right place for it.
 *
 * A permissive default here restores exactly the contract those pages were
 * written against. It does NOT give compile-time checking of these
 * payloads -- and this session proved that matters: a `public_badges`
 * shape mismatch in the CUSTOMER app silently broke Booking Review because
 * a schema said `string[]` where the backend sent objects.
 *
 * The durable fix for these admin surfaces is the same one used there:
 * validate real captured payloads against real schemas in a test. That is
 * follow-up work, not something to fake with hand-guessed field lists.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AdminPayload = any;

type HsRow = AdminPayload;

function _hsdQuery(params?: Record<string, string | number | undefined>): string {
  if (!params) return "";
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (entries.length === 0) return "";
  return `?${new URLSearchParams(Object.fromEntries(entries.map(([k, v]) => [k, String(v)])))}`;
}

const CUSTOMERS = "/v1/admin/home-services/customers";
const PROVIDERS = "/v1/admin/home-services/providers";
const DASHBOARD = "/v1/admin/home-services/dashboard";

export const hsCustomerDirectoryApi = {
  /** Metric definitions power the "what does this number mean?" tooltips --
   * they are authored backend-side so admin and tenant never disagree. */
  getMetricDefinitions: <T = HsRow>() => apiFetch<T>(`${CUSTOMERS}/metric-definitions`),
  getSummary: <T = HsRow>() => apiFetch<T>(`${CUSTOMERS}/summary`),
  list: <T = HsRow>(params?: {
    q?: string;
    /** Backend enforces `^(active|inactive)$`. */
    activity?: string;
    /** Backend enforces `^(repeat|one_time|none)$`. */
    repeat_status?: string;
    page?: number; page_size?: number; pageSize?: number;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    [key: string]: any;
  }) => apiFetch<T>(`${CUSTOMERS}${_hsdQuery(params)}`),

  getDetail: <T = HsRow>(customerId: string) => apiFetch<T>(`${CUSTOMERS}/${customerId}`),
  getJobs: <T = HsRow>(customerId: string) => apiFetch<T>(`${CUSTOMERS}/${customerId}/jobs`),
  getComplaints: <T = HsRow>(customerId: string) => apiFetch<T>(`${CUSTOMERS}/${customerId}/complaints`),
  getPayments: <T = HsRow>(customerId: string) => apiFetch<T>(`${CUSTOMERS}/${customerId}/payments`),
  getActivity: <T = HsRow>(customerId: string) => apiFetch<T>(`${CUSTOMERS}/${customerId}/activity`),
  getReviews: <T = HsRow>(customerId: string) => apiFetch<T>(`${CUSTOMERS}/${customerId}/reviews`),
  getAddresses: <T = HsRow>(customerId: string) => apiFetch<T>(`${CUSTOMERS}/${customerId}/addresses`),
};

export const hsProviderDirectoryApi = {
  getSummary: <T = HsRow>(q?: string) => apiFetch<T>(`${PROVIDERS}/summary${_hsdQuery({ q })}`),
  list: <T = HsRow>(params?: {
    q?: string; status?: string;
    /** Comma-separated, e.g. "suspended,archived". */
    status_in?: string;
    verification_status?: string;
    city?: string; state?: string; health_band?: string;
    page?: number; page_size?: number; pageSize?: number;
    sort_by?: string; sort_dir?: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    [key: string]: any;
  }) => apiFetch<T>(`${PROVIDERS}${_hsdQuery(params)}`),
  getDetail: <T = HsRow>(providerId: string) => apiFetch<T>(`${PROVIDERS}/${providerId}`),
  getFinance: <T = HsRow>(providerId: string) => apiFetch<T>(`${PROVIDERS}/${providerId}/finance`),
  getQuality: <T = HsRow>(providerId: string, params?: { page?: number; page_size?: number }) => apiFetch<T>(`${PROVIDERS}/${providerId}/quality${_hsdQuery(params)}`),
  getTeam: <T = HsRow>(providerId: string, params?: { page?: number; page_size?: number }) => apiFetch<T>(`${PROVIDERS}/${providerId}/team${_hsdQuery(params)}`),
  getOperations: <T = HsRow>(providerId: string, params?: { page?: number; page_size?: number }) => apiFetch<T>(`${PROVIDERS}/${providerId}/operations${_hsdQuery(params)}`),
  getActivity: <T = HsRow>(providerId: string, params?: { page?: number; page_size?: number }) => apiFetch<T>(`${PROVIDERS}/${providerId}/activity${_hsdQuery(params)}`),
  getServices: <T = HsRow>(providerId: string) => apiFetch<T>(`${PROVIDERS}/${providerId}/services`),
};

export const hsDashboardApi = {
  getCustomerIntelligence: <T = HsRow>() => apiFetch<T>(`${DASHBOARD}/customer-intelligence`),
  getOperationalMetrics: <T = HsRow>() => apiFetch<T>(`${DASHBOARD}/operational-metrics`),
};
