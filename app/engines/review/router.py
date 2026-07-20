"""Review Engine — Router (14 endpoints). Zero inline imports."""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission, require_tenant_mutation_permission
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.review.service import ReviewService
from app.schemas.base import ApiResponse, ok
logger = structlog.get_logger("review.router")
router = APIRouter(prefix="/v1/reviews", tags=["Review Engine"])
ENGINE_ID = "review"
def _svc(r: Request, db: AsyncSession=Depends(get_db), u: UserContext=Depends(get_current_user)):
    # Slice 2F-25: the service is now constructed WITH the caller's tenant, so
    # tenant isolation can be enforced server-side. Before this, the service
    # had no tenant context at all and every tenant-facing method trusted a
    # client-supplied tenant_id from the query string or request body.
    return ReviewService(db=db, request_id=getattr(r.state,"request_id","—"),
                          actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                          actor_role=u.role,
                          actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)
def _rid(r): return getattr(r.state,"request_id","—")

@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Review Engine", "version": "11.0.0",
            "endpoint_count": 14, "status": "active",
            "capabilities": ["db_level_idempotency","signal_weight_verification",
                             "precomputed_aggregates","immutable_history",
                             "one_reply_enforcement","moderation","review_requests"]}

@router.post("", status_code=status.HTTP_410_GONE, response_model=None)
async def create_review(r: Request, u: UserContext=Depends(get_current_user)):
    """Phase 2A Slice 2 (non-canonical entry restriction): this legacy
    review engine's `reviews` table was superseded by the `customer_reviews`
    engine (Sprint 24 / MODULE-L5-13) — job-completion ratings write there,
    not here. Phase 1A's review-canonical-decision.md confirmed zero
    frontend callers of this endpoint across all 4 audited apps, so blocking
    it carries no discovered frontend risk. Kept as a 410 (not deleted)
    per the "preserve legacy reads, block legacy writes" retirement plan —
    GET/list/aggregate/flag/resolve on this engine remain unaffected.
    """
    raise HTTPException(
        status_code=410,
        detail="This endpoint is retired. Reviews are created through the customer_reviews engine.",
    )

@router.get("/requests", summary="List review requests for tenant (query param version)", response_model=ApiResponse[dict])
async def list_requests_by_query(r: Request, tenant_id: uuid.UUID=Query(...),
                                  req_status: str|None=Query(None, alias="status"),
                                  limit: int=Query(50,ge=1,le=200), cursor: str|None=Query(None),
                                  u: UserContext=Depends(get_current_user), s: ReviewService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_review_requests(tenant_id, req_status, limit, cursor), _rid(r), ENGINE_ID)

@router.get("/{review_id}", response_model=ApiResponse[dict])
async def get_review(review_id: uuid.UUID, r: Request, u: UserContext=Depends(get_current_user),
                      s: ReviewService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_review(review_id), _rid(r), ENGINE_ID)

@router.get("", summary="List reviews by tenant with cursor pagination", response_model=ApiResponse[dict])
async def list_by_tenant(r: Request, tenant_id: uuid.UUID=Query(...),
                          rv_status: str|None=Query(None, alias="status"),
                          limit: int=Query(50,ge=1,le=200), cursor: str|None=Query(None),
                          u: UserContext=Depends(get_current_user), s: ReviewService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_by_tenant(tenant_id, rv_status, limit, cursor), _rid(r), ENGINE_ID)

@router.get("/staff/{staff_id}", response_model=ApiResponse[dict])
async def list_by_staff(staff_id: uuid.UUID, r: Request, tenant_id: uuid.UUID=Query(...),
                         limit: int=Query(50,ge=1,le=200), cursor: str|None=Query(None),
                         u: UserContext=Depends(get_current_user), s: ReviewService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_by_staff(staff_id, tenant_id, limit, cursor), _rid(r), ENGINE_ID)

@router.get("/customers/{customer_id}", response_model=ApiResponse[dict])
async def list_by_customer(customer_id: uuid.UUID, r: Request,
                            limit: int=Query(50,ge=1,le=200), cursor: str|None=Query(None),
                            u: UserContext=Depends(get_current_user), s: ReviewService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_by_customer(customer_id, limit, cursor), _rid(r), ENGINE_ID)

@router.post("/{review_id}/reply", summary="One reply only — 409 on second attempt", response_model=ApiResponse[dict])
async def submit_reply(review_id: uuid.UUID, r: Request,
                        u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                        s: ReviewService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.submit_reply(review_id, body["reply"]), _rid(r), ENGINE_ID)

@router.post("/{review_id}/flag", response_model=ApiResponse[dict])
async def flag_review(review_id: uuid.UUID, r: Request,
                       u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                       s: ReviewService=Depends(_svc)) -> ApiResponse[dict]:
    # Slice 2F-25: was bare `get_current_user` over a primary-key-only service
    # lookup -- any authenticated principal could flag any tenant's review.
    # Now carries the same tenant permission as the sibling reply route, and
    # ownership is enforced inside the service by `_get_review_scoped`.
    body = await r.json()
    return ok(await s.flag_review(review_id, body.get("reason","Flagged by user")), _rid(r), ENGINE_ID)

@router.post("/{review_id}/resolve", response_model=ApiResponse[dict])
async def resolve_flag(review_id: uuid.UUID, r: Request, u: UserContext=Depends(require_super_admin),
                        s: ReviewService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.resolve_flag(review_id, body["action"], body.get("reason")), _rid(r), ENGINE_ID)

@router.get("/aggregates/{entity_type}/{entity_id}",
            summary="Pre-computed aggregates — never runs AVG() at read time", response_model=ApiResponse[dict])
async def get_aggregate(entity_type: str, entity_id: str, r: Request,
                         u: UserContext=Depends(get_current_user),
                         s: ReviewService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_aggregate(entity_type, entity_id), _rid(r), ENGINE_ID)

@router.post("/requests", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def create_request(r: Request, u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                          s: ReviewService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.create_review_request(body["job_id"], uuid.UUID(body["tenant_id"]),
              uuid.UUID(body["customer_id"]),
              uuid.UUID(body["staff_id"]) if body.get("staff_id") else None), _rid(r), ENGINE_ID)

@router.get("/requests/jobs/{job_id}", response_model=ApiResponse[dict])
async def get_request(job_id: str, r: Request, u: UserContext=Depends(get_current_user),
                       s: ReviewService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_review_request(job_id), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/requests", response_model=ApiResponse[dict])
async def list_requests(tenant_id: uuid.UUID, r: Request,
                         req_status: str|None=Query(None, alias="status"),
                         limit: int=Query(50,ge=1,le=200), cursor: str|None=Query(None),
                         u: UserContext=Depends(get_current_user), s: ReviewService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_review_requests(tenant_id, req_status, limit, cursor), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/recent", response_model=ApiResponse[dict])
async def recent_reviews(tenant_id: uuid.UUID, r: Request, days: int=Query(30,ge=1,le=90),
                          u: UserContext=Depends(get_current_user), s: ReviewService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_recent_reviews(tenant_id, days), _rid(r), ENGINE_ID)
