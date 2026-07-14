/**
 * Customer Reviews API module — the rich review engine.
 *
 * MODULE-L5-13: the customer app could only leave a single-star booking rating
 * (via /v1/customer/bookings/{id}/rating) and had no way to see, edit, or flag
 * its reviews, even though the customer_reviews engine exposes all of it. This
 * wires the real endpoints.
 *
 * Real router: app/engines/customer_reviews/customer_router.py
 *   GET   /v1/customer/reviews/eligibility?record_type&record_id
 *   POST  /v1/customer/reviews
 *   GET   /v1/customer/reviews
 *   GET   /v1/customer/reviews/{id}
 *   PATCH /v1/customer/reviews/{id}
 *   POST  /v1/customer/reviews/{id}/flag
 */
import { apiFetch } from "./client";

export interface CustomerReview {
  id: string;
  review_number: string;
  tenant_id: string;
  record_type: string;
  record_id: string;
  booking_id?: string | null;
  overall_rating: number;
  provider_rating?: number | null;
  staff_rating?: number | null;
  communication_rating?: number | null;
  punctuality_rating?: number | null;
  quality_rating?: number | null;
  value_rating?: number | null;
  review_title?: string | null;
  review_text?: string | null;
  review_tags?: string[] | null;
  status: string;
  created_at?: string | null;
}

export interface ReviewEligibility {
  eligible: boolean;
  reason?: string;
  record?: Record<string, unknown>;
}

export interface SubmitReviewInput {
  tenant_id: string;
  record_type: string;
  record_id: string;
  overall_rating: number;
  provider_rating?: number;
  communication_rating?: number;
  punctuality_rating?: number;
  quality_rating?: number;
  value_rating?: number;
  review_title?: string;
  review_text?: string;
  review_tags?: string[];
}

// The optional dimension ratings a customer can additionally give.
export const REVIEW_DIMENSIONS: { key: keyof SubmitReviewInput; label: string }[] = [
  { key: "quality_rating",       label: "Quality of work" },
  { key: "punctuality_rating",   label: "Punctuality" },
  { key: "communication_rating", label: "Communication" },
  { key: "value_rating",         label: "Value for money" },
];

export async function checkReviewEligibility(
  recordType: string, recordId: string,
): Promise<ReviewEligibility> {
  return apiFetch<ReviewEligibility>(
    `/v1/customer/reviews/eligibility?record_type=${encodeURIComponent(recordType)}&record_id=${encodeURIComponent(recordId)}`,
  );
}

export async function submitReview(input: SubmitReviewInput): Promise<CustomerReview> {
  return apiFetch<CustomerReview>("/v1/customer/reviews", {
    method: "POST", body: JSON.stringify(input),
  });
}

export async function listMyReviews(): Promise<CustomerReview[]> {
  return apiFetch<CustomerReview[]>("/v1/customer/reviews");
}

export async function getMyReview(reviewId: string): Promise<CustomerReview> {
  return apiFetch<CustomerReview>(`/v1/customer/reviews/${reviewId}`);
}

export async function editReview(
  reviewId: string,
  patch: Partial<Pick<SubmitReviewInput,
    "overall_rating" | "review_title" | "review_text" |
    "provider_rating" | "communication_rating" | "punctuality_rating" |
    "quality_rating" | "value_rating">>,
): Promise<CustomerReview> {
  return apiFetch<CustomerReview>(`/v1/customer/reviews/${reviewId}`, {
    method: "PATCH", body: JSON.stringify(patch),
  });
}

export async function flagReview(
  reviewId: string, reasonCode: string, reasonText?: string, tenantId?: string,
): Promise<unknown> {
  return apiFetch(`/v1/customer/reviews/${reviewId}/flag`, {
    method: "POST",
    body: JSON.stringify({ reason_code: reasonCode, reason_text: reasonText, tenant_id: tenantId }),
  });
}
