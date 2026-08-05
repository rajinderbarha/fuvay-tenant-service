/**
 * Customer Home Services API module.
 * Every real backend route used here was verified by reading the actual
 * router source (not the illustrative spec JSON) — see
 * CUSTOMER_FRONTEND_01_API_MAPPING_REPORT.md for the full verified mapping.
 *
 * Real routers used:
 *  - app/engines/admin_catalog/customer_router.py       -> /v1/catalog/master/*
 *  - app/engines/home_service_booking/customer_router.py -> /v1/customer/home-services/booking-drafts/*
 *  - app/engines/home_service_assignment/customer_router.py -> /v1/customer/bookings/*
 *  - app/engines/customer_reviews/customer_router.py     -> /v1/customer/reviews/*  (generic review engine)
 *  - app/engines/execution/home_service_router.py        -> /v1/customer/service-jobs/{job_id}/tracking
 *
 * NOTE: The spec asked for a single submitCustomerBookingReview(bookingId, payload)
 * function. The REAL, wired review flow for Home Services bookings is
 * POST /v1/customer/bookings/{booking_id}/rating (see home_service_assignment/customer_router.py),
 * which wraps app.engines.review.service.ReviewService and enforces
 * BOOKING_NOT_COMPLETED / REVIEW_ALREADY_SUBMITTED with request_id — this is
 * used instead of the separate generic /v1/customer/reviews engine, which
 * expects record_type/record_id and is not booking-shaped the same way.
 */
import { apiFetch } from "./client";

// ── Catalog (public/customer read) ───────────────────────────────────────────

export interface CatalogCategory {
  category_id: string;
  name: string;
  slug: string;
  icon_url?: string | null;
  is_customer_visible: boolean;
  requires_brand?: boolean;
  requires_service_option?: boolean;
  requires_issue_type?: boolean;
  requires_location?: boolean;
  requires_schedule?: boolean;
}

export interface CatalogService {
  service_id: string;
  service_name: string;
  slug?: string;
  category_id: string;
  is_brand_required?: boolean;
  is_type_required?: boolean;
  requires_issue_type?: boolean;
}

// Real backend (admin_catalog list_brands -> Brand._brand_dict) returns "brand_id",
// not "id" — a prior version of this interface used "id" and silently broke brand
// selection (chip clicks set brandId to undefined, so it was never sent to the API).
export interface CatalogBrand { brand_id: string; name: string; }
export interface CatalogServiceType { type_id: string; name: string; }
export interface CatalogIssueType { id: string; name: string; severity?: string; }

export async function getCustomerHomeServicesCatalog(): Promise<{ categories: CatalogCategory[] }> {
  return apiFetch<{ categories: CatalogCategory[] }>("/v1/catalog/master/categories");
}

export async function getCatalogServices(categoryId: string): Promise<{ services: CatalogService[] }> {
  return apiFetch<{ services: CatalogService[] }>(`/v1/catalog/master/services?category_id=${categoryId}`);
}

export async function getCatalogBrands(categoryId: string): Promise<{ brands: CatalogBrand[] }> {
  return apiFetch<{ brands: CatalogBrand[] }>(`/v1/catalog/master/brands?category_id=${categoryId}`);
}

export async function getCatalogServiceTypes(categoryId: string): Promise<{ types: CatalogServiceType[] }> {
  // Real backend (app/engines/admin_catalog/customer_router.py -> list_service_types)
  // returns {"types": [...]}, not {"service_types": [...]}.
  return apiFetch(`/v1/catalog/master/service-types?category_id=${categoryId}`);
}

export async function getCatalogIssueTypes(categoryId: string, masterServiceId?: string): Promise<{ issue_types: CatalogIssueType[] }> {
  const q = masterServiceId ? `?category_id=${categoryId}&master_service_id=${masterServiceId}` : `?category_id=${categoryId}`;
  return apiFetch(`/v1/catalog/master/issue-types${q}`);
}

export async function getFlowConfig(categoryId: string, serviceId?: string): Promise<any> {
  const q = serviceId ? `?category_id=${categoryId}&service_id=${serviceId}` : `?category_id=${categoryId}`;
  return apiFetch(`/v1/catalog/master/flow/config${q}`);
}

/** No dedicated "service questions" endpoint was found wired for customer
 *  Home Services in this backend (searched admin_catalog, home_service_booking,
 *  service_option_customer_router). The nearest real equivalent is the flow
 *  config's requires_* flags plus service-options list, which this app uses
 *  to drive step 3/4. Documented as a gap in CUSTOMER_FRONTEND_01_REMAINING_BLOCKERS.md. */
export async function getCustomerServiceOptions(categoryId: string, masterServiceId?: string): Promise<any> {
  const q = masterServiceId ? `?category_id=${categoryId}&master_service_id=${masterServiceId}` : `?category_id=${categoryId}`;
  return apiFetch(`/v1/catalog/master/service-options${q}`);
}

// ── Booking draft flow (real: home_service_booking/customer_router.py) ───────

export async function startBookingDraft(categorySlug: string, offeringSlug: string): Promise<any> {
  return apiFetch("/v1/customer/home-services/booking-drafts", {
    method: "POST",
    body: JSON.stringify({ category_slug: categorySlug, offering_slug: offeringSlug }),
  });
}

export async function getBookingDraft(draftId: string): Promise<any> {
  return apiFetch(`/v1/customer/home-services/booking-drafts/${draftId}`);
}

export async function updateDraftFields(draftId: string, payload: Record<string, unknown>): Promise<any> {
  return apiFetch(`/v1/customer/home-services/booking-drafts/${draftId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function checkServiceability(draftId: string): Promise<any> {
  return apiFetch(`/v1/customer/home-services/booking-drafts/${draftId}/serviceability-check`, { method: "POST" });
}

/** Provider-First Matching + Low/Mid/High price options — the REAL matching
 *  call (not the spec's illustrative select-provider list endpoint). Backend
 *  selects exactly one provider server-side; no list is ever returned. */
export async function selectProviderForHomeService(draftId: string): Promise<any> {
  return apiFetch(`/v1/customer/home-services/booking-drafts/${draftId}/match-and-price`, { method: "POST" });
}

/** `"standard"` is not optional extra -- the backend REQUIRES it for
 * offerings where bargain pricing is disabled ("Bargain is not available for
 * this offering. Use price_tier='standard' instead."), so omitting it from
 * this type made the fixed-price path untypeable. */
export async function confirmPriceChoice(
  draftId: string,
  priceTier: "low" | "mid" | "high" | "standard",
): Promise<any> {
  return apiFetch(`/v1/customer/home-services/booking-drafts/${draftId}/confirm-price-choice`, {
    method: "POST",
    body: JSON.stringify({ price_tier: priceTier }),
  });
}

export async function buildBookingSummary(draftId: string): Promise<any> {
  return apiFetch(`/v1/customer/home-services/booking-drafts/${draftId}/summary`, { method: "POST" });
}

export async function createCustomerHomeServiceBooking(draftId: string, idempotencyKey: string): Promise<any> {
  return apiFetch(`/v1/customer/home-services/booking-drafts/${draftId}/confirm`, {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
  });
}

export async function addDraftPhoto(draftId: string, photoUrl: string, contentType = "image/jpeg"): Promise<any> {
  return apiFetch(`/v1/customer/home-services/booking-drafts/${draftId}/photos`, {
    method: "POST",
    body: JSON.stringify({ photo_url: photoUrl, content_type: contentType }),
  });
}

// ── Bookings list / detail / tracking (real: home_service_assignment/customer_router.py) ─

export async function getCustomerBookings(params?: { page?: number; page_size?: number }): Promise<any> {
  const q = new URLSearchParams();
  if (params?.page) q.set("page", String(params.page));
  if (params?.page_size) q.set("page_size", String(params.page_size));
  const qs = q.toString() ? `?${q.toString()}` : "";
  return apiFetch(`/v1/customer/bookings${qs}`);
}

export async function getCustomerBookingDetail(bookingId: string): Promise<any> {
  return apiFetch(`/v1/customer/bookings/${bookingId}`);
}

export async function getCustomerBookingTracking(bookingId: string): Promise<any> {
  return apiFetch(`/v1/customer/bookings/${bookingId}/tracking`);
}

// TRACK-TECHNICIAN: real technician GPS, submitted by the assigned
// technician's own device and read only while the job is in an active-
// tracking status (accepted/scheduled/on_the_way). No ETA field exists —
// no routing/distance service exists anywhere in this backend, so one is
// never fabricated here.
export interface TrackingLocation {
  available: boolean;
  reason?: "not_yet_assigned" | "tracking_ended" | "location_unavailable";
  job_status?: string;
  latitude?: number;
  longitude?: number;
  accuracy_meters?: number | null;
  recorded_at?: string;
  is_stale?: boolean;
  destination_latitude?: number | null;
  destination_longitude?: number | null;
  technician?: { name: string; role: string; photo_url: string | null } | null;
}

export async function getTrackingLocation(bookingId: string): Promise<TrackingLocation> {
  return apiFetch(`/v1/customer/bookings/${bookingId}/tracking-location`);
}

// MODULE-L5-29 + CANCEL-RESCHEDULE-FOUNDATION: cancel/reschedule are wired to
// real endpoints (home_service_assignment customer_cancel_booking /
// customer_reschedule_booking). Only allowed while the backend's own
// eligibility check (getCancelRescheduleEligibility) says so — a 409 means
// the job progressed too far and the customer should raise a complaint
// instead. Never reproduce the eligibility rule client-side.

export interface CancelRescheduleEligibility {
  booking_id: string;
  job_id: string;
  status: string;
  version: string;
  can_cancel: boolean;
  cancel_block_reason: string | null;
  allowed_cancellation_reasons: string[];
  cancellation_reasons_requiring_detail: string[];
  can_reschedule: boolean;
  reschedule_block_reason: string | null;
  remaining_reschedule_allowance: number;
  max_reschedule_allowance: number;
  requires_provider_approval: boolean;
  cancellation_fee: number | null;
  cancellation_cutoff: string | null;
}

export async function getCancelRescheduleEligibility(
  bookingId: string,
): Promise<CancelRescheduleEligibility> {
  return apiFetch(`/v1/customer/bookings/${bookingId}/cancel-reschedule-eligibility`);
}

export interface RescheduleAvailability {
  booking_id: string;
  job_id: string;
  dates: { date: string; available: boolean }[];
}

export async function getRescheduleAvailability(
  bookingId: string, horizonDays = 14,
): Promise<RescheduleAvailability> {
  return apiFetch(`/v1/customer/bookings/${bookingId}/reschedule-availability?horizon_days=${horizonDays}`);
}

/** A stable per-attempt key the caller must reuse across retries of the same
 *  user action (e.g. a failed network request the user retries) so the
 *  backend's request_id-based idempotency actually kicks in. A NEW value
 *  must be generated for each distinct customer action. */
export function newIdempotencyKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export async function cancelCustomerBooking(
  bookingId: string,
  payload: { reason: string; detail?: string; expected_version?: string },
  idempotencyKey: string,
): Promise<{ booking_id: string; job_id: string; status: string; version: string }> {
  return apiFetch(`/v1/customer/bookings/${bookingId}/cancel`, {
    method: "POST", body: JSON.stringify(payload),
    headers: { "X-Request-ID": idempotencyKey },
  });
}

export async function rescheduleCustomerBooking(
  bookingId: string,
  payload: { scheduled_date: string; scheduled_time_window?: string; reason: string; expected_version?: string },
  idempotencyKey: string,
): Promise<{ booking_id: string; job_id: string; scheduled_date: string; scheduled_time_window: string | null; version: string }> {
  return apiFetch(`/v1/customer/bookings/${bookingId}/reschedule`, {
    method: "POST", body: JSON.stringify(payload),
    headers: { "X-Request-ID": idempotencyKey },
  });
}

// ── Review (real: POST/GET /v1/customer/bookings/{id}/rating) ────────────────

export async function submitCustomerBookingReview(
  bookingId: string,
  payload: { rating: number; comment?: string },
): Promise<any> {
  return apiFetch(`/v1/customer/bookings/${bookingId}/rating`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getCustomerBookingReview(bookingId: string): Promise<any> {
  return apiFetch(`/v1/customer/bookings/${bookingId}/rating`);
}
