"""Sprint 23 — Invoice / Payment / Commission / Subscription constants."""

# ── Invoice statuses ──────────────────────────────────────────────────────────
INV_DRAFT              = "draft"
INV_ISSUED             = "issued"
INV_PAYMENT_PENDING    = "payment_pending"
INV_PAYMENT_COLLECTED  = "payment_collected"
INV_PAID               = "paid"
INV_CANCELLED          = "cancelled"
INV_FAILED             = "failed"

INVOICE_FINAL_STATUSES = {INV_PAYMENT_COLLECTED, INV_PAID, INV_CANCELLED, INV_FAILED}

# ── Invoice transitions ───────────────────────────────────────────────────────
INVOICE_TRANSITIONS: dict[str, set[str]] = {
    INV_DRAFT:             {INV_ISSUED, INV_CANCELLED},
    INV_ISSUED:            {INV_PAYMENT_PENDING, INV_PAYMENT_COLLECTED, INV_PAID, INV_CANCELLED},
    INV_PAYMENT_PENDING:   {INV_PAYMENT_COLLECTED, INV_PAID, INV_FAILED, INV_CANCELLED},
    INV_PAYMENT_COLLECTED: set(),
    INV_PAID:              set(),
    INV_CANCELLED:         set(),
    INV_FAILED:            {INV_ISSUED},
}

# ── Invoice sources ───────────────────────────────────────────────────────────
INV_SRC_APPROVED_QUOTE  = "approved_quote"
INV_SRC_MANUAL_FINAL    = "manual_final"
INV_SRC_BOOKING_BASE    = "booking_base_price"

VALID_INVOICE_SOURCES = {INV_SRC_APPROVED_QUOTE, INV_SRC_MANUAL_FINAL, INV_SRC_BOOKING_BASE}

# ── Payment modes ─────────────────────────────────────────────────────────────
PAY_MODE_ONSITE_CASH  = "onsite_cash"
PAY_MODE_ONSITE_UPI   = "onsite_upi"
PAY_MODE_ONSITE_CARD  = "onsite_card"
PAY_MODE_ONLINE       = "online"
PAY_MODE_NOT_REQUIRED = "not_required"

VALID_PAYMENT_MODES = {
    PAY_MODE_ONSITE_CASH, PAY_MODE_ONSITE_UPI, PAY_MODE_ONSITE_CARD,
    PAY_MODE_ONLINE, PAY_MODE_NOT_REQUIRED,
}

ONSITE_PAYMENT_MODES = {PAY_MODE_ONSITE_CASH, PAY_MODE_ONSITE_UPI, PAY_MODE_ONSITE_CARD}

# ── Payment statuses ──────────────────────────────────────────────────────────
PAY_STATUS_PENDING      = "pending"
PAY_STATUS_COLLECTED    = "collected"
PAY_STATUS_VERIFIED     = "verified"
PAY_STATUS_FAILED       = "failed"
PAY_STATUS_DISPUTED     = "disputed"
PAY_STATUS_NOT_REQUIRED = "not_required"

# ── Commission statuses ───────────────────────────────────────────────────────
COM_PENDING             = "pending"
COM_CALCULATED          = "calculated"
COM_DEDUCTED            = "deducted"
COM_FAILED              = "failed"
COM_INSUFFICIENT_CREDIT = "insufficient_credit"
COM_REVERSED            = "reversed"
COM_NOT_REQUIRED        = "not_required"

# ── Financial event types ─────────────────────────────────────────────────────
FEV_INVOICE_CREATED       = "invoice_created"
FEV_INVOICE_ISSUED        = "invoice_issued"
FEV_INVOICE_CANCELLED     = "invoice_cancelled"
FEV_PAYMENT_RECORDED      = "payment_recorded"
FEV_PAYMENT_VERIFIED      = "payment_verified"
FEV_COMMISSION_CALCULATED = "commission_calculated"
FEV_COMMISSION_DEDUCTED   = "commission_deducted"
FEV_COMMISSION_FAILED     = "commission_failed"
FEV_WALLET_LOW_BALANCE    = "wallet_low_balance"
FEV_WALLET_EXHAUSTED      = "wallet_exhausted"
FEV_SUBSCRIPTION_CHECKED  = "subscription_checked"
FEV_SUBSCRIPTION_INACTIVE = "subscription_inactive"
FEV_COMMISSION_REVERSED   = "commission_reversed"

# ── Default commission rate (pct) — overridden by category/offering config ────
DEFAULT_COMMISSION_RATE = 10  # 10%

# ── Job statuses triggered by invoice events ──────────────────────────────────
JOB_STATUS_INVOICE_ISSUED = "invoice_issued"

# ── Error codes ───────────────────────────────────────────────────────────────
ERR_INVOICE_NOT_FOUND             = "INVOICE_NOT_FOUND"
ERR_INVOICE_ACCESS_DENIED         = "INVOICE_ACCESS_DENIED"
ERR_INVOICE_ALREADY_EXISTS        = "INVOICE_ALREADY_EXISTS"
ERR_INVOICE_INVALID_STATUS        = "INVOICE_INVALID_STATUS"
ERR_INVOICE_CREATE_FAILED         = "INVOICE_CREATE_FAILED"
ERR_INVOICE_ITEM_INVALID          = "INVOICE_ITEM_INVALID"
ERR_INVOICE_TOTAL_INVALID         = "INVOICE_TOTAL_INVALID"
ERR_INVOICE_ALREADY_ISSUED        = "INVOICE_ALREADY_ISSUED"
ERR_INVALID_PAYMENT_MODE          = "INVALID_PAYMENT_MODE"
ERR_INVOICE_CANCELLED             = "INVOICE_CANCELLED"
ERR_PAYMENT_RECORD_NOT_FOUND      = "PAYMENT_RECORD_NOT_FOUND"
ERR_PAYMENT_ACCESS_DENIED         = "PAYMENT_ACCESS_DENIED"
ERR_PAYMENT_AMOUNT_MISMATCH       = "PAYMENT_AMOUNT_MISMATCH"
ERR_PAYMENT_ALREADY_RECORDED      = "PAYMENT_ALREADY_RECORDED"
ERR_PAYMENT_RECORD_FAILED         = "PAYMENT_RECORD_FAILED"
ERR_COMMISSION_RULE_NOT_FOUND     = "COMMISSION_RULE_NOT_FOUND"
ERR_COMMISSION_CALCULATION_FAILED = "COMMISSION_CALCULATION_FAILED"
ERR_COMMISSION_ALREADY_DEDUCTED   = "COMMISSION_ALREADY_DEDUCTED"
ERR_COMMISSION_INSUFFICIENT_CREDIT = "COMMISSION_INSUFFICIENT_CREDIT"
ERR_COMMISSION_DEDUCTION_FAILED   = "COMMISSION_DEDUCTION_FAILED"
ERR_COMMISSION_RETRY_NOT_ALLOWED  = "COMMISSION_RETRY_NOT_ALLOWED"
ERR_COMMISSION_REVERSAL_REASON    = "COMMISSION_REVERSAL_REASON_REQUIRED"
ERR_COMMISSION_NOT_REVERSIBLE     = "COMMISSION_NOT_REVERSIBLE"
ERR_WALLET_NOT_FOUND              = "WALLET_NOT_FOUND"
ERR_WALLET_INSUFFICIENT_BALANCE   = "WALLET_INSUFFICIENT_BALANCE"
ERR_WALLET_DEBIT_FAILED           = "WALLET_DEBIT_FAILED"
ERR_SUBSCRIPTION_NOT_FOUND        = "SUBSCRIPTION_STATUS_NOT_FOUND"
ERR_SUBSCRIPTION_INACTIVE         = "SUBSCRIPTION_INACTIVE"
