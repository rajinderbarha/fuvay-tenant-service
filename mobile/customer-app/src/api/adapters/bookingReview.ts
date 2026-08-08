import { z } from "zod";
import {
  bookingSummaryDtoSchema, buildBookingSummaryResponseSchema, ConfirmDraftResponseDto,
  availableSlotsResponseSchema, selectSlotResponseSchema,
} from "../contracts/bookingReview";
import { bookingDraftResponseSchema, BookingDraftResponseDto } from "../contracts/bookingDraft";
import { BookingReviewSummary, AvailableSlot } from "../../domain/bookingReview";
import { BookingConfirmationResult } from "../../domain/bookingConfirmation";
import { classifyReviewPricing } from "../../domain/servicePricing";
import { asBookingDraftId } from "../../domain/ids";
import { ContractValidationError } from "../../domain/errors";
import { Money } from "../../domain/money";

/** The backend sends the surcharge as a decimal STRING (Numeric column), so
 * it is parsed here rather than trusted as a number. A non-positive or
 * unparseable value becomes null -- the UI then shows no surcharge line at
 * all rather than a misleading zero. */
function parseSurcharge(raw: string | null | undefined): Money | null {
  if (raw == null || raw === "") return null;
  const amount = Number(raw);
  if (!Number.isFinite(amount) || amount <= 0) return null;
  return { minorUnits: Math.round(amount * 100), currency: "INR" };
}


export function parseDraftDto(raw: unknown): BookingDraftResponseDto {
  const result = bookingDraftResponseSchema.safeParse(raw);
  if (!result.success) throw new ContractValidationError("BookingDraftResponseDto", result.error.issues.map(i => i.message));
  return result.data;
}

export function parseBuildBookingSummaryResponse(raw: unknown) {
  const result = buildBookingSummaryResponseSchema.safeParse(raw);
  if (!result.success) throw new ContractValidationError("BuildBookingSummaryResponseDto", result.error.issues.map(i => i.message));
  return result.data;
}

/** Adapts the combined draft + booking_summary response into the single
 * Review domain model. `catalogQuestionAnswers`/`categoryName`/
 * `jobTypeLabel` come from the enriched draft (`_enrich_draft`); pricing,
 * provider, address and readiness come from `build_booking_summary`. */
export function adaptBookingReviewSummary(
  draft: BookingDraftResponseDto,
  summaryDto: z.infer<typeof bookingSummaryDtoSchema>,
): BookingReviewSummary {
  const priceEstimate = summaryDto.price_estimate ?? {};
  const { state, inspection } = classifyReviewPricing({
    requiresInspectionEstimate: !!priceEstimate.requires_inspection_estimate,
    visitFeeRaw: priceEstimate.visit_fee ?? null,
    feeAdjustmentNote: priceEstimate.customer_message ?? null,
    visitFeePolicy: priceEstimate.visit_fee_policy
      ? {
          creditedAgainstWork: priceEstimate.visit_fee_policy.credited_against_work,
          creditedWhen: priceEstimate.visit_fee_policy.credited_when,
          condition: priceEstimate.visit_fee_policy.condition,
          ifDeclined: priceEstimate.visit_fee_policy.if_declined,
        }
      : null,
    bargainAvailable: !!priceEstimate.bargain_available,
    standardPriceRaw: priceEstimate.standard_price ?? null,
  });

  const addressSnapshot = (summaryDto.address ?? {}) as Record<string, unknown>;
  const addressLines = ["line1", "line2", "label", "landmark"]
    .map(key => addressSnapshot[key])
    .filter((v): v is string => typeof v === "string" && v.trim().length > 0);

  return {
    draftId: asBookingDraftId(draft.id),
    categoryName: draft.category_name ?? null,
    offeringName: summaryDto.offering_name,
    jobTypeLabel: draft.job_type_label ?? null,
    issueSummary: summaryDto.issue_summary,
    // Backend answer labels are not yet exposed by this endpoint --
    // rendered from catalog_question_answers only once a labeled-answer
    // field exists in the summary contract; empty rather than guessed.
    answers: [],
    address: {
      city: summaryDto.city,
      zipcode: summaryDto.zipcode,
      lines: addressLines,
      serviceable: summaryDto.serviceability.serviceable,
      serviceabilityStatus: summaryDto.serviceability.status,
    },
    promisedSlot: summaryDto.promised_slot
      ? {
          date: summaryDto.promised_slot.date,
          timeWindow: summaryDto.promised_slot.time_window,
          startsAt: summaryDto.promised_slot.starts_at,
          endsAt: summaryDto.promised_slot.ends_at,
          slotMinutes: summaryDto.promised_slot.slot_minutes,
          daysAhead: summaryDto.promised_slot.days_ahead,
        }
      : null,
    serviceSlaMinutes: summaryDto.service_sla_minutes ?? null,
    serviceDueAt: summaryDto.service_due_at ?? null,
    isEmergency: summaryDto.is_emergency ?? false,
    emergencySurcharge: parseSurcharge(summaryDto.emergency_surcharge),
    emergencySurchargePreview: parseSurcharge(summaryDto.emergency_surcharge_preview),
    priceState: state,
    inspection,
    bargainAvailable: !!priceEstimate.bargain_available,
    provider: summaryDto.selected_provider
      ? {
          tenantId: summaryDto.selected_provider.tenant_id,
          providerName: summaryDto.selected_provider.provider_name,
          publicBadges: summaryDto.selected_provider.public_badges,
          rating: summaryDto.selected_provider.rating ?? null,
          facts: summaryDto.selected_provider.facts
            ? {
                verified: summaryDto.selected_provider.facts.verified,
                rating: summaryDto.selected_provider.facts.rating,
                reviewCount: summaryDto.selected_provider.facts.review_count,
                jobsCompleted: summaryDto.selected_provider.facts.jobs_completed,
                completionRate: summaryDto.selected_provider.facts.completion_rate,
                onPlatformSince: summaryDto.selected_provider.facts.on_platform_since,
                city: summaryDto.selected_provider.facts.city,
                isNew: summaryDto.selected_provider.facts.is_new,
              }
            : null,
        }
      : null,
    photoCount: draft.photo_urls?.length ?? 0,
    photoUrls: draft.photo_urls ?? [],
    preferredDate: null,
    readyForConfirmation: summaryDto.ready_for_confirmation,
    missing: summaryDto.missing,
  };
}

export function adaptBookingConfirmationResult(dto: ConfirmDraftResponseDto): BookingConfirmationResult {
  return { bookingId: dto.booking_id, bookingNumber: dto.booking_number, idempotent: !!dto.idempotent };
}

export function parseAvailableSlotsResponse(raw: unknown) {
  const result = availableSlotsResponseSchema.safeParse(raw);
  if (!result.success) throw new ContractValidationError("AvailableSlotsResponseDto", result.error.issues.map(i => i.message));
  return result.data;
}

export function adaptAvailableSlots(dto: z.infer<typeof availableSlotsResponseSchema>): AvailableSlot[] {
  return dto.slots.map(s => ({ date: s.date, timeWindow: s.time_window, daysAhead: s.days_ahead }));
}

export function parseSelectSlotResponse(raw: unknown) {
  const result = selectSlotResponseSchema.safeParse(raw);
  if (!result.success) throw new ContractValidationError("SelectSlotResponseDto", result.error.issues.map(i => i.message));
  return result.data;
}

/** Only the fields a slot change can actually affect -- everything else on
 * the summary (address, pricing, provider, answers) is untouched by
 * picking a different time. */
export function applySelectedSlotToSummary(
  prev: BookingReviewSummary,
  summaryDto: z.infer<typeof bookingSummaryDtoSchema>,
): BookingReviewSummary {
  return {
    ...prev,
    promisedSlot: summaryDto.promised_slot
      ? {
          date: summaryDto.promised_slot.date,
          timeWindow: summaryDto.promised_slot.time_window,
          startsAt: summaryDto.promised_slot.starts_at,
          endsAt: summaryDto.promised_slot.ends_at,
          slotMinutes: summaryDto.promised_slot.slot_minutes,
          daysAhead: summaryDto.promised_slot.days_ahead,
        }
      : null,
    serviceSlaMinutes: summaryDto.service_sla_minutes ?? null,
    serviceDueAt: summaryDto.service_due_at ?? null,
    isEmergency: summaryDto.is_emergency ?? false,
    emergencySurcharge: parseSurcharge(summaryDto.emergency_surcharge),
    emergencySurchargePreview: parseSurcharge(summaryDto.emergency_surcharge_preview),
  };
}
