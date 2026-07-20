import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { bookingConfirmationApi } from "../api/booking-confirmation-api";
import { parseReviewResult, type ValidatedReviewResult } from "../domain/review-schema";
import {
  parseConfirmBookingResult,
  parseBookingDetailResponse,
  type ValidatedConfirmBookingResult,
  type ValidatedBookingDetail,
} from "../domain/booking-schema";
import { getRequestLocale, getRequestTenantId } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import { ApiError } from "../../../api/api-errors";

/** A mutation, not a query — `/summary` has no independent cacheable GET; it recomputes and merges fresh on every call (mirrors CUSTOMER-L5-09/10's identical `POST`-only pattern). */
export function useBookingReview() {
  return useMutation<ValidatedReviewResult, ApiError, string>({
    mutationFn: async (draftId: string) => {
      logger.info("booking_review_load_started", {});
      const response = await bookingConfirmationApi.getReview(draftId);
      const parsed = parseReviewResult(response);
      if (!parsed) {
        logger.warn("booking_review_load_failed", { reason: "validation" });
        throw new ApiError({ category: "validation_error", message: "Booking review response did not match the expected shape." });
      }
      return parsed;
    },
    onError: () => {
      logger.warn("booking_review_load_failed", { reason: "request" });
    },
  });
}

export function useConfirmBooking() {
  return useMutation<ValidatedConfirmBookingResult, ApiError, { draftId: string; idempotencyKey: string }>({
    mutationFn: async ({ draftId, idempotencyKey }) => {
      logger.info("booking_create_started", {});
      const response = await bookingConfirmationApi.confirmBooking(draftId, idempotencyKey);
      const parsed = parseConfirmBookingResult(response);
      if (!parsed) {
        logger.warn("booking_create_failed", { reason: "validation" });
        throw new ApiError({ category: "validation_error", message: "Confirm-booking response did not match the expected shape." });
      }
      logger.info("booking_create_succeeded", { idempotent: parsed.idempotent });
      return parsed;
    },
  });
}

export const bookingQueryKeys = {
  detail: (bookingId: string, locale: string, tenantId: string | undefined) => ["booking", "detail", bookingId, locale, tenantId ?? "no-tenant"] as const,
};

/** A real query — `GET /bookings/{id}` is a genuine, cacheable, customer-owned read (CUSTOMER-L5-11 §45: prefer canonical booking data over the mutation response alone). */
export function useBookingDetail(bookingId: string | null) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();

  return useQuery<ValidatedBookingDetail>({
    queryKey: bookingQueryKeys.detail(bookingId ?? "none", locale, tenantId),
    queryFn: async ({ signal }) => {
      const response = await bookingConfirmationApi.getBooking(bookingId as string, { signal });
      const parsed = parseBookingDetailResponse(response);
      if (parsed.kind === "invalid") {
        logger.warn("booking_fetch_failed", { reason: "validation" });
        throw new ApiError({ category: "validation_error", message: "Booking response did not match the expected shape." });
      }
      if (parsed.kind === "error") {
        logger.warn("booking_fetch_failed", { reason: parsed.code });
        throw new ApiError({ category: parsed.code === "FINAL_ACCESS_DENIED" ? "forbidden" : "not_found", message: "Booking not accessible." });
      }
      return parsed.booking;
    },
    enabled: Boolean(bookingId),
    staleTime: 0,
    retry: 1,
  });
}

/** Invalidated after a successful booking creation (CUSTOMER-L5-11 §39). */
export function useInvalidateDraftAfterBooking() {
  const queryClient = useQueryClient();
  return (draftId: string) => {
    const locale = getRequestLocale();
    const tenantId = getRequestTenantId();
    void queryClient.invalidateQueries({ queryKey: ["bookingDraft", "detail", draftId, locale, tenantId ?? "no-tenant"] });
  };
}
