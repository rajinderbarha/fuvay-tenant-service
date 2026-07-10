"""Marketing Automation Engine — Router (20 endpoints). Zero inline imports."""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.marketing.service import MarketingService
from app.schemas.base import ApiResponse, ok

logger = structlog.get_logger("marketing.router")
router = APIRouter(prefix="/v1/marketing", tags=["Marketing Automation Engine"])
ENGINE_ID = "marketing"

def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> MarketingService:
    return MarketingService(db=db, request_id=getattr(r.state,"request_id","—"),
                             actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                             actor_role=u.role)
def _rid(r): return getattr(r.state,"request_id","—")


@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Marketing Automation Engine",
            "version": "15.0.0", "endpoint_count": 20, "status": "active",
            "capabilities": [
                "dalle3_image_generation",
                "prompt_hash_idempotency",
                "daily_budget_hard_limit",
                "dalle_url_immediate_download",
                "exact_cost_per_asset",
                "full_meta_api_response_stored",
                "delivery_idempotent_on_post_id",
                "token_refresh_select_for_update",
                "tenant_onboarding_auto_post",
                "append_only_delivery_log",
                "platform_pays_never_tenant",
            ]}


# ── Social Account Management (4 endpoints) ───────────────────────────────────
@router.post("/accounts",
             summary="Connect social account — Instagram or Facebook page",
             status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def connect_account(r: Request,
                           u: UserContext = Depends(require_super_admin),
                           s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.connect_account(
        body["platform"], body["page_id"], body["page_name"],
        body["access_token"], body.get("ig_user_id"),
        body.get("is_primary", False)), _rid(r), ENGINE_ID)


@router.get("/accounts",
            summary="List connected social accounts",
            response_model=ApiResponse[dict])
async def list_accounts(r: Request,
                         platform: str | None = Query(None),
                         u: UserContext = Depends(require_super_admin),
                         s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_accounts(platform), _rid(r), ENGINE_ID)


@router.get("/accounts/{account_id}",
            summary="Get social account — token REDACTED in response",
            response_model=ApiResponse[dict])
async def get_account(account_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(require_super_admin),
                       s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_account(account_id), _rid(r), ENGINE_ID)


@router.post("/accounts/{account_id}/refresh-token",
             summary="Refresh Meta long-lived token — SELECT FOR UPDATE NOWAIT",
             response_model=ApiResponse[dict])
async def refresh_token(account_id: uuid.UUID, r: Request,
                         u: UserContext = Depends(require_super_admin),
                         s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.refresh_token(account_id), _rid(r), ENGINE_ID)


# ── Content Templates (3 endpoints) ──────────────────────────────────────────
@router.post("/templates",
             summary="Create DALL-E prompt template per post type",
             status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def create_template(r: Request,
                           u: UserContext = Depends(require_super_admin),
                           s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.create_template(
        body["post_type"], body.get("vertical"),
        body["name"], body["dalle_prompt"], body["caption_template"],
        body.get("required_vars",[]), body.get("default_tags",[])), _rid(r), ENGINE_ID)


@router.get("/templates",
            summary="List active content templates",
            response_model=ApiResponse[dict])
async def list_templates(r: Request,
                          post_type: str | None = Query(None),
                          vertical: str | None = Query(None),
                          u: UserContext = Depends(require_super_admin),
                          s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_templates(post_type, vertical), _rid(r), ENGINE_ID)


@router.get("/templates/{template_id}",
            response_model=ApiResponse[dict])
async def get_template(template_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(require_super_admin),
                        s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_template(template_id), _rid(r), ENGINE_ID)


# ── Image Generation (3 endpoints) ───────────────────────────────────────────
@router.post("/images/generate",
             summary="Generate DALL-E image — budget check first, URL downloaded immediately",
             status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def generate_image(r: Request,
                          u: UserContext = Depends(require_super_admin),
                          s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.generate_image(
        body["post_type"], body.get("variables",{}),
        uuid.UUID(body["template_id"]) if body.get("template_id") else None),
        _rid(r), ENGINE_ID)


@router.get("/images/{asset_id}",
            summary="Get generated asset with exact cost and prompt",
            response_model=ApiResponse[dict])
async def get_asset(asset_id: uuid.UUID, r: Request,
                     u: UserContext = Depends(require_super_admin),
                     s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_asset(asset_id), _rid(r), ENGINE_ID)


@router.get("/images",
            summary="List generated assets with cursor pagination",
            response_model=ApiResponse[dict])
async def list_assets(r: Request,
                       post_type: str | None = Query(None),
                       limit: int = Query(50,ge=1,le=200),
                       cursor: str | None = Query(None),
                       u: UserContext = Depends(require_super_admin),
                       s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_assets(post_type, limit, cursor), _rid(r), ENGINE_ID)


# ── Content Calendar (5 endpoints) ───────────────────────────────────────────
@router.post("/posts",
             summary="Schedule a post — idempotent on (post_type + date + account)",
             status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def schedule_post(r: Request,
                         u: UserContext = Depends(require_super_admin),
                         s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.schedule_post(
        uuid.UUID(body["account_id"]), body["post_type"],
        body["scheduled_at"], body.get("variables",{}),
        uuid.UUID(body["tenant_id"]) if body.get("tenant_id") else None,
        uuid.UUID(body["template_id"]) if body.get("template_id") else None,
        body.get("tags")), _rid(r), ENGINE_ID)


@router.get("/calendar",
            summary="Get content calendar for date range",
            response_model=ApiResponse[dict])
async def get_calendar(r: Request,
                        date_from: str = Query(...),
                        date_to: str = Query(...),
                        account_id: uuid.UUID | None = Query(None),
                        u: UserContext = Depends(require_super_admin),
                        s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_calendar(date_from, date_to, account_id), _rid(r), ENGINE_ID)


@router.post("/posts/{post_id}/publish",
             summary="Publish post to Meta Graph API — idempotent on post_id",
             response_model=ApiResponse[dict])
async def publish_post(post_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(require_super_admin),
                        s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.publish_post(post_id), _rid(r), ENGINE_ID)


@router.post("/posts/{post_id}/cancel",
             response_model=ApiResponse[dict])
async def cancel_post(post_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(require_super_admin),
                       s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.cancel_post(post_id,
              body.get("reason","Cancelled by admin")), _rid(r), ENGINE_ID)


# ── Deliveries (2 endpoints) ──────────────────────────────────────────────────
@router.get("/deliveries",
            summary="List post deliveries — append-only, full Meta API response stored",
            response_model=ApiResponse[dict])
async def list_deliveries(r: Request,
                           account_id: uuid.UUID | None = Query(None),
                           dlv_status: str | None = Query(None, alias="status"),
                           limit: int = Query(50,ge=1,le=200),
                           cursor: str | None = Query(None),
                           u: UserContext = Depends(require_super_admin),
                           s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_deliveries(account_id, dlv_status, limit, cursor), _rid(r), ENGINE_ID)


# ── Budget & Summary (2 endpoints) ───────────────────────────────────────────
@router.get("/budget",
            summary="Daily DALL-E budget status — Redis counter, hard limit",
            response_model=ApiResponse[dict])
async def budget_status(r: Request,
                         u: UserContext = Depends(require_super_admin),
                         s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_daily_budget_status(), _rid(r), ENGINE_ID)


@router.get("/summary",
            summary="Marketing platform summary — posts, costs, accounts",
            response_model=ApiResponse[dict])
async def marketing_summary(r: Request,
                             u: UserContext = Depends(require_super_admin),
                             s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_marketing_summary(), _rid(r), ENGINE_ID)


# ── Tenant onboarding trigger (1 endpoint) ────────────────────────────────────
@router.post("/tenant-onboarded",
             summary="Trigger tenant spotlight post — called by event bus on tenant.activated",
             status_code=status.HTTP_202_ACCEPTED,
             response_model=ApiResponse[dict])
async def tenant_onboarded(r: Request,
                            u: UserContext = Depends(require_super_admin),
                            s: MarketingService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.handle_tenant_onboarded(
        uuid.UUID(body["tenant_id"]), body["tenant_name"],
        body.get("city","India"), body.get("vertical","home_services"),
        body.get("service_types",[])), _rid(r), ENGINE_ID)
