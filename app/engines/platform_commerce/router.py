"""Platform Commerce Engine — FastAPI Router. Zero inline imports. Zero business logic."""
import uuid
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission, require_tenant_mutation_permission, require_mutation_access_scope
from app.core.security import get_client_ip, rate_limiter
from app.dependencies.auth import get_current_user, UserContext, require_super_admin, require_customer
from app.dependencies.db import get_db
from app.engine_registry.registry import registry
from app.engines.platform_commerce.schemas import (
    CreatePackageRequest, UpdatePackageRequest,
    PurchaseInitiateRequest, PurchaseConfirmRequest, ManualCreditRequest,
    CommissionDeductRequest, UpdateHealthSignalRequest, HealthOverrideRequest,
    ReservationCreateRequest, WarrantyClaimRequest, WarrantyProviderResponseRequest,
    WarrantyEscalationRequest, ClaimResolveRequest, PreflightRequest,
)
from app.engines.platform_commerce.service import CommerceService
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, Meta, Links, Link, ok

logger = structlog.get_logger("commerce.router")
router = APIRouter(prefix="/v1/commerce", tags=["Platform Commerce"])
retired_admin_warranty_router = APIRouter()
ENGINE_ID = "platform_commerce"


def _meta(r: Request) -> Meta:
    return Meta(request_id=getattr(r.state, "request_id", "—"), engine_id=ENGINE_ID)

def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> CommerceService:
    return CommerceService(db=db, request_id=getattr(r.state, "request_id", "—"),
                            actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                            actor_role=u.role, ip_address=get_client_ip(r),
                            actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)

def _svc_open(r: Request, db: AsyncSession = Depends(get_db)) -> CommerceService:
    return CommerceService(db=db, request_id=getattr(r.state, "request_id", "—"),
                            ip_address=get_client_ip(r))


@router.get("/meta", summary="Platform Commerce engine introspection", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Platform Commerce Engine", "version": "3.0.0",
            "endpoint_count": 48, "status": "active",
            "capabilities": ["credit_packages","tenant_wallet","commission",
                             "customer_health","credit_reservations","warranty_claims","badges","preflight"]}

# ── SECURITY DEPOSIT (5) ──────────────────────────────────────────────────────
# The security deposit was removed in migration 317/318. These endpoints
# went with it: a provider now buys a top-up plan whose credit is spent
# down as commission, so there is no held balance to administer.


@router.get("/packages", summary="List available credit packages", response_model=ApiResponse[dict])
async def list_packages(r: Request, tenant_id: uuid.UUID | None = Query(None),
                         u: UserContext = Depends(get_current_user),
                         s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.list_packages(tenant_id or (uuid.UUID(u.tenant_id) if u.tenant_id else None))
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.get("/packages/{package_id}", summary="Get credit package detail", response_model=ApiResponse[dict])
async def get_package(package_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(get_current_user),
                       s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_package(package_id)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.post("/packages", summary="[Admin] Create credit package", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def create_package(body: CreatePackageRequest, r: Request,
                          u: UserContext = Depends(require_super_admin),
                          s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.create_package(body.model_dump())
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.put("/packages/{package_id}", summary="[Admin] Update credit package", response_model=ApiResponse[dict])
async def update_package(package_id: uuid.UUID, body: UpdatePackageRequest, r: Request,
                          u: UserContext = Depends(require_super_admin),
                          s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.update_package(package_id, body.model_dump(exclude_none=True))
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.delete("/packages/{package_id}", summary="[Admin] Archive credit package (soft-delete)", response_model=ApiResponse[dict])
async def archive_package(package_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_super_admin),
                           s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.archive_package(package_id)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.delete("/packages/{package_id}/permanent", summary="[Admin] Permanently delete a never-purchased credit package", response_model=ApiResponse[dict])
async def delete_package_permanently(package_id: uuid.UUID, r: Request,
                                      u: UserContext = Depends(require_super_admin),
                                      s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.delete_package_permanently(package_id)
    return ok(data, _meta(r).request_id, ENGINE_ID)

# ── TENANT WALLET (8) ─────────────────────────────────────────────────────────
@router.get("/tenants/{tenant_id}/wallet", summary="Get wallet with burn rate and projection", response_model=ApiResponse[dict])
async def get_wallet(tenant_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(require_permission(P.TENANT_BILLING_READ)),
                      s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_wallet(tenant_id)
    return ok(data, _meta(r).request_id, ENGINE_ID,
              links=Links(actions=[Link(href=f"/v1/commerce/tenants/{tenant_id}/wallet/purchase/initiate",
                                        method="POST", rel="purchase_credits")]))

@router.post("/tenants/{tenant_id}/wallet/purchase/initiate", summary="Initiate credit package purchase", response_model=ApiResponse[dict])
async def initiate_purchase(tenant_id: uuid.UUID, body: PurchaseInitiateRequest, r: Request,
                              u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_BILLING_MANAGE)),
                              s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    await rate_limiter.check_and_raise(f"purchase:{tenant_id}", "auth:otp_send", str(tenant_id))
    data = await s.initiate_purchase(tenant_id, body.package_id, body.gateway)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.post("/tenants/{tenant_id}/wallet/purchase/confirm", summary="Confirm purchase — atomic usage-credit grant", response_model=ApiResponse[dict])
async def confirm_purchase(tenant_id: uuid.UUID, body: PurchaseConfirmRequest, r: Request,
                            s: CommerceService = Depends(_svc_open)) -> ApiResponse[dict]:
    data = await s.confirm_purchase(tenant_id, body.package_id, body.razorpay_order_id,
                                     body.razorpay_payment_id, body.razorpay_signature)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.get("/tenants/{tenant_id}/wallet/transactions", summary="Immutable wallet ledger (cursor-paginated)", response_model=ApiResponse[dict])
async def get_wallet_transactions(tenant_id: uuid.UUID, r: Request,
                                   txn_type: str | None = Query(None),
                                   limit: int = Query(50, ge=1, le=200),
                                   cursor: str | None = Query(None),
                                   u: UserContext = Depends(require_permission(P.TENANT_BILLING_READ)),
                                   s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_wallet_transactions(tenant_id, txn_type, limit, cursor)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.get("/tenants/{tenant_id}/wallet/balance", summary="Lightweight balance for other engines (cached)", response_model=ApiResponse[dict])
async def get_wallet_balance(tenant_id: uuid.UUID, r: Request,
                              u: UserContext = Depends(get_current_user),
                              s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_wallet_balance_for_engine(tenant_id)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.post("/tenants/{tenant_id}/wallet/deduct", summary="[DEPRECATED] Blocked — superseded by Completed Job Deduction", response_model=ApiResponse[dict])
async def engine_deduct(tenant_id: uuid.UUID, r: Request,
                         u: UserContext = Depends(require_super_admin),
                         s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    # FINAL-L5-05H: blocked. This posted to TenantWallet/wallet_transactions, a
    # separate ledger from the canonical Completed Job Deduction
    # (app/engines/execution/usage_credit_deduction.py -> tenant_billing /
    # usage_credit_ledger). It had zero internal callers and zero test
    # coverage — nothing in the job-completion/force-close/void flow ever
    # invoked it. Left callable it would risk becoming a second,
    # non-idempotent-with-the-canonical-flow job deduction path. Blocked
    # rather than deleted pending the full domain-service reconciliation.
    from fastapi import HTTPException
    raise HTTPException(status_code=410, detail=(
        "This endpoint is deprecated and blocked. Completed Job Deduction is "
        "the sole canonical job-linked credit deduction path "
        "(app.engines.execution.usage_credit_deduction.deduct_for_completed_job)."
    ))

@router.post("/tenants/{tenant_id}/wallet/credit", summary="[Admin] Manual wallet credit", response_model=ApiResponse[dict])
async def admin_credit(tenant_id: uuid.UUID, body: ManualCreditRequest, r: Request,
                        u: UserContext = Depends(require_super_admin),
                        s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.admin_credit_wallet(tenant_id, body.amount, body.reason, body.category)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.get("/tenants/{tenant_id}/wallet/projection", summary="Burn rate projection with recommended package", response_model=ApiResponse[dict])
async def get_projection(tenant_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(require_permission(P.TENANT_BILLING_READ)),
                          s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_wallet_projection(tenant_id)
    return ok(data, _meta(r).request_id, ENGINE_ID)

# ── COMMISSION (5) ────────────────────────────────────────────────────────────
@router.get("/tenants/{tenant_id}/commission/rate", summary="Get effective commission rate (plan × health band)", response_model=ApiResponse[dict])
async def get_rate(tenant_id: uuid.UUID, r: Request,
                    u: UserContext = Depends(get_current_user),
                    s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_commission_rate(tenant_id)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.post("/jobs/{job_id}/commission/deduct", summary="Deduct commission on job close — atomic, idempotent", response_model=ApiResponse[dict])
async def deduct_commission(job_id: str, body: CommissionDeductRequest, r: Request,
                              u: UserContext = Depends(require_super_admin),
                              s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.deduct_commission(body.tenant_id, job_id, body.job_value, body.description)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.get("/tenants/{tenant_id}/commission/history", summary="Commission history (cursor-paginated, downloadable)", response_model=ApiResponse[dict])
async def get_commission_history(tenant_id: uuid.UUID, r: Request,
                                  limit: int = Query(50, ge=1, le=200),
                                  cursor: str | None = Query(None),
                                  u: UserContext = Depends(require_permission(P.TENANT_BILLING_READ)),
                                  s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_commission_history(tenant_id, limit, cursor)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.get("/tenants/{tenant_id}/commission/projection", summary="Projected monthly commission cost", response_model=ApiResponse[dict])
async def get_commission_projection(tenant_id: uuid.UUID, r: Request,
                                     u: UserContext = Depends(require_permission(P.TENANT_BILLING_READ)),
                                     s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_commission_projection(tenant_id)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.get("/platform/commission/summary", summary="[Admin] Platform-wide commission KPIs", response_model=ApiResponse[dict])
async def platform_commission(r: Request, u: UserContext = Depends(require_super_admin),
                               s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_platform_commission_summary()
    return ok(data, _meta(r).request_id, ENGINE_ID)

# ── CUSTOMER HEALTH (6) ───────────────────────────────────────────────────────
@router.get("/customers/{customer_id}/health", summary="Get customer health score for a tenant", response_model=ApiResponse[dict])
async def get_customer_health(customer_id: uuid.UUID, r: Request,
                               tid: uuid.UUID = Query(..., alias="tenant_id"),
                               u: UserContext = Depends(get_current_user),
                               s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_customer_health(customer_id, tid)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.get("/customers/{customer_id}/health/history", summary="Customer health band history", response_model=ApiResponse[dict])
async def get_customer_health_history(customer_id: uuid.UUID, r: Request,
                                       tid: uuid.UUID = Query(..., alias="tenant_id"),
                                       u: UserContext = Depends(get_current_user),
                                       s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_customer_health_history(customer_id, tid)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.post("/customers/{customer_id}/health/signals", summary="[Internal] Update customer health signal", response_model=ApiResponse[dict])
async def update_health_signal(customer_id: uuid.UUID, body: UpdateHealthSignalRequest, r: Request,
                                tid: uuid.UUID = Query(..., alias="tenant_id"),
                                u: UserContext = Depends(require_super_admin),
                                s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.update_customer_signal(customer_id, tid, body.signal_name, body.value,
                                           body.event_ref, body.event_type)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.post("/customers/{customer_id}/health/recompute", summary="Force-recompute customer health from raw events", response_model=ApiResponse[dict])
async def recompute_health(customer_id: uuid.UUID, r: Request,
                            tid: uuid.UUID = Query(..., alias="tenant_id"),
                            u: UserContext = Depends(require_permission(P.CUSTOMERS_MANAGE)),
                            s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.recompute_customer_health(customer_id, tid)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.get("/tenants/{tenant_id}/customers", summary="List customers with health scores for tenant", response_model=ApiResponse[dict])
async def list_customers(tenant_id: uuid.UUID, r: Request,
                          limit: int = Query(50, ge=1, le=200),
                          cursor: str | None = Query(None),
                          search: str | None = Query(None),
                          band: str | None = Query(None),
                          u: UserContext = Depends(require_permission(P.CUSTOMERS_READ)),
                          db: AsyncSession = Depends(get_db)) -> ApiResponse[dict]:
    from sqlalchemy import text as sql_text
    rid = _meta(r).request_id
    offset = 0
    if cursor:
        try:
            from app.schemas.base import decode_cursor
            offset = decode_cursor(cursor) or 0
        except Exception:
            offset = 0
    where_band = "AND chs.band = :band" if band else ""
    where_search = "AND (u.full_name ILIKE :search OR u.email ILIKE :search)" if search else ""
    q = f"""
        SELECT u.id, u.full_name, u.phone, u.email,
               chs.score AS health_score, chs.band AS health_band,
               chs.can_book, chs.computed_at,
               chs.created_at
        FROM customer_health_scores chs
        JOIN users u ON u.id = chs.customer_id
        WHERE chs.tenant_id = :tid {where_band} {where_search}
        ORDER BY chs.created_at DESC
        LIMIT :limit OFFSET :offset
    """
    params: dict = {"tid": str(tenant_id), "limit": limit + 1, "offset": offset}
    if band:
        params["band"] = band
    if search:
        params["search"] = f"%{search}%"
    result = await db.execute(sql_text(q), params)
    rows = result.mappings().all()
    has_next = len(rows) > limit
    rows = rows[:limit]
    customers = []
    for row in rows:
        customers.append({
            "id": str(row["id"]),
            "name": row["full_name"] or "",
            "phone": row["phone"],
            "email": row["email"],
            "health_score": float(row["health_score"]) if row["health_score"] is not None else 80.0,
            "health_band": row["health_band"] or "standard",
            "can_book": bool(row["can_book"]) if row["can_book"] is not None else True,
            "last_job_at": None,
            "total_jobs": 0,
            "total_spend": 0,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        })
    from app.schemas.base import encode_cursor
    return ok({
        "customers": customers,
        "total": len(customers),
        "has_next": has_next,
        "next_cursor": encode_cursor(offset + limit) if has_next else None,
    }, rid, ENGINE_ID)

@router.get("/tenants/{tenant_id}/customers/at-risk", summary="Customers in Cautious/Restricted/Blocked bands", response_model=ApiResponse[dict])
async def at_risk_customers(tenant_id: uuid.UUID, r: Request,
                             u: UserContext = Depends(require_permission(P.CUSTOMERS_READ)),
                             s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_at_risk_customers(tenant_id)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.post("/customers/{customer_id}/health/override", summary="[Admin] Override customer health band (with expiry)", response_model=ApiResponse[dict])
async def override_health(customer_id: uuid.UUID, body: HealthOverrideRequest, r: Request,
                           tid: uuid.UUID = Query(..., alias="tenant_id"),
                           u: UserContext = Depends(require_super_admin),
                           s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.override_customer_health(customer_id, tid, body.override_band,
                                             body.reason, body.expires_days)
    return ok(data, _meta(r).request_id, ENGINE_ID)

# ── CREDIT RESERVATIONS (4) ───────────────────────────────────────────────────
@router.post("/bookings/{booking_id}/reservation/create", summary="Lock customer credits at booking confirmation", response_model=ApiResponse[dict])
async def create_reservation(booking_id: str, body: ReservationCreateRequest, r: Request,
                              u: UserContext = Depends(require_super_admin),
                              s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.create_reservation(body.customer_id, body.tenant_id, booking_id,
                                       body.advance_pct, body.booking_value)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.post("/bookings/{booking_id}/reservation/confirm", summary="Convert reservation to confirmed deduction at job close", response_model=ApiResponse[dict])
async def confirm_reservation(booking_id: str, r: Request,
                               tid: uuid.UUID = Query(..., alias="tenant_id"),
                               u: UserContext = Depends(require_super_admin),
                               s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.confirm_reservation(booking_id, tid)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.post("/bookings/{booking_id}/reservation/release", summary="Release reservation on policy-compliant cancellation", response_model=ApiResponse[dict])
async def release_reservation(booking_id: str, r: Request,
                               tid: uuid.UUID = Query(..., alias="tenant_id"),
                               u: UserContext = Depends(require_super_admin),
                               s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.release_reservation(booking_id, tid)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.post("/bookings/{booking_id}/reservation/forfeit", summary="Forfeit reservation on no-show / late cancellation", response_model=ApiResponse[dict])
async def forfeit_reservation(booking_id: str, r: Request,
                               tid: uuid.UUID = Query(..., alias="tenant_id"),
                               u: UserContext = Depends(require_super_admin),
                               s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.forfeit_reservation(booking_id, tid)
    return ok(data, _meta(r).request_id, ENGINE_ID)

# ── WARRANTY CLAIMS (6) ───────────────────────────────────────────────────────
@router.post("/warranty/claims", summary="Submit warranty claim for a completed job", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def submit_claim(body: WarrantyClaimRequest, r: Request,
                        u: UserContext = Depends(require_customer),
                        s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.submit_claim(uuid.UUID(u.user_id), body.job_id, body.claim_type,
                                 body.description, body.media_ids, body.amount_requested)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.get("/warranty/claims/{claim_id}", summary="Get warranty claim detail", response_model=ApiResponse[dict])
async def get_claim(claim_id: uuid.UUID, r: Request,
                     u: UserContext = Depends(get_current_user),
                     s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_claim(
        claim_id,
        customer_id=uuid.UUID(u.user_id) if u.role == "customer" else None,
        tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None,
        is_admin=False,
    )
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.get("/tenants/{tenant_id}/warranty/claims", summary="List warranty claims for tenant", response_model=ApiResponse[dict])
async def list_tenant_claims(tenant_id: uuid.UUID, r: Request,
                              status_filter: str | None = Query(None, alias="status"),
                              limit: int = Query(50, ge=1, le=200),
                              cursor: str | None = Query(None),
                              u: UserContext = Depends(get_current_user),
                              s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    if not u.tenant_id or str(u.tenant_id) != str(tenant_id):
        raise ServiceOSException("NOT_FOUND", "Warranty claims not found.", status_code=404)
    data = await s.list_tenant_claims(tenant_id, status_filter, limit, cursor)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.get("/customer/warranty/claims", summary="List my warranty claims", response_model=ApiResponse[dict])
async def list_customer_claims(r: Request,
                               status_filter: str | None = Query(None, alias="status"),
                               limit: int = Query(50, ge=1, le=100),
                               cursor: str | None = Query(None),
                               u: UserContext = Depends(require_customer),
                               s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.list_customer_claims(uuid.UUID(u.user_id), status_filter, limit, cursor)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.post("/warranty/claims/{claim_id}/provider-response", summary="Provider responds to or resolves own warranty claim", response_model=ApiResponse[dict])
async def provider_respond_claim(claim_id: uuid.UUID, body: WarrantyProviderResponseRequest, r: Request,
                                 u: UserContext = Depends(require_mutation_access_scope),
                                 s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    if not u.tenant_id:
        raise ServiceOSException("TENANT_CONTEXT_REQUIRED", "Provider tenant context is required.", status_code=403)
    data = await s.provider_respond_claim(
        claim_id, uuid.UUID(u.tenant_id), body.resolution, resolved=body.resolved,
    )
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.post("/warranty/claims/{claim_id}/escalate", summary="Escalate an unresolved provider warranty claim", response_model=ApiResponse[dict])
async def escalate_claim(claim_id: uuid.UUID, body: WarrantyEscalationRequest, r: Request,
                         u: UserContext = Depends(require_mutation_access_scope),
                         s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.escalate_claim(
        claim_id, body.reason,
        customer_id=uuid.UUID(u.user_id) if u.role == "customer" else None,
        tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None,
    )
    return ok(data, _meta(r).request_id, ENGINE_ID)

@retired_admin_warranty_router.get("/warranty/claims")
async def list_all_claims(r: Request,
                           status_filter: str | None = Query(None, alias="status"),
                           limit: int = Query(50, ge=1, le=200),
                           cursor: str | None = Query(None),
                           u: UserContext = Depends(require_super_admin),
                           s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.list_all_claims(status_filter, limit, cursor)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@retired_admin_warranty_router.post("/warranty/claims/{claim_id}/approve")
async def approve_claim(claim_id: uuid.UUID, body: ClaimResolveRequest, r: Request,
                         u: UserContext = Depends(require_super_admin),
                         s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.approve_claim(claim_id, body.amount_approved or Decimal("0"), body.admin_notes)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@retired_admin_warranty_router.post("/warranty/claims/{claim_id}/reject")
async def reject_claim(claim_id: uuid.UUID, body: ClaimResolveRequest, r: Request,
                        u: UserContext = Depends(require_super_admin),
                        s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.reject_claim(claim_id, body.rejection_reason or "Claim rejected.", body.admin_notes)
    return ok(data, _meta(r).request_id, ENGINE_ID)

# ── BADGES (3) ────────────────────────────────────────────────────────────────
@router.get("/tenants/{tenant_id}/badges", summary="Get active badges for tenant", response_model=ApiResponse[dict])
async def get_badges(tenant_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(get_current_user),
                      s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_badges(tenant_id)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.post("/tenants/{tenant_id}/badges/recalculate", summary="Force badge recalculation (normally runs daily via Celery)", response_model=ApiResponse[dict])
async def recalculate_badges(tenant_id: uuid.UUID, r: Request,
                              u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                              s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.recalculate_badges(tenant_id)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.get("/platform/badges/summary", summary="[Admin] Platform-wide badge distribution", response_model=ApiResponse[dict])
async def badges_summary(r: Request, u: UserContext = Depends(require_super_admin),
                          s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_badges_summary()
    return ok(data, _meta(r).request_id, ENGINE_ID)

# ── PREFLIGHT (2) ─────────────────────────────────────────────────────────────
@router.post("/bookings/preflight", summary="Run 4-check pre-flight — gate for all bookings", response_model=ApiResponse[dict])
async def run_preflight(body: PreflightRequest, r: Request,
                         u: UserContext = Depends(get_current_user),
                         s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.run_preflight(body.tenant_id, body.customer_id,
                                  body.estimated_job_value, body.booking_id)
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.get("/bookings/preflight/rules", summary="Get pre-flight rules and current thresholds", response_model=ApiResponse[dict])
async def preflight_rules(r: Request, tid: uuid.UUID = Query(..., alias="tenant_id"),
                           u: UserContext = Depends(get_current_user),
                           s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_preflight_rules(tid)
    return ok(data, _meta(r).request_id, ENGINE_ID)

# ── PLATFORM ANALYTICS (3) ────────────────────────────────────────────────────
@router.get("/platform/summary", summary="[Admin] Platform-wide commerce KPIs", response_model=ApiResponse[dict])
async def platform_summary(r: Request, u: UserContext = Depends(require_super_admin),
                            s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_platform_summary()
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.get("/platform/tenants/at-risk", summary="[Admin] Tenants in At Risk / Critical health bands", response_model=ApiResponse[dict])
async def at_risk_tenants(r: Request, u: UserContext = Depends(require_super_admin),
                           s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_at_risk_tenants()
    return ok(data, _meta(r).request_id, ENGINE_ID)

@router.get("/platform/commission/daily", summary="[Admin] Daily commission chart data", response_model=ApiResponse[dict])
async def daily_commission(r: Request, days: int = Query(90, ge=7, le=365),
                            cursor: str | None = Query(None),
                            u: UserContext = Depends(require_super_admin),
                            s: CommerceService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_daily_commission_chart(days, cursor)
    return ok(data, _meta(r).request_id, ENGINE_ID)
