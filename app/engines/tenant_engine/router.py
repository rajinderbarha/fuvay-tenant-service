"""
Tenant Engine — FastAPI Router (Complete — 42 endpoints)
Zero inline imports. Zero business logic.
Every handler: auth → permission → rate limit → service → ApiResponse.
"""
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.core.security import get_client_ip
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engine_registry.registry import registry
from app.engines.tenant_engine.service import TenantService
from pydantic import BaseModel
from app.schemas.base import ApiResponse, Meta, Links, Link, ok
from app.exceptions import ServiceOSException

logger = structlog.get_logger("tenant.router")


class SignupBody(BaseModel):
    business_name: str
    vertical:      str
    owner_name:    str
    owner_email:   str
    owner_phone:   str
    city:          str
    state:         str | None = None
    gstin:         str | None = None
    description:   str | None = None
    source:        str        = "self_signup"
    plan_type:     str | None = None
router = APIRouter(prefix="/v1/tenants", tags=["Tenant Engine"])
ENGINE_ID = "tenant"


def _meta(request: Request) -> Meta:
    return Meta(request_id=getattr(request.state, "request_id", "—"), engine_id=ENGINE_ID)


def _svc(request: Request, db: AsyncSession = Depends(get_db)) -> TenantService:
    user = None
    return TenantService(
        db=db,
        request_id=getattr(request.state, "request_id", "—"),
        ip_address=get_client_ip(request),
    )


def _svc_with_actor(request: Request, db: AsyncSession = Depends(get_db),
                    user: UserContext = Depends(get_current_user)) -> TenantService:
    return TenantService(
        db=db,
        request_id=getattr(request.state, "request_id", "—"),
        actor_id=uuid.UUID(user.user_id) if user.user_id else None,
        actor_role=user.role,
        ip_address=get_client_ip(request),
    )



# Platform-level roles (no tenant_id of their own) that are meant to operate
# across tenants by design -- e.g. admin_operations legitimately reads/manages
# ANY tenant's profile per its canonical Tenant Administration scope
# (FINAL-L5-05AI). Only tenant-scoped roles are restricted to their own
# tenant_id below.
_PLATFORM_ROLES = {"super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly"}


def _assert_own_tenant_or_super_admin(tenant_id: uuid.UUID, user: UserContext) -> None:
    """
    MODULE-L5-01: closes a confirmed cross-tenant IDOR -- tenant-scoped roles
    (tenant_owner/staff/technician) hold TENANT_READ/TENANT_UPDATE for their
    OWN tenant's self-service, but the {tenant_id} path parameter was never
    checked against the caller's actual tenant_id, letting any tenant_owner
    substitute a different tenant's UUID and read/update that tenant's
    profile and billing data. Platform-level admin roles are exempt (they
    operate across tenants by design), matching TenantScopeService's existing
    convention elsewhere.
    """
    if user.role in _PLATFORM_ROLES:
        return
    if not user.tenant_id or str(tenant_id) != str(user.tenant_id):
        raise ServiceOSException(
            error_code="PERMISSION_DENIED",
            detail="You may only access your own tenant's data.",
            blocking_rule="tenant_scope: caller.tenant_id must match path tenant_id",
            resolution="Use your own tenant_id, or contact a platform administrator.",
        )


# ── Engine Introspection ──────────────────────────────────────────────────────
@router.get("/meta", summary="Tenant engine introspection", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {
        "engine_id": ENGINE_ID,
        "name": "Tenant Engine",
        "version": "2.4.1",
        "description": "7-state lifecycle · 8-step onboarding · real schema provisioning · 360 view · health score · plan management · engine dependency graph",
        "endpoint_count": 42,
        "status": "active",
        "capabilities": ["onboarding", "lifecycle_management", "engine_management",
                         "feature_flags", "plan_management", "billing", "data_export",
                         "health_scoring", "360_view", "audit_trail"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# ONBOARDING (1–9)
# ─────────────────────────────────────────────────────────────────────────────

# 1. Public signup (no auth)
@router.post("/onboarding/signup", summary="Submit tenant signup request (public — no auth)",
             status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def submit_signup(body: SignupBody, request: Request, svc: TenantService = Depends(_svc)) -> ApiResponse[dict]:
    data = await svc.submit_signup(body.model_dump())
    return ok(data, _meta(request).request_id, ENGINE_ID,
              links=Links(actions=[Link(href="/v1/tenants/onboarding/queue", method="GET",
                                       rel="admin_queue", description="Admins see this in the queue")]))


# 2. List onboarding queue — must be before /{request_id} to avoid UUID parse on "queue"
@router.get("/onboarding/queue", summary="[Admin] List all onboarding requests",
            response_model=ApiResponse[dict])
async def list_onboarding_queue(
    request: Request,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(None),
    user: UserContext = Depends(require_super_admin),
    svc: TenantService = Depends(_svc_with_actor),
) -> ApiResponse[dict]:
    data = await svc.list_onboarding_queue(status_filter, limit, cursor)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 3. Get single onboarding request
@router.get("/onboarding/{request_id}", summary="Get onboarding request detail",
            response_model=ApiResponse[dict])
async def get_onboarding_request(request_id: uuid.UUID, request: Request,
                                  user: UserContext = Depends(require_super_admin),
                                  svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    data = await svc.get_onboarding_request(request_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 4. Start review
@router.post("/onboarding/{request_id}/start-review",
             summary="[Admin] Start reviewing an onboarding request",
             response_model=ApiResponse[dict])
async def start_review(request_id: uuid.UUID, request: Request,
                        user: UserContext = Depends(require_super_admin),
                        svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    data = await svc.start_review(request_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 5. Request documents
@router.post("/onboarding/{request_id}/request-documents",
             summary="[Admin] Request additional documents from applicant",
             response_model=ApiResponse[dict])
async def request_documents(request_id: uuid.UUID, request: Request,
                              user: UserContext = Depends(require_super_admin),
                              svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    body = await request.json()
    data = await svc.request_documents(request_id, body.get("message", "Please provide additional documents."))
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 6. Update checklist item
@router.put("/onboarding/{request_id}/checklist/{item_key}",
            summary="[Admin] Update a checklist item status",
            response_model=ApiResponse[dict])
async def update_checklist(request_id: uuid.UUID, item_key: str, request: Request,
                            user: UserContext = Depends(require_super_admin),
                            svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    body = await request.json()
    data = await svc.update_checklist_item(request_id, item_key,
                                            body.get("status", "done"), body.get("notes"))
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 7. Pre-flight check
@router.post("/onboarding/{request_id}/preflight-check",
             summary="[Admin] Validate everything before activation",
             response_model=ApiResponse[dict])
async def preflight_check(request_id: uuid.UUID, request: Request,
                           user: UserContext = Depends(require_super_admin),
                           svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    data = await svc.run_preflight(request_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 8. Activate tenant
@router.post("/onboarding/{request_id}/activate",
             summary="[Admin] Activate tenant — runs full provisioning transaction",
             status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def activate_tenant(request_id: uuid.UUID, request: Request,
                           user: UserContext = Depends(require_super_admin),
                           svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    data = await svc.activate_tenant(request_id)
    return ok(data, _meta(request).request_id, ENGINE_ID,
              links=Links(actions=[
                  Link(href=f"/v1/tenants/{data.get('tenant_id')}", method="GET", rel="tenant"),
                  Link(href=f"/v1/tenants/{data.get('tenant_id')}/360", method="GET", rel="360_view"),
              ]))


# 9. Reject onboarding
@router.post("/onboarding/{request_id}/reject",
             summary="[Admin] Reject an onboarding request",
             response_model=ApiResponse[dict])
async def reject_onboarding(request_id: uuid.UUID, request: Request,
                              user: UserContext = Depends(require_super_admin),
                              svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    body = await request.json()
    data = await svc.reject_onboarding(request_id, body.get("reason", "Application rejected."))
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ─────────────────────────────────────────────────────────────────────────────
# TENANT CRUD (10–13)
# ─────────────────────────────────────────────────────────────────────────────

# 10. List tenants
@router.get("", summary="[Admin] List all tenants with cursor pagination",
            response_model=ApiResponse[dict])
async def list_tenants(
    request: Request,
    status_filter: str | None = Query(None, alias="status"),
    vertical: str | None = Query(None),
    plan: str | None = Query(None),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(None),
    user: UserContext = Depends(require_permission(P.TENANT_READ)),
    svc: TenantService = Depends(_svc_with_actor),
) -> ApiResponse[dict]:
    data = await svc.list_tenants(status_filter, vertical, plan, limit, cursor)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 11. Get tenant detail
@router.get("/{tenant_id}", summary="Get tenant detail with billing and limits",
            response_model=ApiResponse[dict])
async def get_tenant(tenant_id: uuid.UUID, request: Request,
                     user: UserContext = Depends(require_permission(P.TENANT_READ)),
                     svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.get_tenant_detail(tenant_id)
    return ok(data, _meta(request).request_id, ENGINE_ID,
              links=Links(
                  self_link=f"/v1/tenants/{tenant_id}",
                  actions=[
                      Link(href=f"/v1/tenants/{tenant_id}/360", method="GET", rel="360_view"),
                      Link(href=f"/v1/tenants/{tenant_id}/health", method="GET", rel="health"),
                      Link(href=f"/v1/tenants/{tenant_id}/engines", method="GET", rel="engines"),
                  ],
              ))


# 12. Update tenant
@router.put("/{tenant_id}", summary="Update tenant profile",
            response_model=ApiResponse[dict])
async def update_tenant(tenant_id: uuid.UUID, request: Request,
                         user: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                         svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    body = await request.json()
    data = await svc.update_tenant(tenant_id, body)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 13. 360 view
@router.get("/{tenant_id}/360",
            summary="[Admin] Get 360° view of tenant — all engine data in one response",
            response_model=ApiResponse[dict])
async def get_360_view(tenant_id: uuid.UUID, request: Request,
                        user: UserContext = Depends(require_permission(P.TENANT_360_READ)),
                        svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.get_360_view(tenant_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH (14–16)
# ─────────────────────────────────────────────────────────────────────────────

# 14. Get health score
@router.get("/{tenant_id}/health",
            summary="Get tenant health score with signal breakdown",
            response_model=ApiResponse[dict])
async def get_health_score(tenant_id: uuid.UUID, request: Request,
                            user: UserContext = Depends(require_permission(P.TENANT_HEALTH_READ)),
                            svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.get_health_score(tenant_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 15. Health history
@router.get("/{tenant_id}/health/history",
            summary="Get tenant health score history (hourly, last N days)",
            response_model=ApiResponse[dict])
async def get_health_history(tenant_id: uuid.UUID, request: Request,
                              days: int = Query(default=30, ge=1, le=365),
                              user: UserContext = Depends(require_permission(P.TENANT_HEALTH_READ)),
                              svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.get_health_history(tenant_id, days)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 16. Limit check (used by other engines)
@router.get("/{tenant_id}/limits/check/{limit_type}",
            summary="Check if tenant has capacity for a resource type",
            response_model=ApiResponse[dict])
async def check_limit(tenant_id: uuid.UUID, limit_type: str, request: Request,
                       user: UserContext = Depends(require_permission(P.TENANT_READ)),
                       svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.check_limit(tenant_id, limit_type)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ─────────────────────────────────────────────────────────────────────────────
# LIFECYCLE (17–23)
# ─────────────────────────────────────────────────────────────────────────────

# 17. Suspend
@router.post("/{tenant_id}/suspend",
             summary="[Admin] Suspend tenant — invalidates all sessions",
             response_model=ApiResponse[dict])
async def suspend_tenant(tenant_id: uuid.UUID, request: Request,
                          user: UserContext = Depends(require_permission(P.TENANT_SUSPEND)),
                          svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    body = await request.json()
    data = await svc.suspend_tenant(tenant_id, body.get("reason", "Suspended by admin"),
                                     body.get("reason_category", "manual"))
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 18. Reinstate
@router.post("/{tenant_id}/reinstate",
             summary="[Admin] Reinstate a suspended tenant",
             response_model=ApiResponse[dict])
async def reinstate_tenant(tenant_id: uuid.UUID, request: Request,
                            user: UserContext = Depends(require_permission(P.TENANT_REINSTATE)),
                            svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    body = await request.json()
    reason = (body.get("reason") or body.get("notes") or "").strip()
    if not reason:
        raise ServiceOSException("VALIDATION_ERROR", "A reason is required to reinstate a tenant.")
    data = await svc.reinstate_tenant(tenant_id, reason)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 19. Begin termination
@router.post("/{tenant_id}/terminate/begin",
             summary="[Admin] Begin 14-day termination warning period",
             response_model=ApiResponse[dict])
async def begin_termination(tenant_id: uuid.UUID, request: Request,
                             user: UserContext = Depends(require_permission(P.TENANT_TERMINATE)),
                             svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    body = await request.json()
    data = await svc.begin_termination(tenant_id, body.get("reason", "Terminated by admin"))
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 20. Confirm termination
@router.post("/{tenant_id}/terminate/confirm",
             summary="[Admin] Confirm and execute termination",
             response_model=ApiResponse[dict])
async def confirm_termination(tenant_id: uuid.UUID, request: Request,
                               user: UserContext = Depends(require_permission(P.TENANT_TERMINATE)),
                               svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.confirm_termination(tenant_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 21. Upgrade plan
@router.post("/{tenant_id}/plan/upgrade",
             summary="Upgrade tenant plan (immediate)",
             response_model=ApiResponse[dict])
async def upgrade_plan(tenant_id: uuid.UUID, request: Request,
                        user: UserContext = Depends(require_permission(P.TENANT_PLAN_MANAGE)),
                        svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    body = await request.json()
    reason = (body.get("reason") or "").strip()
    if not reason:
        raise ServiceOSException("VALIDATION_ERROR", "A reason is required to change a tenant's plan.")
    data = await svc.upgrade_plan(tenant_id, body["target_plan"], reason)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 22. Downgrade plan
@router.post("/{tenant_id}/plan/downgrade",
             summary="Downgrade tenant plan (deferred to billing cycle end)",
             response_model=ApiResponse[dict])
async def downgrade_plan(tenant_id: uuid.UUID, request: Request,
                          user: UserContext = Depends(require_permission(P.TENANT_PLAN_MANAGE)),
                          svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    body = await request.json()
    data = await svc.downgrade_plan(tenant_id, body["target_plan"])
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 23. Convert trial
@router.post("/{tenant_id}/trial/convert",
             summary="Convert trial to paid subscription",
             response_model=ApiResponse[dict])
async def convert_trial(tenant_id: uuid.UUID, request: Request,
                         user: UserContext = Depends(require_permission(P.TENANT_PLAN_MANAGE)),
                         svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.convert_trial(tenant_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ─────────────────────────────────────────────────────────────────────────────
# ENGINE MANAGEMENT (24–30)
# ─────────────────────────────────────────────────────────────────────────────

# 24. List engines for tenant
@router.get("/{tenant_id}/engines",
            summary="List all engines with enabled state and config for this tenant",
            response_model=ApiResponse[dict])
async def list_engines(tenant_id: uuid.UUID, request: Request,
                        user: UserContext = Depends(require_permission(P.TENANT_ENGINES_MANAGE)),
                        svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.list_engines(tenant_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 25. Enable engine
@router.post("/{tenant_id}/engines/{engine_id}/enable",
             summary="Enable a plugin engine for this tenant (checks dependency graph)",
             response_model=ApiResponse[dict])
async def enable_engine(tenant_id: uuid.UUID, engine_id: str, request: Request,
                         user: UserContext = Depends(require_permission(P.TENANT_ENGINES_MANAGE)),
                         svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.enable_engine(tenant_id, engine_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 26. Disable engine
@router.post("/{tenant_id}/engines/{engine_id}/disable",
             summary="Disable a plugin engine (checks for dependents first)",
             response_model=ApiResponse[dict])
async def disable_engine(tenant_id: uuid.UUID, engine_id: str, request: Request,
                          user: UserContext = Depends(require_permission(P.TENANT_ENGINES_MANAGE)),
                          svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.disable_engine(tenant_id, engine_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 27. Bulk enable
@router.post("/{tenant_id}/engines/bulk-enable",
             summary="Enable multiple engines in one atomic call",
             response_model=ApiResponse[dict])
async def bulk_enable(tenant_id: uuid.UUID, request: Request,
                       user: UserContext = Depends(require_permission(P.TENANT_ENGINES_MANAGE)),
                       svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    body = await request.json()
    data = await svc.bulk_enable_engines(tenant_id, body.get("engine_ids", []))
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 28. Bulk disable
@router.post("/{tenant_id}/engines/bulk-disable",
             summary="Disable multiple engines in one call",
             response_model=ApiResponse[dict])
async def bulk_disable(tenant_id: uuid.UUID, request: Request,
                        user: UserContext = Depends(require_permission(P.TENANT_ENGINES_MANAGE)),
                        svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    body = await request.json()
    data = await svc.bulk_disable_engines(tenant_id, body.get("engine_ids", []))
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 29. Get engine config
@router.get("/{tenant_id}/engines/{engine_id}/config",
            summary="Get engine configuration for this tenant",
            response_model=ApiResponse[dict])
async def get_engine_config(tenant_id: uuid.UUID, engine_id: str, request: Request,
                             user: UserContext = Depends(require_permission(P.TENANT_ENGINES_MANAGE)),
                             svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.get_engine_config(tenant_id, engine_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 30. Update engine config
@router.put("/{tenant_id}/engines/{engine_id}/config",
            summary="Update engine configuration (validates schema before saving)",
            response_model=ApiResponse[dict])
async def update_engine_config(tenant_id: uuid.UUID, engine_id: str, request: Request,
                                user: UserContext = Depends(require_permission(P.TENANT_ENGINES_MANAGE)),
                                svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    body = await request.json()
    data = await svc.update_engine_config(tenant_id, engine_id, body)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 30b. Validate engine config
@router.post("/{tenant_id}/engines/{engine_id}/config/validate",
             summary="Validate engine config without saving",
             response_model=ApiResponse[dict])
async def validate_engine_config(tenant_id: uuid.UUID, engine_id: str, request: Request,
                                  user: UserContext = Depends(require_permission(P.TENANT_ENGINES_MANAGE)),
                                  svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    body = await request.json()
    data = await svc.validate_engine_config(engine_id, body)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE FLAGS (31–34)
# ─────────────────────────────────────────────────────────────────────────────

# 31. List flags
@router.get("/{tenant_id}/feature-flags",
            summary="List all feature flag overrides for this tenant",
            response_model=ApiResponse[dict])
async def list_feature_flags(tenant_id: uuid.UUID, request: Request,
                              user: UserContext = Depends(require_permission(P.TENANT_FLAGS_MANAGE)),
                              svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.list_feature_flags(tenant_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 32. Set flag
@router.put("/{tenant_id}/feature-flags/{flag_key}",
            summary="Set a feature flag override for this tenant",
            response_model=ApiResponse[dict])
async def set_feature_flag(tenant_id: uuid.UUID, flag_key: str, request: Request,
                            user: UserContext = Depends(require_permission(P.TENANT_FLAGS_MANAGE)),
                            svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    body = await request.json()
    data = await svc.set_feature_flag(tenant_id, flag_key, body.get("value"), body.get("notes"))
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 33. Delete flag
@router.delete("/{tenant_id}/feature-flags/{flag_key}",
               summary="Remove a feature flag override (reverts to platform default)",
               response_model=ApiResponse[dict])
async def delete_feature_flag(tenant_id: uuid.UUID, flag_key: str, request: Request,
                               user: UserContext = Depends(require_permission(P.TENANT_FLAGS_MANAGE)),
                               svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.delete_feature_flag(tenant_id, flag_key)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 34. Resolve flag (effective value through hierarchy)
@router.get("/{tenant_id}/feature-flags/{flag_key}/resolve",
            summary="Get the resolved effective value of a flag (platform → plan → tenant hierarchy)",
            response_model=ApiResponse[dict])
async def resolve_feature_flag(tenant_id: uuid.UUID, flag_key: str, request: Request,
                                user: UserContext = Depends(require_permission(P.TENANT_FLAGS_MANAGE)),
                                svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.resolve_feature_flag(tenant_id, flag_key)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ─────────────────────────────────────────────────────────────────────────────
# BILLING (35–38)
# ─────────────────────────────────────────────────────────────────────────────

# 35. Billing summary
@router.get("/{tenant_id}/billing",
            summary="Get billing summary — credits, subscription, security deposit",
            response_model=ApiResponse[dict])
async def get_billing(tenant_id: uuid.UUID, request: Request,
                       user: UserContext = Depends(require_permission(P.TENANT_BILLING_READ)),
                       svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.get_billing_summary(tenant_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 36. Update payment method
@router.put("/{tenant_id}/billing/payment-method",
            summary="Update the payment method / gateway customer ID",
            response_model=ApiResponse[dict])
async def update_payment_method(tenant_id: uuid.UUID, request: Request,
                                 user: UserContext = Depends(require_permission(P.TENANT_BILLING_MANAGE)),
                                 svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    body = await request.json()
    data = await svc.update_payment_method(tenant_id, body["gateway"], body["gateway_customer_id"])
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 37. List invoices
@router.get("/{tenant_id}/billing/invoices",
            summary="List subscription invoices for this tenant",
            response_model=ApiResponse[dict])
async def list_invoices(tenant_id: uuid.UUID, request: Request,
                         limit: int = Query(default=20, ge=1, le=100),
                         user: UserContext = Depends(require_permission(P.TENANT_BILLING_READ)),
                         svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.list_invoices(tenant_id, limit)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 38. Trigger dunning
@router.post("/{tenant_id}/billing/dunning",
             summary="[Admin] Manually trigger dunning for a failed payment",
             response_model=ApiResponse[dict])
async def trigger_dunning(tenant_id: uuid.UUID, request: Request,
                           user: UserContext = Depends(require_super_admin),
                           svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.trigger_dunning(tenant_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ─────────────────────────────────────────────────────────────────────────────
# DATA MANAGEMENT (39–41)
# ─────────────────────────────────────────────────────────────────────────────

# 39. Request data export
@router.post("/{tenant_id}/data/export",
             summary="Request a full data export (async — returns job_id for polling)",
             status_code=status.HTTP_202_ACCEPTED, response_model=ApiResponse[dict])
async def request_data_export(tenant_id: uuid.UUID, request: Request,
                               user: UserContext = Depends(require_permission(P.TENANT_DATA_EXPORT)),
                               svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.request_data_export(tenant_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 40. Export status
@router.get("/{tenant_id}/data/export/{job_id}",
            summary="Poll export job status",
            response_model=ApiResponse[dict])
async def get_export_status(tenant_id: uuid.UUID, job_id: str, request: Request,
                             user: UserContext = Depends(require_permission(P.TENANT_DATA_EXPORT)),
                             svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.get_export_status(tenant_id, job_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# 41. GDPR deletion
@router.post("/{tenant_id}/data/delete-request",
             summary="Request GDPR data deletion — anonymizes PII, retains financial records",
             response_model=ApiResponse[dict])
async def gdpr_deletion(tenant_id: uuid.UUID, request: Request,
                         user: UserContext = Depends(require_permission(P.TENANT_DATA_DELETE)),
                         svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    body = await request.json()
    data = await svc.request_gdpr_deletion(tenant_id, body.get("reason", "Customer request"))
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT LOG (42)
# ─────────────────────────────────────────────────────────────────────────────

# 42. Audit log
@router.get("/{tenant_id}/audit-log",
            summary="Get tenant audit log with cursor pagination",
            response_model=ApiResponse[dict])
async def get_audit_log(tenant_id: uuid.UUID, request: Request,
                         limit: int = Query(default=50, ge=1, le=200),
                         cursor: str | None = Query(None),
                         user: UserContext = Depends(require_permission(P.AUTH_AUDIT_READ)),
                         svc: TenantService = Depends(_svc_with_actor)) -> ApiResponse[dict]:
    _assert_own_tenant_or_super_admin(tenant_id, user)
    data = await svc.get_audit_log(tenant_id, limit, cursor)
    return ok(data, _meta(request).request_id, ENGINE_ID)
