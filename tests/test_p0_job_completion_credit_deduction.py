"""
P0 Job Completion + Provider Collection + Usage Credit Deduction Verification Sprint
Static source-inspection style, consistent with test_p0_customer_service_credit.py /
test_p0_settings_enterprise.py conventions in this repo — no live DB fixture required.

Regression coverage for bugs found and fixed live this sprint:
1. Job model never carried credit_applied/payable_amount from its originating Booking.
2. record_payment() never validated the collected amount against job.payable_amount.
3. Booking never reached status=completed once its job financially closed — a dead end
   in BOOKING_TRANSITIONS left admin/tenant/customer views stuck at "converted_to_job".
4. field_ops staff_router/router rejected the real seeded role "technician" everywhere
   (only ever checked for the literal string "staff").
5. ROLE_PERMISSIONS had no "technician" entry at all — every real technician account
   got zero permissions from role defaults, silently blocking generate-invoice/
   record-payment/close (all gated on P.FIELD_OPS_JOBS_CLOSE).
6. payment_records table was missing 8 columns the PaymentRecord model declares
   (job_id, payment_number, payment_method, payment_status, collected_by_user_id,
   collected_by_staff_id, paid_at, notes) — every real record_payment() call 500'd.
"""
import os

ROOT              = os.path.dirname(os.path.dirname(__file__))
JOB_MODELS        = os.path.join(ROOT, "app", "engines", "field_ops", "models.py")
FIELD_OPS_SERVICE = os.path.join(ROOT, "app", "engines", "field_ops", "service.py")
BILLING_SERVICE   = os.path.join(ROOT, "app", "engines", "field_ops", "billing_service.py")
FIELD_OPS_ROUTER  = os.path.join(ROOT, "app", "engines", "field_ops", "router.py")
STAFF_ROUTER      = os.path.join(ROOT, "app", "engines", "field_ops", "staff_router.py")
BOOKING_SERVICE   = os.path.join(ROOT, "app", "engines", "booking", "service.py")
BOOKING_CONSTANTS = os.path.join(ROOT, "app", "engines", "booking", "constants.py")
PERMISSIONS       = os.path.join(ROOT, "app", "core", "permissions.py")
MIGRATION_093     = os.path.join(ROOT, "alembic", "versions", "093_job_credit_applied_fields.py")
MIGRATION_094     = os.path.join(ROOT, "alembic", "versions", "094_payment_records_job_fields.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Migrations ───────────────────────────────────────────────────────────────

def test_migration_093_exists_and_chains_from_092():
    assert os.path.exists(MIGRATION_093)
    src = _read(MIGRATION_093)
    assert 'revision = "093"' in src
    assert 'down_revision = "092"' in src


def test_migration_093_adds_job_credit_fields():
    src = _read(MIGRATION_093)
    assert '"jobs"' in src
    assert "credit_applied" in src
    assert "payable_amount" in src


def test_migration_094_exists_and_chains_from_093():
    assert os.path.exists(MIGRATION_094)
    src = _read(MIGRATION_094)
    assert 'revision = "094"' in src
    assert 'down_revision = "093"' in src


def test_migration_094_adds_all_missing_payment_columns():
    src = _read(MIGRATION_094)
    for col in ("job_id", "payment_number", "payment_method", "payment_status",
                "collected_by_user_id", "collected_by_staff_id", "paid_at", "notes"):
        assert f'"{col}"' in src, f"migration 094 missing column {col}"


# ── Job model ────────────────────────────────────────────────────────────────

def test_job_model_has_credit_fields():
    src = _read(JOB_MODELS)
    assert "credit_applied:" in src
    assert "payable_amount:" in src


def test_job_model_importable():
    import importlib
    mod = importlib.import_module("app.engines.field_ops.models")
    assert hasattr(mod, "Job")


# ── Booking -> Job propagation ───────────────────────────────────────────────

def test_convert_to_job_copies_credit_fields_from_booking():
    src = _read(BOOKING_SERVICE)
    body = src.split("async def convert_to_job")[1].split("\n    async def ")[0]
    assert "credit_applied=b.credit_applied" in body
    assert "payable_amount=b.payable_amount" in body


# ── Staff job detail exposes correct payment breakdown ──────────────────────

def test_job_dict_exposes_ticket_required_fields():
    src = _read(FIELD_OPS_SERVICE)
    body = src.split("def _job_dict")[1].split("\n    def ")[0]
    assert '"customer_credit_applied"' in body
    assert '"payable_to_provider"' in body
    assert '"payment_collection_mode"' in body
    assert '"platform_payment_collected"' in body
    # Home Services rule: platform never collects the service payment
    assert '"payment_collection_mode": "customer_pays_provider_directly"' in body
    assert '"platform_payment_collected": False' in body


def test_job_dict_never_shows_payout_language():
    src = _read(FIELD_OPS_SERVICE)
    body = src.split("def _job_dict")[1].split("\n    def ")[0].lower()
    for forbidden in ("payout", "withdraw", "cash wallet", "escrow"):
        assert forbidden not in body


# ── Payment amount enforcement ───────────────────────────────────────────────

def test_record_payment_validates_against_payable_amount():
    src = _read(BILLING_SERVICE)
    body = src.split("async def record_payment")[1].split("\n    async def ")[0]
    assert "job.payable_amount" in body
    assert "PAYMENT_AMOUNT_MISMATCH" in body
    assert "Amount collected must match payable-to-provider amount." in body


# ── Booking completion propagation (dead-end fix) ───────────────────────────

def test_booking_transitions_allow_converted_to_job_to_completed():
    src = _read(BOOKING_CONSTANTS)
    assert "BS.CONVERTED_TO_JOB:    [BS.COMPLETED]" in src


def test_close_job_financial_propagates_booking_completion():
    src = _read(BILLING_SERVICE)
    body = src.split("async def close_job_financial")[1].split("\n    async def ")[0]
    assert "from app.engines.booking.models import Booking, BookingStatusHistory" in body
    assert "BS.COMPLETED" in body
    assert "booking.status = BS.COMPLETED" in body


# ── Role-naming fix: "technician" vs "staff" ─────────────────────────────────

def test_staff_router_accepts_real_technician_role():
    src = _read(STAFF_ROUTER)
    assert 'if u.role not in ("staff", "technician"):' in src
    assert 'if u.role != "staff":' not in src


def test_field_ops_router_accepts_real_technician_role():
    src = _read(FIELD_OPS_ROUTER)
    assert 'u.role != "staff"' not in src
    assert 'u.role not in ("staff", "technician")' in src


def test_field_ops_service_actor_role_checks_include_technician():
    src = _read(FIELD_OPS_SERVICE)
    assert 'self.actor_role == "staff"' not in src
    assert 'self.actor_role in ("staff", "technician")' in src


def test_billing_service_actor_role_checks_include_technician():
    src = _read(BILLING_SERVICE)
    assert 'self.actor_role == "staff"' not in src
    assert 'self.actor_role in ("staff", "technician")' in src


def test_assign_staff_accepts_technician_role_target():
    src = _read(FIELD_OPS_SERVICE)
    assert 'staff.role != "staff"' not in src
    assert 'staff.role not in ("staff", "technician")' in src


# ── ROLE_PERMISSIONS gap ─────────────────────────────────────────────────────

def test_role_permissions_has_technician_entry():
    src = _read(PERMISSIONS)
    assert '"technician": [' in src


def test_technician_role_can_close_jobs():
    """Ticket requires the technician to record direct payment and complete jobs —
    both gated on P.FIELD_OPS_JOBS_CLOSE at the router level."""
    from app.core.permissions import ROLE_PERMISSIONS, P
    assert P.FIELD_OPS_JOBS_CLOSE in ROLE_PERMISSIONS["technician"]
    assert P.FIELD_OPS_JOBS_CLOSE in ROLE_PERMISSIONS["staff"]


def test_technician_role_mirrors_staff_role():
    from app.core.permissions import ROLE_PERMISSIONS
    assert set(ROLE_PERMISSIONS["technician"]) == set(ROLE_PERMISSIONS["staff"])
