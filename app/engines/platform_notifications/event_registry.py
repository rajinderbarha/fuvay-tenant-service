"""Sprint 27 — Notification Event Registry.

Defines what event keys exist, which channels they use by default,
who receives them, and which template to render.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable

from app.engines.platform_notifications.constants import (
    CHANNEL_IN_APP, CHANNEL_EMAIL, CHANNEL_SMS, CHANNEL_PUSH,
    RECIP_CUSTOMER, RECIP_PROVIDER, RECIP_STAFF, RECIP_ADMIN,
    SEV_INFO, SEV_SUCCESS, SEV_WARNING, SEV_CRITICAL,
    EVT_BOOKING_CONFIRMED, EVT_JOB_CREATED, EVT_JOB_ASSIGNED,
    EVT_JOB_ACCEPTED, EVT_JOB_REJECTED, EVT_JOB_SCHEDULED,
    EVT_JOB_ON_THE_WAY, EVT_JOB_REACHED_SITE, EVT_JOB_INSPECTION_STARTED,
    EVT_JOB_QUOTE_REQUIRED, EVT_JOB_WORK_DONE, EVT_JOB_COMPLETED,
    EVT_QUOTE_SENT, EVT_QUOTE_APPROVED, EVT_QUOTE_REJECTED, EVT_QUOTE_REVISION,
    EVT_INVOICE_ISSUED, EVT_PAYMENT_COLLECTED, EVT_COMMISSION_DEDUCTED,
    EVT_COMMISSION_FAILED, EVT_WALLET_LOW, EVT_WALLET_EXHAUSTED,
    EVT_APPT_CONFIRMED, EVT_APPT_ACCEPTED, EVT_APPT_STARTED,
    EVT_APPT_COMPLETED, EVT_APPT_NO_SHOW,
    EVT_LEAD_CREATED, EVT_LEAD_ACCEPTED, EVT_LEAD_CONTACTED,
    EVT_LEAD_FOLLOW_UP, EVT_LEAD_SITE_VISIT,
    EVT_REVIEW_SUBMITTED, EVT_REVIEW_APPROVED, EVT_REVIEW_REJECTED,
    EVT_REVIEW_FLAGGED, EVT_REVIEW_REPLY,
    EVT_COMPLAINT_CREATED, EVT_COMPLAINT_RESPONDED, EVT_COMPLAINT_RESOLUTION,
    EVT_COMPLAINT_REWORK, EVT_COMPLAINT_REFUND, EVT_COMPLAINT_RESOLVED,
    EVT_AUTH_LOGIN_SUCCESS, EVT_AUTH_LOGIN_FAILED,
    EVT_TENANT_VERIFIED, EVT_TENANT_SUSPENDED,
    EVT_ENGINE_ENABLED, EVT_ENGINE_DISABLED,
    EVT_CATEGORY_ENABLED, EVT_CATEGORY_DISABLED,
    EVT_CHAT_NEW_MESSAGE,
)


@dataclass
class NotificationEventConfig:
    event_key:          str
    event_name:         str
    source_engine:      str
    default_channels:   list[str]
    primary_recipient:  str          # customer | provider | staff | admin
    template_key:       str          # {event_key}.in_app suffix convention
    severity:           str = SEV_INFO
    is_enabled:         bool = True
    also_notify:        list[str] = field(default_factory=list)  # additional recipient types


_REGISTRY: dict[str, NotificationEventConfig] = {}


def _reg(cfg: NotificationEventConfig) -> None:
    _REGISTRY[cfg.event_key] = cfg


# ── Home Service ──────────────────────────────────────────────────────────────
_reg(NotificationEventConfig(EVT_BOOKING_CONFIRMED, "Booking Confirmed",
     "home_service", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "booking.confirmed.in_app", SEV_SUCCESS,
     also_notify=[RECIP_PROVIDER]))

_reg(NotificationEventConfig(EVT_JOB_CREATED, "Job Created",
     "home_service", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "job.created.in_app"))

_reg(NotificationEventConfig(EVT_JOB_ASSIGNED, "Technician Assigned",
     "home_service", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "job.assigned.in_app", also_notify=[RECIP_STAFF]))

_reg(NotificationEventConfig(EVT_JOB_ACCEPTED, "Job Accepted by Tech",
     "home_service", [CHANNEL_IN_APP], RECIP_PROVIDER,
     "job.accepted.in_app", also_notify=[RECIP_CUSTOMER]))

_reg(NotificationEventConfig(EVT_JOB_REJECTED, "Job Rejected by Tech",
     "home_service", [CHANNEL_IN_APP], RECIP_PROVIDER,
     "job.accepted.in_app"))

_reg(NotificationEventConfig(EVT_JOB_SCHEDULED, "Job Scheduled",
     "home_service", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "job.scheduled.in_app"))

_reg(NotificationEventConfig(EVT_JOB_ON_THE_WAY, "Technician On the Way",
     "home_service", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "job.assigned.in_app"))

_reg(NotificationEventConfig(EVT_JOB_REACHED_SITE, "Technician Reached Site",
     "home_service", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "job.assigned.in_app"))

_reg(NotificationEventConfig(EVT_JOB_INSPECTION_STARTED, "Inspection Started",
     "home_service", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "job.assigned.in_app"))

_reg(NotificationEventConfig(EVT_JOB_QUOTE_REQUIRED, "Quote Required",
     "home_service", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "quote.sent_to_customer.in_app"))

_reg(NotificationEventConfig(EVT_JOB_WORK_DONE, "Work Done",
     "home_service", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "job.completed.in_app"))

_reg(NotificationEventConfig(EVT_JOB_COMPLETED, "Job Completed",
     "home_service", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "job.completed.in_app", SEV_SUCCESS,
     also_notify=[RECIP_PROVIDER]))

# ── Quote ─────────────────────────────────────────────────────────────────────
_reg(NotificationEventConfig(EVT_QUOTE_SENT, "Quote Sent to Customer",
     "quote_checklist", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "quote.sent_to_customer.in_app"))

_reg(NotificationEventConfig(EVT_QUOTE_APPROVED, "Quote Approved by Customer",
     "quote_checklist", [CHANNEL_IN_APP], RECIP_PROVIDER,
     "quote.customer_approved.in_app"))

_reg(NotificationEventConfig(EVT_QUOTE_REJECTED, "Quote Rejected by Customer",
     "quote_checklist", [CHANNEL_IN_APP], RECIP_PROVIDER,
     "quote.customer_rejected.in_app", SEV_WARNING))

_reg(NotificationEventConfig(EVT_QUOTE_REVISION, "Quote Revision Requested",
     "quote_checklist", [CHANNEL_IN_APP], RECIP_PROVIDER,
     "quote.customer_rejected.in_app"))

# ── Invoice / Payment ─────────────────────────────────────────────────────────
_reg(NotificationEventConfig(EVT_INVOICE_ISSUED, "Invoice Issued",
     "invoice_payment", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "invoice.issued.in_app"))

_reg(NotificationEventConfig(EVT_PAYMENT_COLLECTED, "Payment Collected",
     "invoice_payment", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "payment.collected.in_app", SEV_SUCCESS,
     also_notify=[RECIP_PROVIDER]))

_reg(NotificationEventConfig(EVT_COMMISSION_DEDUCTED, "Commission Deducted",
     "invoice_payment", [CHANNEL_IN_APP], RECIP_PROVIDER,
     "payment.collected.in_app"))

_reg(NotificationEventConfig(EVT_COMMISSION_FAILED, "Commission Deduction Failed",
     "invoice_payment", [CHANNEL_IN_APP], RECIP_ADMIN,
     "wallet.low_balance.in_app", SEV_CRITICAL))

_reg(NotificationEventConfig(EVT_WALLET_LOW, "Wallet Low Balance",
     "invoice_payment", [CHANNEL_IN_APP], RECIP_PROVIDER,
     "wallet.low_balance.in_app", SEV_WARNING))

_reg(NotificationEventConfig(EVT_WALLET_EXHAUSTED, "Wallet Exhausted",
     "invoice_payment", [CHANNEL_IN_APP], RECIP_PROVIDER,
     "wallet.low_balance.in_app", SEV_CRITICAL))

# ── Coaching ──────────────────────────────────────────────────────────────────
_reg(NotificationEventConfig(EVT_APPT_CONFIRMED, "Appointment Confirmed",
     "coaching_appointment", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "appointment.confirmed.in_app", SEV_SUCCESS,
     also_notify=[RECIP_PROVIDER]))

_reg(NotificationEventConfig(EVT_APPT_ACCEPTED, "Appointment Accepted",
     "coaching_appointment", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "appointment.confirmed.in_app"))

_reg(NotificationEventConfig(EVT_APPT_STARTED, "Session Started",
     "coaching_appointment", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "appointment.completed.in_app"))

_reg(NotificationEventConfig(EVT_APPT_COMPLETED, "Session Completed",
     "coaching_appointment", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "appointment.completed.in_app", SEV_SUCCESS))

_reg(NotificationEventConfig(EVT_APPT_NO_SHOW, "No Show",
     "coaching_appointment", [CHANNEL_IN_APP], RECIP_PROVIDER,
     "appointment.completed.in_app", SEV_WARNING))

# ── Real Estate ───────────────────────────────────────────────────────────────
_reg(NotificationEventConfig(EVT_LEAD_CREATED, "New Lead Created",
     "real_estate", [CHANNEL_IN_APP], RECIP_PROVIDER,
     "lead.created.in_app"))

_reg(NotificationEventConfig(EVT_LEAD_ACCEPTED, "Lead Accepted",
     "real_estate", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "lead.accepted.in_app"))

_reg(NotificationEventConfig(EVT_LEAD_CONTACTED, "Lead Contacted",
     "real_estate", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "lead.accepted.in_app"))

_reg(NotificationEventConfig(EVT_LEAD_FOLLOW_UP, "Follow-up Scheduled",
     "real_estate", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "lead.accepted.in_app"))

_reg(NotificationEventConfig(EVT_LEAD_SITE_VISIT, "Site Visit Planned",
     "real_estate", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "lead.accepted.in_app"))

# ── Review ────────────────────────────────────────────────────────────────────
_reg(NotificationEventConfig(EVT_REVIEW_SUBMITTED, "Review Submitted",
     "customer_reviews", [CHANNEL_IN_APP], RECIP_PROVIDER,
     "review.submitted.in_app"))

_reg(NotificationEventConfig(EVT_REVIEW_APPROVED, "Review Approved",
     "customer_reviews", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "review.approved.in_app"))

_reg(NotificationEventConfig(EVT_REVIEW_REJECTED, "Review Rejected",
     "customer_reviews", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "review.approved.in_app", SEV_WARNING))

_reg(NotificationEventConfig(EVT_REVIEW_FLAGGED, "Review Flagged",
     "customer_reviews", [CHANNEL_IN_APP], RECIP_ADMIN,
     "review.submitted.in_app", SEV_WARNING))

_reg(NotificationEventConfig(EVT_REVIEW_REPLY, "Review Reply",
     "customer_reviews", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "review.approved.in_app"))

# ── Complaint ─────────────────────────────────────────────────────────────────
_reg(NotificationEventConfig(EVT_COMPLAINT_CREATED, "Complaint Filed",
     "complaints", [CHANNEL_IN_APP], RECIP_PROVIDER,
     "complaint.created.in_app", SEV_WARNING,
     also_notify=[RECIP_ADMIN]))

_reg(NotificationEventConfig(EVT_COMPLAINT_RESPONDED, "Complaint Response",
     "complaints", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "complaint.provider_responded.in_app"))

_reg(NotificationEventConfig(EVT_COMPLAINT_RESOLUTION, "Resolution Proposed",
     "complaints", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "complaint.provider_responded.in_app"))

_reg(NotificationEventConfig(EVT_COMPLAINT_REWORK, "Rework Approved",
     "complaints", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "complaint.resolved.in_app", SEV_SUCCESS))

_reg(NotificationEventConfig(EVT_COMPLAINT_REFUND, "Refund Approved",
     "complaints", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "complaint.refund_approved.in_app", SEV_SUCCESS))

_reg(NotificationEventConfig(EVT_COMPLAINT_RESOLVED, "Complaint Resolved",
     "complaints", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "complaint.resolved.in_app", SEV_SUCCESS))

# ── System / Admin ────────────────────────────────────────────────────────────
_reg(NotificationEventConfig(EVT_AUTH_LOGIN_FAILED, "Login Failed",
     "auth", [CHANNEL_IN_APP], RECIP_ADMIN,
     "tenant.suspended.in_app", SEV_WARNING))

_reg(NotificationEventConfig(EVT_TENANT_VERIFIED, "Provider Verified",
     "tenant_engine", [CHANNEL_IN_APP], RECIP_PROVIDER,
     "tenant.verified.in_app", SEV_SUCCESS))

_reg(NotificationEventConfig(EVT_TENANT_SUSPENDED, "Provider Suspended",
     "tenant_engine", [CHANNEL_IN_APP], RECIP_PROVIDER,
     "tenant.suspended.in_app", SEV_CRITICAL))

_reg(NotificationEventConfig(EVT_CHAT_NEW_MESSAGE, "New Chat Message",
     "platform_notifications", [CHANNEL_IN_APP], RECIP_CUSTOMER,
     "chat.new_message.in_app"))


class NotificationEventRegistry:

    @classmethod
    def get(cls, event_key: str) -> NotificationEventConfig | None:
        return _REGISTRY.get(event_key)

    @classmethod
    def all_keys(cls) -> list[str]:
        return list(_REGISTRY.keys())

    @classmethod
    def get_all(cls) -> dict[str, NotificationEventConfig]:
        return dict(_REGISTRY)
