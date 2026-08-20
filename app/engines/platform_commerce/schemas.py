"""Platform Commerce Engine — Pydantic v2 Schemas."""
import uuid
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


# ── Deposit ───────────────────────────────────────────────────────────────────
class DepositStatusResponse(BaseModel):
    tenant_id: str
    status: str
    required_amount: Decimal
    total_paid: Decimal
    warranty_drawn: Decimal
    replenishment_total: Decimal
    current_balance: Decimal
    is_unlocked: bool
    paid_at: str | None

class DepositInitiateRequest(BaseModel):
    gateway: Literal["razorpay", "stripe"] = "razorpay"

class DepositConfirmRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class DepositAdminAdjustRequest(BaseModel):
    amount: Decimal = Field(description="Positive=credit, negative=debit")
    reason: str = Field(min_length=10, max_length=500)
    category: Literal["goodwill", "dispute", "correction", "refund"]

# ── Credit Packages ───────────────────────────────────────────────────────────
class CreatePackageRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None
    credits_amount: Decimal = Field(gt=0)
    price_inr: Decimal = Field(gt=0)
    bonus_pct: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    validity_days: int | None = Field(None, ge=1, le=3650)
    plan_restriction: str | None = None
    sort_order: int = 0

class UpdatePackageRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = None
    price_inr: Decimal | None = Field(None, gt=0)
    bonus_pct: Decimal | None = Field(None, ge=0, le=100)
    is_active: bool | None = None
    sort_order: int | None = None

class PackageResponse(BaseModel):
    package_id: str
    name: str
    description: str | None
    credits_amount: Decimal
    price_inr: Decimal
    bonus_pct: Decimal
    total_credits: Decimal
    validity_days: int | None
    plan_restriction: str | None
    is_active: bool
    sort_order: int
    purchase_count: int

# ── Wallet ────────────────────────────────────────────────────────────────────
class PurchaseInitiateRequest(BaseModel):
    package_id: uuid.UUID
    gateway: Literal["razorpay", "stripe"] = "razorpay"

class PurchaseConfirmRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    package_id: uuid.UUID

class ManualCreditRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    reason: str = Field(min_length=20, max_length=500)
    category: Literal["goodwill", "refund", "dispute", "correction"]

class WalletResponse(BaseModel):
    tenant_id: str
    credit_balance: Decimal
    lifetime_purchased: Decimal
    lifetime_consumed: Decimal
    last_transaction_at: str | None
    burn_rate_daily: Decimal
    projected_days_remaining: int | None
    low_balance_alert: bool

class TransactionItem(BaseModel):
    txn_id: str
    txn_type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    reference_id: str | None
    reference_type: str | None
    description: str | None
    created_at: str

# ── Commission ────────────────────────────────────────────────────────────────
class CommissionRateResponse(BaseModel):
    tenant_id: str
    base_rate: Decimal
    health_adjustment: Decimal
    effective_rate: Decimal
    health_band: str
    plan_type: str
    next_review_at: str

class CommissionDeductRequest(BaseModel):
    job_id: str = Field(min_length=1, max_length=100)
    job_value: Decimal = Field(gt=0)
    tenant_id: uuid.UUID
    description: str | None = None

class CommissionRecordResponse(BaseModel):
    record_id: str
    job_id: str
    effective_rate: Decimal
    job_value: Decimal
    commission_amount: Decimal
    wallet_balance_before: Decimal
    wallet_balance_after: Decimal
    health_band_at_time: str
    deducted_at: str
    idempotent: bool = False

# ── Customer Health ───────────────────────────────────────────────────────────
class CustomerHealthResponse(BaseModel):
    customer_id: str
    tenant_id: str
    score: Decimal
    band: str
    can_book: bool
    advance_required_pct: Decimal
    signals: dict
    computed_at: str

class UpdateHealthSignalRequest(BaseModel):
    signal_name: str
    value: float = Field(ge=0.0, le=100.0)
    event_ref: str = Field(description="Idempotency — same event_ref does not re-apply signal")
    event_type: str | None = None

class HealthOverrideRequest(BaseModel):
    override_band: str
    reason: str = Field(min_length=10, max_length=500)
    expires_days: int = Field(ge=1, le=365)

# ── Reservations ──────────────────────────────────────────────────────────────
class ReservationCreateRequest(BaseModel):
    customer_id: uuid.UUID
    tenant_id: uuid.UUID
    booking_id: str
    advance_pct: Decimal = Field(ge=0, le=100)
    booking_value: Decimal = Field(gt=0)

class ReservationResponse(BaseModel):
    reservation_id: str
    booking_id: str
    reserved_amount: Decimal
    status: str
    expires_at: str
    new_available_balance: Decimal

# ── Warranty ──────────────────────────────────────────────────────────────────
class WarrantyClaimRequest(BaseModel):
    job_id: str
    claim_type: str = "service_quality"
    description: str = Field(min_length=20, max_length=2000)
    media_ids: list[str] = Field(default_factory=list)
    amount_requested: Decimal | None = Field(None, gt=0)

class WarrantyProviderResponseRequest(BaseModel):
    resolution: str = Field(min_length=10, max_length=2000)
    resolved: bool = False

class WarrantyEscalationRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)

class ClaimResolveRequest(BaseModel):
    amount_approved: Decimal | None = Field(None, ge=0)
    admin_notes: str = Field(min_length=5, max_length=1000)
    rejection_reason: str | None = None

# ── Pre-flight ────────────────────────────────────────────────────────────────
class PreflightRequest(BaseModel):
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    estimated_job_value: Decimal = Field(gt=0)
    booking_id: str | None = None

class PreflightResponse(BaseModel):
    allowed: bool
    blocking_check: str | None
    blocking_reason: str | None
    advance_required_pct: Decimal
    estimated_advance_amount: Decimal
    estimated_commission: Decimal
    tenant_wallet_sufficient: bool
    customer_can_book: bool
    allowed_transitions: list[dict]
