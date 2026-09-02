"""Finance Hub Engine — Admin Router.
All endpoints under /v1/admin/finance/*. All write endpoints are permission-guarded
via P.FINANCE_*; super_admin holds P.ALL so this is additive, not a regression.
"""
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.auth import UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.finance_hub.service import FinanceHubService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/finance", tags=["Finance Hub"])
retired_warranty_router = APIRouter()
ENGINE_ID = "finance_hub"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_permission(P.FINANCE_READ))) -> FinanceHubService:
    return FinanceHubService(db=db, request_id=getattr(r.state, "request_id", "—"),
                              actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)


def _rid(r): return getattr(r.state, "request_id", "—")


# ═══════════════════════════════════════════════════════════════
# OVERVIEW
# ═══════════════════════════════════════════════════════════════

@router.get("/summary", response_model=ApiResponse[dict], summary="Finance Hub summary cards")
async def finance_summary(r: Request, s: FinanceHubService = Depends(_svc), u: UserContext = Depends(require_super_admin)):
    return ok(await s.get_finance_summary(), _rid(r), ENGINE_ID)


@router.get("/overview", response_model=ApiResponse[dict], summary="Finance Hub overview insights")
async def finance_overview(r: Request, s: FinanceHubService = Depends(_svc), u: UserContext = Depends(require_super_admin)):
    return ok(await s.get_finance_overview(), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# SECURITY DEPOSITS
# ═══════════════════════════════════════════════════════════════

# The security deposit was removed in migration 317/318. These endpoints
# went with it: a provider now buys a top-up plan whose credit is spent
# down as commission, so there is no held balance to administer.


@router.get("/topups", response_model=ApiResponse[dict], summary="List credit top-ups")
async def list_topups(r: Request,
                       tenant_id: uuid.UUID | None = Query(None),
                       payment_status: str | None = Query(None),
                       q: str | None = Query(None),
                       page: int = Query(1, ge=1),
                       page_size: int = Query(50, ge=1, le=500),
                       sort_by: str = Query("created_at"),
                       sort_dir: str = Query("desc"),
                       u: UserContext = Depends(require_permission(P.FINANCE_TOPUPS_READ)),
                       s: FinanceHubService = Depends(_svc)):
    return ok(await s.list_topups(tenant_id, payment_status, q, page, page_size, sort_by, sort_dir), _rid(r), ENGINE_ID)


@router.get("/topups/summary", response_model=ApiResponse[dict], summary="Credit top-ups summary cards")
async def topups_summary(r: Request,
                          u: UserContext = Depends(require_permission(P.FINANCE_TOPUPS_READ)),
                          s: FinanceHubService = Depends(_svc)):
    return ok(await s.get_topups_summary(), _rid(r), ENGINE_ID)


@router.get("/topups/export", response_model=ApiResponse[dict], summary="Export credit top-ups")
async def export_topups(r: Request, payment_status: str | None = Query(None),
                         # FINAL-L5-05O: distinct export permission (was READ).
                         u: UserContext = Depends(require_permission(P.FINANCE_EXPORT)),
                         s: FinanceHubService = Depends(_svc)):
    rows = await s.export_topups(payment_status=payment_status)
    return ok({"rows": rows, "count": len(rows), "format": "json"}, _rid(r), ENGINE_ID)


@router.get("/topups/{topup_id}", response_model=ApiResponse[dict], summary="Get credit top-up detail")
async def get_topup(topup_id: uuid.UUID, r: Request,
                     u: UserContext = Depends(require_permission(P.FINANCE_TOPUPS_READ)),
                     s: FinanceHubService = Depends(_svc)):
    return ok(await s.get_topup_detail(topup_id), _rid(r), ENGINE_ID)


@router.post("/topups/{topup_id}/retry-credit", response_model=ApiResponse[dict], summary="Retry credit posting")
async def retry_credit(topup_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(require_permission(P.FINANCE_TOPUPS_UPDATE)),
                        s: FinanceHubService = Depends(_svc)):
    return ok(await s.retry_credit_posting(topup_id), _rid(r), ENGINE_ID)


@router.post("/topups/{topup_id}/refund", response_model=ApiResponse[dict], summary="Refund a credit top-up")
async def refund_topup(topup_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(require_permission(P.FINANCE_TOPUPS_REFUND)),
                        s: FinanceHubService = Depends(_svc)):
    body = await r.json()
    return ok(await s.refund_topup(topup_id, Decimal(str(body["amount"])), body.get("reason", "")), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# WARRANTY CLAIMS
# ═══════════════════════════════════════════════════════════════

@retired_warranty_router.get("/warranty-claims")
async def list_claims(r: Request,
                       status: str | None = Query(None),
                       category: str | None = Query(None),
                       q: str | None = Query(None),
                       page: int = Query(1, ge=1),
                       page_size: int = Query(50, ge=1, le=500),
                       sort_by: str = Query("created_at"),
                       sort_dir: str = Query("desc"),
                       u: UserContext = Depends(require_permission(P.FINANCE_CLAIMS_READ)),
                       s: FinanceHubService = Depends(_svc)):
    return ok(await s.list_claims(status, category, q, page, page_size, sort_by, sort_dir), _rid(r), ENGINE_ID)


@retired_warranty_router.get("/warranty-claims/summary")
async def claims_summary(r: Request,
                          u: UserContext = Depends(require_permission(P.FINANCE_CLAIMS_READ)),
                          s: FinanceHubService = Depends(_svc)):
    return ok(await s.get_claims_summary(), _rid(r), ENGINE_ID)


@retired_warranty_router.get("/warranty-claims/export")
async def export_claims(r: Request, status: str | None = Query(None),
                         # FINAL-L5-05O: distinct export permission (was READ).
                         u: UserContext = Depends(require_permission(P.FINANCE_EXPORT)),
                         s: FinanceHubService = Depends(_svc)):
    rows = await s.export_claims(status=status)
    return ok({"rows": rows, "count": len(rows), "format": "json"}, _rid(r), ENGINE_ID)


@retired_warranty_router.get("/warranty-claims/{claim_id}")
async def get_claim(claim_id: uuid.UUID, r: Request,
                     u: UserContext = Depends(require_permission(P.FINANCE_CLAIMS_READ)),
                     s: FinanceHubService = Depends(_svc)):
    return ok(await s.get_claim_detail(claim_id), _rid(r), ENGINE_ID)


@retired_warranty_router.post("/warranty-claims/{claim_id}/assign")
async def assign_reviewer(claim_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_permission(P.FINANCE_CLAIMS_ASSIGN)),
                           s: FinanceHubService = Depends(_svc)):
    body = await r.json()
    return ok(await s.assign_reviewer(claim_id, uuid.UUID(str(body["reviewer_id"]))), _rid(r), ENGINE_ID)


@retired_warranty_router.post("/warranty-claims/{claim_id}/request-documents")
async def request_documents(claim_id: uuid.UUID, r: Request,
                             u: UserContext = Depends(require_permission(P.FINANCE_CLAIMS_ASSIGN)),
                             s: FinanceHubService = Depends(_svc)):
    body = await r.json()
    return ok(await s.request_documents(claim_id, body.get("notes", "")), _rid(r), ENGINE_ID)


@retired_warranty_router.post("/warranty-claims/{claim_id}/approve")
async def approve_claim(claim_id: uuid.UUID, r: Request,
                         u: UserContext = Depends(require_permission(P.FINANCE_CLAIMS_APPROVE)),
                         s: FinanceHubService = Depends(_svc)):
    body = await r.json()
    return ok(await s.approve_claim(claim_id, Decimal(str(body["amount_approved"])), body.get("admin_notes")), _rid(r), ENGINE_ID)


@retired_warranty_router.post("/warranty-claims/{claim_id}/reject")
async def reject_claim(claim_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(require_permission(P.FINANCE_CLAIMS_REJECT)),
                        s: FinanceHubService = Depends(_svc)):
    body = await r.json()
    return ok(await s.reject_claim(claim_id, body["rejection_reason"], body.get("admin_notes")), _rid(r), ENGINE_ID)


@retired_warranty_router.post("/warranty-claims/{claim_id}/settle")
async def settle_claim(claim_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(require_permission(P.FINANCE_CLAIMS_SETTLE)),
                        s: FinanceHubService = Depends(_svc)):
    return ok(await s.settle_claim(claim_id), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# PAYOUTS
# ═══════════════════════════════════════════════════════════════

@router.get("/payouts", response_model=ApiResponse[dict], summary="List payouts")
async def list_payouts(r: Request,
                        status: str | None = Query(None),
                        tenant_id: uuid.UUID | None = Query(None),
                        q: str | None = Query(None),
                        page: int = Query(1, ge=1),
                        page_size: int = Query(50, ge=1, le=500),
                        sort_by: str = Query("created_at"),
                        sort_dir: str = Query("desc"),
                        u: UserContext = Depends(require_permission(P.FINANCE_PAYOUTS_READ)),
                        s: FinanceHubService = Depends(_svc)):
    return ok(await s.list_payouts(status, tenant_id, q, page, page_size, sort_by, sort_dir), _rid(r), ENGINE_ID)


@router.get("/payouts/summary", response_model=ApiResponse[dict], summary="Payouts summary cards")
async def payouts_summary(r: Request,
                           u: UserContext = Depends(require_permission(P.FINANCE_PAYOUTS_READ)),
                           s: FinanceHubService = Depends(_svc)):
    return ok(await s.get_payouts_summary(), _rid(r), ENGINE_ID)


@router.get("/payouts/export", response_model=ApiResponse[dict], summary="Export payouts")
async def export_payouts(r: Request, status: str | None = Query(None),
                          # FINAL-L5-05O: distinct export permission (was READ).
                          u: UserContext = Depends(require_permission(P.FINANCE_EXPORT)),
                          s: FinanceHubService = Depends(_svc)):
    rows = await s.export_payouts(status=status)
    return ok({"rows": rows, "count": len(rows), "format": "json"}, _rid(r), ENGINE_ID)


@router.get("/payouts/{payout_id}", response_model=ApiResponse[dict], summary="Get payout detail")
async def get_payout(payout_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(require_permission(P.FINANCE_PAYOUTS_READ)),
                      s: FinanceHubService = Depends(_svc)):
    return ok(await s.get_payout_detail(payout_id), _rid(r), ENGINE_ID)


@router.post("/payouts/{payout_id}/approve", response_model=ApiResponse[dict], summary="Approve payout")
async def approve_payout(payout_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(require_permission(P.FINANCE_PAYOUTS_APPROVE)),
                          s: FinanceHubService = Depends(_svc)):
    body = await r.json() if await r.body() else {}
    approved_amount = Decimal(str(body["approved_amount"])) if body.get("approved_amount") is not None else None
    return ok(await s.approve_payout(payout_id, approved_amount), _rid(r), ENGINE_ID)


@router.post("/payouts/{payout_id}/reject", response_model=ApiResponse[dict], summary="Reject payout")
async def reject_payout(payout_id: uuid.UUID, r: Request,
                         u: UserContext = Depends(require_permission(P.FINANCE_PAYOUTS_REJECT)),
                         s: FinanceHubService = Depends(_svc)):
    body = await r.json()
    return ok(await s.reject_payout(payout_id, body["reason"]), _rid(r), ENGINE_ID)


@router.post("/payouts/{payout_id}/mark-processing", response_model=ApiResponse[dict], summary="Mark payout as processing")
async def mark_processing(payout_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_permission(P.FINANCE_PAYOUTS_PROCESS)),
                           s: FinanceHubService = Depends(_svc)):
    return ok(await s.mark_processing(payout_id), _rid(r), ENGINE_ID)


@router.post("/payouts/{payout_id}/mark-completed", response_model=ApiResponse[dict], summary="Mark payout as completed")
async def mark_completed(payout_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(require_permission(P.FINANCE_PAYOUTS_COMPLETE)),
                          s: FinanceHubService = Depends(_svc)):
    body = await r.json() if await r.body() else {}
    return ok(await s.mark_completed(payout_id, body.get("gateway_transfer_id")), _rid(r), ENGINE_ID)


@router.post("/payouts/{payout_id}/mark-failed", response_model=ApiResponse[dict], summary="Mark payout as failed")
async def mark_failed(payout_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(require_permission(P.FINANCE_PAYOUTS_PROCESS)),
                       s: FinanceHubService = Depends(_svc)):
    body = await r.json()
    return ok(await s.mark_failed(payout_id, body["failure_reason"]), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# WALLETS
# ═══════════════════════════════════════════════════════════════

@router.get("/wallets", response_model=ApiResponse[dict], summary="Wallet directory")
async def list_wallets(r: Request,
                        q: str | None = Query(None),
                        health_band: str | None = Query(None),
                        page: int = Query(1, ge=1),
                        page_size: int = Query(50, ge=1, le=500),
                        u: UserContext = Depends(require_permission(P.FINANCE_WALLETS_READ)),
                        s: FinanceHubService = Depends(_svc)):
    return ok(await s.list_wallets(q, health_band, page, page_size), _rid(r), ENGINE_ID)


@router.get("/wallets/{wallet_id}/ledger", response_model=ApiResponse[dict], summary="Wallet ledger detail")
async def get_wallet_ledger(wallet_id: uuid.UUID, r: Request,
                             page: int = Query(1, ge=1),
                             page_size: int = Query(50, ge=1, le=500),
                             u: UserContext = Depends(require_permission(P.FINANCE_WALLETS_READ)),
                             s: FinanceHubService = Depends(_svc)):
    return ok(await s.get_wallet_ledger(wallet_id, page, page_size), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# AUDIT LOGS
# ═══════════════════════════════════════════════════════════════

@router.get("/audit-logs", response_model=ApiResponse[dict], summary="Query finance audit logs for an entity")
async def list_audit_logs(r: Request,
                           entity_type: str = Query(...),
                           entity_id: str = Query(...),
                           limit: int = Query(50, ge=1, le=200),
                           u: UserContext = Depends(require_permission(P.FINANCE_AUDIT_READ)),
                           s: FinanceHubService = Depends(_svc)):
    return ok(await s.list_audit_logs(entity_type, entity_id, limit), _rid(r), ENGINE_ID)
