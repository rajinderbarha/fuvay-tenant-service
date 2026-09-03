"""TENANT-HS-DIRECT-PAYMENTS-01 — constants for the Home Services
direct-payment confirmation / reconciliation workflow.

Fuvay never collects, holds, settles or transfers this money and never
creates a payout for it. Every name in this module is about RECORDING a
customer-to-provider payment, not moving one.
"""
from __future__ import annotations

# ── Reconciliation status (canonical, computed server-side) ──────────────────
RS_NOT_REQUIRED       = "not_required"
RS_AWAITING_PROVIDER  = "awaiting_provider"
RS_AWAITING_CUSTOMER  = "awaiting_customer"
RS_CONFIRMED          = "confirmed"
RS_MISMATCHED         = "mismatched"
RS_DISPUTED           = "disputed"
RS_CANCELLED          = "cancelled"
RS_REVERSED           = "reversed"

RECONCILIATION_STATUSES = {
    RS_NOT_REQUIRED, RS_AWAITING_PROVIDER, RS_AWAITING_CUSTOMER,
    RS_CONFIRMED, RS_MISMATCHED, RS_DISPUTED, RS_CANCELLED, RS_REVERSED,
}

# Legal server-side transitions. The frontend NEVER writes a status string --
# it calls an action endpoint and the service derives the next state.
RECONCILIATION_TRANSITIONS: dict[str, set[str]] = {
    RS_NOT_REQUIRED:      {RS_AWAITING_PROVIDER},
    RS_AWAITING_PROVIDER: {RS_AWAITING_CUSTOMER, RS_CANCELLED},
    RS_AWAITING_CUSTOMER: {RS_CONFIRMED, RS_MISMATCHED, RS_DISPUTED, RS_CANCELLED},
    RS_MISMATCHED:        {RS_AWAITING_CUSTOMER, RS_DISPUTED, RS_CONFIRMED, RS_CANCELLED},
    RS_DISPUTED:          {RS_CONFIRMED, RS_REVERSED, RS_CANCELLED},
    RS_CONFIRMED:         {RS_DISPUTED, RS_REVERSED},
    RS_CANCELLED:         set(),
    RS_REVERSED:          set(),
}

STATUS_LABELS = {
    RS_NOT_REQUIRED:      "Not required",
    RS_AWAITING_PROVIDER: "Awaiting provider",
    RS_AWAITING_CUSTOMER: "Awaiting customer",
    RS_CONFIRMED:         "Confirmed",
    RS_MISMATCHED:        "Mismatched",
    RS_DISPUTED:          "Disputed",
    RS_CANCELLED:         "Cancelled",
    RS_REVERSED:          "Reversed",
}

# ── Direct payment methods ──────────────────────────────────────────────────
# Deliberately the same vocabulary as invoice_payment.constants
# VALID_PAYMENT_MODES so the canonical ServicePaymentRecord writer keeps
# working -- Fuvay-collected online gateway payments are NOT a direct
# payment and are excluded here.
DP_METHOD_CASH          = "onsite_cash"
DP_METHOD_UPI           = "onsite_upi"
DP_METHOD_CARD          = "onsite_card"
DP_METHOD_BANK_TRANSFER = "onsite_bank_transfer"
DP_METHOD_OTHER         = "onsite_other"

DIRECT_PAYMENT_METHODS = {
    DP_METHOD_CASH, DP_METHOD_UPI, DP_METHOD_CARD,
    DP_METHOD_BANK_TRANSFER, DP_METHOD_OTHER,
}

METHOD_LABELS = {
    DP_METHOD_CASH:          "Cash",
    DP_METHOD_UPI:           "UPI",
    DP_METHOD_CARD:          "Card (provider terminal)",
    DP_METHOD_BANK_TRANSFER: "Bank transfer",
    DP_METHOD_OTHER:         "Other (direct)",
}

# ── Customer confirmation actions ───────────────────────────────────────────
CA_CONFIRM            = "confirm"
CA_DIFFERENT_AMOUNT   = "different_amount"
CA_NOT_PAID           = "not_paid"
CA_DIFFERENT_METHOD   = "different_method"
CA_CLARIFICATION      = "request_clarification"

CUSTOMER_ACTIONS = {
    CA_CONFIRM, CA_DIFFERENT_AMOUNT, CA_NOT_PAID,
    CA_DIFFERENT_METHOD, CA_CLARIFICATION,
}

MISMATCH_ACTIONS = {CA_DIFFERENT_AMOUNT, CA_NOT_PAID, CA_DIFFERENT_METHOD}

# ── Evidence ────────────────────────────────────────────────────────────────
EV_PROVIDER_RECEIPT   = "provider_receipt"
EV_UPI_REFERENCE      = "upi_reference"
EV_CASH_RECEIPT       = "cash_receipt"
EV_BANK_REFERENCE     = "bank_transfer_reference"
EV_CUSTOMER_ACK       = "customer_acknowledgement"

EVIDENCE_TYPES = {
    EV_PROVIDER_RECEIPT, EV_UPI_REFERENCE, EV_CASH_RECEIPT,
    EV_BANK_REFERENCE, EV_CUSTOMER_ACK,
}

# ── Reminder policy ─────────────────────────────────────────────────────────
REMINDER_MIN_INTERVAL_HOURS = 12
REMINDER_MAX_PER_RECORD     = 5
# Escalation window after which an unresponsive customer becomes an
# actionable admin escalation rather than an indefinitely stuck job. Never
# auto-confirms.
CUSTOMER_NONRESPONSE_ESCALATION_DAYS = 7

# ── Amount tolerance ────────────────────────────────────────────────────────
# Zero tolerance: any difference between expected and declared is a real
# mismatch requiring a reason. No silent rounding-away of money.
AMOUNT_TOLERANCE = "0.00"

# ── Job statuses that make a direct-payment declaration eligible ────────────
# Work must be done before a payment can be declared against it.
WORK_DONE_JOB_STATUSES = {"work_done", "completed", "payment_pending", "awaiting_payment"}

# ── Notification event keys (registered in platform_notifications) ──────────
EVT_DP_CONFIRMATION_REQUESTED = "payment.confirmation_requested"
EVT_DP_MISMATCH_REPORTED      = "payment.mismatch_reported"
EVT_DP_CONFIRMED_BY_CUSTOMER  = "payment.confirmed_by_customer"

# ── Financial event types (audit trail on financial_events) ─────────────────
FEV_DP_DECLARED       = "direct_payment_declared"
FEV_DP_CORRECTED      = "direct_payment_declaration_corrected"
FEV_DP_REMINDER_SENT  = "direct_payment_reminder_sent"
FEV_DP_CONFIRMED      = "direct_payment_customer_confirmed"
FEV_DP_MISMATCH       = "direct_payment_mismatch_reported"
FEV_DP_DISPUTE_OPENED = "direct_payment_dispute_opened"

# ── Error codes ─────────────────────────────────────────────────────────────
ERR_DP_NOT_FOUND              = "DIRECT_PAYMENT_NOT_FOUND"
ERR_DP_JOB_NOT_FOUND          = "DIRECT_PAYMENT_JOB_NOT_FOUND"
ERR_DP_WORK_NOT_DONE          = "DIRECT_PAYMENT_WORK_NOT_DONE"
ERR_DP_ALREADY_DECLARED       = "DIRECT_PAYMENT_ALREADY_DECLARED"
ERR_DP_INVALID_METHOD         = "DIRECT_PAYMENT_INVALID_METHOD"
ERR_DP_INVALID_AMOUNT         = "DIRECT_PAYMENT_INVALID_AMOUNT"
ERR_DP_REASON_REQUIRED        = "DIRECT_PAYMENT_DIFFERENCE_REASON_REQUIRED"
ERR_DP_EXPECTED_UNRESOLVED    = "DIRECT_PAYMENT_EXPECTED_AMOUNT_UNRESOLVED"
ERR_DP_NO_APPROVED_ESTIMATE   = "DIRECT_PAYMENT_NO_APPROVED_ESTIMATE"
ERR_DP_STALE_VERSION          = "DIRECT_PAYMENT_STALE_VERSION"
ERR_DP_LOCKED_AFTER_CONFIRM   = "DIRECT_PAYMENT_LOCKED_AFTER_CONFIRMATION"
ERR_DP_LOCKED_BY_DISPUTE      = "DIRECT_PAYMENT_LOCKED_BY_DISPUTE"
ERR_DP_REMINDER_RATE_LIMITED  = "DIRECT_PAYMENT_REMINDER_RATE_LIMITED"
ERR_DP_ALREADY_CONFIRMED      = "DIRECT_PAYMENT_ALREADY_CONFIRMED"
ERR_DP_DISPUTE_EXISTS         = "DIRECT_PAYMENT_DISPUTE_ALREADY_OPEN"
ERR_DP_INVALID_ACTION         = "DIRECT_PAYMENT_INVALID_CUSTOMER_ACTION"
ERR_DP_ACCESS_DENIED          = "DIRECT_PAYMENT_ACCESS_DENIED"
ERR_DP_INVALID_EVIDENCE_TYPE  = "DIRECT_PAYMENT_INVALID_EVIDENCE_TYPE"

# ── Policy guidance shown in the UI (single source of truth) ────────────────
POLICY_BULLETS = [
    "Fuvay does not collect, hold, settle or pay out job money. "
    "We only record confirmation.",
    "Amount must match the approved estimate after visit-fee adjustment.",
    "No wallet credit, no security deposit, no platform revenue.",
    "All communication happens through Fuvay.",
    "No payout or settlement is created.",
]

BANNER_TEXT = ("Fuvay does not collect this money. "
               "Customers pay your business directly.")

FOOTER_DISCLAIMER = ("All confirmations are recorded securely within Fuvay. "
                     "We never share or request personal contact details.")

SENSITIVE_EVIDENCE_WARNING = (
    "Never upload card numbers, CVV, UPI PIN, OTP, net-banking passwords or "
    "any full bank credentials."
)

# ── Workflow tracker steps (5, in order) ────────────────────────────────────
WORKFLOW_STEPS = [
    ("work_done",         "Work done"),
    ("provider_declares", "Provider records payment"),
    ("customer_confirms", "Customer confirms"),
    ("reconciled",        "Reconciled"),
    ("job_completed",     "Job completed"),
]
