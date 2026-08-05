import { ServerTimestamp } from "./dates";

/**
 * "Support requests" in this app ARE the real backend complaint engine
 * (`app/engines/complaints/customer_router.py`, prefix `/v1/customer/
 * complaints`) -- confirmed during the Help & Support Hub audit to be the
 * only real, ownership-enforced customer request/case system that exists.
 * There is no separate free-text ticket system reachable by customers
 * (the `app/engines/support` ticket engine is tenant-staff-only). Every
 * value below is a real backend constant (`app/engines/complaints/
 * constants.py`), never invented.
 */
export type SupportRequestType =
  | "service_quality" | "technician_behavior" | "late_arrival" | "no_show"
  | "overcharging" | "payment_issue" | "refund_request" | "rework_request"
  | "wrong_information" | "appointment_issue" | "agent_issue" | "other";

/** `safety_concern` is a real value in the backend's extended type set
 * (`COMPLAINT_TYPES_EXT`) even though the base creation route accepts any
 * string -- used only for the dedicated "Report a safety concern" flow,
 * never presented as a general category choice. */
export const SAFETY_CONCERN_TYPE = "safety_concern";

export type SupportRequestRecordType =
  | "service_booking" | "service_job" | "service_invoice"
  | "coaching_appointment" | "real_estate_lead" | "customer_review";

export interface SupportRequestMessage {
  id: string;
  senderType: string;
  messageText: string;
  createdAt: ServerTimestamp;
}

export interface SupportRequest {
  id: string;
  complaintNumber: string;
  recordType: SupportRequestRecordType;
  recordId: string;
  bookingId: string | null;
  complaintType: string;
  status: string;
  title: string | null;
  description: string;
  requestedResolution: string | null;
  customerVisibleSummary: string | null;
  createdAt: ServerTimestamp | null;
  updatedAt: ServerTimestamp | null;
  resolvedAt: ServerTimestamp | null;
  closedAt: ServerTimestamp | null;
}

const FINAL_STATUSES = new Set(["closed", "cancelled", "rejected"]);

export function isSupportRequestFinal(status: string): boolean {
  return FINAL_STATUSES.has(status);
}
