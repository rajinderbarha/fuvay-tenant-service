// ═══════════════════════════════════════════════════════════════════════════
// Tenant Help & Support workspace — /v1/tenant/support/*
//
// Real bug fixed here: app/(tenant)/help-support/page.tsx has always
// imported `supportApi` plus seven types from lib/api, but none of them were
// ever implemented -- so the page could not compile and the tenant-portal
// production build failed.
//
// Every path below is matched against a real route in the live OpenAPI
// schema (app/engines/support/tenant_router.py).
// ═══════════════════════════════════════════════════════════════════════════
import { apiFetch } from "./api";

/**
 * TRADEOFF, deliberately made and worth revisiting:
 *
 * These workspace payloads are large, backend-shaped and tab-specific, and
 * the calling page already declares the slices it renders. A permissive
 * element type restores exactly the contract the page was written against
 * without this client guessing at hundreds of field names that would drift
 * from the backend on the next change.
 *
 * It does NOT give compile-time checking of these payloads -- and this
 * session proved that matters: a `public_badges` shape mismatch in the
 * CUSTOMER app silently broke Booking Review because a schema claimed
 * `string[]` where the backend sent objects. The durable fix is the same one
 * used there: validate real captured payloads against real schemas in a
 * test. That is follow-up work, not something to fake with guessed fields.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SupportPayload = any;

export type SupportRequestRow = SupportPayload;
export type SupportRequestDetail = SupportPayload;
export type SupportWorkspace = SupportPayload;
export type SupportKnowledge = SupportPayload;
export type SupportArticle = SupportPayload;
export type SupportAnnouncementItem = SupportPayload;
export type SupportServiceStatus = SupportPayload;

const BASE = "/v1/tenant/support";

function post(body?: unknown): RequestInit {
  return { method: "POST", body: JSON.stringify(body ?? {}) };
}

function query(params?: Record<string, string | number | boolean | undefined>): string {
  if (!params) return "";
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (entries.length === 0) return "";
  return `?${new URLSearchParams(Object.fromEntries(entries.map(([k, v]) => [k, String(v)])))}`;
}

export const supportApi = {
  /** The workspace bundle powering the landing tab (open tickets, SLA, etc). */
  workspace: <T = SupportWorkspace>() => apiFetch<T>(`${BASE}/workspace`),
  serviceStatus: <T = SupportServiceStatus>() => apiFetch<T>(`${BASE}/service-status`),

  // ── Requests (tickets) ──────────────────────────────────────────────────
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  listRequests: <T = SupportPayload>(params?: Record<string, any>) =>
    apiFetch<T>(`${BASE}/requests${query(params)}`),
  getRequest: <T = SupportRequestDetail>(ticketId: string) =>
    apiFetch<T>(`${BASE}/requests/${ticketId}`),
  createRequest: <T = SupportRequestDetail>(payload: Record<string, unknown>) =>
    apiFetch<T>(`${BASE}/requests`, post(payload)),
  /** Adds a message to an existing thread (backend: .../messages). */
  reply: <T = SupportPayload>(ticketId: string, message: string) =>
    apiFetch<T>(`${BASE}/requests/${ticketId}/messages`, post({ message })),
  reopen: <T = SupportPayload>(ticketId: string, reason?: string) =>
    apiFetch<T>(`${BASE}/requests/${ticketId}/reopen`, post({ reason: reason ?? "" })),
  confirmResolution: <T = SupportPayload>(ticketId: string, payload?: Record<string, unknown>) =>
    apiFetch<T>(`${BASE}/requests/${ticketId}/confirm-resolution`, post(payload)),
  escalate: <T = SupportPayload>(ticketId: string, reason?: string) =>
    apiFetch<T>(`${BASE}/requests/${ticketId}/escalate`, post({ reason: reason ?? "" })),

  /** Critical incidents are a separate, higher-priority intake -- deliberately
   * NOT folded into createRequest, because the backend routes them
   * differently and the distinction is the whole point of the surface. */
  reportCriticalIncident: <T = SupportPayload>(payload: Record<string, unknown>) =>
    apiFetch<T>(`${BASE}/critical-incident`, post(payload)),

  // ── Knowledge base ──────────────────────────────────────────────────────
  /** The page filters by free-text `search` and by product `area`; both are
   * passed straight through as the backend's own query params. */
  knowledge: <T = SupportKnowledge>(params?: { search?: string; area?: string; q?: string; category?: string }) =>
    apiFetch<T>(`${BASE}/knowledge${query(params)}`),
  articleFeedback: <T = SupportPayload>(articleId: string, helpful: boolean, comment?: string) =>
    apiFetch<T>(`${BASE}/knowledge/${articleId}/feedback`, post({ helpful, comment: comment ?? "" })),

  // ── Announcements ───────────────────────────────────────────────────────
  announcements: <T = SupportPayload>() => apiFetch<T>(`${BASE}/announcements`),
  acknowledgeAnnouncement: <T = SupportPayload>(announcementId: string) =>
    apiFetch<T>(`${BASE}/announcements/${announcementId}/acknowledge`, post()),
};
