/**
 * ServiceOS Customer App — API Client
 *
 * UX-06 ROUND 1 CORRECTION: the prior scaffold pointed at a plausible-looking
 * but almost entirely FAKE endpoint surface (/v1/auth/customer/otp-request,
 * /v1/services/categories, /v1/reviews, /v1/chat/rooms, /v1/commerce/customers/{id}/addresses,
 * /v1/settings/{id}/preferences, /v1/help/faqs, /v1/payments/customers/*, none of which
 * exist in the live backend openapi.json). This file has been re-pointed at the REAL
 * customer-facing namespace found in the live backend (verified against openapi.json,
 * curl http://localhost:8000/openapi.json, 2026-07-20):
 *   - Auth is the SAME unified /v1/auth/login (email+password) every role uses —
 *     there is no separate customer OTP endpoint. Matches UX-05's finding for staff.
 *   - Real customer surface lives almost entirely under /v1/customer/*, /v1/me/*,
 *     and /v1/customers/me/addresses.
 *   - See docs/design/ux-06-customer-app/existing-customer-app-audit.md for the
 *     full fake-vs-real endpoint table this correction is based on.
 *
 * PROVEN LEVEL 5 conventions kept from the prior scaffold:
 *   ALL API calls through this file — no inline fetch() in screens
 *   Customer token from AsyncStorage — never hardcoded
 *   Authorization injected once in apiFetch
 *   API_BASE from EXPO_PUBLIC_API_URL env variable
 */
import AsyncStorage from "@react-native-async-storage/async-storage";

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

export const STORAGE_KEYS = {
  token:      "serviceos_customer_token",
  customerId: "serviceos_customer_id",
  name:       "serviceos_customer_name",
  phone:      "serviceos_customer_phone",
  email:      "serviceos_customer_email",
} as const;

export class ServiceOSError extends Error {
  constructor(public code:string, message:string, public resolution?:string) {
    super(message); this.name = "ServiceOSError";
  }
}

export async function getToken():      Promise<string|null> { return AsyncStorage.getItem(STORAGE_KEYS.token); }
export async function getCustomerId(): Promise<string|null> { return AsyncStorage.getItem(STORAGE_KEYS.customerId); }
export async function clearSession():  Promise<void>        { await AsyncStorage.multiRemove(Object.values(STORAGE_KEYS)); }

async function apiFetch<T>(path:string, options:RequestInit={}, skipAuth=false): Promise<T> {
  const token = await getToken();
  const headers: Record<string,string> = {
    "Content-Type":"application/json", "X-Request-Source":"customer-mobile-app",
    ...(options.headers as Record<string,string>),
  };
  if (token && !skipAuth) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let err: { error_code?:string; message?:string; resolution?:string } = {};
    try { err = await res.json(); } catch { err.message = `HTTP ${res.status}`; }
    throw new ServiceOSError(err.error_code ?? "API_ERROR", err.message ?? "Request failed.", err.resolution);
  }
  const json = await res.json();
  // ApiResponse envelope: { success, data, ... }. Some endpoints (e.g. auth/login)
  // return the payload directly inside `data` as a dict — callers destructure it.
  return (json.data !== undefined ? json.data : json) as T;
}

// ── Types ─────────────────────────────────────────────────────────────────────
export interface CustomerUser {
  id:string; name:string; phone?:string; email?:string;
}
export interface ServiceCategory {
  category_slug:string; name:string; category_type?:string; icon?:string; description?:string;
}
export interface Booking {
  id:string; booking_number?:string; service_type?:string; scheduled_at?:string; status:string;
  created_at:string; notes?:string;
}
export interface Job {
  id:string; job_number?:string; status:string; service_type?:string; created_at:string; updated_at?:string;
}

// ── Auth ──────────────────────────────────────────────────────────────────────
// Real, verified contract: POST /v1/auth/login { email, password, device_id } — the
// SAME endpoint used by every role (staff-app confirmed this pattern in UX-05). There
// is no customer-specific or phone/OTP login endpoint in the live backend today.
export const authApi = {
  login: (email:string, password:string) =>
    apiFetch<{ access_token:string; user:CustomerUser }>(
      "/v1/auth/login",
      { method:"POST", body:JSON.stringify({ email, password, device_id:"customer-mobile-app" }) }, true),
  me:     () => apiFetch<CustomerUser>("/v1/customer/profile"),
  logout: () => apiFetch<void>("/v1/auth/logout", { method:"POST" }),
};

// ── Catalog / discovery ─────────────────────────────────────────────────────────
// Real: GET /v1/customer/categories (customer-visible, active only)
export const catalogApi = {
  categories: (search?:string) =>
    apiFetch<{ items:ServiceCategory[]; total:number }>(
      `/v1/customer/categories${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  categoryOfferings: (categorySlug:string) =>
    apiFetch<unknown>(`/v1/customer/categories/${encodeURIComponent(categorySlug)}/offerings`),
};

// ── Bookings (Booking→field_ops.Job pipeline) ───────────────────────────────────
// Real: /v1/customer/bookings*. NOTE distinct from the ServiceBooking→ServiceJob
// pipeline surfaced separately below — never merged, per UX-04's pipeline-separation rule.
export const bookingsApi = {
  list:   () => apiFetch<{ items:Booking[]; total:number }>("/v1/customer/bookings"),
  get:    (id:string) => apiFetch<Booking>(`/v1/customer/bookings/${id}`),
  tracking: (id:string) => apiFetch<unknown>(`/v1/customer/bookings/${id}/tracking`),
  // Cancellation/reschedule endpoints exist server-side but per the UX-06 brief's
  // canonical rule, cancellation/reschedule remains UNRESOLVED for exposure — no
  // active UI control calls these yet. Kept here only as a documented, unused contract.
  cancelEndpointExists: true as const,
};

// ── Service jobs (ServiceBooking→ServiceJob pipeline) ──────────────────────────
// Real: /v1/customer/jobs*, /v1/customer/service-jobs/{id}/tracking
export const serviceJobsApi = {
  list:      () => apiFetch<{ items:Job[]; total:number }>("/v1/customer/jobs"),
  get:       (id:string) => apiFetch<Job>(`/v1/customer/jobs/${id}`),
  progress:  (id:string) => apiFetch<unknown>(`/v1/customer/jobs/${id}/progress`),
  tracking:  (id:string) => apiFetch<unknown>(`/v1/customer/service-jobs/${id}/tracking`),
};

// ── My activity (unified booking/job/appointment/lead feed) ────────────────────
export const myActivityApi = {
  summary:  () => apiFetch<unknown>("/v1/customer/my-activity"),
  bookings: () => apiFetch<unknown>("/v1/customer/my-activity/bookings"),
};

// ── Reviews — CANONICAL customer_reviews engine only. Legacy /v1/reviews is a
// dead route (returns 410 per repo memory) — never call it. ────────────────────
export interface Review { id:string; job_id?:string; rating?:number; comment?:string; status:string; created_at:string; }
export const reviewsApi = {
  eligibility: () => apiFetch<unknown>("/v1/customer/reviews/eligibility"),
  list:        () => apiFetch<{ items:Review[] }>("/v1/customer/reviews"),
  get:         (id:string) => apiFetch<Review>(`/v1/customer/reviews/${id}`),
};

// ── Chat (customer↔provider/staff thread — distinct from AI conversation) ──────
// Real: /v1/customer/chat/threads*
export interface ChatThread   { thread_id:string; last_message?:string; last_message_at?:string; unread_count?:number; }
export interface ChatMessage  { id:string; thread_id:string; sender_id?:string; content:string; sent_at:string; is_read?:boolean; }
export const chatApi = {
  listThreads: () => apiFetch<{ items:ChatThread[] }>("/v1/customer/chat/threads"),
  getMessages: (threadId:string) => apiFetch<{ items:ChatMessage[] }>(`/v1/customer/chat/threads/${threadId}/messages`),
  sendMessage: (threadId:string, content:string) =>
    apiFetch<ChatMessage>(`/v1/customer/chat/threads/${threadId}/messages`, { method:"POST", body:JSON.stringify({ content }) }),
  markRead: (threadId:string) => apiFetch<void>(`/v1/customer/chat/threads/${threadId}/read`, { method:"POST" }),
};

// ── Profile ───────────────────────────────────────────────────────────────────
// Real: /v1/customer/profile and /v1/me/profile (both exist — /v1/customer/profile used
// as the primary customer-role surface).
export const profileApi = {
  get:    () => apiFetch<CustomerUser>("/v1/customer/profile"),
  update: (payload:Partial<Pick<CustomerUser,"name"|"phone"|"email">>) =>
    apiFetch<CustomerUser>("/v1/customer/profile", { method:"PUT", body:JSON.stringify(payload) }),
};

// ── Notifications ─────────────────────────────────────────────────────────────
// Real: /v1/customer/notifications* (role-scoped, mirrors the pattern UX-05 used for
// /v1/staff/notifications).
export interface AppNotification {
  id:string; title:string; body:string; type:string;
  is_read:boolean; created_at:string; action_url?:string;
}
export const notificationsApi = {
  list:        (limit=30) => apiFetch<{ items:AppNotification[]; total:number }>(`/v1/customer/notifications?limit=${limit}`),
  unreadCount: () => apiFetch<{ count:number }>("/v1/customer/notifications/unread-count"),
  markRead:    (id:string) => apiFetch<void>(`/v1/customer/notifications/${id}/read`, { method:"POST" }),
  markAllRead: () => apiFetch<void>("/v1/customer/notifications/mark-all-read", { method:"POST" }),
};

// ── Saved addresses ──────────────────────────────────────────────────────────
// Real: /v1/customers/me/addresses (NOT /v1/commerce/customers/{id}/addresses,
// which does not exist).
export interface SavedAddress {
  id:string; label:string; address_line:string; city?:string; pincode?:string;
  lat?:number; lng?:number; is_default:boolean;
}
export const addressApi = {
  list:       () => apiFetch<{ items:SavedAddress[] }>("/v1/customers/me/addresses"),
  add:        (a:Omit<SavedAddress,"id"|"is_default">) => apiFetch<SavedAddress>("/v1/customers/me/addresses", { method:"POST", body:JSON.stringify(a) }),
  update:     (id:string, a:Partial<SavedAddress>) => apiFetch<SavedAddress>(`/v1/customers/me/addresses/${id}`, { method:"PUT", body:JSON.stringify(a) }),
  delete:     (id:string) => apiFetch<void>(`/v1/customers/me/addresses/${id}`, { method:"DELETE" }),
  setDefault: (id:string) => apiFetch<SavedAddress>(`/v1/customers/me/addresses/${id}/set-default`, { method:"POST" }),
};

// ── Quotes (post-inspection quote approval, ServiceJob pipeline only) ──────────
// Real: /v1/customer/quotes/{quote_id} (approve/reject) and /v1/customer/quotes/jobs/{job_id}
export interface Quote {
  id:string; job_id:string; status:"pending"|"approved"|"rejected"|string;
  quoted_price?:number; findings?:string; expires_at?:string;
}
export const quoteApi = {
  forJob:  (jobId:string) => apiFetch<Quote>(`/v1/customer/quotes/jobs/${jobId}`),
  get:     (quoteId:string) => apiFetch<Quote>(`/v1/customer/quotes/${quoteId}`),
  approve: (quoteId:string) => apiFetch<Quote>(`/v1/customer/quotes/${quoteId}/approve`, { method:"POST" }),
  reject:  (quoteId:string, reason:string) =>
    apiFetch<Quote>(`/v1/customer/quotes/${quoteId}/reject`, { method:"POST", body:JSON.stringify({ reason }) }),
};

// ── Service invoices (on-site payment stays outside the platform — this surface
// is READ-ONLY status + credit-apply, never card capture) ──────────────────────
export interface ServiceInvoice {
  id:string; booking_id?:string; job_id?:string; status:string;
  amount?:number; total?:number; currency?:string;
}
export const invoiceApi = {
  list: () => apiFetch<{ items:ServiceInvoice[] }>("/v1/customer/service-invoices"),
  get:  (id:string) => apiFetch<ServiceInvoice>(`/v1/customer/service-invoices/${id}`),
  // Applies existing platform Service Credit toward an invoice. This is NOT cash and
  // NOT a card-capture flow — wording must stay "Service Credit", never "refund"/"payout".
  applyCredit: (id:string, creditId:string) =>
    apiFetch<ServiceInvoice>(`/v1/customer/service-invoices/${id}/apply-credit`, { method:"POST", body:JSON.stringify({ credit_id:creditId }) }),
};

// ── Service Credit (platform credit only — never cash/withdrawable) ────────────
// Real: /v1/me/credits*
export interface ServiceCredit { id:string; amount:number; currency?:string; reason?:string; status:string; expires_at?:string; }
export const serviceCreditApi = {
  list:    () => apiFetch<{ items:ServiceCredit[] }>("/v1/me/credits"),
  summary: () => apiFetch<unknown>("/v1/me/credits/summary"),
};

// ── DeepSeek conversational booking (AI chat) ───────────────────────────────────
// Real, verified: POST /v1/customer/ai-chat/sessions (create), POST .../messages (send),
// GET .../messages (history), POST .../close. Backend proxies DeepSeek — no key in app.
// A second, separate /v1/ai/chat + /v1/ai/chat/meta generic endpoint also exists in the
// live backend (not session-based) — NOT used here; the session-based customer engine
// is the correct contract for a stateful, language-aware booking conversation.
export interface AISession {
  id: string;
  session_key?: string;
  customer_id: string | null;
  current_intent?: string;
  workflow_status: "active" | "completed" | "abandoned" | "paused" | string;
  turn_count?: number;
  is_active?: boolean;
}
export interface AISessionMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  tool_calls_made?: string[];
  created_at: string;
}
export interface AISendResponse {
  reply: string;
  tools_called?: string[];
  intent?: string;
  session: AISession;
}
export const aiConversationApi = {
  createSession: (categoryId?: string, language?: { code:string; name:string }) =>
    apiFetch<AISession>("/v1/customer/ai-chat/sessions", {
      method: "POST",
      body: JSON.stringify({ category_id: categoryId, language_code: language?.code, language_name: language?.name }),
    }),
  sendMessage: (sessionId: string, message: string, language?: { code:string; name:string }) =>
    apiFetch<AISendResponse>(`/v1/customer/ai-chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ message, language_code: language?.code, language_name: language?.name }),
    }),
  getMessages: (sessionId: string) =>
    apiFetch<{ messages: AISessionMessage[]; total: number }>(
      `/v1/customer/ai-chat/sessions/${sessionId}/messages`
    ),
  closeSession: (sessionId: string) =>
    apiFetch<AISession>(`/v1/customer/ai-chat/sessions/${sessionId}/close`, { method: "POST" }),
};
