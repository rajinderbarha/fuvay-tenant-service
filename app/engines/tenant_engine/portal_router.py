"""Sprint 4 — Tenant Portal Router.

Mirror of the admin router for tenant-facing self-service.
tenant_id is extracted from the JWT — no manual passing.
All endpoints under /v1/tenant/.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_tenant_owner, get_current_user, UserContext
from app.core.permissions import require_tenant_owner_mutation
from app.dependencies.db import get_db
from app.engines.tenant_engine.admin_service import AdminTenantService
from app.engines.tenant_engine.models import Tenant
from app.engines.admin_catalog.models import ServiceCategory
from app.engines.entitlement.service import entitlement_service
from app.exceptions import ServiceOSException
from app.schemas.base import ok

router = APIRouter(prefix="/v1/tenant", tags=["Tenant Portal"])


def _svc(db: AsyncSession, request: Request, user: UserContext) -> AdminTenantService:
    """Build service from the tenant's own JWT context."""
    actor_id = uuid.UUID(user.user_id) if user.user_id else None
    ip = request.client.host if request.client else None
    return AdminTenantService(
        db=db,
        request_id=(getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")),
        actor_id=actor_id,
        actor_role=user.role,
        ip_address=ip,
    )


def _tenant_id(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise ServiceOSException("TENANT_ACCESS_DENIED", "No tenant context in token.")
    return uuid.UUID(user.tenant_id)


# ── Profile ────────────────────────────────────────────────────

@router.get("/profile")
async def get_profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> dict:
    tid = _tenant_id(user)
    return await _svc(db, request, user).get_tenant(tid)


@router.patch("/profile")
async def update_profile(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
) -> dict:
    tid = _tenant_id(user)
    # Restrict what tenant can change (no status/verification changes)
    safe_fields = [
        "address_line1", "address_line2", "district",
        "phone", "email", "logo_url", "is_discoverable",
    ]
    safe_payload = {k: v for k, v in payload.items() if k in safe_fields}
    return await _svc(db, request, user).update_tenant(tid, safe_payload)


# ── Settings ───────────────────────────────────────────────────

@router.get("/settings")
async def get_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> dict:
    tid = _tenant_id(user)
    return await _svc(db, request, user).get_settings(tid)


@router.patch("/settings")
async def update_settings(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
) -> dict:
    tid = _tenant_id(user)
    # Tenant cannot change commission_rate (platform-set)
    payload.pop("commission_rate", None)
    return await _svc(db, request, user).update_settings(tid, payload)


# ── Users ──────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    request: Request,
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> dict:
    tid = _tenant_id(user)
    return await _svc(db, request, user).list_users(tid, search=search)


@router.post("/users", status_code=201)
async def create_user(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
) -> dict:
    tid = _tenant_id(user)
    return await _svc(db, request, user).create_user(tid, payload)


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
) -> dict:
    tid = _tenant_id(user)
    return await _svc(db, request, user).suspend_user(tid, user_id)


# ── Staff ──────────────────────────────────────────────────────

@router.get("/staff")
async def list_staff(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> dict:
    tid = _tenant_id(user)
    return await _svc(db, request, user).list_staff(tid)


@router.post("/staff", status_code=201)
async def create_staff(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
) -> dict:
    tid = _tenant_id(user)
    return await _svc(db, request, user).create_staff(tid, payload)


@router.post("/staff/{staff_id}/deactivate")
async def deactivate_staff(
    staff_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
) -> dict:
    tid = _tenant_id(user)
    return await _svc(db, request, user).deactivate_staff(tid, staff_id)


@router.patch("/staff/{staff_id}/photo")
async def update_staff_photo(
    staff_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
) -> dict:
    tid = _tenant_id(user)
    photo_url = payload.get("photo_url", "")
    if not photo_url:
        raise HTTPException(status_code=422, detail="photo_url is required")
    return await _svc(db, request, user).update_staff_photo(tid, staff_id, photo_url)


# FINAL-L5-05T: Service Area routes removed from this router entirely.
# GET/POST/DELETE were exact (method, path) duplicates of
# app.engines.serviceability.router's list/create/delete_tenant_service_area
# (unreachable dead code -- serviceability.router registers first).
# PATCH /service-areas/{area_id} was a second live mutation path on a
# different verb from the canonical PUT, but had zero real caller --
# the tenant-portal frontend (frontend/tenant-portal/lib/api.ts,
# `serviceAreaApi.update`) already calls PUT, matching serviceability's
# real contract. See
# docs/final-l5-05/FINAL_L5_05T_ADR_SERVICE_AREA_CANONICAL_OWNER.md.
# Canonical: GET/POST /v1/tenant/service-areas,
# GET/PUT/DELETE /v1/tenant/service-areas/{area_id}, plus limits/validate/
# set-primary/services (app/engines/serviceability/router.py).

# ── Wallet (read-only for tenant) ──────────────────────────────

@router.get("/wallet")
async def get_tenant_wallet(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> dict:
    tid = _tenant_id(user)
    return await _svc(db, request, user).get_credit_wallet(tid)


@router.get("/wallet/ledger")
async def get_tenant_ledger(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> dict:
    tid = _tenant_id(user)
    return await _svc(db, request, user).get_credit_ledger(tid, limit=limit)


# ── Navigation ─────────────────────────────────────────────────

_NAV_BY_DASHBOARD_TYPE: dict[str, list[dict]] = {
    "home_services": [
        {"label": "Dashboard",           "route": "/dashboard"},
        {"label": "Jobs",                "route": "/jobs"},
        {"label": "Service Jobs",        "route": "/service-jobs"},
        {"label": "Bookings",            "route": "/bookings"},
        {"label": "Staff",               "route": "/staff"},
        {"label": "Catalog",             "route": "/catalog"},
        {"label": "Dispatch",            "route": "/dispatch"},
        {"label": "Finance",             "route": "/finance"},
        {"label": "Reviews",             "route": "/reviews"},
        {"label": "Analytics",           "route": "/analytics"},
        {"label": "My Status",           "route": "/provider/status"},
        {"label": "My Marketing",        "route": "/provider/marketing"},
        {"label": "My Offerings",        "route": "/provider/offerings"},
        {"label": "Service Areas",       "route": "/provider/service-areas"},
        {"label": "Team Members",        "route": "/provider/team-members"},
        {"label": "Availability",        "route": "/provider/availability"},
        {"label": "Onboarding Checklist","route": "/onboarding-status"},
    ],
    "coaching": [
        {"label": "Dashboard",           "route": "/dashboard"},
        {"label": "Appointments",        "route": "/appointments"},
        {"label": "Staff",               "route": "/staff"},
        {"label": "Finance",             "route": "/finance"},
        {"label": "Reviews",             "route": "/reviews"},
        {"label": "Analytics",           "route": "/analytics"},
        {"label": "My Status",           "route": "/provider/status"},
        {"label": "My Offerings",        "route": "/provider/offerings"},
        {"label": "My Marketing",        "route": "/provider/marketing"},
        {"label": "Availability",        "route": "/provider/availability"},
        {"label": "Onboarding Checklist","route": "/onboarding-status"},
    ],
    "real_estate": [
        {"label": "Dashboard",           "route": "/dashboard"},
        {"label": "Leads",               "route": "/provider/my-records/leads"},
        {"label": "Staff / Agents",      "route": "/staff"},
        {"label": "Finance",             "route": "/finance"},
        {"label": "Analytics",           "route": "/analytics"},
        {"label": "My Status",           "route": "/provider/status"},
        {"label": "My Marketing",        "route": "/provider/marketing"},
        {"label": "Onboarding Checklist","route": "/onboarding-status"},
    ],
}

_NAV_GENERIC = [
    {"label": "Dashboard",           "route": "/dashboard"},
    {"label": "Jobs",                "route": "/jobs"},
    {"label": "Bookings",            "route": "/bookings"},
    {"label": "Staff",               "route": "/staff"},
    {"label": "Catalog",             "route": "/catalog"},
    {"label": "Dispatch",            "route": "/dispatch"},
    {"label": "Finance",             "route": "/finance"},
    {"label": "Reviews",             "route": "/reviews"},
    {"label": "Analytics",           "route": "/analytics"},
    {"label": "My Status",           "route": "/provider/status"},
    {"label": "My Offerings",        "route": "/provider/offerings"},
    {"label": "Onboarding Checklist","route": "/onboarding-status"},
]


@router.get("/dashboard/runtime", summary="Return tenant category runtime — drives which dashboard component loads")
async def get_dashboard_runtime(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tenant_id(user)
    tenant = await db.scalar(select(Tenant).where(Tenant.id == tid))
    category: ServiceCategory | None = None

    if tenant and tenant.category_id:
        category = await db.scalar(
            select(ServiceCategory).where(ServiceCategory.id == tenant.category_id)
        )

    category_obj = None
    if category:
        category_obj = {
            "id": str(category.id),
            "name": category.name,
            "slug": category.slug,
            "category_type": category.category_type,
            "customer_flow_type": category.customer_flow_type,
            "provider_dashboard_type": category.provider_dashboard_type,
        }

    # `tenant.category_id` and `ServiceCategory.category_type` are both
    # frequently unpopulated in real tenant data (e.g. real seeded tenants
    # have category_id=NULL) — `tenant.vertical` is the actual, always-set
    # source of truth used everywhere else in the backend (matches
    # ServiceCategory.vertical_type). Surfacing it here as a top-level
    # `category_type` fixes the tenant-portal login flow, which reads
    # `runtime.category_type` to populate `serviceos_tenant_vertical` in
    # localStorage — without this, every real (non-mock) tenant login left
    # that value blank, incorrectly triggering every Home-Services-only
    # guard in the app for every tenant, every time.
    vertical = tenant.vertical if tenant else None

    # FINAL-L5-04B: modules/categories now come from the real
    # tenant_module_entitlements / tenant_category_entitlements tables
    # instead of the hardcoded empty arrays this endpoint returned before
    # (tenant.category_id was always NULL for real tenants — see
    # FINAL_L5_04B_TENANT_ENTITLEMENT_NAVIGATION_REPORT.md).
    entitled_modules: list[dict] = []
    entitled_categories: list[dict] = []
    if tenant:
        entitled_modules = await entitlement_service.get_tenant_modules(db, tid, effective_only=True)
        entitled_categories = await entitlement_service.get_tenant_categories(db, tid, effective_only=True)

    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    return ok({
        "tenant": {
            "tenant_id": str(tid),
            "business_name": (tenant.business_name or tenant.tenant_name) if tenant else None,
            "category": category_obj,
        } if tenant else None,
        "category_type": vertical or (category.category_type if category else None),
        "dashboard_type": category.provider_dashboard_type if category else None,
        "primary_engine": category.primary_engine_key if category else None,
        "enabled_engines": [m["module_key"] for m in entitled_modules],
        "modules": entitled_modules,
        "entitled_categories": entitled_categories,
        "category": category_obj,
    }, rid, "tenant_portal")


@router.get("/navigation", summary="Dynamic sidebar navigation for this tenant's category")
async def get_navigation(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tenant_id(user)

    # Load tenant + category in one query
    tenant = await db.scalar(select(Tenant).where(Tenant.id == tid))
    category: ServiceCategory | None = None
    dashboard_type: str | None = None

    if tenant and tenant.category_id:
        category = await db.scalar(
            select(ServiceCategory).where(ServiceCategory.id == tenant.category_id)
        )
        if category:
            dashboard_type = category.provider_dashboard_type

    items = _NAV_BY_DASHBOARD_TYPE.get(dashboard_type or "", _NAV_GENERIC)

    # FINAL-L5-04B: real per-tenant category entitlement, not just the
    # dashboard-type-keyed static item list above (which is module-shaped,
    # not category-shaped, and unaffected by this addition).
    entitled_categories = await entitlement_service.get_tenant_categories(db, tid, effective_only=True) if tenant else []

    payload = {
        "category": {
            "id":                      str(category.id) if category else None,
            "name":                    category.name if category else None,
            "category_type":           category.category_type if category else None,
            "provider_dashboard_type": dashboard_type,
        },
        "items": items,
        "entitled_categories": entitled_categories,
    }
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    return ok(payload, rid, "tenant_portal")


# ── Staff Security (tenant-scoped) ─────────────────────────────
# Tenant owners can lock/unlock/revoke sessions of their own staff.
# _can_admin_manage_user() in AuthService already enforces tenant scope.

@router.post("/staff/{user_id}/lock", summary="Lock a staff member's account (tenant-scoped)")
async def lock_staff(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    from app.engines.auth.service import AuthService
    from app.engines.auth.schemas import LockAccountRequest
    body = await request.json()
    svc = AuthService(db=db, request_id=(getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")))
    req = LockAccountRequest(
        reason=body.get("reason", "Admin review"),
        locked_until=body.get("locked_until"),
        revoke_sessions=body.get("revoke_sessions", True),
    )
    data = await svc.lock_user(admin=user, target_user_id=user_id,
                               reason=req.reason, locked_until=req.locked_until,
                               revoke_sessions=req.revoke_sessions)
    return ok(data, (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")), "tenant_portal")


@router.post("/staff/{user_id}/unlock", summary="Unlock a staff member's account (tenant-scoped)")
async def unlock_staff(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    from app.engines.auth.service import AuthService
    from app.engines.auth.schemas import UnlockAccountRequest
    body = await request.json()
    svc = AuthService(db=db, request_id=(getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")))
    req = UnlockAccountRequest(reason=body.get("reason", "Issue resolved"))
    data = await svc.unlock_user(admin=user, target_user_id=user_id, reason=req.reason)
    return ok(data, (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")), "tenant_portal")


@router.post("/staff/{user_id}/sessions/revoke-all", summary="Revoke all sessions for a staff member")
async def revoke_staff_sessions(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    from app.engines.auth.service import AuthService
    _tenant_id(user)
    svc = AuthService(db=db, request_id=(getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")))
    body = await request.json()
    data = await svc.admin_revoke_all_sessions(user, user_id, body.get("reason", "Tenant admin revoke"))
    return ok(data, (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")), "tenant_portal")


@router.get("/staff/{user_id}/login-history", summary="Get staff login history (tenant-scoped)")
async def staff_login_history(
    user_id: uuid.UUID,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner),
):
    from app.engines.auth.service import AuthService
    svc = AuthService(db=db, request_id=(getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")))
    data = await svc.get_audit_log(user_id=user_id, tenant_id=None, role="tenant_owner", limit=limit)
    return ok(data, (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")), "tenant_portal")


@router.get("/staff/{user_id}/security", summary="Get staff security status (tenant-scoped)")
async def staff_security_status(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner),
):
    from app.engines.auth.service import AuthService
    svc = AuthService(db=db, request_id=(getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")))
    data = await svc.get_full_security_status(admin=user, target_user_id=user_id)
    return ok(data, (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")), "tenant_portal")


# ── Dashboard Summaries (category-specific) ────────────────────
# Aggregated from existing analytics/jobs/appointment tables per category.

@router.get("/dashboard/home-services/summary", summary="Home services dashboard summary")
async def home_services_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    from sqlalchemy import text
    tid = _tenant_id(user)
    try:
        job_count = (await db.execute(
            text("SELECT COUNT(*) FROM jobs WHERE tenant_id = :tid"), {"tid": tid}
        )).scalar() or 0
        open_jobs = (await db.execute(
            text("SELECT COUNT(*) FROM jobs WHERE tenant_id = :tid AND status NOT IN ('completed','cancelled')"),
            {"tid": tid}
        )).scalar() or 0
    except Exception:
        job_count = 0
        open_jobs = 0
    summary = {
        "total_jobs": int(job_count),
        "open_jobs": int(open_jobs),
        "category_type": "home_services",
    }
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    return ok(summary, rid, "tenant_portal")


@router.get("/dashboard/coaching/summary", summary="Coaching dashboard summary")
async def coaching_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    from sqlalchemy import text
    tid = _tenant_id(user)
    try:
        appt_count = (await db.execute(
            text("SELECT COUNT(*) FROM appointments WHERE tenant_id = :tid"), {"tid": tid}
        )).scalar() or 0
    except Exception:
        appt_count = 0
    summary = {
        "total_appointments": int(appt_count),
        "category_type": "coaching",
    }
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    return ok(summary, rid, "tenant_portal")


@router.get("/dashboard/real-estate/summary", summary="Real estate dashboard summary")
async def real_estate_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    from sqlalchemy import text
    tid = _tenant_id(user)
    try:
        lead_count = (await db.execute(
            text("SELECT COUNT(*) FROM real_estate_leads WHERE tenant_id = :tid"), {"tid": tid}
        )).scalar() or 0
    except Exception:
        lead_count = 0
    summary = {
        "total_leads": int(lead_count),
        "category_type": "real_estate",
    }
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    return ok(summary, rid, "tenant_portal")


@router.get("/engines/effective", summary="Effective engine list for this tenant")
async def get_tenant_effective_engines(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    from app.engine_registry.registry import registry
    from app.engine_registry.models import TenantEngine

    tid = _tenant_id(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))

    rows = (await db.execute(
        select(TenantEngine).where(TenantEngine.tenant_id == tid, TenantEngine.is_enabled == True)  # noqa: E712
    )).scalars().all()
    enabled_ids = {r.engine_id for r in rows}

    summary = registry.summary()
    summary["tenant_id"] = str(tid)
    for e in summary["engines"]:
        # Core engines are always active; plugin engines reflect this
        # tenant's real enabled_engines state. Aliased as engine_key /
        # effective_enabled to match the tenant-portal frontend's contract
        # (e.g. the Inventory Document Extraction upload gate).
        e["engine_key"] = e["engine_id"]
        e["effective_enabled"] = e["type"] == "core" or e["engine_id"] in enabled_ids
    return ok(summary, rid, "tenant_portal")


@router.get("/monetization/status", summary="Tenant monetization readiness status")
async def get_monetization_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    from sqlalchemy import text
    tid = _tenant_id(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    try:
        row = await db.execute(text("SELECT * FROM provider_monetization_statuses WHERE tenant_id=:tid LIMIT 1"), {"tid": tid})
        r = row.fetchone()
        data = dict(r._mapping) if r else {"tenant_id": str(tid), "is_monetization_ready": False, "monetization_model": None}
    except Exception:
        data = {"tenant_id": str(tid), "is_monetization_ready": False, "monetization_model": None}
    return ok(data, rid, "tenant_portal")
