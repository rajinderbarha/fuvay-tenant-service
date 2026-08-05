// ═══════════════════════════════════════════════════════════════════════════
// Home Services Reviews (admin) — /v1/admin/verticals/{vertical}/...
//
// Real bug fixed here: components/home-services/ReviewFeedbackTab.tsx,
// app/admin/home-services/reviews/moderation/page.tsx and the provider
// detail page have always imported `hsReviewApi`, but it was never
// implemented -- TypeScript resolved it to the unrelated `reviewApi` and the
// build failed. Routes matched against
// app/engines/customer_reviews/hs_review_router.py.
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

type ReviewRow = AdminPayload;

const _hsBase = (vertical: string) => `/v1/admin/verticals/${encodeURIComponent(vertical)}`;

function _hsQuery(params?: Record<string, string | number | undefined>): string {
  if (!params) return "";
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (entries.length === 0) return "";
  return `?${new URLSearchParams(Object.fromEntries(entries.map(([k, v]) => [k, String(v)])))}`;
}

/** Every moderation action shares the same `{ reason }` body
 * (ModerationActionRequest on the backend). */
function _hsReason(reason: string): RequestInit {
  return { method: "POST", body: JSON.stringify({ reason: reason ?? "" }) };
}

export interface HsModerationQueue {
  items: ReviewRow[];
  total: number;
  page: number;
  page_size: number;
}

export const hsReviewApi = {
  // ── Per-job review inspection ───────────────────────────────────────────
  getJobReview: <T = ReviewRow>(vertical: string, jobId: string) =>
    apiFetch<T>(`${_hsBase(vertical)}/jobs/${jobId}/review`),
  getJobReviewIntegrity: <T = ReviewRow>(vertical: string, jobId: string) =>
    apiFetch<T>(`${_hsBase(vertical)}/jobs/${jobId}/review/integrity`),
  getJobReviewLifecycle: <T = ReviewRow>(vertical: string, jobId: string) =>
    apiFetch<T>(`${_hsBase(vertical)}/jobs/${jobId}/review/lifecycle`),
  getJobReviewRatingImpact: <T = ReviewRow>(vertical: string, jobId: string) =>
    apiFetch<T>(`${_hsBase(vertical)}/jobs/${jobId}/review/rating-impact`),

  // ── Aggregate summaries ─────────────────────────────────────────────────
  getProviderReviewSummary: <T = ReviewRow>(vertical: string, tenantId: string) =>
    apiFetch<T>(`${_hsBase(vertical)}/providers/${tenantId}/review-summary`),
  getStaffReviewSummary: <T = ReviewRow>(vertical: string, staffId: string) =>
    apiFetch<T>(`${_hsBase(vertical)}/staff/${staffId}/review-summary`),

  // ── Moderation queue ────────────────────────────────────────────────────
  listModerationQueue: <T = ReviewRow>(vertical: string, params?: {
    status?: string; rating?: number; provider_id?: string; page?: number; page_size?: number;
  }) => apiFetch<T>(`${_hsBase(vertical)}/reviews/moderation${_hsQuery(params)}`),
  moderationSummary: <T = ReviewRow>(vertical: string) =>
    apiFetch<T>(`${_hsBase(vertical)}/reviews/moderation/summary`),

  moderationFlag: <T = ReviewRow>(vertical: string, reviewId: string, reason: string) =>
    apiFetch<T>(`${_hsBase(vertical)}/reviews/${reviewId}/flag`, _hsReason(reason)),
  moderationHide: <T = ReviewRow>(vertical: string, reviewId: string, reason: string) =>
    apiFetch<T>(`${_hsBase(vertical)}/reviews/${reviewId}/hide`, _hsReason(reason)),
  moderationRestore: <T = ReviewRow>(vertical: string, reviewId: string, reason: string) =>
    apiFetch<T>(`${_hsBase(vertical)}/reviews/${reviewId}/restore`, _hsReason(reason)),
  moderationResolve: <T = ReviewRow>(vertical: string, reviewId: string, reason: string) =>
    apiFetch<T>(`${_hsBase(vertical)}/reviews/${reviewId}/resolve`, _hsReason(reason)),
  moderationEscalate: <T = ReviewRow>(vertical: string, reviewId: string, reason: string) =>
    apiFetch<T>(`${_hsBase(vertical)}/reviews/${reviewId}/escalate`, _hsReason(reason)),
};
