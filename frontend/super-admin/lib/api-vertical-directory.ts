// ═══════════════════════════════════════════════════════════════════════════
// Vertical Directory — /v1/admin/verticals/{vertical}/...
//
// Every route below is matched one-for-one against
// app/engines/vertical_directory/admin_router.py.
// ═══════════════════════════════════════════════════════════════════════════
import { apiFetch } from "./api";

/** Paged list envelope used by every directory list route. */
export interface VerticalDirectoryPage<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

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

type DirRow = AdminPayload;

function _vdQuery(params?: Record<string, string | number | undefined>): string {
  if (!params) return "";
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (entries.length === 0) return "";
  return `?${new URLSearchParams(Object.fromEntries(entries.map(([k, v]) => [k, String(v)])))}`;
}

const _vdBase = (vertical: string) => `/v1/admin/verticals/${encodeURIComponent(vertical)}`;

/** Every mutating staff action takes the same `{ reason }` body. */
function _vdReason(reason: string): RequestInit {
  return { method: "POST", body: JSON.stringify({ reason: reason ?? "" }) };
}

export const verticalDirectoryApi = {
  // ── Providers ───────────────────────────────────────────────────────────
  listProviders: <T = DirRow>(vertical: string, params?: { search?: string; status?: string; page?: number; page_size?: number }) =>
    apiFetch<T>(`${_vdBase(vertical)}/providers${_vdQuery(params)}`),
  providersSummary: <T = DirRow>(vertical: string) =>
    apiFetch<T>(`${_vdBase(vertical)}/providers/summary`),
  getProvider: <T = DirRow>(vertical: string, tenantId: string) =>
    apiFetch<T>(`${_vdBase(vertical)}/providers/${tenantId}`),

  // ── Staff ───────────────────────────────────────────────────────────────
  listStaff: <T = DirRow>(vertical: string, params?: {
    search?: string; verification_status?: string; assignment_status?: string;
    availability?: string; page?: number; page_size?: number;
  }) => apiFetch<T>(`${_vdBase(vertical)}/staff${_vdQuery(params)}`),
  staffSummary: <T = DirRow>(vertical: string) =>
    apiFetch<T>(`${_vdBase(vertical)}/staff/summary`),
  /** Returns the same paged envelope as `listStaff`, just with a large
   * page_size -- callers build CSV from `.items`. */
  exportStaff: <T = DirRow>(vertical: string) =>
    apiFetch<T>(`${_vdBase(vertical)}/staff/export`),
  getStaff: <T = DirRow>(vertical: string, staffId: string) =>
    apiFetch<T>(`${_vdBase(vertical)}/staff/${staffId}`),
  getStaffCapabilities: <T = DirRow>(vertical: string, staffId: string) =>
    apiFetch<T>(`${_vdBase(vertical)}/staff/${staffId}/capabilities`),
  getStaffWorkload: <T = DirRow>(vertical: string, staffId: string) =>
    apiFetch<T>(`${_vdBase(vertical)}/staff/${staffId}/workload`),
  getStaffPerformance: <T = DirRow>(vertical: string, staffId: string) =>
    apiFetch<T>(`${_vdBase(vertical)}/staff/${staffId}/performance`),
  getStaffActivity: <T = DirRow>(vertical: string, staffId: string) =>
    apiFetch<T>(`${_vdBase(vertical)}/staff/${staffId}/activity`),

  staffRequestChanges: <T = DirRow>(vertical: string, staffId: string, reason: string) =>
    apiFetch<T>(`${_vdBase(vertical)}/staff/${staffId}/request-changes`, _vdReason(reason)),
  staffVerify: <T = DirRow>(vertical: string, staffId: string, reason: string) =>
    apiFetch<T>(`${_vdBase(vertical)}/staff/${staffId}/verify`, _vdReason(reason)),
  staffReject: <T = DirRow>(vertical: string, staffId: string, reason: string) =>
    apiFetch<T>(`${_vdBase(vertical)}/staff/${staffId}/reject`, _vdReason(reason)),
  staffRestrict: <T = DirRow>(vertical: string, staffId: string, reason: string) =>
    apiFetch<T>(`${_vdBase(vertical)}/staff/${staffId}/restrict`, _vdReason(reason)),
  staffSuspend: <T = DirRow>(vertical: string, staffId: string, reason: string) =>
    apiFetch<T>(`${_vdBase(vertical)}/staff/${staffId}/suspend`, _vdReason(reason)),
  staffReactivate: <T = DirRow>(vertical: string, staffId: string, reason: string) =>
    apiFetch<T>(`${_vdBase(vertical)}/staff/${staffId}/reactivate`, _vdReason(reason)),

  // ── Customers ───────────────────────────────────────────────────────────
  listCustomers: <T = DirRow>(vertical: string, params?: { search?: string; page?: number; page_size?: number }) =>
    apiFetch<T>(`${_vdBase(vertical)}/customers${_vdQuery(params)}`),
  customersSummary: <T = DirRow>(vertical: string) =>
    apiFetch<T>(`${_vdBase(vertical)}/customers/summary`),
  getCustomer: <T = DirRow>(vertical: string, customerId: string) =>
    apiFetch<T>(`${_vdBase(vertical)}/customers/${customerId}`),
};
