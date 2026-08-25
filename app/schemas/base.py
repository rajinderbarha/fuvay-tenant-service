"""
ServiceOS — Base Response Schemas
Level 5: RFC 7807, HATEOAS, cursor pagination, idempotency, sparse fieldsets,
         allowed transitions (state machine), bulk operation responses.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")


# ── Meta ──────────────────────────────────────────────────────────────────────
class Meta(BaseModel):
    request_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "2.4.1"
    engine_id: str | None = None
    tenant_id: str | None = None
    idempotent: bool = False  # True if this response was served from idempotency cache


# ── HATEOAS ───────────────────────────────────────────────────────────────────
class Link(BaseModel):
    """A single HATEOAS navigation link."""
    href: str
    method: str = "GET"
    rel: str
    description: str | None = None


class Links(BaseModel):
    """
    HATEOAS links on every entity response.
    Clients use these — they never construct URLs themselves.
    """
    self_link: str | None = Field(None, alias="self")
    collection: str | None = None
    related: dict[str, str] | None = None
    actions: list[Link] | None = None

    model_config = ConfigDict(populate_by_name=True)


# ── State Machine ─────────────────────────────────────────────────────────────
class AllowedTransition(BaseModel):
    """
    Returned on entity responses with state machines.
    Clients render action buttons from this — no hardcoded state logic.
    """
    to_status: str
    endpoint: str
    method: str = "POST"
    label: str
    description: str | None = None
    requires_payload: bool = False
    payload_schema: dict[str, Any] | None = None
    available: bool = True
    unavailable_reason: str | None = None


# ── Standard Response ─────────────────────────────────────────────────────────
class ApiResponse(BaseModel, Generic[T]):
    """
    Standard success envelope.
    Every single endpoint returns this.

    Example:
        GET /v1/auth/me → ApiResponse[UserProfile]
        {
            "success": true,
            "data": { ...user... },
            "links": { "self": "/v1/auth/me", "actions": [...] },
            "meta": { "request_id": "req_abc", ... }
        }
    """
    success: bool = True
    data: T
    links: Links | None = None
    meta: Meta

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ── Cursor Pagination ─────────────────────────────────────────────────────────
class CursorPage(BaseModel, Generic[T]):
    """
    Cursor-based pagination — never offset (breaks at scale).
    Cursor is an opaque base64-encoded string encoding the last item's sort key.

    Usage: GET /v1/field-ops/jobs?cursor=eyJpZCI6Ijg0...&limit=20
    """
    items: list[T]
    total: int | None = None           # None when count is expensive
    limit: int
    has_next: bool
    has_prev: bool
    next_cursor: str | None = None
    prev_cursor: str | None = None
    links: dict[str, str | None] = Field(default_factory=dict)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response with cursor pagination."""
    success: bool = True
    data: CursorPage[T]
    meta: Meta


# ── Error Schemas (RFC 7807) ──────────────────────────────────────────────────
class ProblemDetail(BaseModel):
    """
    RFC 7807 Problem Details.
    Every error uses this format — no exceptions.
    Clients switch on error_code, never on HTTP status code.

    Content-Type: application/problem+json
    """
    type: str                  # URI: https://serviceos.io/errors/{error_code}
    title: str                 # Short human-readable summary
    status: int                # HTTP status code
    detail: str                # Human-readable explanation for this occurrence
    instance: str | None = None  # URI of the specific request
    error_code: str            # Machine-readable — clients switch on this
    blocking_rule: str | None = None   # The specific rule violated
    resolution: str | None = None      # What to do to fix this
    request_id: str | None = None
    context: dict[str, Any] | None = None
    allowed_transitions: list[AllowedTransition] | None = None  # For state machine errors

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "https://serviceos.io/errors/PERMISSION_DENIED",
                "title": "Permission Denied",
                "status": 403,
                "detail": "Permission 'field_ops:jobs:assign' required.",
                "instance": "/v1/field-ops/jobs/JB-001/assign",
                "error_code": "PERMISSION_DENIED",
                "blocking_rule": "required_permission: field_ops:jobs:assign",
                "resolution": "Ask your administrator to grant this permission.",
                "request_id": "req_abc123",
            }
        }
    )


class ValidationErrorItem(BaseModel):
    field: str
    message: str
    received: Any | None = None
    expected: str | None = None


class ValidationProblemDetail(ProblemDetail):
    errors: list[ValidationErrorItem] = []


# ── Bulk Operations ───────────────────────────────────────────────────────────
class AsyncJobResponse(BaseModel):
    """
    Response for long-running operations (202 Accepted).
    Client polls GET /{entity}/jobs/{job_id} for progress.
    """
    job_id: str
    status: str = "pending"
    estimated_duration_seconds: int | None = None
    poll_url: str
    webhook_event: str | None = None  # Event fired when complete
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ── Error Code Registry ───────────────────────────────────────────────────────
BASE_URL = "https://serviceos.io/errors"

ERROR_CODES: dict[str, dict[str, Any]] = {
    # Auth
    "UNAUTHORIZED":            {"status": 401, "title": "Unauthorized"},
    "INVALID_TOKEN":           {"status": 401, "title": "Invalid or Expired Token"},
    "TOKEN_BLACKLISTED":       {"status": 401, "title": "Token Revoked"},
    "SESSION_REVOKED":         {"status": 401, "title": "Session Revoked"},
    "TOKEN_EXPIRED":           {"status": 401, "title": "Token Expired"},
    "MFA_REQUIRED":            {"status": 403, "title": "MFA Required"},
    "MFA_SETUP_REQUIRED":      {"status": 403, "title": "MFA Setup Required"},
    "MFA_ENROLLMENT_REQUIRED": {"status": 403, "title": "MFA Enrollment Required"},
    "DEVICE_APPROVAL_REQUIRED":{"status": 403, "title": "Device Approval Required"},
    "FORCE_PASSWORD_CHANGE":   {"status": 403, "title": "Password Change Required"},
    "ACCOUNT_LOCKED":          {"status": 423, "title": "Account Locked"},
    # Permission
    "PERMISSION_DENIED":       {"status": 403, "title": "Permission Denied"},
    # Tenant — core
    "TENANT_NOT_FOUND":              {"status": 404, "title": "Tenant Not Found"},
    "TENANT_SUSPENDED":              {"status": 403, "title": "Tenant Account Suspended"},
    "TENANT_TERMINATED":             {"status": 403, "title": "Tenant Account Terminated"},
    "TENANT_TRIAL_EXPIRED":          {"status": 403, "title": "Trial Expired"},
    # Tenant — Sprint 4 onboarding & lifecycle
    "TENANT_ALREADY_EXISTS":         {"status": 409, "title": "Tenant Already Exists"},
    "TENANT_ONBOARDING_FAILED":      {"status": 500, "title": "Tenant Onboarding Failed"},
    "TENANT_OWNER_CREATE_FAILED":    {"status": 500, "title": "Owner User Creation Failed"},
    "TENANT_WALLET_INIT_FAILED":     {"status": 500, "title": "Wallet Initialisation Failed"},
    "TENANT_SETTINGS_INIT_FAILED":   {"status": 500, "title": "Settings Initialisation Failed"},
    "TENANT_ACCESS_DENIED":          {"status": 403, "title": "Tenant Access Denied"},
    "TENANT_VERIFICATION_INVALID_STATUS": {"status": 422, "title": "Invalid Verification Status Transition"},
    "TENANT_CATEGORY_REQUIRED":      {"status": 422, "title": "Category Is Required"},
    "TENANT_OWNER_REQUIRED":         {"status": 422, "title": "Owner Details Are Required"},
    "TENANT_ARCHIVED":               {"status": 410, "title": "Tenant Archived"},
    # Tenant Users — Sprint 4
    "TENANT_USER_NOT_FOUND":         {"status": 404, "title": "Tenant User Not Found"},
    "TENANT_USER_ALREADY_EXISTS":    {"status": 409, "title": "User Already Exists For This Tenant"},
    "TENANT_USER_ACCESS_DENIED":     {"status": 403, "title": "User Does Not Belong To This Tenant"},
    "TENANT_USER_ROLE_INVALID":      {"status": 422, "title": "Invalid Tenant User Role"},
    # Tenant Staff — Sprint 4
    "TENANT_STAFF_NOT_FOUND":        {"status": 404, "title": "Tenant Staff Not Found"},
    "TENANT_STAFF_ALREADY_EXISTS":   {"status": 409, "title": "Staff Member Already Exists"},
    "TENANT_STAFF_ACCESS_DENIED":    {"status": 403, "title": "Staff Does Not Belong To This Tenant"},
    "TENANT_STAFF_INACTIVE":         {"status": 422, "title": "Staff Member Is Inactive"},
    "TENANT_STAFF_PHOTO_UPLOAD_FAILED": {"status": 500, "title": "Staff Photo Upload Failed"},
    # Tenant Service Areas — Sprint 4
    "TENANT_SERVICE_AREA_NOT_FOUND": {"status": 404, "title": "Service Area Not Found"},
    "TENANT_SERVICE_AREA_ACCESS_DENIED": {"status": 403, "title": "Service Area Does Not Belong To This Tenant"},
    "TENANT_SERVICE_AREA_INVALID":   {"status": 422, "title": "Invalid Service Area Configuration"},
    "TENANT_SERVICE_AREA_SERVICE_MAPPING_INVALID": {"status": 422, "title": "Service Not Enabled For This Tenant"},
    # Tenant Media — Sprint 4
    "TENANT_MEDIA_NOT_FOUND":        {"status": 404, "title": "Media File Not Found"},
    "TENANT_MEDIA_ACCESS_DENIED":    {"status": 403, "title": "Media Does Not Belong To This Tenant"},
    "TENANT_MEDIA_QUOTA_EXCEEDED":   {"status": 422, "title": "Storage Quota Exceeded"},
    "TENANT_MEDIA_INVALID_TYPE":     {"status": 422, "title": "Invalid Media File Type"},
    "TENANT_MEDIA_UPLOAD_FAILED":    {"status": 500, "title": "Media Upload Failed"},
    # Security Deposit & Credit — Sprint 4
    "SECURITY_DEPOSIT_NOT_FOUND":    {"status": 404, "title": "Security Deposit Record Not Found"},
    "SECURITY_DEPOSIT_ALREADY_PAID": {"status": 409, "title": "Security Deposit Already Marked As Paid"},
    "CREDIT_WALLET_NOT_FOUND":       {"status": 404, "title": "Credit Wallet Not Found"},
    "CREDIT_ADJUSTMENT_REASON_REQUIRED": {"status": 422, "title": "Adjustment Reason Is Required"},
    # Packages — Sprint 5
    "PACKAGE_NOT_FOUND":             {"status": 404, "title": "Package Not Found"},
    "PACKAGE_INACTIVE":              {"status": 422, "title": "Package Is Inactive"},
    "PACKAGE_ALREADY_PURCHASED":     {"status": 409, "title": "Package Already Purchased"},
    "PACKAGE_PURCHASE_NOT_ALLOWED":  {"status": 422, "title": "Package Purchase Not Allowed"},
    "PACKAGE_PURCHASE_FAILED":       {"status": 500, "title": "Package Purchase Failed"},
    "PACKAGE_TYPE_INVALID":          {"status": 422, "title": "Invalid Package Type"},
    "PACKAGE_PRICE_INVALID":         {"status": 422, "title": "Invalid Package Price or Amount"},
    # Security Deposit — Sprint 5 additions
    "SECURITY_DEPOSIT_REQUIRED":     {"status": 402, "title": "Security Deposit Required Before Proceeding"},
    "SECURITY_DEPOSIT_PAYMENT_FAILED":  {"status": 500, "title": "Security Deposit Payment Failed"},
    "SECURITY_DEPOSIT_REFUND_FAILED":   {"status": 422, "title": "Security Deposit Cannot Be Refunded"},
    "SECURITY_DEPOSIT_FORFEIT_FAILED":  {"status": 422, "title": "Security Deposit Cannot Be Forfeited"},
    # Credit Wallet — Sprint 5
    "CREDIT_WALLET_INACTIVE":        {"status": 422, "title": "Credit Wallet Is Inactive"},
    "CREDIT_WALLET_INSUFFICIENT_BALANCE": {"status": 402, "title": "Insufficient Credit Wallet Balance"},
    "CREDIT_LEDGER_CREATE_FAILED":   {"status": 500, "title": "Credit Ledger Entry Creation Failed"},
    "CREDIT_AMOUNT_INVALID":         {"status": 422, "title": "Credit Amount Must Be Greater Than Zero"},
    # Commission — Sprint 5
    "COMMISSION_NOT_FOUND":          {"status": 404, "title": "Commission Record Not Found"},
    "COMMISSION_ALREADY_EXISTS":     {"status": 409, "title": "Commission Already Exists For This Job"},
    "COMMISSION_ALREADY_DEDUCTED":   {"status": 409, "title": "Commission Already Deducted For This Job"},
    "COMMISSION_CALCULATION_FAILED": {"status": 500, "title": "Commission Calculation Failed"},
    "COMMISSION_DEDUCTION_FAILED":   {"status": 402, "title": "Commission Deduction Failed"},
    "COMMISSION_REQUIRED_BEFORE_CLOSE": {"status": 422, "title": "Commission Must Be Deducted Before Job Can Close"},
    "COMMISSION_RATE_NOT_FOUND":     {"status": 422, "title": "Commission Rate Not Configured"},
    # Storage — Sprint 5
    "TENANT_STORAGE_QUOTA_EXCEEDED": {"status": 422, "title": "Tenant Storage Quota Exceeded"},
    # Package/low credit alerts — Sprint 5
    "TENANT_PACKAGE_REQUIRED":       {"status": 402, "title": "Tenant Must Purchase a Package First"},
    "TENANT_LOW_CREDIT":             {"status": 402, "title": "Tenant Credit Balance Is Low"},
    # Location hierarchy — Scalability Sprint
    "LOCATION_STATE_NOT_FOUND":      {"status": 404, "title": "State Not Found"},
    "LOCATION_DISTRICT_NOT_FOUND":   {"status": 404, "title": "District Not Found"},
    "LOCATION_CITY_NOT_FOUND":       {"status": 404, "title": "City Not Found"},
    "LOCATION_ZONE_NOT_FOUND":       {"status": 404, "title": "Zone Not Found"},
    "LOCATION_INVALID_HIERARCHY":    {"status": 422, "title": "Invalid Location Hierarchy"},
    "ADDRESS_DISTRICT_REQUIRED":     {"status": 422, "title": "District Is Required"},
    "TENANT_LOCATION_REQUIRED":      {"status": 422, "title": "Tenant Location Required"},
    # Pagination / filter errors — Scalability Sprint
    "TENANT_FILTER_INVALID":         {"status": 400, "title": "Invalid Tenant Filter"},
    "PAGINATION_REQUIRED":           {"status": 400, "title": "Pagination Parameters Required"},
    "PAGE_SIZE_TOO_LARGE":           {"status": 400, "title": "Page Size Exceeds Maximum"},
    "SORT_FIELD_NOT_ALLOWED":        {"status": 400, "title": "Sort Field Not Allowed"},
    "FILTER_FIELD_NOT_ALLOWED":      {"status": 400, "title": "Filter Field Not Allowed"},
    # Engine
    "ENGINE_DISABLED":         {"status": 403, "title": "Engine Not Enabled for This Tenant"},
    "ENGINE_DEPENDENCY":       {"status": 400, "title": "Engine Dependency Not Satisfied"},
    "ENGINE_IN_USE":           {"status": 409, "title": "Engine In Use By Dependent Engine"},
    # Plan
    "PLAN_LIMIT_EXCEEDED":     {"status": 402, "title": "Plan Limit Exceeded"},
    "PLAN_FEATURE_UNAVAILABLE":{"status": 402, "title": "Feature Not Available on Current Plan"},
    "DOWNGRADE_BLOCKED":       {"status": 409, "title": "Downgrade Blocked — Usage Exceeds Target Plan"},
    # Resource
    "NOT_FOUND":               {"status": 404, "title": "Resource Not Found"},
    "ALREADY_EXISTS":          {"status": 409, "title": "Resource Already Exists"},
    "CONFLICT":                {"status": 409, "title": "Conflict"},
    # State Machine
    "INVALID_TRANSITION":      {"status": 422, "title": "Invalid State Transition"},
    "TRANSITION_BLOCKED":      {"status": 422, "title": "Transition Blocked by Business Rule"},
    "QUOTE_EXPIRED":           {"status": 409, "title": "Quote Has Expired"},
    "CHECKLIST_INCOMPLETE":    {"status": 422, "title": "Checklist Incomplete"},
    "DEEPSEEK_NOT_CONFIGURED": {"status": 503, "title": "AI Assistant Not Configured"},
    "DEEPSEEK_API_ERROR":      {"status": 502, "title": "AI Assistant Upstream Error"},
    "DEEPSEEK_TIMEOUT":        {"status": 504, "title": "AI Assistant Timed Out"},
    "DEEPSEEK_UNREACHABLE":    {"status": 503, "title": "AI Assistant Unavailable"},
    # Self-registration
    "OTP_NOT_VERIFIED":              {"status": 400, "title": "OTP Not Verified"},
    "PAYMENT_SIGNATURE_INVALID":     {"status": 400, "title": "Payment Signature Invalid"},
    "PAYMENT_REQUIRED":              {"status": 402, "title": "Payment Required to Complete Registration"},
    "REGISTRATION_DUPLICATE":        {"status": 409, "title": "Business Already Registered"},
    "REGISTRATION_FAILED":           {"status": 500, "title": "Registration Failed"},
    # Validation
    "VALIDATION_ERROR":        {"status": 422, "title": "Validation Error"},
    "INVALID_PAYLOAD":         {"status": 400, "title": "Invalid Request Payload"},
    # Rate / Commerce
    "RATE_LIMITED":            {"status": 429, "title": "Rate Limit Exceeded"},
    "PLAN_LIMIT_EXCEEDED":     {"status": 402, "title": "Plan Limit Exceeded"},
    "COMMISSION_WALLET_EMPTY": {"status": 402, "title": "Commission Wallet Insufficient"},
    "SECURITY_DEPOSIT_REQUIRED":{"status": 402, "title": "Security Deposit Required"},
    # Serviceability — Customer Addresses
    "CUSTOMER_ADDRESS_NOT_FOUND":      {"status": 404, "title": "Customer Address Not Found"},
    "CUSTOMER_ADDRESS_ACCESS_DENIED":  {"status": 403, "title": "Customer Address Access Denied"},
    "CUSTOMER_ADDRESS_REQUIRED":       {"status": 422, "title": "Customer Address Required"},
    "INVALID_ZIPCODE":                 {"status": 422, "title": "Invalid Zipcode"},
    "INVALID_CITY":                    {"status": 422, "title": "Invalid City"},
    "DEFAULT_ADDRESS_REQUIRED":        {"status": 422, "title": "Default Address Required"},
    # Serviceability — Tenant Service Areas
    "TENANT_SERVICE_AREA_NOT_FOUND":          {"status": 404, "title": "Tenant Service Area Not Found"},
    "TENANT_SERVICE_AREA_ACCESS_DENIED":      {"status": 403, "title": "Tenant Service Area Access Denied"},
    "DUPLICATE_SERVICE_AREA":                 {"status": 409, "title": "Duplicate Service Area"},
    "INVALID_COVERAGE_TYPE":                  {"status": 422, "title": "Invalid Coverage Type"},
    "ZIPCODE_REQUIRED_FOR_ZIPCODE_COVERAGE":  {"status": 422, "title": "Zipcode Required for Zipcode Coverage"},
    "CITY_REQUIRED_FOR_CITY_COVERAGE":        {"status": 422, "title": "City Required for City Coverage"},
    "ZONE_REQUIRED_FOR_ZONE_COVERAGE":        {"status": 422, "title": "Zone Required for Zone Coverage"},
    "RADIUS_FIELDS_REQUIRED":                 {"status": 422, "title": "Radius Fields Required"},
    # Serviceability — Service Area Mappings
    "TENANT_SERVICE_AREA_SERVICE_NOT_FOUND":  {"status": 404, "title": "Service Area Mapping Not Found"},
    "DUPLICATE_SERVICE_AREA_SERVICE":         {"status": 409, "title": "Duplicate Service Area Mapping"},
    "SERVICE_NOT_FOUND":                      {"status": 404, "title": "Service Not Found"},
    "SERVICE_NOT_ACTIVE":                     {"status": 422, "title": "Service Not Active"},
    "INVALID_JOB_TYPE":                       {"status": 422, "title": "Invalid Job Type"},
    "INVALID_PRICE_RANGE":                    {"status": 422, "title": "Invalid Price Range"},
    "INVALID_SLA_MINUTES":                    {"status": 422, "title": "Invalid SLA Minutes"},
    # Serviceability — Matching (Step 3)
    "CITY_REQUIRED":                          {"status": 422, "title": "City Required"},
    "STATE_REQUIRED":                         {"status": 422, "title": "State Required"},
    "ZIPCODE_REQUIRED":                       {"status": 422, "title": "Zipcode Required"},
    "SERVICE_ID_REQUIRED":                    {"status": 422, "title": "Service ID Required"},
    "SERVICE_NOT_AVAILABLE_IN_AREA":          {"status": 200, "title": "Service Not Available In Area"},
    "NO_ACTIVE_TENANT_FOR_AREA":              {"status": 200, "title": "No Active Tenant For Area"},
    "INVALID_SERVICEABILITY_REQUEST":         {"status": 422, "title": "Invalid Serviceability Request"},
    "LOCATION_REQUIRED":                      {"status": 422, "title": "Location Required"},
    "LAT_LNG_REQUIRED_FOR_RADIUS":            {"status": 422, "title": "Latitude/Longitude Required For Radius"},
    "ZONE_MAPPING_NOT_CONFIGURED":            {"status": 200, "title": "Zone Mapping Not Configured"},
    # Booking — Step 4
    "BOOKING_NOT_FOUND":                {"status": 404, "title": "Booking Not Found"},
    "BOOKING_ACCESS_DENIED":            {"status": 404, "title": "Booking Not Found"},
    "BOOKING_CANNOT_BE_CANCELLED":      {"status": 409, "title": "Booking Cannot Be Cancelled"},
    "BOOKING_PREFLIGHT_FAILED":         {"status": 422, "title": "Booking Preflight Failed"},
    "BOOKING_CREATE_FAILED":            {"status": 422, "title": "Booking Creation Failed"},
    "SCHEDULED_TIME_IN_PAST":           {"status": 422, "title": "Scheduled Time In The Past"},
    "BOOKING_SLOT_NOT_AVAILABLE":       {"status": 409, "title": "Booking Slot Not Available"},
    "PRICING_NOT_CONFIGURED":           {"status": 422, "title": "Pricing Not Configured"},
    "SLA_NOT_CONFIGURED":               {"status": 422, "title": "SLA Not Configured"},
    "TENANT_INACTIVE":                  {"status": 422, "title": "Tenant Inactive"},
    "SERVICE_AREA_INACTIVE":            {"status": 422, "title": "Service Area Inactive"},
    "SERVICE_MAPPING_INACTIVE":         {"status": 422, "title": "Service Mapping Inactive"},
    "FRONTEND_TENANT_ID_NOT_ALLOWED":   {"status": 400, "title": "Frontend Tenant ID Not Allowed"},
    # Booking Step 5 — Confirmation / Rejection / Convert-to-Job
    "BOOKING_ALREADY_CONFIRMED":        {"status": 409, "title": "Booking Already Confirmed"},
    "BOOKING_ALREADY_REJECTED":         {"status": 409, "title": "Booking Already Rejected"},
    "BOOKING_ALREADY_CANCELLED":        {"status": 409, "title": "Booking Already Cancelled"},
    "BOOKING_ALREADY_CONVERTED":        {"status": 409, "title": "Booking Already Converted To Job"},
    "BOOKING_INVALID_STATUS_TRANSITION":{"status": 422, "title": "Invalid Booking Status Transition"},
    "BOOKING_REJECTION_REASON_REQUIRED":{"status": 422, "title": "Rejection Reason Required"},
    "BOOKING_CONFIRM_FAILED":           {"status": 422, "title": "Booking Confirmation Failed"},
    "BOOKING_REJECT_FAILED":            {"status": 422, "title": "Booking Rejection Failed"},
    "BOOKING_CONVERT_FAILED":           {"status": 422, "title": "Booking Conversion Failed"},
    "JOB_ALREADY_EXISTS_FOR_BOOKING":   {"status": 409, "title": "Job Already Exists For This Booking"},
    "JOB_CREATE_FAILED":                {"status": 422, "title": "Job Creation Failed"},
    "STAFF_NOT_FOUND":                  {"status": 404, "title": "Staff Not Found"},
    "STAFF_ACCESS_DENIED":              {"status": 403, "title": "Staff Access Denied"},
    "STAFF_INACTIVE":                   {"status": 422, "title": "Staff Member Is Inactive"},
    "INVALID_ASSIGNMENT_MODE":          {"status": 422, "title": "Invalid Assignment Mode"},
    "CUSTOMER_CANNOT_CONFIRM_BOOKING":  {"status": 403, "title": "Customer Cannot Confirm Booking"},
    "CUSTOMER_CANNOT_REJECT_BOOKING":   {"status": 403, "title": "Customer Cannot Reject Booking"},
    "CUSTOMER_CANNOT_CONVERT_BOOKING":  {"status": 403, "title": "Customer Cannot Convert Booking"},
    "TENANT_MISMATCH":                  {"status": 403, "title": "Tenant Mismatch"},
    "TRANSACTION_FAILED":               {"status": 500, "title": "Transaction Failed"},
    # Step 6 — Job Assignment + Staff Status Lifecycle
    "JOB_NOT_FOUND":                    {"status": 404, "title": "Job Not Found"},
    "JOB_ACCESS_DENIED":                {"status": 403, "title": "Job Access Denied"},
    "JOB_ASSIGNMENT_FAILED":            {"status": 422, "title": "Job Assignment Failed"},
    "JOB_ALREADY_ASSIGNED":             {"status": 409, "title": "Job Already Assigned"},
    "JOB_NOT_ASSIGNABLE":               {"status": 422, "title": "Job Not Assignable In Current Status"},
    "STAFF_TENANT_MISMATCH":            {"status": 403, "title": "Staff Belongs To A Different Tenant"},
    "STAFF_NOT_ASSIGNED_TO_JOB":        {"status": 403, "title": "Staff Not Assigned To This Job"},
    "INVALID_JOB_STATUS":               {"status": 422, "title": "Invalid Job Status"},
    "INVALID_JOB_STATUS_TRANSITION":    {"status": 422, "title": "Invalid Job Status Transition"},
    "JOB_ALREADY_COMPLETED":            {"status": 409, "title": "Job Already Completed"},
    "JOB_ALREADY_CANCELLED":            {"status": 409, "title": "Job Already Cancelled"},
    "JOB_STATUS_UPDATE_FAILED":         {"status": 422, "title": "Job Status Update Failed"},
    "JOB_REJECTION_REASON_REQUIRED":    {"status": 422, "title": "Job Rejection Reason Required"},
    "JOB_HISTORY_NOT_FOUND":            {"status": 404, "title": "Job History Not Found"},
    "CUSTOMER_JOB_ACCESS_DENIED":       {"status": 403, "title": "Customer Cannot Access This Job"},
    "TENANT_JOB_ACCESS_DENIED":         {"status": 403, "title": "Tenant Cannot Access This Job"},
    "CROSS_TENANT_ASSIGNMENT_BLOCKED":  {"status": 403, "title": "Cross-Tenant Staff Assignment Blocked"},
    # Step 7 — Job Type-Specific Flow (Repair / Service / Consultation)
    "INVALID_JOB_TYPE_TRANSITION":      {"status": 422, "title": "Invalid Job-Type-Specific Transition"},
    "ASSESSMENT_NOT_ALLOWED_FOR_SERVICE": {"status": 422, "title": "Assessment Not Allowed For Service Jobs"},
    "ASSESSMENT_REQUIRED_BEFORE_WORK":   {"status": 422, "title": "Assessment Required Before Work"},
    "ASSESSMENT_NOT_STARTED":            {"status": 422, "title": "Assessment Not Started"},
    "ASSESSMENT_ALREADY_COMPLETED":      {"status": 409, "title": "Assessment Already Completed"},
    "ASSESSMENT_FINDINGS_REQUIRED":      {"status": 422, "title": "Assessment Findings Required"},
    "QUOTE_REQUIRED_BEFORE_WORK":        {"status": 422, "title": "Quote Approval Required Before Work"},
    "QUOTE_NOT_FOUND":                   {"status": 404, "title": "Quote Not Found"},
    "QUOTE_ALREADY_SENT":                {"status": 409, "title": "Quote Already Sent"},
    "QUOTE_ALREADY_APPROVED":            {"status": 409, "title": "Quote Already Approved"},
    "QUOTE_ALREADY_REJECTED":            {"status": 409, "title": "Quote Already Rejected"},
    "QUOTE_APPROVAL_REQUIRED":           {"status": 422, "title": "Quote Approval Required"},
    "QUOTE_ACCESS_DENIED":               {"status": 403, "title": "Quote Access Denied"},
    "INVALID_QUOTE_AMOUNT":              {"status": 422, "title": "Invalid Quote Amount"},
    "WORK_NOT_ALLOWED_FOR_CONSULTATION": {"status": 422, "title": "Work Not Allowed For Consultation Jobs"},
    "CHECKLIST_REQUIRED_BEFORE_WORK_COMPLETE": {"status": 422, "title": "Checklist Required Before Work Complete"},
    "CHECKLIST_NOT_COMPLETE":            {"status": 422, "title": "Checklist Not Complete"},
    "CONSULTATION_CONVERSION_NOT_ALLOWED": {"status": 422, "title": "Consultation Conversion Not Allowed"},
    "CONSULTATION_ALREADY_CONVERTED":    {"status": 409, "title": "Consultation Already Converted"},
    "PARENT_JOB_NOT_FOUND":              {"status": 404, "title": "Parent Job Not Found"},
    "REPAIR_SERVICE_REQUIRED":           {"status": 422, "title": "Repair Service Required"},
    # Step 8 — Customer Quote Approval + Service Checklist UI/API
    "QUOTE_NOT_APPROVABLE":              {"status": 422, "title": "Quote Cannot Be Approved In Current Status"},
    "QUOTE_NOT_REJECTABLE":              {"status": 422, "title": "Quote Cannot Be Rejected In Current Status"},
    "QUOTE_REJECTION_REASON_REQUIRED":   {"status": 422, "title": "Quote Rejection Reason Required"},
    "QUOTE_APPROVAL_FAILED":             {"status": 422, "title": "Quote Approval Failed"},
    "QUOTE_REJECTION_FAILED":            {"status": 422, "title": "Quote Rejection Failed"},
    "CHECKLIST_TEMPLATE_NOT_FOUND":      {"status": 404, "title": "Checklist Template Not Found"},
    "CHECKLIST_TEMPLATE_ACCESS_DENIED":  {"status": 403, "title": "Checklist Template Access Denied"},
    "CHECKLIST_ITEM_NOT_FOUND":          {"status": 404, "title": "Checklist Item Not Found"},
    "CHECKLIST_ITEM_ACCESS_DENIED":      {"status": 403, "title": "Checklist Item Access Denied"},
    "CHECKLIST_NOT_FOUND_FOR_JOB":       {"status": 404, "title": "No Checklist Exists For This Job"},
    "CHECKLIST_REQUIRED":                {"status": 422, "title": "Checklist Required"},
    "CHECKLIST_ITEM_NOTE_REQUIRED":      {"status": 422, "title": "Checklist Item Note Required"},
    "CHECKLIST_ITEM_PHOTO_REQUIRED":     {"status": 422, "title": "Checklist Item Photo Required"},
    "CHECKLIST_ALREADY_COMPLETED":       {"status": 409, "title": "Checklist Already Completed"},
    "CHECKLIST_NOT_ALLOWED_FOR_JOB_TYPE": {"status": 422, "title": "Checklist Not Allowed For This Job Type"},
    "CHECKLIST_UPDATE_FAILED":           {"status": 422, "title": "Checklist Update Failed"},
    # Step 9 — Payment / Invoice / Commission Closure Flow
    "INVOICE_NOT_FOUND":                 {"status": 404, "title": "Invoice Not Found"},
    "INVOICE_ALREADY_EXISTS":            {"status": 409, "title": "Invoice Already Exists For This Job"},
    "INVOICE_ALREADY_PAID":              {"status": 409, "title": "Invoice Already Paid"},
    "INVOICE_GENERATION_FAILED":         {"status": 422, "title": "Invoice Generation Failed"},
    "INVALID_INVOICE_AMOUNT":            {"status": 422, "title": "Invalid Invoice Amount"},
    "PAYMENT_NOT_FOUND":                 {"status": 404, "title": "Payment Not Found"},
    "PAYMENT_AMOUNT_MISMATCH":           {"status": 422, "title": "Payment Amount Does Not Match Invoice Total"},
    "PAYMENT_ALREADY_RECORDED":          {"status": 409, "title": "Payment Already Recorded For This Job"},
    "PAYMENT_RECORD_FAILED":             {"status": 422, "title": "Payment Record Failed"},
    "PAYMENT_NOT_PAID":                  {"status": 422, "title": "Payment Is Not Marked Paid"},
    "INVALID_PAYMENT_METHOD":            {"status": 422, "title": "Invalid Payment Method"},
    "COMMISSION_NOT_FOUND":              {"status": 404, "title": "Commission Record Not Found"},
    "COMMISSION_ALREADY_DEDUCTED":       {"status": 409, "title": "Commission Already Deducted"},
    "COMMISSION_CALCULATION_FAILED":     {"status": 422, "title": "Commission Calculation Failed"},
    "COMMISSION_DEDUCTION_FAILED":       {"status": 422, "title": "Commission Deduction Failed"},
    "INSUFFICIENT_WALLET_BALANCE":       {"status": 402, "title": "Insufficient Wallet Balance"},
    "TENANT_WALLET_NOT_FOUND":           {"status": 404, "title": "Tenant Wallet Not Found"},
    "WALLET_LEDGER_CREATE_FAILED":       {"status": 422, "title": "Wallet Ledger Entry Creation Failed"},
    "JOB_NOT_SIGNED_OFF":                {"status": 422, "title": "Job Is Not Signed Off"},
    "JOB_NOT_READY_FOR_INVOICE":         {"status": 422, "title": "Job Is Not Ready For Invoicing"},
    "JOB_NOT_READY_FOR_PAYMENT":         {"status": 422, "title": "Job Is Not Ready For Payment"},
    "JOB_NOT_READY_FOR_CLOSE":           {"status": 422, "title": "Job Is Not Ready To Close"},
    "JOB_ALREADY_CLOSED":                {"status": 409, "title": "Job Already Closed"},
    "FINANCIAL_CLOSE_FAILED":            {"status": 422, "title": "Financial Close Failed"},
    "RAZORPAY_SIGNATURE_INVALID":        {"status": 400, "title": "Razorpay Signature Invalid"},
    "PAYMENT_WEBHOOK_FAILED":            {"status": 422, "title": "Payment Webhook Processing Failed"},
    # Sprint 3 — Admin Catalog + Pricing + Tenant Service Enablement
    "SERVICE_CATEGORY_NOT_FOUND":          {"status": 404, "title": "Service Category Not Found"},
    "SERVICE_CATEGORY_INACTIVE":           {"status": 422, "title": "Service Category Is Inactive"},
    "SERVICE_CATEGORY_NAME_REQUIRED":      {"status": 422, "title": "Service Category Name Required"},
    "SERVICE_CATEGORY_SLUG_DUPLICATE":     {"status": 409, "title": "Service Category Slug Already Exists"},
    "SERVICE_CATEGORY_HAS_ACTIVE_SERVICES":{"status": 409, "title": "Category Has Active Services"},
    "MASTER_SERVICE_NOT_FOUND":            {"status": 404, "title": "Master Service Not Found"},
    "MASTER_SERVICE_INACTIVE":             {"status": 422, "title": "Master Service Is Inactive"},
    "MASTER_SERVICE_NAME_REQUIRED":        {"status": 422, "title": "Master Service Name Required"},
    "MASTER_SERVICE_JOB_TYPE_REQUIRED":    {"status": 422, "title": "Job Type Required"},
    "INVALID_JOB_TYPE":                    {"status": 422, "title": "Invalid Job Type"},
    "INVALID_PRICING_MODEL":               {"status": 422, "title": "Invalid Pricing Model"},
    "INVALID_PRICE":                       {"status": 422, "title": "Price Cannot Be Negative"},
    "INVALID_PRICE_RANGE":                 {"status": 422, "title": "Min Price Cannot Exceed Max Price"},
    "SERVICE_TYPE_NOT_FOUND":              {"status": 404, "title": "Service Type Not Found"},
    "SERVICE_TYPE_INACTIVE":               {"status": 422, "title": "Service Type Is Inactive"},
    "SERVICE_TYPE_REQUIRED":               {"status": 422, "title": "Service Type Selection Required"},
    "SERVICE_TYPE_NOT_SUPPORTED":          {"status": 422, "title": "Service Type Not Supported By Tenant"},
    "SERVICE_TYPE_NAME_REQUIRED":          {"status": 422, "title": "Service Type Name Required"},
    "BRAND_NOT_FOUND":                     {"status": 404, "title": "Brand Not Found"},
    "BRAND_INACTIVE":                      {"status": 422, "title": "Brand Is Inactive"},
    "BRAND_REQUIRED":                      {"status": 422, "title": "Brand Selection Required"},
    "BRAND_NOT_SUPPORTED":                 {"status": 422, "title": "Brand Not Supported By Tenant"},
    "BRAND_NAME_REQUIRED":                 {"status": 422, "title": "Brand Name Required"},
    "TIER_NOT_FOUND":                      {"status": 404, "title": "Pricing Tier Not Found"},
    "TIER_INACTIVE":                       {"status": 422, "title": "Pricing Tier Is Inactive"},
    "TIER_NAME_REQUIRED":                  {"status": 422, "title": "Tier Name Required"},
    "TIER_CODE_REQUIRED":                  {"status": 422, "title": "Tier Code Required"},
    "TIER_CODE_DUPLICATE":                 {"status": 409, "title": "Tier Code Already Exists"},
    "TIER_INVALID_TYPE":                   {"status": 422, "title": "Invalid Tier Type"},
    "TIER_INVALID_MULTIPLIER":             {"status": 422, "title": "Base Multiplier Cannot Be Negative"},
    "TIER_LOCATION_NOT_FOUND":             {"status": 404, "title": "Tier Location Not Found"},
    "TIER_LOCATION_CITY_OR_ZIP":           {"status": 422, "title": "City Or Zipcode Required"},
    "PRICING_RULE_NOT_FOUND":              {"status": 404, "title": "Pricing Rule Not Found"},
    "PRICING_RULE_DUPLICATE":              {"status": 409, "title": "Duplicate Pricing Rule"},
    "PRICING_RULE_INACTIVE":               {"status": 422, "title": "Pricing Rule Is Inactive"},
    "PRICING_RULE_SERVICE_REQUIRED":       {"status": 422, "title": "master_service_id Required"},
    "PRICE_RESOLUTION_FAILED":             {"status": 422, "title": "Price Resolution Failed"},
    "MAPPING_DUPLICATE":                   {"status": 409, "title": "Mapping Already Exists"},
    "TENANT_SERVICE_NOT_FOUND":            {"status": 404, "title": "Tenant Service Not Found"},
    "TENANT_SERVICE_ALREADY_ENABLED":      {"status": 409, "title": "Service Already Enabled For Tenant"},
    "TENANT_SERVICE_NOT_ENABLED":          {"status": 404, "title": "Service Not Enabled For Tenant"},
    "TENANT_SERVICE_OVERRIDE_NOT_ALLOWED": {"status": 422, "title": "Price Override Not Allowed For This Service"},
    "TENANT_PRICE_BELOW_ADMIN_MIN":        {"status": 422, "title": "Tenant Price Below Admin Minimum"},
    "TENANT_PRICE_ABOVE_ADMIN_MAX":        {"status": 422, "title": "Tenant Price Exceeds Admin Maximum"},
    # Job assignment (home services dispatch)
    "JOB_ASSIGNMENT_JOB_NOT_FOUND":        {"status": 404, "title": "Job Not Found"},
    "JOB_ASSIGNMENT_STAFF_NOT_FOUND":      {"status": 404, "title": "Staff Member Not Found"},
    "JOB_ASSIGNMENT_ASSIGNMENT_NOT_FOUND": {"status": 404, "title": "No Active Assignment"},
    "JOB_ASSIGNMENT_ACCESS_DENIED":        {"status": 403, "title": "Access Denied"},
    "JOB_ASSIGNMENT_STAFF_WRONG_TENANT":   {"status": 403, "title": "Staff Member Belongs To Another Organization"},
    "JOB_ASSIGNMENT_STAFF_INACTIVE":       {"status": 422, "title": "Staff Member Is Inactive"},
    "JOB_ASSIGNMENT_ROLE_NOT_ALLOWED":     {"status": 422, "title": "Role Not Eligible For Field Assignment"},
    "JOB_ASSIGNMENT_STAFF_NOT_ELIGIBLE":   {"status": 422, "title": "Staff Member Not Eligible For This Job"},
    "JOB_ASSIGNMENT_INVALID_STATUS":       {"status": 422, "title": "Job Not In A Valid State"},
    "JOB_ASSIGNMENT_REASON_REQUIRED":      {"status": 422, "title": "Reason Required"},
    "JOB_ASSIGNMENT_REASSIGN_NOT_ALLOWED": {"status": 409, "title": "Cannot Reassign An Accepted Job"},
    "JOB_ASSIGNMENT_CANCEL_NOT_ALLOWED":   {"status": 409, "title": "Cannot Cancel An Accepted Assignment"},
    "JOB_ASSIGNMENT_JOB_CANCELLED":        {"status": 409, "title": "Job Is Cancelled"},
    "JOB_ASSIGNMENT_JOB_COMPLETED":        {"status": 409, "title": "Job Is Already Completed"},
    "JOB_ASSIGNMENT_SLOT_UNAVAILABLE":     {"status": 409, "title": "Slot No Longer Available"},
    "JOB_ASSIGNMENT_NOT_FOUND":             {"status": 404, "title": "Assignment Not Found"},
    "JOB_ASSIGNMENT_BOOKING_NOT_FOUND":     {"status": 404, "title": "Booking Not Found"},
    "JOB_ASSIGNMENT_ALREADY_ASSIGNED":      {"status": 409, "title": "Job Is Already Assigned"},
    "JOB_ASSIGNMENT_CONFLICT":              {"status": 409, "title": "Assignment Conflict"},
    "JOB_ASSIGNMENT_STALE_VERSION":         {"status": 409, "title": "Assignment Changed — Reload And Retry"},
    "JOB_ASSIGNMENT_RESCHEDULE_NOT_ALLOWED":{"status": 422, "title": "Reschedule Not Allowed"},
    "JOB_ASSIGNMENT_RESCHEDULE_LIMIT_REACHED": {"status": 422, "title": "Reschedule Limit Reached"},
    "JOB_ASSIGNMENT_INVALID_REASON":        {"status": 422, "title": "Invalid Reason"},
    "JOB_ASSIGNMENT_PAST_DATE":             {"status": 422, "title": "Date Is In The Past"},
    "JOB_ASSIGNMENT_LOCATION_NOT_TRACKABLE":{"status": 422, "title": "Location Not Trackable"},
    "JOB_ASSIGNMENT_LOCATION_INVALID_COORDS": {"status": 422, "title": "Invalid Coordinates"},
    "STAFF_JOB_NOT_ASSIGNED_TO_USER":       {"status": 403, "title": "Job Not Assigned To You"},
    "STAFF_JOB_ALREADY_ACCEPTED":           {"status": 409, "title": "Job Already Accepted"},
    "STAFF_JOB_ALREADY_REJECTED":           {"status": 409, "title": "Job Already Rejected"},
    # Reports
    "REPORT_FORMAT_UNSUPPORTED": {"status": 422, "title": "Export Format Not Supported"},
    "REPORT_ASYNC_REQUIRED":     {"status": 422, "title": "Report Too Large For Immediate Export"},
    "REPORT_TOO_LARGE":          {"status": 422, "title": "Report Too Large"},
    # Messaging gateway
    "HANDOFF_LINK_INVALID":    {"status": 404, "title": "Handoff Link Expired Or Already Used"},
    # Async
    "ASYNC_JOB_PENDING":       {"status": 202, "title": "Request Accepted — Processing"},
    # Server
    "INTERNAL_ERROR":          {"status": 500, "title": "Internal Server Error"},
    "SERVICE_UNAVAILABLE":     {"status": 503, "title": "Service Temporarily Unavailable"},
}


def make_problem(
    error_code: str,
    detail: str,
    instance: str | None = None,
    blocking_rule: str | None = None,
    resolution: str | None = None,
    request_id: str | None = None,
    context: dict[str, Any] | None = None,
    allowed_transitions: list[AllowedTransition] | None = None,
) -> ProblemDetail:
    info = ERROR_CODES.get(error_code, {"status": 500, "title": "Unknown Error"})
    return ProblemDetail(
        type=f"{BASE_URL}/{error_code}",
        title=info["title"],
        status=info["status"],
        detail=detail,
        instance=instance,
        error_code=error_code,
        blocking_rule=blocking_rule,
        resolution=resolution,
        request_id=request_id,
        context=context,
        allowed_transitions=allowed_transitions,
    )


# ── Response Builders ─────────────────────────────────────────────────────────
def ok(
    data: Any,
    request_id: str,
    engine_id: str | None = None,
    tenant_id: str | None = None,
    links: Links | None = None,
    idempotent: bool = False,
) -> ApiResponse:
    """Convenience builder for standard success responses."""
    return ApiResponse(
        data=data,
        links=links,
        meta=Meta(
            request_id=request_id,
            engine_id=engine_id,
            tenant_id=tenant_id,
            idempotent=idempotent,
        ),
    )


def paginated(
    items: list,
    total: int | None,
    limit: int,
    next_cursor: str | None,
    prev_cursor: str | None,
    request_id: str,
    engine_id: str | None = None,
    base_url: str = "",
) -> PaginatedResponse:
    """Convenience builder for paginated list responses."""
    return PaginatedResponse(
        data=CursorPage(
            items=items,
            total=total,
            limit=limit,
            has_next=next_cursor is not None,
            has_prev=prev_cursor is not None,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            links={
                "next": f"{base_url}?cursor={next_cursor}&limit={limit}" if next_cursor else None,
                "prev": f"{base_url}?cursor={prev_cursor}&limit={limit}" if prev_cursor else None,
            },
        ),
        meta=Meta(request_id=request_id, engine_id=engine_id),
    )


# ── Cursor Encoding ───────────────────────────────────────────────────────────
import base64
import json as _json


def encode_cursor(data: dict) -> str:
    return base64.urlsafe_b64encode(_json.dumps(data).encode()).decode()


def decode_cursor(cursor: str) -> dict:
    try:
        return _json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
    except Exception:
        from app.exceptions import ServiceOSException
        raise ServiceOSException("INVALID_PAYLOAD", "Invalid cursor value.")
