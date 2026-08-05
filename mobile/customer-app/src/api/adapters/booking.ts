import { ServiceBookingDto, serviceBookingDtoSchema } from "../contracts/bookings";
import { ServiceBooking } from "../../domain/booking";
import { asServiceBookingId, asBookingDraftId, asCustomerId, asTenantId, asCategoryId } from "../../domain/ids";
import { isBookingStatus, isAssignmentStatus } from "../../domain/status";
import { parseServerDate, parseServerTimestamp } from "../../domain/dates";
import { parseMoney } from "../../domain/money";
import { ContractValidationError, UnknownStatusError } from "../../domain/errors";

export function parseServiceBookingDto(raw: unknown): ServiceBookingDto {
  const result = serviceBookingDtoSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("ServiceBookingDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}

/** `price_snapshot` is a free-form JSONB blob (see final_records/models.py)
 * -- this reads only the one field this app currently needs (the agreed/
 * standard price) and never assumes the rest of the shape. */
function extractAgreedPrice(snapshot: Record<string, unknown> | null) {
  if (!snapshot) return null;
  const candidate = snapshot["agreed_price"] ?? snapshot["standard_price"];
  if (candidate === undefined || candidate === null) return null;
  return parseMoney(candidate);
}

export function adaptServiceBooking(dto: ServiceBookingDto): ServiceBooking {
  if (!isBookingStatus(dto.status)) {
    throw new UnknownStatusError("status", dto.status, dto.id);
  }
  if (!isAssignmentStatus(dto.assignment_status)) {
    throw new UnknownStatusError("assignment_status", dto.assignment_status, dto.id);
  }
  return {
    id: asServiceBookingId(dto.id),
    bookingNumber: dto.booking_number,
    draftId: asBookingDraftId(dto.draft_id),
    customerId: dto.customer_id ? asCustomerId(dto.customer_id) : null,
    tenantId: dto.tenant_id ? asTenantId(dto.tenant_id) : null,
    categoryId: asCategoryId(dto.category_id),
    customerName: dto.customer_name,
    city: dto.city,
    zipcode: dto.zipcode,
    preferredDate: dto.preferred_date ? parseServerDate(dto.preferred_date, "preferred_date") : null,
    preferredTimeWindow: dto.preferred_time_window,
    agreedPrice: extractAgreedPrice(dto.price_snapshot),
    provider: dto.provider_snapshot
      ? {
          providerName: dto.provider_snapshot.provider_name ?? null,
          rating: dto.provider_snapshot.rating ?? null,
          publicBadges: dto.provider_snapshot.public_badges ?? [],
        }
      : null,
    status: dto.status,
    assignmentStatus: dto.assignment_status,
    failureReason: dto.failure_reason,
    createdAt: dto.created_at ? parseServerTimestamp(dto.created_at, "created_at") : null,
    updatedAt: dto.updated_at ? parseServerTimestamp(dto.updated_at, "updated_at") : null,
  };
}
