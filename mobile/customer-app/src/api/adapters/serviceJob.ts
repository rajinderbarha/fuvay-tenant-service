import { ServiceJobDto, serviceJobDtoSchema } from "../contracts/serviceJobs";
import { ServiceJob } from "../../domain/serviceJob";
import { asServiceJobId, asServiceBookingId, asCustomerId, asTenantId, asCategoryId } from "../../domain/ids";
import { isJobStatus, isAssignmentStatus } from "../../domain/status";
import { parseServerDate, parseServerTimestamp } from "../../domain/dates";
import { ContractValidationError, UnknownStatusError } from "../../domain/errors";

export function parseServiceJobDto(raw: unknown): ServiceJobDto {
  const result = serviceJobDtoSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("ServiceJobDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}

export function adaptServiceJob(dto: ServiceJobDto): ServiceJob {
  if (!isJobStatus(dto.status)) {
    throw new UnknownStatusError("status", dto.status, dto.id);
  }
  if (!isAssignmentStatus(dto.assignment_status)) {
    throw new UnknownStatusError("assignment_status", dto.assignment_status, dto.id);
  }
  return {
    id: asServiceJobId(dto.id),
    jobNumber: dto.job_number,
    bookingId: asServiceBookingId(dto.booking_id),
    customerId: dto.customer_id ? asCustomerId(dto.customer_id) : null,
    tenantId: dto.tenant_id ? asTenantId(dto.tenant_id) : null,
    categoryId: asCategoryId(dto.category_id),
    scheduledDate: dto.scheduled_date ? parseServerDate(dto.scheduled_date, "scheduled_date") : null,
    scheduledTimeWindow: dto.scheduled_time_window,
    city: dto.city,
    zipcode: dto.zipcode,
    status: dto.status,
    assignmentStatus: dto.assignment_status,
    failureReason: dto.failure_reason,
    createdAt: dto.created_at ? parseServerTimestamp(dto.created_at, "created_at") : null,
    updatedAt: dto.updated_at ? parseServerTimestamp(dto.updated_at, "updated_at") : null,
  };
}
