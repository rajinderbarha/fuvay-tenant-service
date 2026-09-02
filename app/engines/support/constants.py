"""TENANT-SUPPORT canonical constants: categories, lifecycle, impact→priority
derivation and SLA policy.

SUPPORT vs COMPLAINT BOUNDARY (audited, deliberate):
  * app/engines/complaints -> CustomerComplaint: a CUSTOMER disputes or
    complains about a service job delivered by a tenant. Actors: customer,
    provider, ServiceOS mediator. Has refunds/rework/settlement.
  * this engine -> SupportTicket: a PROVIDER BUSINESS (tenant) needs help
    from ServiceOS about its own account or the platform. Actors: tenant
    user, ServiceOS support/ops. Has SLA, triage, incidents. No refund or
    settlement semantics.
Separate tables, separate routes, separate statuses, separate SLA. They are
NOT merged, and the tenant Support UI links out to Complaints instead of
accepting job complaints.
"""
from __future__ import annotations

# ── Lifecycle (server-side state machine, section 11) ────────────────────────
ST_DRAFT                = "draft"
ST_SUBMITTED            = "submitted"
ST_TRIAGED              = "triaged"
ST_ASSIGNED             = "assigned"
ST_INVESTIGATING        = "investigating"
ST_WAITING_FOR_TENANT   = "waiting_for_tenant"
ST_WAITING_FOR_SERVICEOS= "waiting_for_serviceos"
ST_RESOLVED             = "resolved"
ST_CLOSED               = "closed"
ST_REOPENED             = "reopened"
ST_WITHDRAWN            = "withdrawn"

STATUSES = [
    ST_DRAFT, ST_SUBMITTED, ST_TRIAGED, ST_ASSIGNED, ST_INVESTIGATING,
    ST_WAITING_FOR_TENANT, ST_WAITING_FOR_SERVICEOS, ST_RESOLVED, ST_CLOSED,
    ST_REOPENED, ST_WITHDRAWN,
]

OPEN_STATUSES = [
    ST_SUBMITTED, ST_TRIAGED, ST_ASSIGNED, ST_INVESTIGATING,
    ST_WAITING_FOR_TENANT, ST_WAITING_FOR_SERVICEOS, ST_REOPENED,
]

STATUS_LABELS = {
    ST_DRAFT: "Draft", ST_SUBMITTED: "Submitted", ST_TRIAGED: "Triaged",
    ST_ASSIGNED: "Assigned", ST_INVESTIGATING: "Investigating",
    ST_WAITING_FOR_TENANT: "Awaiting your reply",
    ST_WAITING_FOR_SERVICEOS: "With ServiceOS support",
    ST_RESOLVED: "Resolved", ST_CLOSED: "Closed", ST_REOPENED: "Reopened",
    ST_WITHDRAWN: "Withdrawn",
}

# Admin-driven transitions. Tenant transitions are restricted separately below.
ADMIN_TRANSITIONS: dict[str, list[str]] = {
    ST_SUBMITTED:             [ST_TRIAGED, ST_ASSIGNED, ST_INVESTIGATING, ST_WAITING_FOR_TENANT, ST_RESOLVED],
    ST_TRIAGED:               [ST_ASSIGNED, ST_INVESTIGATING, ST_WAITING_FOR_TENANT, ST_RESOLVED],
    ST_ASSIGNED:              [ST_INVESTIGATING, ST_WAITING_FOR_TENANT, ST_RESOLVED],
    ST_INVESTIGATING:         [ST_WAITING_FOR_TENANT, ST_WAITING_FOR_SERVICEOS, ST_RESOLVED],
    ST_WAITING_FOR_TENANT:    [ST_INVESTIGATING, ST_WAITING_FOR_SERVICEOS, ST_RESOLVED],
    ST_WAITING_FOR_SERVICEOS: [ST_INVESTIGATING, ST_WAITING_FOR_TENANT, ST_RESOLVED],
    ST_RESOLVED:              [ST_CLOSED, ST_REOPENED],
    ST_REOPENED:              [ST_TRIAGED, ST_ASSIGNED, ST_INVESTIGATING, ST_WAITING_FOR_TENANT, ST_RESOLVED],
    ST_CLOSED:                [],
    ST_DRAFT:                 [],
    ST_WITHDRAWN:             [],
}

# ── Categories (section 8) ──────────────────────────────────────────────────
CATEGORIES: list[dict] = [
    {"key": "account_access",     "label": "Account & access",             "area": "account_security",  "security_sensitive": True},
    {"key": "onboarding",         "label": "Onboarding & verification",    "area": "getting_started"},
    {"key": "profile_documents",  "label": "Business profile & documents", "area": "getting_started"},
    {"key": "bookings_jobs",      "label": "Bookings & jobs",              "area": "bookings_jobs",     "operational": True},
    {"key": "dispatch",           "label": "Dispatch & technicians",       "area": "bookings_jobs",     "operational": True},
    {"key": "services_pricing",   "label": "Services & pricing",           "area": "services_pricing"},
    {"key": "coverage",           "label": "Coverage",                     "area": "services_pricing"},
    {"key": "finance_credits",    "label": "Finance & credits",            "area": "finance_credits"},
    {"key": "direct_payments",    "label": "Direct-payment records",       "area": "finance_credits"},
    {"key": "notifications",      "label": "Notifications",                "area": "account_security"},
    {"key": "integrations",       "label": "Integrations",                 "area": "account_security"},
    {"key": "security",           "label": "Security",                     "area": "account_security",  "security_sensitive": True},
    {"key": "technical",          "label": "Technical issue",              "area": "bookings_jobs",     "operational": True},
    {"key": "other",              "label": "Other",                        "area": "getting_started"},
]
CATEGORY_KEYS = [c["key"] for c in CATEGORIES]
CATEGORY_MAP = {c["key"]: c for c in CATEGORIES}

SUBCATEGORY_SUGGESTIONS: dict[str, list[str]] = {
    "account_access":    ["Cannot sign in", "Locked out", "Password reset", "Team member cannot access"],
    "onboarding":        ["Verification pending too long", "Document rejected unclear", "Activation blocked"],
    "profile_documents":  ["Document upload fails", "Wrong business details", "Expiry not updating"],
    "bookings_jobs":     ["Booking not appearing", "Job stuck in a status", "Cannot complete job"],
    "dispatch":          ["Technician not assignable", "Availability wrong", "Auto-dispatch not matching"],
    "services_pricing":  ["Price not applying", "Service option missing", "Cannot publish service"],
    "coverage":          ["Area not bookable", "Pincode missing", "Coverage saved but not live"],
    "finance_credits":   ["Usage credit not credited", "Top-up or seat issue", "Invoice looks wrong"],
    "direct_payments":   ["Cash record not reconciling", "Payment record rejected"],
    "notifications":     ["Not receiving notifications", "Duplicate notifications"],
    "integrations":      ["Webhook failing", "API errors"],
    "security":          ["Suspicious activity", "Unauthorised access", "Data concern"],
    "technical":         ["Page error", "Slow or timing out", "Data not loading"],
    "other":             ["General question"],
}

# ── Quick help categories (section 6) ───────────────────────────────────────
PRODUCT_AREAS: list[dict] = [
    {"key": "getting_started",  "label": "Getting started",     "icon": "rocket",   "description": "Set up your business, verification and go live.",       "href": "/help-support?tab=knowledge&area=getting_started"},
    {"key": "bookings_jobs",    "label": "Bookings & jobs",     "icon": "wrench",   "description": "Booking flow, job lifecycle, dispatch and completion.", "href": "/help-support?tab=knowledge&area=bookings_jobs"},
    {"key": "team_access",      "label": "Team & access",       "icon": "users",    "description": "Invite staff, roles, permissions and technician access.","href": "/help-support?tab=knowledge&area=team_access"},
    {"key": "services_pricing", "label": "Services & pricing",  "icon": "tag",      "description": "Service catalogue, options, pricing rules and coverage.","href": "/help-support?tab=knowledge&area=services_pricing"},
    {"key": "finance_credits",  "label": "Finance & credits",   "icon": "wallet",   "description": "Usage credits, top-up plans, technician seats and invoices.", "href": "/help-support?tab=knowledge&area=finance_credits"},
    {"key": "account_security", "label": "Account & security",  "icon": "shield",   "description": "Sign-in, notifications, integrations and data safety.",  "href": "/help-support?tab=knowledge&area=account_security"},
]

# ── Impact (tenant-chosen) → priority (backend-derived), section 10 ──────────
IMPACT_QUESTION        = "question"
IMPACT_ONE_USER        = "one_user_affected"
IMPACT_SOME_OPERATIONS = "some_operations_affected"
IMPACT_BUSINESS_BLOCKED= "business_blocked"
IMPACTS = [IMPACT_QUESTION, IMPACT_ONE_USER, IMPACT_SOME_OPERATIONS, IMPACT_BUSINESS_BLOCKED]
IMPACT_LABELS = {
    IMPACT_QUESTION:         "Question — nothing is blocked",
    IMPACT_ONE_USER:         "One user affected",
    IMPACT_SOME_OPERATIONS:  "Some operations affected",
    IMPACT_BUSINESS_BLOCKED: "Business blocked — cannot operate",
}

PRIORITY_LOW      = "low"
PRIORITY_NORMAL   = "normal"
PRIORITY_HIGH     = "high"
PRIORITY_URGENT   = "urgent"
PRIORITY_CRITICAL = "critical"
PRIORITIES = [PRIORITY_LOW, PRIORITY_NORMAL, PRIORITY_HIGH, PRIORITY_URGENT, PRIORITY_CRITICAL]
_PRIORITY_RANK = {p: i for i, p in enumerate(PRIORITIES)}

_IMPACT_BASE = {
    IMPACT_QUESTION:          PRIORITY_LOW,
    IMPACT_ONE_USER:          PRIORITY_NORMAL,
    IMPACT_SOME_OPERATIONS:   PRIORITY_HIGH,
    IMPACT_BUSINESS_BLOCKED:  PRIORITY_URGENT,
}


def derive_priority(
    impact: str,
    category: str,
    *,
    is_critical_incident: bool = False,
    active_incident: bool = False,
) -> tuple[str, list[str]]:
    """Backend-only priority derivation. The tenant NEVER submits priority.

    Returns (priority, reasons) so the derivation is explainable in the
    audit trail and in the admin queue.
    """
    reasons: list[str] = []
    pri = _IMPACT_BASE.get(impact, PRIORITY_NORMAL)
    reasons.append(f"impact={impact} -> {pri}")

    cat = CATEGORY_MAP.get(category, {})
    if cat.get("security_sensitive") and _PRIORITY_RANK[pri] < _PRIORITY_RANK[PRIORITY_HIGH]:
        pri = PRIORITY_HIGH
        reasons.append("security-sensitive category raises to high")
    if cat.get("operational") and impact in (IMPACT_SOME_OPERATIONS, IMPACT_BUSINESS_BLOCKED):
        if _PRIORITY_RANK[pri] < _PRIORITY_RANK[PRIORITY_URGENT]:
            pri = PRIORITY_URGENT
            reasons.append("operational capability affected raises to urgent")
    if active_incident:
        reasons.append("linked to an active platform incident")
        if _PRIORITY_RANK[pri] < _PRIORITY_RANK[PRIORITY_HIGH]:
            pri = PRIORITY_HIGH
    if is_critical_incident:
        pri = PRIORITY_CRITICAL
        reasons.append("reported through the critical incident channel")
    return pri, reasons


# ── SLA policy (section 12) — real, conservative, stated in hours ────────────
SLA_POLICY_NAME = "serviceos_standard_support_v1"
# priority -> (first response hrs, next update hrs, resolution target hrs|None)
SLA_TARGETS: dict[str, tuple[int, int, int | None]] = {
    PRIORITY_LOW:      (24, 48, None),
    PRIORITY_NORMAL:   (12, 24, 120),
    PRIORITY_HIGH:     (6,  12, 48),
    PRIORITY_URGENT:   (2,   4, 24),
    PRIORITY_CRITICAL: (1,   2,  8),
}

BREACH_OK        = "on_track"
BREACH_AT_RISK   = "at_risk"
BREACH_BREACHED  = "breached"
BREACH_PAUSED    = "paused"
BREACH_MET       = "met"
BREACH_NA        = "not_applicable"

# Reopen window, backend-controlled (section 11)
REOPEN_WINDOW_DAYS = 14

# Critical incident rate limit (section 17)
CRITICAL_INCIDENT_MAX_PER_WINDOW = 2
CRITICAL_INCIDENT_WINDOW_HOURS = 24
CRITICAL_INCIDENT_IMPACTS = [
    ("cannot_access",      "Cannot access ServiceOS at all"),
    ("major_outage",       "Major outage affecting active operations"),
    ("data_loss",          "Confirmed data loss or corruption"),
    ("security_incident",  "Serious security incident"),
    ("booking_failure",    "Platform-wide booking or dispatch failure"),
]
CRITICAL_INCIDENT_IMPACT_KEYS = [k for k, _ in CRITICAL_INCIDENT_IMPACTS]

# ── Service status (section 4) ──────────────────────────────────────────────
STATUS_OPERATIONAL   = "operational"
STATUS_DEGRADED      = "degraded"
STATUS_MAJOR         = "major_incident"
STATUS_MAINTENANCE   = "maintenance"
STATUS_UNAVAILABLE   = "unavailable"

INCIDENT_SEVERITY_TO_STATUS = {
    "maintenance": STATUS_MAINTENANCE,
    "minor":       STATUS_DEGRADED,
    "major":       STATUS_MAJOR,
}

# ── Message/author kinds (section 13) ───────────────────────────────────────
MSG_TENANT              = "tenant_message"
MSG_SUPPORT             = "serviceos_response"
MSG_SYSTEM              = "system_event"
MSG_INFO_REQUEST        = "information_request"
MSG_RESOLUTION          = "resolution_summary"
MSG_INTERNAL_NOTE       = "internal_note"   # NEVER returned on tenant endpoints
TENANT_VISIBLE_MESSAGE_KINDS = [MSG_TENANT, MSG_SUPPORT, MSG_SYSTEM, MSG_INFO_REQUEST, MSG_RESOLUTION]

# ── Attachments (section 14) ───────────────────────────────────────────────
SUPPORT_MEDIA_CONTEXT = "support_attachment"
BLOCKED_ATTACHMENT_EXTENSIONS = {
    "exe", "bat", "cmd", "com", "cpl", "dll", "js", "jse", "jar", "lnk",
    "msi", "ps1", "reg", "scr", "sh", "vbs", "vbe", "wsf", "hta", "apk",
}
ALLOWED_ATTACHMENT_MIME_PREFIXES = ("image/", "text/", "application/pdf")
ALLOWED_ATTACHMENT_MIME_EXTRA = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel", "application/zip", "application/json",
}
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
ATTACHMENT_PRIVACY_WARNING = (
    "Never upload passwords, OTPs, card or UPI credentials, private keys, or "
    "customer identity documents. Share only the evidence needed to "
    "reproduce the problem — reference IDs are enough."
)

# ── Announcements (section 16) ─────────────────────────────────────────────
ANNOUNCEMENT_TYPES = [
    "planned_maintenance", "feature_release", "policy_update",
    "known_issue", "resolved_incident", "vertical_notice",
]

# ── Notification event keys (section 19) ───────────────────────────────────
EV_SUBMITTED        = "support.request.submitted"
EV_REPLIED          = "support.request.replied"
EV_INFO_REQUESTED   = "support.request.info_requested"
EV_PRIORITY_CHANGED = "support.request.priority_changed"
EV_SLA_BREACHED     = "support.request.sla_breached"
EV_RESOLVED         = "support.request.resolved"
EV_REOPENED         = "support.request.reopened"
EV_CRITICAL         = "support.incident.critical_reported"
EV_ANNOUNCEMENT     = "support.announcement.published"

DEEP_LINK = "/help-support?tab=requests&ticket={ticket_id}"
