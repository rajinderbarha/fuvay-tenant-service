"""Sprint 5 — Package Commerce Tenant Router.

Self-service endpoints for tenant owners under /v1/tenant/packages/, /v1/tenant/credit-wallet, etc.
tenant_id always extracted from JWT — never from request body.
"""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_tenant_owner_mutation
from app.dependencies.auth import require_tenant_owner, get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.package_commerce.service import PackageCommerceService
from app.exceptions import ServiceOSException

router = APIRouter(tags=["Tenant Packages"])

ENGINE_ID = "package_credit"


def _tenant_id(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise ServiceOSException("TENANT_ACCESS_DENIED", "No tenant context in token.")
    return uuid.UUID(user.tenant_id)


def _svc(db: AsyncSession, request: Request, user: UserContext) -> PackageCommerceService:
    actor_id = uuid.UUID(user.user_id) if user and user.user_id else None
    ip = request.client.host if request.client else None
    return PackageCommerceService(
        db=db,
        request_id=(getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")),
        actor_id=actor_id,
        actor_role=user.role if user else None,
        ip_address=ip,
    )


def _ok(data: dict, request: Request) -> dict:
    return {
        "success": True,
        "data": data,
        "request_id": (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")),
        "engine_id": ENGINE_ID,
    }


# ══════════════════════════════════════════════════════════════
# PACKAGE VISIBILITY
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# P1 — PACKAGE ASSIGNMENT SUMMARY (starts after admin approval)
# ══════════════════════════════════════════════════════════════

@router.get("/v1/provider/onboarding/package-summary",
            summary="Get current package assignment status (P1: starts after admin approval)",
            tags=["Provider Onboarding"])
async def provider_package_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> dict:
    """
    Returns the tenant's package assignment status.

    Before admin approval: starts_at and expires_at are null.
    After admin approval: package is active with starts_at and expires_at set.
    """
    tid = _tenant_id(user)
    data = await _svc(db, request, user).get_package_assignment_summary(tid)
    return _ok(data, request)


# ══════════════════════════════════════════════════════════════
# PACKAGE VISIBILITY
# ══════════════════════════════════════════════════════════════

@router.get("/v1/tenant/packages/available",
            summary="Get packages available to this tenant",
            tags=["Tenant Packages"])
async def tenant_get_available_packages(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> dict:
    tid = _tenant_id(user)
    return _ok(await _svc(db, request, user).get_available_packages(tid), request)


@router.get("/v1/tenant/packages/purchases",
            summary="List this tenant's package purchase history",
            tags=["Tenant Packages"])
async def tenant_list_purchases(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> dict:
    tid = _tenant_id(user)
    return _ok(await _svc(db, request, user).get_tenant_purchases(tid, limit, offset), request)


class TenantPackagePurchaseRequest(BaseModel):
    """Slice 2F-22 — deliberately accepts NO client-supplied fields.

    This body was previously an untyped `payload: dict`, from which the route
    read two fields that a tenant has no authority to assert:

      * `mark_paid`  -> passed straight through as `is_paid`, which set the
        assignment to `paid_pending_approval` WITH a `paid_at` timestamp.
        A tenant could therefore declare its own payment settled without any
        payment ever occurring (CLIENT_SETTLEMENT_ATTESTATION_TRUSTED).
      * `payment_reference` -> stored verbatim as `payment_reference_id`,
        letting a tenant fabricate an external transaction reference to
        corroborate that false claim.

    Both mattered because `activate_tenant_package_assignment` orders
    candidates by `paid_at DESC NULLS LAST` -- a self-attested "paid"
    assignment was actively PREFERRED for activation, and activation is what
    grants wallet credits, storage quota and commission rate.

    The two legitimate callers that DO set is_paid=True are unaffected and
    remain correct, because each holds real authority the tenant does not:
      * public_registration -> only after `verify_payment_signature()` passes
        (authoritative gateway proof).
      * admin_router        -> under `P.PACKAGES_CREATE` (admin attestation).

    `extra="forbid"` additionally rejects any monetary/entitlement field a
    client might try (amount, price, currency, discount, credits, expiry,
    ...) rather than silently ignoring it, so the request contract cannot be
    misread as accepting terms the server does not honour. Every such value
    is server-derived from the ServicePackage record.
    """
    model_config = ConfigDict(extra="forbid")


@router.post("/v1/tenant/packages/{package_id}/purchase",
             status_code=201,
             summary="Request a package (creates an unpaid selection pending admin approval)",
             tags=["Tenant Packages", "Package Purchase"])
async def tenant_purchase_package(
    package_id: uuid.UUID,
    payload: TenantPackagePurchaseRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
) -> dict:
    # MODULE-L5-30: this used to call purchase_package(), which writes a
    # TenantPackagePurchase row into `tenant_package_purchases` — a table that
    # was never migrated (does not exist in the database), so every call 500'd.
    # The real, tested, symmetric mechanism is the P1 assignment lifecycle
    # (create_package_assignment now / admin activate_tenant_package_assignment
    # on approval), which is what tenant_package_assignments-backed status
    # checks (get_packages_status) actually read. Previously that mechanism was
    # only ever invoked inline during initial public registration — an already
    # onboarded tenant had no way at all to buy an additional/renewal package.
    # Slice 2F-22: no payment verifier is wired to the ServicePackage /
    # TenantPackageAssignment flow for a tenant-initiated purchase, so this
    # route creates ONLY the safe unpaid state the model already supports
    # (`pending_review`). Payment is established later by an authority that
    # can actually prove it -- gateway signature (public_registration) or
    # admin attestation (admin_router). Nothing here activates a package,
    # issues credits, or writes a paid ledger entry.
    tid = _tenant_id(user)
    result = await _svc(db, request, user).create_package_assignment(
        tid, package_id,
        payment_reference=None,
        is_paid=False,
        payment_authority="tenant_unpaid_request",
    )
    await db.commit()
    return _ok(result, request)


# ══════════════════════════════════════════════════════════════
# SECURITY DEPOSIT (read-only for tenant)
# ══════════════════════════════════════════════════════════════

@router.get("/v1/tenant/security-deposit",
            summary="Get security deposit status",
            tags=["Security Deposit"])
async def tenant_get_deposit(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> dict:
    tid = _tenant_id(user)
    return _ok(await _svc(db, request, user).get_security_deposit(tid), request)


# ══════════════════════════════════════════════════════════════
# CREDIT WALLET + LEDGER
# ══════════════════════════════════════════════════════════════

@router.get("/v1/tenant/credit-wallet",
            summary="Get credit wallet balance",
            tags=["Credit Wallet"])
async def tenant_get_credit_wallet(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> dict:
    tid = _tenant_id(user)
    return _ok(await _svc(db, request, user).get_credit_wallet_detail(tid), request)


@router.get("/v1/tenant/credit-ledger",
            summary="Get credit ledger",
            tags=["Credit Ledger"])
async def tenant_get_credit_ledger(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> dict:
    tid = _tenant_id(user)
    return _ok(await _svc(db, request, user).get_credit_ledger(tid, limit, offset), request)


# ══════════════════════════════════════════════════════════════
# COMMISSIONS (read-only for tenant)
# ══════════════════════════════════════════════════════════════

@router.get("/v1/tenant/commissions",
            summary="List commission deductions for this tenant",
            tags=["Commission Deduction"])
async def tenant_list_commissions(
    request: Request,
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> dict:
    tid = _tenant_id(user)
    return _ok(await _svc(db, request, user).list_commissions(tid, status, limit, offset), request)


# ══════════════════════════════════════════════════════════════
# STORAGE QUOTA (read-only for tenant)
# ══════════════════════════════════════════════════════════════

@router.get("/v1/tenant/storage-quota",
            summary="Get storage quota usage",
            tags=["Storage Quota"])
async def tenant_get_storage_quota(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> dict:
    tid = _tenant_id(user)
    return _ok(await _svc(db, request, user).get_storage_quota(tid), request)
