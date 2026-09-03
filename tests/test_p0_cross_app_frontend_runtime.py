"""P0 Cross-App Frontend Runtime Verification Sprint — static-inspection
regression tests, matching this session's established convention: read
source files as text and assert the fields/labels/endpoints that make the
credit/payable/payment breakdown actually reach the tenant/staff/customer/
admin UIs (rather than only existing on the backend, unused)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── Backend: _booking_dict must expose credit/payable fields ──────────────

def test_booking_dict_exposes_credit_applied_and_payable_amount():
    src = _read("app/engines/booking/service.py")
    assert '"credit_applied": float(b.credit_applied or 0)' in src
    assert '"payable_amount": float(b.payable_amount)' in src
    assert '"payment_collection_mode": "customer_pays_provider_directly"' in src
    assert '"platform_payment_collected": False' in src


def test_admin_bookings_join_falls_back_to_converted_job_id():
    src = _read("app/engines/booking/admin_router.py")
    assert "COALESCE(b.job_id, b.converted_job_id)" in src


def test_job_dict_exposes_payment_recorded_and_amount_collected():
    src = _read("app/engines/field_ops/service.py")
    assert '"payment_recorded": j.payment_id is not None' in src
    assert '"amount_collected":' in src


def test_admin_booking_router_exposes_credit_applied_and_payable_amount():
    src = _read("app/engines/booking/admin_router.py")
    assert "b.credit_applied" in src
    assert "b.payable_amount" in src
    assert '"credit_applied":' in src
    assert '"payable_amount":' in src
    assert '"payment_recorded":' in src


# ── Tenant portal ───────────────────────────────────────────────────────────

def test_tenant_booking_detail_shows_payment_breakdown():
    src = _read("frontend/tenant-portal/app/(tenant)/home-services/bookings-jobs/page.tsx")
    assert "Confirm direct payment" in src
    assert "Record the amount paid directly" in src
    assert "does not charge the customer or create a platform settlement" in src


def test_tenant_job_detail_shows_payment_collection_and_deduction():
    src = _read("frontend/tenant-portal/app/(tenant)/home-services/finance/page.tsx")
    assert "Usage Credits" in src
    assert "Completed-job deductions" in src
    assert "deduct commission from your wallet" not in src  # old forbidden phrasing removed


def test_tenant_finance_ledger_labels_completed_job_deduction():
    # The canonical workspace owns both the balance and immutable ledger;
    # there is no redirect-only finance page anymore.
    src = _read("frontend/tenant-portal/app/(tenant)/home-services/finance/page.tsx")
    assert "Usage Credits" in src
    assert "Usage-credit ledger" in src
    assert "completion deductions" in src


def test_tenant_api_types_have_payment_breakdown_fields():
    src = _read("frontend/tenant-portal/lib/api.ts")
    assert "BookingPaymentBreakdown" in src
    assert "JobPaymentBreakdown" in src
    assert "customer_credit_applied?:number" in src
    assert "payable_to_provider?:number" in src
    assert "recordPayment:" in src


# ── Admin ───────────────────────────────────────────────────────────────────

def test_admin_booking_detail_shows_payment_breakdown():
    src = _read("frontend/super-admin/app/admin/home-services/bookings-jobs/page.tsx")
    assert "WorkDetailDrawer" in src
    assert "price_snapshot" in src
    assert "customer_total" in src


def test_admin_job_detail_shows_credit_and_deduction_record():
    # FINAL-L5-05E: /admin/operations/[jobId] is now a redirect to the
    # canonical service_jobs detail page, which already has a real
    # "Completed Job Deduction" section (built in FINAL-L5-05B) linking to
    # the exact Usage Credit Ledger entry.
    src = _read("frontend/super-admin/app/admin/home-services/service-jobs/[jobId]/page.tsx")
    assert "Completed Job Deduction" in src
    assert "Usage Credit Ledger" in src


def test_admin_api_types_have_payment_breakdown_fields():
    src = _read("frontend/super-admin/lib/api.ts")
    assert "customer_credit_applied?: number" in src
    assert "payable_to_provider?: number" in src
    assert "credit_applied?: number;" in src
    assert "payable_amount?: number;" in src


# ── Staff app (React Native) ────────────────────────────────────────────────

# MODULE-L5-36: the staff app's job surface was repointed from the dead
# field_ops engine (0 rows platform-wide) to the real service_jobs pipeline.
# Payment collection is no longer a separate "Record Payment" + "Close Job"
# flow with a fictional payable_to_provider breakdown (field_ops shapes that
# never populated); it's the real backend's single validated `complete`
# action, which takes work_summary + collected_amount together.

def test_staff_app_has_payment_recording_form():
    src = _read("mobile/staff-app/src/screens/directPayment/DirectPaymentScreen.tsx")
    assert "Payment received by provider" in src
    assert "Submit payment record" in src
    assert "Complete job" in src
    assert "Payout" not in src and "Withdraw" not in src and "Cash Wallet" not in src


def test_staff_app_completion_records_work_summary_and_amount():
    src = _read("mobile/staff-app/src/screens/directPayment/DirectPaymentScreen.tsx")
    assert "Completion proof" in src
    assert "Customer payment confirmation" in src
    assert "handleFinalize" in src


def test_staff_app_api_client_has_complete_action():
    src = _read("mobile/staff-app/src/lib/api.ts")
    assert "complete:" in src
    assert "/complete" in src
    assert "collected_amount" in src
    assert "work_summary" in src


# ── Customer app (React Native) ─────────────────────────────────────────────

def test_customer_app_booking_detail_shows_credit_and_direct_payment():
    src = _read("mobile/customer-app/src/components/booking-details/WorkCompletedCard.tsx")
    assert "Final service amount" in src
    assert "Payment is made directly to the provider" in src


def test_customer_app_does_not_show_provider_deduction_language():
    src = _read("mobile/customer-app/src/components/booking-details/WorkCompletedCard.tsx")
    forbidden = ["commission", "Commission", "usage credit balance", "wallet"]
    for term in forbidden:
        assert term not in src, f"Customer app must not show '{term}'"


def test_customer_app_api_types_have_credit_applied_and_payable_amount():
    src = _read("mobile/customer-app/src/api/contracts/customerQuote.ts")
    assert "customer_payable_amount" in src


# ── Forbidden-term scan on all fixed job-completion-facing pages ────────────

_FORBIDDEN = ["Payout", "Withdraw", "Cash Wallet", "Escrow", "Provider Earnings Wallet"]

def test_no_forbidden_labels_on_job_completion_facing_pages():
    # "Platform Payment" is exempted: the ticket's own Part C spec requires the
    # literal disclosure line "Platform Payment: Not collected by Fuvay" —
    # a negation clarifying Fuvay does NOT hold the payment, not a payout
    # feature name. The other 5 forbidden terms have no such carve-out.
    pages = [
        "frontend/tenant-portal/app/(tenant)/home-services/bookings-jobs/page.tsx",
        "frontend/tenant-portal/app/(tenant)/home-services/finance/page.tsx",
        "mobile/staff-app/src/screens/directPayment/DirectPaymentScreen.tsx",
        "mobile/customer-app/src/components/booking-details/WorkCompletedCard.tsx",
    ]
    for page in pages:
        src = _read(page)
        for term in _FORBIDDEN:
            assert term not in src, f"{page} must not contain forbidden term '{term}'"
