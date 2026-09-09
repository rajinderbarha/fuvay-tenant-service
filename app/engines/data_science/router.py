"""Data Science Engine — Router (20 endpoints). Zero inline imports. Zero business logic."""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission, require_tenant_mutation_permission, require_mutation_access_scope
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.data_science.service import DSService
from app.schemas.base import ApiResponse, ok

logger = structlog.get_logger("ds.router")
router = APIRouter(prefix="/v1/ds", tags=["Data Science Engine"])
ENGINE_ID = "data_science"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> DSService:
    return DSService(db=db, request_id=getattr(r.state,"request_id","—"),
                      actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                      actor_role=u.role,
                      actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)
def _rid(r): return getattr(r.state,"request_id","—")


# ── Engine Meta ───────────────────────────────────────────────────────────────
@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {
        "engine_id": ENGINE_ID, "name": "Data Science Engine", "version": "7.0.0",
        "endpoint_count": 21, "status": "active",
        "phases": {
            "0": "rule_based — < 50 jobs",
            "1": "observation — 50–500 jobs",
            "2": "platform_model — 500–2000 jobs",
            "3": "tenant_model — 2000+ jobs",
        },
        "capabilities": ["churn_prediction","demand_forecasting","geographic_demand_intelligence","pricing_recommendations",
                         "staff_performance","customer_ltv","anomaly_detection",
                         "model_versioning","observation_mode_flag"],
    }


# ── Churn Prediction (4 endpoints) ───────────────────────────────────────────
@router.get("/tenants/{tenant_id}/churn/score",
            summary="Get churn risk score with contributing factors and observation mode flag",
            response_model=ApiResponse[dict])
async def get_churn_score(tenant_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(get_current_user),
                           s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_churn_score(tenant_id), _rid(r), ENGINE_ID)


@router.get("/churn/at-risk",
            summary="[Admin] List all tenants in high/critical churn bands",
            response_model=ApiResponse[dict])
async def list_at_risk(r: Request, limit: int = Query(50,ge=1,le=200),
                        cursor: str|None = Query(None),
                        u: UserContext = Depends(require_super_admin),
                        s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_at_risk_tenants(limit, cursor), _rid(r), ENGINE_ID)


@router.get("/tenants/{tenant_id}/churn/factors",
            summary="Get detailed churn contributing factors with recommended actions",
            response_model=ApiResponse[dict])
async def get_churn_factors(tenant_id: uuid.UUID, r: Request,
                             u: UserContext = Depends(get_current_user),
                             s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_churn_factors(tenant_id), _rid(r), ENGINE_ID)


@router.get("/tenants/{tenant_id}/churn/history",
            summary="Churn score history from prediction records",
            response_model=ApiResponse[dict])
async def churn_history(tenant_id: uuid.UUID, r: Request,
                         days: int = Query(30,ge=1,le=365),
                         u: UserContext = Depends(get_current_user),
                         s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_churn_history(tenant_id, days), _rid(r), ENGINE_ID)


# ── Demand Forecasting (3 endpoints) ─────────────────────────────────────────
@router.get("/tenants/{tenant_id}/demand/forecast",
            summary="Get 14-day demand forecast. Cached 6h, updates with more data.",
            response_model=ApiResponse[dict])
async def get_forecast(tenant_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(get_current_user),
                        s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_demand_forecast(tenant_id), _rid(r), ENGINE_ID)


@router.post("/tenants/{tenant_id}/demand/recompute",
             summary="Force recompute demand forecast immediately",
             response_model=ApiResponse[dict])
async def trigger_recompute(tenant_id: uuid.UUID, r: Request,
                             u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                             s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.trigger_recompute(tenant_id), _rid(r), ENGINE_ID)


@router.get("/tenants/{tenant_id}/demand/history",
            summary="Historical demand forecast records",
            response_model=ApiResponse[dict])
async def forecast_history(tenant_id: uuid.UUID, r: Request,
                            days: int = Query(30,ge=1,le=90),
                            u: UserContext = Depends(get_current_user),
                            s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_forecast_history(tenant_id, days), _rid(r), ENGINE_ID)


# ── Pricing Recommendations (3 endpoints) ────────────────────────────────────
@router.get("/tenants/{tenant_id}/pricing/recommendations",
            summary="Get pricing recommendations vs platform benchmark",
            response_model=ApiResponse[dict])
async def pricing_recs(tenant_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(get_current_user),
                        s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_pricing_recommendations(tenant_id), _rid(r), ENGINE_ID)


@router.post("/tenants/{tenant_id}/pricing/apply",
             summary="Apply a pricing recommendation — delegates to Pricing Engine",
             response_model=ApiResponse[dict])
async def apply_pricing(tenant_id: uuid.UUID, r: Request,
                         u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                         s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.apply_pricing_recommendation(
              tenant_id, body["service_type_id"], body["target_price"]), _rid(r), ENGINE_ID)


@router.get("/tenants/{tenant_id}/pricing/history",
            summary="History of pricing recommendation computations",
            response_model=ApiResponse[dict])
async def pricing_history(tenant_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(get_current_user),
                           s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_pricing_history(tenant_id), _rid(r), ENGINE_ID)


# ── Staff Performance (3 endpoints) ──────────────────────────────────────────
@router.get("/tenants/{tenant_id}/staff/rankings",
            summary="Get staff performance rankings for dispatch prioritisation",
            response_model=ApiResponse[dict])
async def staff_rankings(tenant_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(get_current_user),
                          s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_staff_rankings(tenant_id), _rid(r), ENGINE_ID)


@router.get("/tenants/{tenant_id}/staff/{staff_id}/score",
            summary="Get individual staff performance score with signal breakdown",
            response_model=ApiResponse[dict])
async def staff_score(tenant_id: uuid.UUID, staff_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(get_current_user),
                       s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    # A staff member may only view their own score, not a colleague's.
    if u.role == "staff" and (not u.user_id or uuid.UUID(u.user_id) != staff_id):
        from app.exceptions import NotFoundException
        raise NotFoundException("StaffScore", str(staff_id))
    return ok(await s.get_staff_score(staff_id, tenant_id), _rid(r), ENGINE_ID)


@router.post("/tenants/{tenant_id}/staff/{staff_id}/signal",
             summary="[Internal] Update a staff performance signal after job event",
             response_model=ApiResponse[dict])
async def update_staff_signal(tenant_id: uuid.UUID, staff_id: uuid.UUID, r: Request,
                               u: UserContext = Depends(require_super_admin),
                               s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.update_staff_signal(staff_id, tenant_id,
              body["signal"], body["value"]), _rid(r), ENGINE_ID)


# ── Customer LTV (3 endpoints) ────────────────────────────────────────────────
@router.get("/tenants/{tenant_id}/customers/{customer_id}/ltv",
            summary="Get customer lifetime value prediction",
            response_model=ApiResponse[dict])
async def customer_ltv(tenant_id: uuid.UUID, customer_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(require_mutation_access_scope),
                        s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_customer_ltv(customer_id, tenant_id), _rid(r), ENGINE_ID)


@router.get("/tenants/{tenant_id}/customers/high-value",
            summary="List top customers by predicted lifetime value",
            response_model=ApiResponse[dict])
async def high_value_customers(tenant_id: uuid.UUID, r: Request,
                                limit: int = Query(20,ge=1,le=100),
                                u: UserContext = Depends(get_current_user),
                                s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_high_value_customers(tenant_id, limit), _rid(r), ENGINE_ID)


@router.post("/tenants/{tenant_id}/customers/{customer_id}/ltv/recompute",
             summary="Force recompute LTV for a customer",
             response_model=ApiResponse[dict])
async def recompute_ltv(tenant_id: uuid.UUID, customer_id: uuid.UUID, r: Request,
                         u: UserContext = Depends(require_mutation_access_scope),
                         s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.recompute_ltv(customer_id, tenant_id), _rid(r), ENGINE_ID)


# ── Anomaly Detection (3 endpoints) ──────────────────────────────────────────
@router.get("/anomalies",
            summary="List detected anomalies — filter by tenant or status",
            response_model=ApiResponse[dict])
async def list_anomalies(r: Request,
                          tenant_id: uuid.UUID|None = Query(None),
                          anom_status: str|None = Query(None, alias="status"),
                          limit: int = Query(50,ge=1,le=200),
                          cursor: str|None = Query(None),
                          u: UserContext = Depends(get_current_user),
                          s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_anomalies(tenant_id, anom_status, limit, cursor), _rid(r), ENGINE_ID)


@router.get("/anomalies/{anomaly_id}",
            summary="Get anomaly detail with context and threshold",
            response_model=ApiResponse[dict])
async def get_anomaly(anomaly_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(get_current_user),
                       s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_anomaly(anomaly_id), _rid(r), ENGINE_ID)


@router.post("/anomalies/{anomaly_id}/acknowledge",
             summary="Acknowledge anomaly with resolution notes",
             response_model=ApiResponse[dict])
async def acknowledge_anomaly(anomaly_id: uuid.UUID, r: Request,
                               u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                               s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.acknowledge_anomaly(anomaly_id, body.get("notes")), _rid(r), ENGINE_ID)


# ── Model Management (2 endpoints) ───────────────────────────────────────────
@router.get("/models",
            summary="[Admin] List model versions with metrics",
            response_model=ApiResponse[dict])
async def model_versions(r: Request,
                          model_type: str|None = Query(None),
                          u: UserContext = Depends(require_super_admin),
                          s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_model_versions(model_type), _rid(r), ENGINE_ID)


@router.post("/models/{model_type}/retrain",
             summary="[Admin] Trigger model retraining — queues Celery job",
             status_code=status.HTTP_202_ACCEPTED, response_model=ApiResponse[dict])
async def trigger_retrain(model_type: str, r: Request,
                           u: UserContext = Depends(require_super_admin),
                           s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.trigger_retrain(model_type), _rid(r), ENGINE_ID)


# ── Business Performance (1 endpoint) ────────────────────────────────────────
@router.get("/tenants/{tenant_id}/business-performance",
            summary="Tenant BI dashboard — jobs by type, conversion, revenue, repeat rate, quality, SLA, staff",
            response_model=ApiResponse[dict])
async def business_performance(tenant_id: uuid.UUID, r: Request,
                                days: int = Query(30, ge=1, le=365),
                                u: UserContext = Depends(get_current_user),
                                s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_business_performance(tenant_id, days), _rid(r), ENGINE_ID)


# ── Platform Summary (1 endpoint) ─────────────────────────────────────────────
@router.get("/platform/summary",
            summary="[Admin] Platform-wide DS metrics — churn, anomalies, predictions",
            response_model=ApiResponse[dict])
async def platform_summary(r: Request,
                            u: UserContext = Depends(require_super_admin),
                            s: DSService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_platform_summary(), _rid(r), ENGINE_ID)


@router.get("/platform/demand-intelligence",
            summary="[Admin] Geographic Home Services demand intelligence",
            response_model=ApiResponse[dict])
async def platform_demand_intelligence(
    r: Request,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(8, ge=1, le=20),
    u: UserContext = Depends(require_super_admin),
    s: DSService = Depends(_svc),
) -> ApiResponse[dict]:
    return ok(
        await s.get_platform_area_demand_intelligence(days=days, limit=limit),
        _rid(r), ENGINE_ID,
    )
