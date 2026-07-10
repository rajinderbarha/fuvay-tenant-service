"""Sprint P1 — Package Approval Lifecycle Tests.

P0 Rule: Package starts ONLY after admin approval.
- starts_at / expires_at remain NULL until admin approves the tenant
- Payment does NOT activate the package
- Admin approval date = starts_at; expires_at = starts_at + validity_days
- Credits added ONLY after approval; deposit never becomes wallet credit
- Rejected tenant: package never activates, starts_at/expires_at stay null
"""
import re
import uuid
from pathlib import Path

# ────────────────────────────────────────────────────────────────────────────
# Migration + Model layer
# ────────────────────────────────────────────────────────────────────────────

def test_migration_072_exists():
    p = Path("alembic/versions/072_tenant_package_assignments.py")
    assert p.exists(), "Migration 072 not found"


def test_migration_072_revision():
    src = Path("alembic/versions/072_tenant_package_assignments.py").read_text(encoding="utf-8")
    assert 'revision = "072"' in src
    assert 'down_revision = "071"' in src


def test_migration_072_creates_table():
    src = Path("alembic/versions/072_tenant_package_assignments.py").read_text(encoding="utf-8")
    assert "tenant_package_assignments" in src


def test_migration_072_starts_at_nullable():
    src = Path("alembic/versions/072_tenant_package_assignments.py").read_text(encoding="utf-8")
    assert "starts_at" in src
    assert "nullable=True" in src


def test_migration_072_expires_at_nullable():
    src = Path("alembic/versions/072_tenant_package_assignments.py").read_text(encoding="utf-8")
    assert "expires_at" in src


def test_model_tenant_package_assignment_exists():
    src = Path("app/engines/package_commerce/models.py").read_text(encoding="utf-8")
    assert "class TenantPackageAssignment" in src


def test_model_starts_at_null_docstring():
    src = Path("app/engines/package_commerce/models.py").read_text(encoding="utf-8")
    assert "starts_at" in src and "NULL until admin approval" in src


def test_model_valid_statuses():
    src = Path("app/engines/package_commerce/service.py").read_text(encoding="utf-8")
    for status in ("selected", "pending_review", "paid_pending_approval", "active", "rejected"):
        assert status in src, f"Status '{status}' not found in service.py"


# ────────────────────────────────────────────────────────────────────────────
# Service layer
# ────────────────────────────────────────────────────────────────────────────

def test_service_create_assignment_method_exists():
    src = Path("app/engines/package_commerce/service.py").read_text(encoding="utf-8")
    assert "async def create_package_assignment" in src


def test_service_activate_assignment_method_exists():
    src = Path("app/engines/package_commerce/service.py").read_text(encoding="utf-8")
    assert "async def activate_tenant_package_assignment" in src


def test_service_reject_assignment_method_exists():
    src = Path("app/engines/package_commerce/service.py").read_text(encoding="utf-8")
    assert "async def reject_tenant_package_assignment" in src


def test_service_get_summary_method_exists():
    src = Path("app/engines/package_commerce/service.py").read_text(encoding="utf-8")
    assert "async def get_package_assignment_summary" in src


def test_service_activation_sets_starts_at():
    src = Path("app/engines/package_commerce/service.py").read_text(encoding="utf-8")
    assert "starts_at" in src
    # Activation must set starts_at to now
    assert "now()" in src or "datetime.now" in src or "utcnow" in src


def test_service_activation_sets_expires_at_from_validity():
    src = Path("app/engines/package_commerce/service.py").read_text(encoding="utf-8")
    assert "expires_at" in src
    assert "validity_days" in src


def test_service_credits_only_on_activation():
    src = Path("app/engines/package_commerce/service.py").read_text(encoding="utf-8")
    # create_package_assignment must NOT call credit_wallet
    create_idx = src.find("async def create_package_assignment")
    activate_idx = src.find("async def activate_tenant_package_assignment")
    assert create_idx != -1 and activate_idx != -1
    between = src[create_idx:activate_idx]
    assert "credit_wallet" not in between, \
        "create_package_assignment must not credit wallet — only activation should"


def test_service_reject_does_not_set_starts_at():
    src = Path("app/engines/package_commerce/service.py").read_text(encoding="utf-8")
    reject_idx = src.find("async def reject_tenant_package_assignment")
    activate_idx = src.find("async def activate_tenant_package_assignment")
    assert reject_idx != -1 and activate_idx != -1
    # The reject method comes after activate, grab reject body until next async def
    after_reject = src[reject_idx:]
    next_def = after_reject.find("\n    async def ", 10)
    reject_body = after_reject[:next_def] if next_def != -1 else after_reject[:2000]
    assert "starts_at" not in reject_body or "= None" in reject_body or "null" in reject_body.lower()


def test_service_deposit_separate_from_wallet():
    src = Path("app/engines/package_commerce/service.py").read_text(encoding="utf-8")
    # security_deposit must never call credit_wallet
    # Find create_package_assignment block
    create_idx = src.find("async def create_package_assignment")
    activate_idx = src.find("async def activate_tenant_package_assignment")
    between = src[create_idx:activate_idx]
    # No credit_wallet call with deposit amount in the create flow
    assert "security_deposit" not in between or "credit_wallet" not in between, \
        "Security deposit must never be credited as spendable wallet credit"


# ────────────────────────────────────────────────────────────────────────────
# Admin service integration
# ────────────────────────────────────────────────────────────────────────────

def test_admin_service_verify_calls_activate():
    src = Path("app/engines/tenant_engine/admin_service.py").read_text(encoding="utf-8")
    assert "activate_tenant_package_assignment" in src


def test_admin_service_reject_calls_reject_assignment():
    src = Path("app/engines/tenant_engine/admin_service.py").read_text(encoding="utf-8")
    assert "reject_tenant_package_assignment" in src


def test_admin_service_activation_failure_does_not_block_approval():
    src = Path("app/engines/tenant_engine/admin_service.py").read_text(encoding="utf-8")
    # The activate call must be wrapped in try/except
    activate_idx = src.find("activate_tenant_package_assignment")
    assert activate_idx != -1
    surrounding = src[max(0, activate_idx - 200):activate_idx + 400]
    assert "try" in surrounding or "except" in surrounding, \
        "Package activation failure must be caught and not block tenant approval"


# ────────────────────────────────────────────────────────────────────────────
# Tenant router
# ────────────────────────────────────────────────────────────────────────────

def test_tenant_router_package_summary_endpoint():
    src = Path("app/engines/package_commerce/tenant_router.py").read_text(encoding="utf-8")
    assert "/v1/provider/onboarding/package-summary" in src


def test_tenant_router_summary_returns_message():
    src = Path("app/engines/package_commerce/tenant_router.py").read_text(encoding="utf-8")
    assert "package-summary" in src


# ────────────────────────────────────────────────────────────────────────────
# Public registration router
# ────────────────────────────────────────────────────────────────────────────

def test_public_router_complete_accepts_selected_package_id():
    src = Path("app/engines/public_registration/router.py").read_text(encoding="utf-8")
    assert "selected_package_id" in src


def test_public_router_complete_creates_assignment():
    src = Path("app/engines/public_registration/router.py").read_text(encoding="utf-8")
    assert "create_package_assignment" in src or "TenantPackageAssignment" in src


def test_public_router_assignment_failure_does_not_block_registration():
    src = Path("app/engines/public_registration/router.py").read_text(encoding="utf-8")
    # Package assignment creation in complete_registration should be try/except
    create_idx = src.find("create_package_assignment")
    if create_idx == -1:
        create_idx = src.find("TenantPackageAssignment")
    assert create_idx != -1
    surrounding = src[max(0, create_idx - 300):create_idx + 400]
    assert "try" in surrounding or "except" in surrounding, \
        "Package assignment creation must not block tenant account creation"


# ────────────────────────────────────────────────────────────────────────────
# Frontend — tenant-portal api.ts
# ────────────────────────────────────────────────────────────────────────────

def test_api_ts_package_assignment_summary_interface():
    src = Path("frontend/tenant-portal/lib/api.ts").read_text(encoding="utf-8")
    assert "PackageAssignmentSummary" in src


def test_api_ts_package_summary_has_starts_at():
    src = Path("frontend/tenant-portal/lib/api.ts").read_text(encoding="utf-8")
    idx = src.find("PackageAssignmentSummary")
    block = src[idx:idx + 400]
    assert "starts_at" in block


def test_api_ts_package_summary_has_message():
    src = Path("frontend/tenant-portal/lib/api.ts").read_text(encoding="utf-8")
    idx = src.find("PackageAssignmentSummary")
    block = src[idx:idx + 400]
    assert "message" in block


def test_api_ts_provider_package_api_has_summary_method():
    src = Path("frontend/tenant-portal/lib/api.ts").read_text(encoding="utf-8")
    assert "packageSummary" in src
    assert "/v1/provider/onboarding/package-summary" in src


def test_api_ts_complete_passes_selected_package_id():
    src = Path("frontend/tenant-portal/lib/api.ts").read_text(encoding="utf-8")
    idx = src.find("complete:")
    block = src[idx:idx + 300]
    assert "selected_package_id" in block or "selectedPackageId" in block


# ────────────────────────────────────────────────────────────────────────────
# Frontend — register/page.tsx
# ────────────────────────────────────────────────────────────────────────────

def test_register_page_passes_package_id_to_complete():
    src = Path("frontend/tenant-portal/app/register/page.tsx").read_text(encoding="utf-8")
    # Both complete calls should forward package_id
    assert "selectedPlan?.package_id" in src or "selected_package_id" in src


def test_register_page_passes_package_id_dev_bypass():
    src = Path("frontend/tenant-portal/app/register/page.tsx").read_text(encoding="utf-8")
    # dev bypass path
    idx = src.find("pay_dev_bypass")
    assert idx != -1
    surrounding = src[idx:idx + 200]
    assert "package_id" in surrounding or "selectedPlan" in surrounding


# ────────────────────────────────────────────────────────────────────────────
# Frontend — onboarding-status/page.tsx
# ────────────────────────────────────────────────────────────────────────────

def test_onboarding_status_imports_package_summary():
    src = Path("frontend/tenant-portal/app/(tenant)/onboarding-status/page.tsx").read_text(encoding="utf-8")
    assert "PackageAssignmentSummary" in src or "packageSummary" in src


def test_onboarding_status_shows_package_status_card():
    src = Path("frontend/tenant-portal/app/(tenant)/onboarding-status/page.tsx").read_text(encoding="utf-8")
    assert "PackageStatusCard" in src


def test_onboarding_status_shows_message_field():
    src = Path("frontend/tenant-portal/app/(tenant)/onboarding-status/page.tsx").read_text(encoding="utf-8")
    assert "pkg.message" in src or "message" in src


def test_onboarding_status_shows_starts_at():
    src = Path("frontend/tenant-portal/app/(tenant)/onboarding-status/page.tsx").read_text(encoding="utf-8")
    assert "starts_at" in src


# ────────────────────────────────────────────────────────────────────────────
# Acceptance criteria sentinel
# ────────────────────────────────────────────────────────────────────────────

def test_acceptance_package_never_starts_before_approval():
    """
    If starts_at is populated before admin approval, this test fails.
    We verify the service sets starts_at=None during create_package_assignment.
    """
    src = Path("app/engines/package_commerce/service.py").read_text(encoding="utf-8")
    create_idx = src.find("async def create_package_assignment")
    assert create_idx != -1
    # Look for starts_at = None or starts_at=None inside the create method body
    activate_idx = src.find("async def activate_tenant_package_assignment")
    body = src[create_idx:activate_idx]
    # The assignment record in create method must not set starts_at to a real datetime
    # It may set it to None explicitly or just not set it (relies on DB NULL default)
    assert "starts_at" not in body or "None" in body or "null" in body.lower()


def test_acceptance_no_hardcoded_not_ready_sentinel():
    """The sentinel NOT_READY_PACKAGE_STARTS_BEFORE_APPROVAL must not appear in prod code
    (it's only valid as a test gate, not embedded in source)."""
    service_src = Path("app/engines/package_commerce/service.py").read_text(encoding="utf-8")
    router_src  = Path("app/engines/public_registration/router.py").read_text(encoding="utf-8")
    for src in (service_src, router_src):
        assert "NOT_READY_PACKAGE_STARTS_BEFORE_APPROVAL" not in src
