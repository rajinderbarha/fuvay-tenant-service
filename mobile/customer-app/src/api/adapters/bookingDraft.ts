import { BookingDraftResponseDto, bookingDraftResponseSchema, bookingDraftOrNullSchema } from "../contracts/bookingDraft";
import { BookingDraftSummary } from "../../domain/bookingDraft";
import { asBookingDraftId } from "../../domain/ids";
import { parseServerTimestamp } from "../../domain/dates";
import { ContractValidationError } from "../../domain/errors";

export function parseBookingDraftDto(raw: unknown): BookingDraftResponseDto {
  const result = bookingDraftResponseSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("BookingDraftResponseDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}

export function parseBookingDraftOrNullDto(raw: unknown): BookingDraftResponseDto | null {
  const result = bookingDraftOrNullSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("BookingDraftResponseDto|null", result.error.issues.map(i => i.message));
  }
  return result.data;
}

export function adaptBookingDraft(dto: BookingDraftResponseDto): BookingDraftSummary {
  return {
    id: asBookingDraftId(dto.id),
    aiSessionId: dto.ai_session_id,
    status: dto.status,
    city: dto.city,
    zipcode: dto.zipcode,
    issueSummary: dto.issue_summary,
    serviceabilityStatus: dto.serviceability_status,
    priceStatus: dto.price_status,
    categoryName: dto.category_name ?? null,
    offeringName: dto.offering_name ?? null,
    jobTypeLabel: dto.job_type_label ?? null,
    createdAt: dto.created_at ? parseServerTimestamp(dto.created_at, "created_at") : null,
  };
}
