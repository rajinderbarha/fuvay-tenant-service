import { IconProps } from "../../design-system/components/Icon";
import { NotificationSeverity } from "../../services/notifications/types";

export interface EventVisual {
  icon: IconProps["name"];
  tone: "danger" | "warning" | "orange" | "success" | "info" | "neutral";
}

/**
 * One typed registry mapping a real event_type to its icon/tone (spec
 * section 4) -- never scattered per-component switch statements. Unknown
 * event types fall through to the safe neutral fallback in
 * `resolveEventVisual`, never a guessed icon.
 */
const REGISTRY: Record<string, EventVisual> = {
  "job.assigned": { icon: "briefcase-outline", tone: "orange" },
  "job_assigned": { icon: "briefcase-outline", tone: "orange" },
  "job.rescheduled": { icon: "calendar-outline", tone: "info" },
  "job.cancelled": { icon: "close-circle-outline", tone: "danger" },
  "quote.revision_requested": { icon: "alert-circle", tone: "danger" },
  "quote.sent_to_customer": { icon: "document-text-outline", tone: "info" },
  "quote.customer_approved": { icon: "checkmark-circle", tone: "success" },
  "quote.customer_rejected": { icon: "close-circle-outline", tone: "danger" },
  "payment.confirmation_requested": { icon: "cash-outline", tone: "warning" },
  "payment.confirmed_by_customer": { icon: "checkmark-circle", tone: "success" },
  "payment.mismatch_reported": { icon: "warning-outline", tone: "danger" },
  "leave.approved": { icon: "calendar-outline", tone: "orange" },
  "leave.rejected": { icon: "calendar-outline", tone: "warning" },
  "auth.login_success": { icon: "shield-checkmark-outline", tone: "info" },
  "auth.login_failed": { icon: "shield-outline", tone: "warning" },
  "tenant.suspended": { icon: "alert-circle", tone: "danger" },
};

const SEVERITY_FALLBACK: Record<NotificationSeverity, EventVisual> = {
  critical: { icon: "alert-circle", tone: "danger" },
  warning: { icon: "warning-outline", tone: "warning" },
  success: { icon: "checkmark-circle", tone: "success" },
  info: { icon: "information-circle-outline", tone: "info" },
};

/** Unknown event fallback (spec section 12): neutral icon, never a guessed
 * business meaning -- severity (a real backend field) is the only signal used. */
export function resolveEventVisual(eventType: string, severity: NotificationSeverity): EventVisual {
  return REGISTRY[eventType] ?? SEVERITY_FALLBACK[severity] ?? { icon: "notifications-outline", tone: "neutral" };
}
