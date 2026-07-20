import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { bookingsApi } from "../api/bookings-api";
import { parseBookingListPage } from "../domain/booking-list-schema";
import { parseBookingDetail } from "../domain/booking-detail-schema";
import { parseBookingTracking } from "../domain/booking-tracking-schema";
import { parseBookingReviewStatus } from "../domain/booking-review-status-schema";
import { getRequestLocale, getRequestTenantId } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import { ApiError } from "../../../api/api-errors";

const PAGE_SIZE = 20;

export const bookingsQueryKeys = {
  list: (locale: string, tenantId: string | undefined) => ["bookings", "list", locale, tenantId ?? "no-tenant"] as const,
  detail: (bookingId: string, locale: string, tenantId: string | undefined) => ["bookings", "detail", bookingId, locale, tenantId ?? "no-tenant"] as const,
  tracking: (bookingId: string, locale: string, tenantId: string | undefined) => ["bookings", "tracking", bookingId, locale, tenantId ?? "no-tenant"] as const,
  reviewStatus: (bookingId: string, locale: string, tenantId: string | undefined) =>
    ["bookings", "reviewStatus", bookingId, locale, tenantId ?? "no-tenant"] as const,
};

/**
 * A real, server-paginated infinite query — `GET /v1/customer/bookings`
 * has no status/date/search filter param at all (confirmed this sprint,
 * see contract-matrix.md), so Active/Past grouping is applied client-side
 * over whatever pages have been loaded so far (list-architecture.md
 * documents this real, disclosed limitation).
 */
export function useBookingsList() {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();

  return useInfiniteQuery({
    queryKey: bookingsQueryKeys.list(locale, tenantId),
    queryFn: async ({ pageParam, signal }) => {
      const response = await bookingsApi.listBookings(pageParam, PAGE_SIZE, { signal });
      const parsed = parseBookingListPage(response);
      if (!parsed) {
        logger.warn("bookings_list_load_failed", { reason: "validation" });
        throw new ApiError({ category: "validation_error", message: "Bookings list response did not match the expected shape." });
      }
      return parsed;
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage) => (lastPage.mayHaveMore ? lastPage.page + 1 : undefined),
    staleTime: 0,
  });
}

export function useBookingDetail(bookingId: string | null) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();

  return useQuery({
    queryKey: bookingsQueryKeys.detail(bookingId ?? "none", locale, tenantId),
    queryFn: async ({ signal }) => {
      const response = await bookingsApi.getBooking(bookingId as string, { signal });
      const parsed = parseBookingDetail(response);
      if (parsed.kind === "invalid") {
        logger.warn("booking_detail_load_failed", { reason: "validation" });
        throw new ApiError({ category: "validation_error", message: "Booking detail response did not match the expected shape." });
      }
      if (parsed.kind === "error") {
        logger.warn("booking_detail_load_failed", { reason: parsed.code });
        throw new ApiError({ category: "not_found", message: "Booking not accessible." });
      }
      return parsed.booking;
    },
    enabled: Boolean(bookingId),
    staleTime: 0,
    retry: 1,
  });
}

export function useBookingTracking(bookingId: string | null) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();

  return useQuery({
    queryKey: bookingsQueryKeys.tracking(bookingId ?? "none", locale, tenantId),
    queryFn: async ({ signal }) => {
      const response = await bookingsApi.getBookingTracking(bookingId as string, { signal });
      const parsed = parseBookingTracking(response);
      if (!parsed) {
        logger.warn("booking_timeline_load_failed", { reason: "validation" });
        throw new ApiError({ category: "validation_error", message: "Booking tracking response did not match the expected shape." });
      }
      return parsed;
    },
    enabled: Boolean(bookingId),
    staleTime: 0,
    retry: 1,
  });
}

/** Only queried to decide review-boundary visibility (§36) — never used to submit a review. */
export function useBookingReviewStatus(bookingId: string | null, enabled: boolean) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();

  return useQuery({
    queryKey: bookingsQueryKeys.reviewStatus(bookingId ?? "none", locale, tenantId),
    queryFn: async ({ signal }) => {
      const response = await bookingsApi.getBookingReviewStatus(bookingId as string, { signal });
      const parsed = parseBookingReviewStatus(response);
      if (!parsed) throw new ApiError({ category: "validation_error", message: "Review status response did not match the expected shape." });
      return parsed;
    },
    enabled: Boolean(bookingId) && enabled,
    staleTime: 0,
    retry: 1,
  });
}
