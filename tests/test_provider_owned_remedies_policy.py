from pathlib import Path
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import uuid

import pytest

from app.engines.complaints import constants as complaint_states
from app.engines.final_records.warranty_certificate import (
    issue_warranty_certificate,
    render_certificate_html,
)
from app.engines.vertical_catalog.document_requirements import (
    required_technician_keys,
    resolve_technician_requirements,
)


ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_technician_screening_is_provider_owned_not_platform_gated():
    assert required_technician_keys(vertical="home_services") == set()
    technician_keys = {
        item["key"] for item in resolve_technician_requirements(vertical="home_services")
    }
    assert "technician_identity" not in technician_keys
    assert "technician_background_check" not in technician_keys


def test_customer_rejection_returns_case_to_provider_not_admin():
    assert complaint_states.ALLOWED_TRANSITIONS[
        complaint_states.STATUS_RESOLUTION_PROPOSED
    ] >= {complaint_states.STATUS_AWAITING_PROVIDER}
    assert "under_admin_review" not in complaint_states.ALLOWED_TRANSITIONS[
        complaint_states.STATUS_RESOLUTION_PROPOSED
    ]


def test_admin_and_ai_case_workspaces_are_not_mounted():
    main = source("app/main.py")
    assert "admin_complaint_router," not in main
    assert "admin_rework_router," not in main
    assert "admin_refund_router," not in main
    assert "vertical_complaint" not in main
    customer = source("app/engines/complaints/customer_router.py")
    provider = source("app/engines/complaints/provider_router.py")
    assert "retired_ai_router" not in customer
    assert "retired_ai_router" not in provider
    assert not (ROOT / "app/engines/complaints/ai_settlement_service.py").exists()
    assert not (ROOT / "app/engines/complaints/settlement_rules.py").exists()
    credit_admin = source("app/engines/customer_credits/admin_router.py")
    admin_finance = source("app/engines/finance_hub/admin_hs_finance_router.py")
    assert 'router.post("/settlements' not in credit_admin
    assert 'router.post("/disputes' not in credit_admin
    assert 'router.post("/credits' not in credit_admin
    assert 'router.post("/customers' not in credit_admin
    assert 'open-dispute' not in admin_finance


def test_warranty_certificate_is_downloadable_provider_evidence():
    html = render_certificate_html({
        "certificate_number": "WRN-1",
        "terms_version": "2026-09-01",
        "service_name": "AC <Repair>",
        "provider": {"name": "Provider & Co"},
        "terms": ["Provider is responsible."],
    })
    assert "Provider Warranty Certificate" in html
    assert "WRN-1" in html
    assert "Provider &amp; Co" in html
    assert "AC &lt;Repair&gt;" in html
    assert "Provider is responsible." in html
    customer_router = source("app/engines/final_records/customer_router.py")
    assert "warranty-certificate" in customer_router
    assert 'media_type="application/pdf"' in customer_router
    assert 'filename = f"warranty-{job.warranty_certificate_number}.pdf"' in customer_router


@pytest.mark.asyncio
async def test_warranty_certificate_snapshot_is_issued_once_and_keeps_provider_evidence():
    tenant = SimpleNamespace(
        legal_name="Provider Legal Pvt Ltd", business_name="Provider Trading",
        tenant_name="Provider", tenant_code="TEN-7", gst_number="GST123",
        logo_url="https://res.cloudinary.com/provider/image/upload/logo.png",
        phone="9000000000", email="provider@example.test",
        address_line1="12 Main Road", address_line2=None, city="Ludhiana",
        district="Ludhiana", state="Punjab", zipcode="141001", country="India",
    )
    booking = SimpleNamespace(booking_number="BK-7", customer_name="Customer")
    service = SimpleNamespace(service_name="AC Repair")
    tenant_id, booking_id, offering_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    job = SimpleNamespace(
        id=uuid.uuid4(), job_number="JOB-7", booking_id=booking_id,
        tenant_id=tenant_id, offering_id=offering_id,
        warranty_certificate_snapshot=None, warranty_certificate_number=None,
        warranty_certificate_issued_at=None,
        warranty_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        warranty_days_snapshot=30,
        address_snapshot={"line1": "Customer address", "zipcode": "141001"},
        completion_data={"work_summary": "Replaced compressor"},
    )

    class FakeDb:
        flushed = 0

        async def get(self, model, key):
            return {
                "ServiceBooking": booking,
                "Tenant": tenant,
                "MasterService": service,
            }[model.__name__]

        async def flush(self):
            self.flushed += 1

    db = FakeDb()
    first = await issue_warranty_certificate(db, job)
    tenant.legal_name = "Changed After Completion"
    second = await issue_warranty_certificate(db, job)

    assert first is second
    assert first["provider"]["name"] == "Provider Legal Pvt Ltd"
    assert first["provider"]["gst_number"] == "GST123"
    assert first["provider"]["logo_url"] == tenant.logo_url
    assert first["work_summary"] == "Replaced compressor"
    assert first["terms_version"] == "2026-09-01"
    assert db.flushed == 1


def test_policy_migration_covers_direct_resolution_paid_seats_and_penalties():
    policy_migration = source("alembic/versions/337_provider_owned_service_remedies.py")
    for phrase in (
        "does not verify or certify individual technicians",
        "active, paid technician-seat packages",
        "does not collect, hold, or promise recovery from a provider security deposit",
        "does not provide AI settlement",
        "deduct usage credits from the provider",
        "requires_reacceptance",
    ):
        assert phrase in policy_migration

    # Applied migrations are immutable audit history.  The product rename is
    # therefore a later legal version, not an edit to what users accepted.
    brand_migration = source("alembic/versions/339_fuvay_display_brand.py")
    assert "replace(body, 'ServiceOS', 'Fuvay')" in brand_migration
    assert "supersedes_id" in brand_migration
    assert "requires_reacceptance" in brand_migration


def test_mobile_and_provider_ui_expose_direct_resolution_without_admin_or_ai():
    remedy = source("mobile/customer-app/src/screens/service-remedies/ServiceRemediesScreen.tsx")
    protection = source("mobile/customer-app/src/components/booking-details/ServiceProtectionCard.tsx")
    provider = source("frontend/tenant-portal/app/(tenant)/provider/complaints/[complaint_id]/page.tsx")
    customer = source("mobile/customer-app/src/screens/support/SupportRequestDetailsScreen.tsx")
    customer_api = source("mobile/customer-app/src/api/supportRequests/supportRequestsApi.ts")
    assert "Ask provider to review again" in remedy
    assert "mutually agreed resolution" in remedy
    assert "requires your agreement with the provider" in protection
    assert "AI settlement" not in provider
    assert "/ai-session" not in provider
    assert "aiSession" not in customer
    assert "/ai-session" not in customer_api


def test_refund_and_warranty_sla_penalties_are_automatic_and_idempotent():
    job = source("app/jobs/complaint_sla.py")
    assert "run_remedy_sla_check" in job
    assert 'source_type="warranty_claim"' in job
    assert 'source_type="refund_request"' in job
    assert 'result["idempotent"]' in job
    assert "compute_health_score" in job
    assert "run_escalations" not in job
    assert "run_ai_auto_start" not in job


def test_retired_admin_settlement_pages_are_deleted():
    for path in (
        "frontend/super-admin/app/admin/finance/dispute-settlements/page.tsx",
        "frontend/super-admin/app/admin/finance/customer-credits/page.tsx",
    ):
        assert not (ROOT / path).exists()


def test_tenant_ai_chat_and_admin_refund_decisions_are_not_reachable():
    admin_finance = source("frontend/super-admin/app/admin/home-services/finance/page.tsx")
    assert not (ROOT / "frontend/tenant-portal/app/(tenant)/ai-chat/page.tsx").exists()
    assert not (ROOT / "frontend/tenant-portal/components/assistant/AssistantPanel.tsx").exists()
    assert not (ROOT / "frontend/tenant-portal/lib/api-tenant-assistant.ts").exists()
    assert 'key: "customer-refunds"' not in admin_finance
    assert 'tab === "customer-refunds"' not in admin_finance


def test_material_terms_reacceptance_is_enforced_in_tenant_and_customer_apps():
    router = source("app/engines/legal_documents/user_router.py")
    tenant_gate = source("frontend/tenant-portal/components/shared/LegalReacceptanceGate.tsx")
    customer_gate = source("mobile/customer-app/src/components/legal/LegalReacceptanceGate.tsx")
    customer_root = source("mobile/customer-app/src/navigation/RootNavigator.tsx")
    assert 'router.get("/consent-status"' in router
    assert 'router.post("/accept"' in router
    assert "requires_reacceptance" in router
    assert "legal_reacceptance" in router
    assert "Accept and continue" in tenant_gate
    assert "Accept and continue" in customer_gate
    assert "CustomerAppWithLegalGate" in customer_root
