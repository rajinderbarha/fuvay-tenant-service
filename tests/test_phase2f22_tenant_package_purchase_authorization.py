"""Phase 2A Slice 2F-22 — Tenant Package Purchase Authorization, Payment-State
Authority, Price Integrity, Credit Issuance and Activation Closure.

Selected module: `app.engines.package_commerce.tenant_router`
Selected mutation: POST /v1/tenant/packages/{package_id}/purchase

The defect this slice closes: the route read `mark_paid` and
`payment_reference` from an untyped `payload: dict` body and passed them
straight into `create_package_assignment(is_paid=..., payment_reference=...)`.
A tenant could therefore declare its own payment settled, with a fabricated
external transaction reference, without any payment occurring
(CLIENT_SETTLEMENT_ATTESTATION_TRUSTED -- NOT CLIENT_AMOUNT_TRUSTED: every
monetary value was already server-derived from the ServicePackage record).

That mattered because `activate_tenant_package_assignment` orders activation
candidates by `paid_at DESC NULLS LAST`, so a self-attested "paid" assignment
was actively PREFERRED -- and activation grants wallet credits, storage quota
and commission rate.
"""
from __future__ import annotations

import inspect
import uuid

import pytest

from app.engines.package_commerce import tenant_router, admin_router, service as pkg_service
from app.engines.package_commerce.tenant_router import TenantPackagePurchaseRequest
from app.exceptions import ServiceOSException


class TestRouteAuthorizationWiring:
    """WS4 / WS19 — canonical persona and mutation-capable scope."""

    def test_route_uses_mutation_capable_dependency(self):
        src = inspect.getsource(tenant_router.tenant_purchase_package)
        assert "require_tenant_owner_mutation" in src, (
            "the purchase mutation must use the access-scope-aware dependency"
        )

    def test_route_no_longer_uses_scope_blind_dependency(self):
        src = inspect.getsource(tenant_router.tenant_purchase_package)
        assert "Depends(require_tenant_owner)" not in src

    def test_mutation_dependency_admits_only_tenant_owner_and_super_admin(self):
        """Canonical persona: no staff, technician, customer or guest."""
        from app.core import permissions
        src = inspect.getsource(permissions.require_tenant_owner_mutation)
        assert "tenant_owner" in src
        assert "super_admin" in src
        for forbidden in ("technician", "customer", "guest"):
            assert f'"{forbidden}"' not in src, (
                f"{forbidden} must not be admitted to a financial mutation"
            )

    def test_mutation_dependency_denies_read_only_scope(self):
        """A read-only tenant owner must be denied a purchase."""
        from app.core import permissions
        src = inspect.getsource(permissions.require_tenant_owner_mutation)
        assert "access_scope" in src


class TestRequestFieldAuthority:
    """WS7 — every client field classified; none silently ignored."""

    def test_schema_forbids_extra_fields(self):
        assert TenantPackagePurchaseRequest.model_config.get("extra") == "forbid"

    def test_schema_accepts_no_client_fields_at_all(self):
        assert TenantPackagePurchaseRequest.model_fields == {}

    def test_empty_body_is_valid(self):
        """The frontend sends `{}` -- must keep working."""
        assert TenantPackagePurchaseRequest() is not None

    @pytest.mark.parametrize("field,value", [
        ("mark_paid", True),
        ("payment_reference", "pay_FAKE123"),
        ("amount", 0),
        ("price", 1),
        ("currency", "USD"),
        ("discount", 100),
        ("coupon", "FREE"),
        ("tax", 0),
        ("credits", 99999),
        ("points", 99999),
        ("quantity", 10),
        ("validity_days", 36500),
        ("starts_at", "2020-01-01"),
        ("expires_at", "2099-01-01"),
        ("storage_quota_gb", 9999),
        ("commission_rate", 0),
        ("status", "active"),
        ("external_transaction_id", "txn_FAKE"),
    ])
    def test_client_supplied_field_is_rejected_not_ignored(self, field, value):
        """No monetary/entitlement/state field may be accepted OR silently
        dropped -- a silently-dropped field misrepresents the contract."""
        with pytest.raises(Exception):
            TenantPackagePurchaseRequest(**{field: value})


class TestMarkPaidRemoved:
    """WS8 — mark_paid adjudication: CLIENT_SETTLEMENT_ATTESTATION_TRUSTED."""

    def test_handler_never_reads_mark_paid(self):
        src = inspect.getsource(tenant_router.tenant_purchase_package)
        assert 'payload.get("mark_paid")' not in src
        assert "mark_paid" not in src.split('"""')[-1], (
            "mark_paid must not survive anywhere in executable handler code"
        )

    def test_handler_passes_is_paid_false_literally(self):
        src = inspect.getsource(tenant_router.tenant_purchase_package)
        assert "is_paid=False" in src

    def test_handler_passes_no_client_payment_reference(self):
        src = inspect.getsource(tenant_router.tenant_purchase_package)
        assert "payment_reference=None" in src
        assert 'payload.get("payment_reference")' not in src

    def test_handler_declares_unpaid_authority(self):
        src = inspect.getsource(tenant_router.tenant_purchase_package)
        assert 'payment_authority="tenant_unpaid_request"' in src


class TestServiceLayerPaymentAuthority:
    """WS16 — router dependencies do not replace service-layer integrity."""

    def test_create_package_assignment_has_payment_authority_param(self):
        sig = inspect.signature(pkg_service.PackageCommerceService.create_package_assignment)
        assert "payment_authority" in sig.parameters

    def test_payment_authority_defaults_to_unspecified(self):
        sig = inspect.signature(pkg_service.PackageCommerceService.create_package_assignment)
        assert sig.parameters["payment_authority"].default == "unspecified"

    def test_only_two_authorities_can_mark_paid(self):
        src = inspect.getsource(pkg_service.PackageCommerceService.create_package_assignment)
        assert "gateway_signature_verified" in src
        assert "admin_attestation" in src
        assert "PAYMENT_AUTHORITY_REQUIRED" in src

    @pytest.mark.asyncio
    async def test_is_paid_without_authority_fails_closed(self):
        """The core service-layer guard: a caller cannot mark paid without
        declaring an authoritative payment source."""
        svc = pkg_service.PackageCommerceService(db=None)
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_package_assignment(
                uuid.uuid4(), uuid.uuid4(), is_paid=True,
            )
        assert exc.value.error_code == "PAYMENT_AUTHORITY_REQUIRED"

    @pytest.mark.asyncio
    async def test_is_paid_with_tenant_authority_fails_closed(self):
        """A tenant-originated request must never reach paid state, even if a
        future caller wires the tenant authority string through with is_paid."""
        svc = pkg_service.PackageCommerceService(db=None)
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_package_assignment(
                uuid.uuid4(), uuid.uuid4(), is_paid=True,
                payment_authority="tenant_unpaid_request",
            )
        assert exc.value.error_code == "PAYMENT_AUTHORITY_REQUIRED"

    @pytest.mark.asyncio
    async def test_unpaid_selection_rejects_payment_reference(self):
        """An unverifiable transaction reference on an unpaid selection would
        mislead the admin who later approves it."""
        svc = pkg_service.PackageCommerceService(db=None)
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_package_assignment(
                uuid.uuid4(), uuid.uuid4(), is_paid=False,
                payment_reference="pay_FAKE123",
            )
        assert exc.value.error_code == "PAYMENT_REFERENCE_WITHOUT_PAYMENT"


class TestLegitimateCallersPreserved:
    """WS15 — the two authoritative callers must keep working unchanged."""

    def test_admin_router_declares_admin_attestation(self):
        src = inspect.getsource(admin_router.admin_purchase_package)
        assert 'payment_authority="admin_attestation"' in src
        assert "is_paid=True" in src

    def test_admin_purchase_still_permission_guarded(self):
        src = inspect.getsource(admin_router.admin_purchase_package)
        assert "PACKAGES_CREATE" in src

    def test_public_registration_declares_gateway_verified(self):
        from app.engines.public_registration import router as reg_router
        src = inspect.getsource(reg_router)
        assert 'payment_authority="gateway_signature_verified"' in src

    def test_public_registration_verifies_signature_before_marking_paid(self):
        """The authority claim must be backed by a real signature check that
        runs BEFORE the assignment is created."""
        from app.engines.public_registration import router as reg_router
        src = inspect.getsource(reg_router)
        verify_at = src.index("verify_payment_signature(body.razorpay_order_id")
        assign_at = src.index('payment_authority="gateway_signature_verified"')
        assert verify_at < assign_at, (
            "signature verification must precede the paid assignment"
        )


class TestServerPriceAuthority:
    """WS9 — every monetary/entitlement value derives from the package."""

    def test_all_financial_fields_derive_from_package_record(self):
        src = inspect.getsource(pkg_service.PackageCommerceService.create_package_assignment)
        for server_derived in (
            "price_amount=pkg.package_price",
            "security_deposit_amount=pkg.security_deposit_amount",
            "included_spendable_credits=pkg.included_credit_amount",
            "lead_credits=pkg.lead_credits",
            "validity_days=pkg.validity_days",
            "billing_cycle=pkg.billing_cycle",
        ):
            assert server_derived in src, f"{server_derived} must be package-derived"

    def test_package_must_be_active(self):
        src = inspect.getsource(pkg_service.PackageCommerceService.create_package_assignment)
        assert "PACKAGE_INACTIVE" in src

    def test_soft_deleted_package_is_not_loadable(self):
        src = inspect.getsource(pkg_service.PackageCommerceService._load_package)
        assert "deleted_at.is_(None)" in src


class TestNoActivationOrCreditIssuanceOnPurchase:
    """WS12 — purchase must not activate or issue credits."""

    def test_purchase_leaves_activation_dates_null(self):
        src = inspect.getsource(pkg_service.PackageCommerceService.create_package_assignment)
        assert "starts_at=None" in src
        assert "expires_at=None" in src

    def test_purchase_issues_no_wallet_credits(self):
        src = inspect.getsource(pkg_service.PackageCommerceService.create_package_assignment)
        assert "credit_wallet(" not in src, (
            "credits must issue only on admin activation, never at purchase"
        )

    def test_credits_issue_only_in_activation_path_and_are_idempotent(self):
        src = inspect.getsource(
            pkg_service.PackageCommerceService.activate_tenant_package_assignment)
        assert "credit_wallet(" in src
        assert "idempotency_key=" in src, (
            "credit issuance must be idempotent so re-activation cannot double-issue"
        )


class TestDuplicatePurchaseGuard:
    """WS13 — duplicate/idempotency policy (pre-existing MODULE-L5-30 guard)."""

    def test_duplicate_pending_selection_is_rejected(self):
        src = inspect.getsource(pkg_service.PackageCommerceService.create_package_assignment)
        assert "PACKAGE_ALREADY_PENDING" in src

    def test_duplicate_guard_is_scoped_to_tenant_and_package(self):
        src = inspect.getsource(pkg_service.PackageCommerceService.create_package_assignment)
        assert "TenantPackageAssignment.tenant_id == tenant_id" in src
        assert "TenantPackageAssignment.package_id == package_id" in src


class TestTenantAuthority:
    """WS5 — tenant identity is server-derived, never client-supplied."""

    def test_tenant_id_comes_from_token_not_body(self):
        src = inspect.getsource(tenant_router.tenant_purchase_package)
        assert "_tenant_id(user)" in src

    def test_tenant_id_helper_reads_only_the_principal(self):
        src = inspect.getsource(tenant_router._tenant_id)
        assert "user.tenant_id" in src
        assert "TENANT_ACCESS_DENIED" in src

    def test_no_client_tenant_field_is_accepted(self):
        assert "tenant_id" not in TenantPackagePurchaseRequest.model_fields
