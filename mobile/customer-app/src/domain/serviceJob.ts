import { ServiceJobId, ServiceBookingId, CustomerId, TenantId, CategoryId } from "./ids";
import { JobStatus, AssignmentStatus } from "./status";
import { ServerDate, ServerTimestamp } from "./dates";

export interface ServiceJob {
  id: ServiceJobId;
  jobNumber: string;
  bookingId: ServiceBookingId;
  customerId: CustomerId | null;
  tenantId: TenantId | null;
  categoryId: CategoryId;
  scheduledDate: ServerDate | null;
  scheduledTimeWindow: string | null;
  city: string | null;
  zipcode: string | null;
  status: JobStatus;
  assignmentStatus: AssignmentStatus;
  failureReason: string | null;
  createdAt: ServerTimestamp | null;
  updatedAt: ServerTimestamp | null;
}
