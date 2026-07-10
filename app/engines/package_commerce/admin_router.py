"""Sprint 5 — Package Commerce Admin Router.

All endpoints under /v1/admin/packages/ and /v1/admin/tenants/{tenant_id}/...
Requires super_admin for write operations.
"""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin, get_current_user, UserContext
from app.dependencies.db import get_db
from app.core.permissions import require_permission, P
from app.engines.package_commerce.service import PackageCommerceService
from app.exceptions import ServiceOSException

router = APIRouter(tags=["Admin Packages"])

ENGINE_ID = "package_credit"


def _svc(db: AsyncSession, request: Request, user: UserContext) -> PackageCommerceService:
    actor_id = uuid.UUID(user.user_id) if user and user.user_id else None
    ip = request.client.host if request.client else None
    return PackageCommerceService(
        db=db,
        request_id=getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"),
        actor_id=actor_id,
        actor_role=user.role if user else None,
        ip_address=ip,
    )


def _ok(data: dict, request: Request) -> dict:
    return {
        "success": True,
        "data": data,
        "request_id": getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"),
        "engine_id": ENGINE_ID,
    }


# ══════════════════════════════════════════════════════════════
# PACKAGE SUMMARY
# ══════════════════════════════════════════════════════════════

@router.get("/v1/admin/packages/summary", summary="Package summary counts", tags=["Admin Packages"])
async def get_packages_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_READ)),
):
    """Summary counts for the Packages & Plans enterprise page."""
    result = await db.execute(text("""
        SELECT
            COUNT(*)                                                            AS total,
            SUM(CASE WHEN is_active = TRUE  THEN 1 ELSE 0 END)                 AS active,
            SUM(CASE WHEN is_active = FALSE THEN 1 ELSE 0 END)                 AS inactive,
            SUM(CASE WHEN package_type = 'onboarding'     THEN 1 ELSE 0 END)   AS onboarding,
            SUM(CASE WHEN package_type = 'subscription'   THEN 1 ELSE 0 END)   AS subscription,
            SUM(CASE WHEN package_type = 'lead_credit'    THEN 1 ELSE 0 END)   AS lead_credit,
            SUM(CASE WHEN package_type = 'deposit'        THEN 1 ELSE 0 END)   AS deposit,
            SUM(CASE WHEN is_featured = TRUE              THEN 1 ELSE 0 END)   AS featured
        FROM service_packages
        WHERE deleted_at IS NULL
    """))
    r = result.fetchone()
    # Assigned packages count (tenant_package_assignments active)
    asgn = await db.execute(text("""
        SELECT COUNT(*) FROM tenant_package_assignments
        WHERE status = 'active' AND deleted_at IS NULL
    """))
    active_assignments = int(asgn.scalar() or 0)
    return _ok({
        "total":              int(r[0] or 0),
        "active":             int(r[1] or 0),
        "inactive":           int(r[2] or 0),
        "onboarding":         int(r[3] or 0),
        "subscription":       int(r[4] or 0),
        "lead_credit":        int(r[5] or 0),
        "deposit":            int(r[6] or 0),
        "featured":           int(r[7] or 0),
        "active_assignments": active_assignments,
    }, request)


# PACKAGE CRUD — /v1/admin/packages
# ══════════════════════════════════════════════════════════════

@router.get("/v1/admin/packages", summary="List all packages", tags=["Admin Packages"])
async def list_packages(
    request: Request,
    package_type: str | None = Query(None),
    is_active: bool | None = Query(None),
    vertical_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_READ)),
) -> dict:
    return _ok(await _svc(db, request, user).list_packages(package_type, is_active, vertical_type), request)


@router.post("/v1/admin/packages", status_code=201, summary="Create package", tags=["Admin Packages"])
async def create_package(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_CREATE)),
) -> dict:
    return _ok(await _svc(db, request, user).create_package(payload), request)


@router.get("/v1/admin/packages/audit-logs", summary="List package/finance audit log (global)", tags=["Admin Packages"])
async def list_all_package_audit(
    request: Request,
    tenant_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_AUDIT_READ)),
) -> dict:
    return _ok(await _svc(db, request, user).list_package_audit(None, tenant_id, limit), request)


@router.get("/v1/admin/packages/purchases", summary="List tenant package assignments (global)", tags=["Admin Packages"])
async def list_all_package_purchases(
    request: Request,
    tenant_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_READ)),
) -> dict:
    return _ok(await _svc(db, request, user).get_tenant_purchases(tenant_id, limit, offset), request)


@router.get("/v1/admin/packages/{package_id}", summary="Get package detail (with features/limits)", tags=["Admin Packages"])
async def get_package(
    package_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_READ)),
) -> dict:
    return _ok(await _svc(db, request, user).get_package_with_details(package_id), request)


@router.put("/v1/admin/packages/{package_id}", summary="Update package", tags=["Admin Packages"])
async def update_package(
    package_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_UPDATE)),
) -> dict:
    return _ok(await _svc(db, request, user).update_package(package_id, payload), request)


@router.delete("/v1/admin/packages/{package_id}", summary="Soft-delete package", tags=["Admin Packages"])
async def delete_package(
    package_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_ARCHIVE)),
) -> dict:
    return _ok(await _svc(db, request, user).delete_package(package_id), request)


@router.post("/v1/admin/packages/{package_id}/activate",
             summary="Activate package", tags=["Admin Packages"])
async def activate_package(
    package_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_ACTIVATE)),
) -> dict:
    return _ok(await _svc(db, request, user).activate_package(package_id), request)


@router.post("/v1/admin/packages/{package_id}/deactivate",
             summary="Deactivate package", tags=["Admin Packages"])
async def deactivate_package(
    package_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_DEACTIVATE)),
) -> dict:
    return _ok(await _svc(db, request, user).deactivate_package(package_id), request)


@router.post("/v1/admin/packages/{package_id}/clone",
             status_code=201, summary="Clone package (with features/limits)", tags=["Admin Packages"])
async def clone_package(
    package_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_CLONE)),
) -> dict:
    return _ok(await _svc(db, request, user).clone_package(package_id), request)


@router.get("/v1/admin/packages/{package_id}/audit", summary="Package audit trail", tags=["Admin Packages"])
async def get_package_audit(
    package_id: uuid.UUID,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_AUDIT_READ)),
) -> dict:
    return _ok(await _svc(db, request, user).list_package_audit(package_id, None, limit), request)


# ══════════════════════════════════════════════════════════════
# PACKAGE FEATURES — /v1/admin/packages/{id}/features
# ══════════════════════════════════════════════════════════════

@router.get("/v1/admin/packages/{package_id}/features",
            summary="List package features", tags=["Package Features"])
async def list_package_features(
    package_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_READ)),
) -> dict:
    return _ok(await _svc(db, request, user).list_package_features(package_id), request)


@router.post("/v1/admin/packages/{package_id}/features",
             status_code=201, summary="Add package feature", tags=["Package Features"])
async def create_package_feature(
    package_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_UPDATE)),
) -> dict:
    return _ok(await _svc(db, request, user).create_package_feature(package_id, payload), request)


@router.put("/v1/admin/packages/{package_id}/features/{feature_id}",
            summary="Update package feature", tags=["Package Features"])
async def update_package_feature(
    package_id: uuid.UUID,
    feature_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_UPDATE)),
) -> dict:
    return _ok(await _svc(db, request, user).update_package_feature(package_id, feature_id, payload), request)


@router.delete("/v1/admin/packages/{package_id}/features/{feature_id}",
               summary="Delete package feature", tags=["Package Features"])
async def delete_package_feature(
    package_id: uuid.UUID,
    feature_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_UPDATE)),
) -> dict:
    return _ok(await _svc(db, request, user).delete_package_feature(package_id, feature_id), request)


# ══════════════════════════════════════════════════════════════
# PACKAGE LIMITS — /v1/admin/packages/{id}/limits
# ══════════════════════════════════════════════════════════════

@router.get("/v1/admin/packages/{package_id}/limits",
            summary="List package limits", tags=["Package Limits"])
async def list_package_limits(
    package_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_READ)),
) -> dict:
    return _ok(await _svc(db, request, user).list_package_limits(package_id), request)


@router.post("/v1/admin/packages/{package_id}/limits",
             status_code=201, summary="Add package limit", tags=["Package Limits"])
async def create_package_limit(
    package_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_UPDATE)),
) -> dict:
    return _ok(await _svc(db, request, user).create_package_limit(package_id, payload), request)


@router.put("/v1/admin/packages/{package_id}/limits/{limit_id}",
            summary="Update package limit", tags=["Package Limits"])
async def update_package_limit(
    package_id: uuid.UUID,
    limit_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_UPDATE)),
) -> dict:
    return _ok(await _svc(db, request, user).update_package_limit(package_id, limit_id, payload), request)


@router.delete("/v1/admin/packages/{package_id}/limits/{limit_id}",
               summary="Delete package limit", tags=["Package Limits"])
async def delete_package_limit(
    package_id: uuid.UUID,
    limit_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_UPDATE)),
) -> dict:
    return _ok(await _svc(db, request, user).delete_package_limit(package_id, limit_id), request)


# ══════════════════════════════════════════════════════════════
# TENANT PACKAGE — /v1/admin/tenants/{tenant_id}/packages
# ══════════════════════════════════════════════════════════════

@router.get("/v1/admin/tenants/{tenant_id}/packages/available",
            summary="Get available packages for tenant", tags=["Admin Packages"])
async def admin_get_available_packages(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_READ)),
) -> dict:
    return _ok(await _svc(db, request, user).get_available_packages(tenant_id), request)


@router.get("/v1/admin/tenants/{tenant_id}/packages/purchases",
            summary="List tenant package purchases", tags=["Admin Packages"])
async def admin_list_purchases(
    tenant_id: uuid.UUID,
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_READ)),
) -> dict:
    return _ok(await _svc(db, request, user).get_tenant_purchases(tenant_id, limit, offset), request)


@router.post("/v1/admin/tenants/{tenant_id}/packages/{package_id}/purchase",
             status_code=201, summary="Purchase package for tenant (admin)", tags=["Admin Packages"])
async def admin_purchase_package(
    tenant_id: uuid.UUID,
    package_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.PACKAGES_CREATE)),
) -> dict:
    return _ok(
        await _svc(db, request, user).purchase_package(tenant_id, package_id, payload), request
    )


# ══════════════════════════════════════════════════════════════
# SECURITY DEPOSIT — /v1/admin/tenants/{tenant_id}/security-deposit
# ══════════════════════════════════════════════════════════════

@router.get("/v1/admin/tenants/{tenant_id}/security-deposit",
            summary="Get tenant security deposit", tags=["Security Deposit"])
async def admin_get_deposit(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.FINANCE_SECURITY_DEPOSITS_READ)),
) -> dict:
    return _ok(await _svc(db, request, user).get_security_deposit(tenant_id), request)


@router.post("/v1/admin/tenants/{tenant_id}/security-deposit/mark-paid",
             summary="Mark security deposit as paid", tags=["Security Deposit"])
async def admin_mark_deposit_paid(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.FINANCE_SECURITY_DEPOSITS_MARK_RECEIVED)),
) -> dict:
    return _ok(await _svc(db, request, user).admin_mark_deposit_paid(tenant_id, payload), request)


@router.post("/v1/admin/tenants/{tenant_id}/security-deposit/refund",
             summary="Refund security deposit", tags=["Security Deposit"])
async def admin_refund_deposit(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.FINANCE_SECURITY_DEPOSITS_RELEASE)),
) -> dict:
    return _ok(await _svc(db, request, user).admin_refund_deposit(tenant_id, payload), request)


@router.post("/v1/admin/tenants/{tenant_id}/security-deposit/forfeit",
             summary="Forfeit security deposit", tags=["Security Deposit"])
async def admin_forfeit_deposit(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.FINANCE_SECURITY_DEPOSITS_ADJUST)),
) -> dict:
    return _ok(await _svc(db, request, user).admin_forfeit_deposit(tenant_id, payload), request)


# ══════════════════════════════════════════════════════════════
# CREDIT WALLET — /v1/admin/tenants/{tenant_id}/credit-wallet
# ══════════════════════════════════════════════════════════════

@router.get("/v1/admin/tenants/{tenant_id}/credit-wallet",
            summary="Get tenant credit wallet", tags=["Credit Wallet"])
async def admin_get_wallet(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.FINANCE_USAGE_CREDITS_READ)),
) -> dict:
    return _ok(await _svc(db, request, user).get_credit_wallet_detail(tenant_id), request)


@router.get("/v1/admin/tenants/{tenant_id}/credit-ledger",
            summary="Get tenant credit ledger", tags=["Credit Ledger"])
async def admin_get_ledger(
    tenant_id: uuid.UUID,
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.FINANCE_USAGE_CREDITS_LEDGER_READ)),
) -> dict:
    return _ok(await _svc(db, request, user).get_credit_ledger(tenant_id, limit, offset), request)


@router.post("/v1/admin/tenants/{tenant_id}/credit-wallet/top-up",
             summary="Admin top-up tenant credit wallet", tags=["Credit Wallet"])
async def admin_topup_wallet(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.FINANCE_USAGE_CREDITS_TOP_UP)),
) -> dict:
    return _ok(await _svc(db, request, user).admin_topup_wallet(tenant_id, payload), request)


@router.post("/v1/admin/tenants/{tenant_id}/credit-wallet/adjust",
             summary="Admin adjust tenant credit wallet", tags=["Credit Wallet"])
async def admin_adjust_wallet(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.FINANCE_USAGE_CREDITS_ADJUST)),
) -> dict:
    return _ok(await _svc(db, request, user).admin_adjust_wallet(tenant_id, payload), request)


# ══════════════════════════════════════════════════════════════
# COMMISSION — /v1/admin/jobs/{job_id}/...
# ══════════════════════════════════════════════════════════════

@router.get("/v1/admin/tenants/{tenant_id}/commissions",
            summary="List commissions for tenant", tags=["Commission Deduction"])
async def admin_list_commissions(
    tenant_id: uuid.UUID,
    request: Request,
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> dict:
    return _ok(
        await _svc(db, request, user).list_commissions(tenant_id, status, limit, offset), request
    )


@router.post("/v1/admin/jobs/{job_id}/deduct-commission",
             summary="Deduct commission from tenant wallet for a job",
             tags=["Commission Deduction"])
async def admin_deduct_commission(
    job_id: str,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
) -> dict:
    tenant_id_str = payload.get("tenant_id")
    if not tenant_id_str:
        raise ServiceOSException("VALIDATION_ERROR", "tenant_id is required in request body.")
    tenant_id = uuid.UUID(tenant_id_str)
    return _ok(await _svc(db, request, user).deduct_commission(job_id, tenant_id), request)


@router.post("/v1/admin/jobs/{job_id}/calculate-commission",
             summary="Calculate commission for a job",
             tags=["Commission Deduction"])
async def admin_calculate_commission(
    job_id: str,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
) -> dict:
    from decimal import Decimal
    tenant_id_str = payload.get("tenant_id")
    if not tenant_id_str:
        raise ServiceOSException("VALIDATION_ERROR", "tenant_id is required.")
    job_value = Decimal(str(payload.get("job_value", 0)))
    invoice_id = uuid.UUID(payload["invoice_id"]) if payload.get("invoice_id") else None
    payment_id = uuid.UUID(payload["payment_id"]) if payload.get("payment_id") else None
    return _ok(
        await _svc(db, request, user).calculate_commission(
            job_id, uuid.UUID(tenant_id_str), job_value, invoice_id, payment_id
        ),
        request,
    )


# ══════════════════════════════════════════════════════════════
# STORAGE QUOTA — /v1/admin/tenants/{tenant_id}/storage-quota
# ══════════════════════════════════════════════════════════════

@router.get("/v1/admin/tenants/{tenant_id}/storage-quota",
            summary="Get tenant storage quota usage", tags=["Storage Quota"])
async def admin_get_storage_quota(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> dict:
    return _ok(await _svc(db, request, user).get_storage_quota(tenant_id), request)
