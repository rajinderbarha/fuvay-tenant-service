import { ServiceBookingDto, AnswerSnapshotDto, ServiceJobDto } from "../contracts/customerBookings";
import { CustomerBookingDetails, CustomerBookingAnswer, CustomerActiveJob } from "../../domain/customerBookingDetails";
import { interpretBookingStatus } from "../../domain/bookingStatus";
import { classifyReviewPricing } from "../../domain/servicePricing";
import { resolveNotificationCapability } from "../../domain/notificationCapability";
import { deriveBookingActivity } from "../../domain/bookingActivity";
import { parseServerTimestamp } from "../../domain/dates";

/**
 * Reads the real, versioned `answer_snapshot` (migration 222,
 * `QuestionFlowService.build_answer_snapshot`) -- resolved once at
 * finalize() time from the live catalog, so a later question/option
 * relabel can never change what a historical booking shows. Deliberately
 * NOT `issue_details` (that column is read by
 * `execution/mobile_inspection_service.py` for an unrelated inspection-
 * report shape -- confirmed via a full-codebase audit of every
 * `issue_details` reader before this contract changed). Sorted by the
 * snapshot's own `sequence`, never re-derived client-side.
 */
function adaptAnswers(snapshot: AnswerSnapshotDto | null | undefined): CustomerBookingAnswer[] {
  if (!snapshot) return [];
  return [...snapshot.answers]
    .sort((a, b) => a.sequence - b.sequence)
    .map(a => ({ id: a.question_id, label: a.question_label, value: a.answer_label }));
}

function formatAddress(snapshot: Record<string, unknown> | null, city: string | null, zipcode: string | null) {
  const lines = ["line1", "line2", "label", "landmark"]
    .map(key => snapshot?.[key])
    .filter((v): v is string => typeof v === "string" && v.trim().length > 0);
  const cityZip = [city, zipcode].filter(Boolean).join(", ");
  const formatted = [...lines, cityZip].filter(Boolean).join(", ");
  return {
    label: typeof snapshot?.label === "string" ? snapshot.label : null,
    formatted: formatted || "Address not available",
    zipcode,
  };
}

function adaptJob(dto: ServiceJobDto | null | undefined): CustomerActiveJob | null {
  if (!dto) return null;
  return {
    jobId: dto.id,
    rawStage: dto.stage,
    rawStatus: dto.status,
    scheduledDate: dto.scheduled_date,
    scheduledTimeWindow: dto.scheduled_time_window,
    technician: dto.technician
      ? {
          displayName: dto.technician.display_name,
          designation: dto.technician.designation,
          photoUrl: dto.technician.photo_url,
        }
      : null,
    completion: dto.completion
      ? {
          workSummary: dto.completion.work_summary,
          collectedAmount: dto.completion.collected_amount,
          completedAt: dto.completion.completed_at,
        }
      : null,
    warrantyDays: dto.warranty_days ?? null,
    warrantyExpiresAt: dto.warranty_expires_at ?? null,
    warrantyActive: dto.warranty_active ?? false,
    warrantyCertificate: dto.warranty_certificate
      ? {
          certificateNumber: dto.warranty_certificate.certificate_number,
          issuedAt: dto.warranty_certificate.issued_at,
          downloadPath: dto.warranty_certificate.download_path,
        }
      : null,
  };
}

export function adaptCustomerBookingDetails(dto: ServiceBookingDto): CustomerBookingDetails {
  const interpretation = interpretBookingStatus(dto.status, dto.assignment_status);
  const priceSnapshot = (dto.price_snapshot ?? {}) as Record<string, unknown>;
  const { state, inspection } = classifyReviewPricing({
    requiresInspectionEstimate: !!priceSnapshot.requires_inspection_estimate,
    visitFeeRaw: typeof priceSnapshot.visit_fee === "number" ? priceSnapshot.visit_fee : null,
    feeAdjustmentNote: typeof priceSnapshot.customer_message === "string" ? priceSnapshot.customer_message : null,
    // Historical snapshots predate `visit_fee_policy`; asserting the
    // guarantee here would be claiming something this record never carried.
    visitFeePolicy: null,
    standardPriceRaw: typeof priceSnapshot.standard_price === "number" ? priceSnapshot.standard_price : null,
  });

  const createdAt = dto.created_at ? parseServerTimestamp(dto.created_at, "created_at") : null;
  const updatedAt = dto.updated_at ? parseServerTimestamp(dto.updated_at, "updated_at") : null;

  return {
    bookingId: dto.id,
    bookingNumber: dto.booking_number,
    stage: interpretation.stage,
    statusLabel: interpretation.statusLabel,
    activityText: interpretation.activityText,
    supportingText: interpretation.supportingText,
    createdAt,
    updatedAt,
    service: {
      name: dto.offering_name ?? dto.category_name ?? null,
      jobType: dto.job_type_label ?? null,
      inspectionRequired: !!priceSnapshot.requires_inspection_estimate,
      issueSummary: dto.issue_summary,
      answers: adaptAnswers(dto.answer_snapshot),
    },
    address: formatAddress(dto.address_snapshot, dto.city, dto.zipcode),
    pricing: { state, inspection },
    // Finalization freezes customer-owned Cloudinary/media references on the
    // booking. IDs are stable per booking+position without pretending the URL
    // itself is an asset identifier.
    attachments: (dto.customer_photo_urls ?? []).map((url, index) => ({
      id: `${dto.id}:customer-photo:${index}`,
      url,
    })),
    note: dto.customer_note ?? null,
    activity: createdAt ? deriveBookingActivity(dto.id, dto.booking_number, createdAt) : [],
    notifications: resolveNotificationCapability(),
    job: adaptJob(dto.job),
    workflowStages: dto.workflow_stages ?? [],
  };
}
