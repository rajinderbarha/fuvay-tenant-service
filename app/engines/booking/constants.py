"""Booking Engine — constants."""
import hashlib

# ── Booking lifecycle statuses ─────────────────────────────────────────────
class BS:
    DRAFT                = "draft"
    PENDING_CONFIRMATION = "pending_confirmation"  # Step 4: initial status for all customer bookings
    PENDING              = "pending"
    CONFIRMED            = "confirmed"
    REJECTED             = "rejected"              # Step 5: tenant rejected the booking
    CONVERTED_TO_JOB     = "converted_to_job"     # Step 5: booking converted to a field ops job
    SCHEDULED            = "scheduled"
    DISPATCHING          = "dispatching"
    IN_PROGRESS          = "in_progress"
    COMPLETED            = "completed"
    CANCELLED            = "cancelled"
    EXPIRED              = "expired"
    VOIDED               = "voided"

# ── Allowed transitions ────────────────────────────────────────────────────
BOOKING_TRANSITIONS: dict[str, list[str]] = {
    BS.DRAFT:               [BS.PENDING_CONFIRMATION, BS.PENDING, BS.CANCELLED],
    BS.PENDING_CONFIRMATION:[BS.CONFIRMED, BS.REJECTED, BS.CANCELLED, BS.EXPIRED],
    BS.PENDING:             [BS.CONFIRMED, BS.REJECTED, BS.CANCELLED, BS.EXPIRED],
    BS.CONFIRMED:           [BS.CONVERTED_TO_JOB, BS.SCHEDULED, BS.CANCELLED],
    BS.REJECTED:            [],
    BS.CONVERTED_TO_JOB:    [BS.COMPLETED],
    BS.SCHEDULED:           [BS.DISPATCHING, BS.CANCELLED],
    BS.DISPATCHING:         [BS.IN_PROGRESS, BS.CANCELLED],
    BS.IN_PROGRESS:         [BS.COMPLETED, BS.CANCELLED],
    BS.COMPLETED:           [],
    BS.CANCELLED:           [],
    BS.EXPIRED:             [],
    BS.VOIDED:              [],
}

TERMINAL_BOOKING_STATUSES = [
    BS.COMPLETED, BS.CANCELLED, BS.EXPIRED, BS.VOIDED,
    BS.REJECTED, BS.CONVERTED_TO_JOB,
]

# ── Preflight checks (ordered — fail-fast) ─────────────────────────────────
class PreflightCheck:
    TENANT_ACTIVE       = "tenant_active"
    ZONE_COVERAGE       = "zone_coverage"
    SLOT_AVAILABLE      = "slot_available"
    CAPACITY_LIMIT      = "capacity_limit"
    COMMERCE_PREFLIGHT  = "commerce_preflight"

# ── Idempotency window ─────────────────────────────────────────────────────
BOOKING_IDEM_WINDOW_MINUTES = 5

# ── Default cancellation window ────────────────────────────────────────────
DEFAULT_CANCELLATION_WINDOW_HOURS = 24
MAX_RESCHEDULE_COUNT = 3

# ── Redis keys ─────────────────────────────────────────────────────────────
REDIS_BOOKING_IDEM   = "serviceos:booking:idem:{idem_key}"
REDIS_SLOT_LOCK      = "serviceos:booking:slot:{tenant_id}:{date}:{slot}"
REDIS_BOOKING_COUNT  = "serviceos:booking:count:{tenant_id}:{date}"

def make_booking_idempotency_key(customer_id: str, tenant_id: str,
                                   service_type_id: str, scheduled_date: str) -> str:
    raw = f"{customer_id}:{tenant_id}:{service_type_id}:{scheduled_date}"
    return hashlib.sha256(raw.encode()).hexdigest()[:64]
