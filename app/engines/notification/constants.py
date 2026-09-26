"""Notification Engine — constants."""

class Channel:
    PUSH  = "push"
    SMS   = "sms"
    EMAIL = "email"
    INAPP = "in_app"
    INSTAGRAM = "instagram"

class NotifStatus:
    PENDING   = "pending"
    QUEUED    = "queued"
    SENT      = "sent"
    DELIVERED = "delivered"
    FAILED    = "failed"
    BOUNCED   = "bounced"

class NotifType:
    JOB_ASSIGNED        = "job_assigned"
    JOB_STATUS_CHANGED  = "job_status_changed"
    BOOKING_CONFIRMED   = "booking_confirmed"
    BOOKING_CANCELLED   = "booking_cancelled"
    PAYMENT_RECEIVED    = "payment_received"
    WALLET_LOW          = "wallet_low"
    WARRANTY_CLAIM      = "warranty_claim"
    STAFF_INVITED       = "staff_invited"
    REVIEW_REQUESTED    = "review_requested"
    SYSTEM_ALERT        = "system_alert"

MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = [60, 300, 900]  # 1min, 5min, 15min
RATE_LIMIT_PER_TENANT_PER_HOUR = 500

# ── Enterprise Notification Template Center (migration 102) ────────────────

VALID_EVENT_TYPES = {
    "booking_confirmed", "booking_cancelled", "booking_rescheduled",
    "provider_assigned", "job_assigned", "job_status_changed",
    "payment_recorded", "review_requested", "complaint_created",
    "dispute_created", "customer_service_credit_issued", "tenant_approved",
    "tenant_changes_requested", "staff_invited", "package_expiring",
    "usage_credit_low", "document_expiring",
    "login_otp", "password_reset", "marketing_post_scheduled",
    "customer_technician_assigned", "customer_technician_on_the_way",
    "customer_technician_arrived", "customer_arrival_confirmation_requested",
    "customer_arrival_confirmed", "customer_reschedule_approval_requested",
    "customer_provider_cancellation_confirmation_requested",
    "customer_stage_scheduled", "customer_stage_inspection_started",
    "customer_stage_inspection_done", "customer_stage_quote_required",
    "customer_stage_service_started", "customer_stage_work_done",
    "customer_stage_customer_not_available",
    "customer_stage_delay_action_required", "customer_stage_delay_critical",
    "customer_stage_delay_warning", "customer_handover_requested",
    "customer_handover_reminder", "customer_payment_requested",
    "customer_payment_reminder", "customer_provider_cancelled",
    "customer_technician_unavailable_cancelled", "customer_sla_cancelled",
    "customer_visit_reminder", "customer_assignment_cancelled",
}

VALID_CHANNELS = {"in_app", "email", "sms", "whatsapp", "push", "instagram"}
VALID_AUDIENCES = {
    "admin", "tenant_owner", "tenant_staff", "technician",
    "customer", "support_admin", "finance_admin",
}
VALID_APP_SCOPES = {"admin_app", "tenant_app", "staff_app", "customer_app", "system"}
VALID_SCOPE_TYPES = {"platform_default", "vertical", "category", "tenant", "environment"}
VALID_STATUSES = {"draft", "active", "inactive", "deprecated", "validation_failed", "archived"}
VALID_LANGUAGES = {"en", "hi", "pa"}
DEFAULT_LANGUAGE = "en"

# Variables allowed per event (used to reject unknown variables at validation time).
EVENT_VARIABLES: dict[str, list[str]] = {
    "booking_confirmed": ["customer_name", "booking_number", "service_name", "provider_name",
                           "scheduled_time", "scheduled_date", "slot", "payable_to_provider",
                           "serviceos_credit_applied", "booking_status", "tracking_url"],
    "booking_cancelled": ["customer_name", "booking_number", "service_name", "booking_status"],
    "booking_rescheduled": ["customer_name", "booking_number", "scheduled_time", "tracking_url"],
    "provider_assigned": ["customer_name", "booking_number", "provider_name", "tracking_url"],
    "job_assigned": ["job_number", "technician_name", "job_status", "arrival_time"],
    "job_status_changed": ["job_number", "technician_name", "job_status", "completion_time"],
    "payment_recorded": ["job_number", "amount_collected", "payable_to_provider"],
    "review_requested": ["customer_name", "booking_number", "service_name", "provider_name"],
    "complaint_created": ["customer_name", "booking_number", "job_number"],
    "dispute_created": ["job_number", "booking_number", "deduction_amount"],
    "customer_service_credit_issued": ["customer_name", "customer_service_credit_amount"],
    "tenant_approved": ["tenant_name", "review_status", "approval_date", "package_name"],
    "tenant_changes_requested": ["tenant_name", "review_status", "change_request_reason"],
    "staff_invited": ["tenant_name", "job_number"],
    "package_expiring": ["tenant_name", "package_name", "approval_date"],
    "usage_credit_low": ["tenant_name", "usage_credit_balance"],
    "document_expiring": ["tenant_name"],
    "login_otp": ["customer_name"],
    "password_reset": ["customer_name"],
    "marketing_post_scheduled": ["tenant_name"],
    "customer_technician_assigned": ["booking_number", "technician_name", "visit_label"],
    "customer_technician_on_the_way": ["technician_name", "visit_label"],
    "customer_technician_arrived": ["technician_name", "visit_label"],
    "customer_arrival_confirmation_requested": ["technician_name", "arrival_code", "expiry_minutes"],
    "customer_arrival_confirmed": [],
    "customer_reschedule_approval_requested": ["booking_number", "current_slot", "requested_slot", "reason", "expires_at"],
    "customer_provider_cancellation_confirmation_requested": ["booking_number", "reason", "expires_at"],
    "customer_stage_scheduled": ["job_number", "stage_label"],
    "customer_stage_inspection_started": ["job_number", "stage_label"],
    "customer_stage_inspection_done": ["job_number", "stage_label"],
    "customer_stage_quote_required": ["job_number", "stage_label"],
    "customer_stage_service_started": ["job_number", "stage_label"],
    "customer_stage_work_done": ["job_number", "stage_label"],
    "customer_stage_customer_not_available": ["job_number", "stage_label"],
    "customer_stage_delay_action_required": ["job_number", "stage_label"],
    "customer_stage_delay_critical": ["job_number", "stage_label"],
    "customer_stage_delay_warning": ["job_number", "stage_label"],
    "customer_handover_requested": ["job_number"],
    "customer_handover_reminder": ["job_number"],
    "customer_payment_requested": ["job_number", "amount"],
    "customer_payment_reminder": ["job_number", "amount"],
    "customer_provider_cancelled": ["booking_number", "reason"],
    "customer_technician_unavailable_cancelled": ["booking_number"],
    "customer_sla_cancelled": ["booking_number"],
    "customer_visit_reminder": ["job_number", "technician_name", "visit_label"],
    "customer_assignment_cancelled": ["booking_number"],
}
# Always allowed regardless of event (generic/system).
COMMON_VARIABLES = ["customer_name", "tenant_name"]

# Internal/finance/risk variables that must never appear in a customer-audience template
# (provider payable_to_provider is customer-visible by design for Home Services direct-pay).
CUSTOMER_FORBIDDEN_VARIABLES = {
    "usage_credit_balance", "deduction_amount",
    "change_request_reason", "review_status",
}
