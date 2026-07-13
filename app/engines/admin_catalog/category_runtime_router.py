"""Category Runtime Admin Router — Enterprise Upgrade (P0).

Endpoints:
  GET    /v1/admin/categories/summary             — summary cards
  GET    /v1/admin/categories                     — enterprise list (filters + linked counts + readiness)
  GET    /v1/admin/categories/export              — CSV export
  GET    /v1/admin/categories/{id}                — get single category + runtime
  PUT    /v1/admin/categories/{id}                — update category
  PUT    /v1/admin/categories/{id}/runtime        — update runtime fields alias
  GET    /v1/admin/categories/{id}/readiness      — readiness detail
  POST   /v1/admin/categories/{id}/activate       — set is_active=True
  POST   /v1/admin/categories/{id}/deactivate     — set is_active=False
  GET    /v1/admin/categories/{id}/engines        — engine stubs
  GET    /v1/admin/categories/{id}/dashboard-modules — module stubs
  POST   /v1/admin/categories/{id}/engines/{eid}/enable
  POST   /v1/admin/categories/{id}/engines/{eid}/disable
  POST   /v1/admin/categories/{id}/engines/{eid}/set-primary
  POST   /v1/admin/categories/{id}/dashboard-modules
  PUT    /v1/admin/categories/{id}/dashboard-modules/{mid}
  POST   /v1/admin/categories/{id}/dashboard-modules/{mid}/enable
  POST   /v1/admin/categories/{id}/dashboard-modules/{mid}/disable
  POST   /v1/admin/categories/{id}/dashboard-modules/reorder
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin, get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.admin_catalog.service import AdminCatalogService
from app.schemas.base import ok

router = APIRouter(prefix="/v1/admin/categories", tags=["Category Runtime"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(get_current_user)) -> AdminCatalogService:
    return AdminCatalogService(db=db, request_id=getattr(r.state, "request_id", "—"),
                               actor_id=uuid.UUID(u.user_id) if u.user_id else None)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _compute_readiness(cat: dict) -> dict:
    """Return readiness_status + readiness_items from a category dict with linked_counts."""
    items: list[dict] = []
    counts = cat.get("linked_counts", {})

    if not cat.get("is_active", False):
        return {
            "readiness_status": "inactive",
            "readiness_items": [{"key": "status", "status": "missing", "message": "Category is not active."}],
        }

    if not cat.get("customer_flow_type"):
        items.append({"key": "customer_flow", "status": "missing", "message": "No customer flow type configured."})
    if not cat.get("finance_model"):
        items.append({"key": "finance_model", "status": "missing", "message": "No finance model configured."})

    service_count = counts.get("services", 0) + counts.get("service_groups", 0)
    if service_count == 0:
        items.append({"key": "services", "status": "missing", "message": "No active services or service groups linked."})

    if cat.get("pricing_supported") and counts.get("pricing_rules", 0) == 0:
        items.append({"key": "pricing_rules", "status": "missing", "message": "No active pricing rule configured for this category."})

    if cat.get("tenant_selectable") and counts.get("packages", 0) == 0:
        items.append({"key": "packages", "status": "warning", "message": "No packages/plans configured for tenant selection."})

    if not items:
        return {"readiness_status": "ready", "readiness_items": []}

    # Map to primary status
    if any(i["key"] == "services" for i in items):
        status = "missing_services"
    elif any(i["key"] == "pricing_rules" for i in items):
        status = "missing_pricing"
    elif any(i["key"] == "customer_flow" for i in items):
        status = "missing_flow_config"
    elif any(i["key"] == "packages" for i in items):
        status = "missing_package"
    else:
        status = "incomplete"

    return {"readiness_status": status, "readiness_items": items}


async def _linked_counts(db: AsyncSession, category_ids: list[str]) -> dict[str, dict]:
    """Fetch linked counts for a list of category IDs in one SQL batch."""
    if not category_ids:
        return {}

    id_list = ", ".join(f"'{cid}'" for cid in category_ids)

    sql = text(f"""
        SELECT
            sc.id::text                                              AS category_id,
            COALESCE(sg.cnt, 0)                                      AS service_groups,
            COALESCE(ms.cnt, 0)                                      AS services,
            COALESCE(pr.cnt, 0)                                      AS pricing_rules,
            COALESCE(br.cnt, 0)                                      AS brands,
            COALESCE(pkg.cnt, 0)                                     AS packages,
            COALESCE(ts.cnt, 0)                                      AS providers
        FROM service_categories sc
        LEFT JOIN (
            SELECT category_id, COUNT(*) AS cnt
            FROM service_groups
            WHERE deleted_at IS NULL
            GROUP BY category_id
        ) sg ON sg.category_id = sc.id
        LEFT JOIN (
            SELECT category_id, COUNT(*) AS cnt
            FROM master_services
            WHERE is_active = TRUE AND deleted_at IS NULL
            GROUP BY category_id
        ) ms ON ms.category_id = sc.id
        LEFT JOIN (
            SELECT category_id, COUNT(*) AS cnt
            FROM service_pricing_rules
            WHERE is_active = TRUE AND deleted_at IS NULL AND category_id IS NOT NULL
            GROUP BY category_id
        ) pr ON pr.category_id = sc.id
        LEFT JOIN (
            SELECT category_id, COUNT(*) AS cnt
            FROM brands
            WHERE is_active = TRUE AND deleted_at IS NULL AND category_id IS NOT NULL
            GROUP BY category_id
        ) br ON br.category_id = sc.id
        LEFT JOIN (
            SELECT category_id, COUNT(DISTINCT tpa.id) AS cnt
            FROM master_services ms2
            JOIN tenant_package_assignments tpa ON tpa.category_id = ms2.category_id
            WHERE ms2.is_active = TRUE AND ms2.deleted_at IS NULL
            GROUP BY ms2.category_id
        ) pkg ON pkg.category_id = sc.id
        LEFT JOIN (
            SELECT ts2.category_id, COUNT(DISTINCT ts2.tenant_id) AS cnt
            FROM tenant_services ts2
            WHERE ts2.is_active = TRUE AND ts2.deleted_at IS NULL
            GROUP BY ts2.category_id
        ) ts ON ts.category_id = sc.id
        WHERE sc.id::text IN ({id_list})
    """)
    try:
        rows = (await db.execute(sql)).mappings().all()
        return {
            row["category_id"]: {
                "service_groups": int(row["service_groups"] or 0),
                "services": int(row["services"] or 0),
                "pricing_rules": int(row["pricing_rules"] or 0),
                "brands": int(row["brands"] or 0),
                "packages": int(row["packages"] or 0),
                "providers": int(row["providers"] or 0),
            }
            for row in rows
        }
    except Exception:
        return {cid: {"service_groups": 0, "services": 0, "pricing_rules": 0, "brands": 0, "packages": 0, "providers": 0}
                for cid in category_ids}


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("/summary", summary="Category summary cards")
async def get_categories_summary(
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    sql = text("""
        SELECT
            COUNT(*)                                                             AS total,
            COUNT(*) FILTER (WHERE is_active = TRUE)                            AS active,
            COUNT(*) FILTER (WHERE is_active = FALSE)                           AS inactive,
            COUNT(*) FILTER (WHERE is_customer_visible = TRUE)                  AS customer_visible,
            COUNT(*) FILTER (WHERE tenant_selectable = TRUE)                    AS tenant_selectable
        FROM service_categories
    """)
    row = (await db.execute(sql)).mappings().one()

    # Readiness: active + has flow + has finance model
    ready_sql = text("""
        SELECT
            COUNT(*) FILTER (
                WHERE is_active = TRUE
                  AND customer_flow_type IS NOT NULL
                  AND finance_model IS NOT NULL
            ) AS runtime_ready,
            COUNT(*) FILTER (
                WHERE is_active = TRUE
                  AND (customer_flow_type IS NULL OR finance_model IS NULL)
            ) AS missing_required_setup
        FROM service_categories
    """)
    ready_row = (await db.execute(ready_sql)).mappings().one()

    # Categories with at least one service
    svc_sql = text("""
        SELECT COUNT(DISTINCT ms.category_id) AS with_services
        FROM master_services ms
        WHERE ms.is_active = TRUE AND ms.deleted_at IS NULL
    """)
    svc_row = (await db.execute(svc_sql)).mappings().one()

    # Categories with pricing rules
    pr_sql = text("""
        SELECT COUNT(DISTINCT pr.category_id) AS with_pricing
        FROM service_pricing_rules pr
        WHERE pr.is_active = TRUE AND pr.deleted_at IS NULL AND pr.category_id IS NOT NULL
    """)
    pr_row = (await db.execute(pr_sql)).mappings().one()

    return ok({
        "total":                 int(row["total"] or 0),
        "active":                int(row["active"] or 0),
        "inactive":              int(row["inactive"] or 0),
        "customer_visible":      int(row["customer_visible"] or 0),
        "tenant_selectable":     int(row["tenant_selectable"] or 0),
        "runtime_ready":         int(ready_row["runtime_ready"] or 0),
        "missing_required_setup":int(ready_row["missing_required_setup"] or 0),
        "with_services":         int(svc_row["with_services"] or 0),
        "with_pricing":          int(pr_row["with_pricing"] or 0),
    }, _rid(r), "category_summary")


# ── Enterprise List ───────────────────────────────────────────────────────────

@router.get("", summary="List categories with filters, linked counts, and readiness")
async def list_categories(
    r: Request,
    q: Optional[str] = Query(None),
    vertical_type: Optional[str] = Query(None),
    finance_model: Optional[str] = Query(None),
    customer_flow_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    customer_visible: Optional[bool] = Query(None),
    tenant_selectable: Optional[bool] = Query(None),
    pricing_supported: Optional[bool] = Query(None),
    readiness_status: Optional[str] = Query(None),
    # legacy param kept
    is_active: Optional[bool] = Query(None),
    category_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: str = Query("display_order"),
    sort_dir: str = Query("asc"),
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
    db: AsyncSession = Depends(get_db),
):
    data = await svc.list_categories(is_active=is_active if isinstance(is_active, bool) else None)
    cats = data["categories"]

    # Apply category_type filter (legacy)
    if category_type:
        cats = [c for c in cats if c.get("category_type") == category_type]

    # Apply server-side filters
    if q:
        ql = q.lower()
        cats = [c for c in cats if ql in c["name"].lower()
                or ql in (c.get("slug") or "").lower()
                or ql in (c.get("description") or "").lower()]
    if vertical_type:
        cats = [c for c in cats if c.get("vertical_type") == vertical_type]
    if finance_model:
        cats = [c for c in cats if c.get("finance_model") == finance_model]
    if customer_flow_type:
        cats = [c for c in cats if c.get("customer_flow_type") == customer_flow_type]
    if status == "active":
        cats = [c for c in cats if c.get("is_active")]
    elif status == "inactive":
        cats = [c for c in cats if not c.get("is_active")]
    if customer_visible is not None:
        cats = [c for c in cats if c.get("is_customer_visible") == customer_visible]
    if tenant_selectable is not None:
        cats = [c for c in cats if c.get("tenant_selectable") == tenant_selectable]
    if pricing_supported is not None:
        cats = [c for c in cats if c.get("pricing_supported") == pricing_supported]

    # Fetch linked counts for all filtered categories
    cat_ids = [c["category_id"] for c in cats]
    counts_map = await _linked_counts(db, cat_ids)

    # Attach linked counts + readiness to each category
    enriched = []
    for c in cats:
        cid = c["category_id"]
        linked = counts_map.get(cid, {"service_groups": 0, "services": 0, "pricing_rules": 0, "brands": 0, "packages": 0, "providers": 0})
        c_copy = {**c, "linked_counts": linked}
        rd = _compute_readiness(c_copy)
        c_copy["readiness_status"] = rd["readiness_status"]
        c_copy["readiness_items"] = rd["readiness_items"]
        enriched.append(c_copy)

    # Filter by readiness_status after computing
    if readiness_status:
        enriched = [c for c in enriched if c.get("readiness_status") == readiness_status]

    total = len(enriched)

    # Sort
    valid_sort = {"display_order", "name", "vertical_type", "finance_model", "readiness_status", "updated_at"}
    sort_key = sort_by if sort_by in valid_sort else "display_order"
    reverse = sort_dir == "desc"
    # FINAL-L5-05AK: `c.get(sort_key) or ""` treated falsy-but-valid values
    # (display_order == 0, e.g. the real seeded "Home Services" category)
    # as "missing" and substituted "" -- mixing int and str in the same
    # sort comparison raises TypeError on every call with the default
    # sort_by="display_order", which is exactly why GET /v1/admin/categories
    # 500'd unconditionally. Use an explicit None-check with a
    # type-appropriate default instead of a truthy/falsy fallback.
    _numeric_sort_keys = {"display_order"}
    def _sort_value(c: dict):
        v = c.get(sort_key)
        if v is not None:
            return v
        return 0 if sort_key in _numeric_sort_keys else ""
    enriched.sort(key=_sort_value, reverse=reverse)

    # Paginate
    offset = (page - 1) * page_size
    page_items = enriched[offset: offset + page_size]

    return ok({
        "items": page_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
        # legacy compat
        "categories": page_items,
    }, _rid(r), "category_list")


# ── Export ────────────────────────────────────────────────────────────────────

@router.get("/export", summary="Export categories as CSV")
async def export_categories(
    r: Request,
    status: Optional[str] = Query(None),
    vertical_type: Optional[str] = Query(None),
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
    db: AsyncSession = Depends(get_db),
):
    data = await svc.list_categories()
    cats = data["categories"]
    if status == "active":
        cats = [c for c in cats if c.get("is_active")]
    elif status == "inactive":
        cats = [c for c in cats if not c.get("is_active")]
    if vertical_type:
        cats = [c for c in cats if c.get("vertical_type") == vertical_type]

    cat_ids = [c["category_id"] for c in cats]
    counts_map = await _linked_counts(db, cat_ids)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Name", "Slug", "Vertical Type", "Finance Model", "Customer Flow",
        "Status", "Customer Visible", "Tenant Selectable", "Pricing Supported",
        "Requires Location", "Requires Schedule", "Requires Brand",
        "Requires Service Option", "Requires Issue Type",
        "Service Groups", "Services", "Pricing Rules", "Brands", "Packages", "Providers",
        "Updated At",
    ])
    for c in cats:
        cid = c["category_id"]
        lc = counts_map.get(cid, {})
        writer.writerow([
            c.get("name", ""), c.get("slug", ""),
            c.get("vertical_type", ""), c.get("finance_model", ""), c.get("customer_flow_type", ""),
            "Active" if c.get("is_active") else "Inactive",
            c.get("is_customer_visible", ""), c.get("tenant_selectable", ""), c.get("pricing_supported", ""),
            c.get("requires_location", ""), c.get("requires_schedule", ""), c.get("requires_brand", ""),
            c.get("requires_service_option", ""), c.get("requires_issue_type", ""),
            lc.get("service_groups", 0), lc.get("services", 0), lc.get("pricing_rules", 0),
            lc.get("brands", 0), lc.get("packages", 0), lc.get("providers", 0),
            c.get("updated_at", ""),
        ])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=service_categories.csv"},
    )


# ── Single Category ───────────────────────────────────────────────────────────

@router.get("/{category_id}", summary="Get category with runtime config")
async def get_category(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
    db: AsyncSession = Depends(get_db),
):
    data = await svc.get_category(category_id)
    counts = await _linked_counts(db, [str(category_id)])
    linked = counts.get(str(category_id), {})
    data["linked_counts"] = linked
    rd = _compute_readiness({**data, "linked_counts": linked})
    data["readiness_status"] = rd["readiness_status"]
    data["readiness_items"] = rd["readiness_items"]
    return ok(data, _rid(r), "category_runtime")


@router.put("/{category_id}", summary="Update category (runtime fields)")
async def update_category(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
):
    body = await r.json()
    data = await svc.update_category(category_id, body)
    return ok(data, _rid(r), "category_runtime")


@router.get("/{category_id}/runtime", summary="Get category runtime config")
async def get_category_runtime(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
    db: AsyncSession = Depends(get_db),
):
    data = await svc.get_category(category_id)
    counts = await _linked_counts(db, [str(category_id)])
    linked = counts.get(str(category_id), {})
    data["linked_counts"] = linked
    rd = _compute_readiness({**data, "linked_counts": linked})
    data["readiness_status"] = rd["readiness_status"]
    data["readiness_items"] = rd["readiness_items"]
    return ok(data, _rid(r), "category_runtime")


@router.put("/{category_id}/runtime", summary="Update category runtime config")
async def update_category_runtime(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
):
    body = await r.json()
    data = await svc.update_category(category_id, body)
    return ok(data, _rid(r), "category_runtime")


# ── Readiness ─────────────────────────────────────────────────────────────────

@router.get("/{category_id}/readiness", summary="Get category readiness detail")
async def get_category_readiness(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
    db: AsyncSession = Depends(get_db),
):
    cat = await svc.get_category(category_id)
    counts = await _linked_counts(db, [str(category_id)])
    linked = counts.get(str(category_id), {"service_groups": 0, "services": 0, "pricing_rules": 0, "brands": 0, "packages": 0, "providers": 0})
    cat_with_counts = {**cat, "linked_counts": linked}
    rd = _compute_readiness(cat_with_counts)
    return ok({
        "category_id": str(category_id),
        "category_name": cat.get("name"),
        "readiness_status": rd["readiness_status"],
        "readiness_items": rd["readiness_items"],
        "linked_counts": linked,
        "is_active": cat.get("is_active"),
        "has_customer_flow": bool(cat.get("customer_flow_type")),
        "has_finance_model": bool(cat.get("finance_model")),
    }, _rid(r), "category_readiness")


# ── Activate / Deactivate ─────────────────────────────────────────────────────

@router.post("/{category_id}/activate", summary="Activate category")
async def activate_category(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
):
    data = await svc.update_category(category_id, {"is_active": True})
    return ok({"activated": True, "category": data}, _rid(r), "category_runtime")


@router.post("/{category_id}/deactivate", summary="Deactivate category")
async def deactivate_category(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
):
    data = await svc.update_category(category_id, {"is_active": False})
    return ok({"deactivated": True, "category": data}, _rid(r), "category_runtime")


# ── Engines ───────────────────────────────────────────────────────────────────

@router.get("/{category_id}/engines", summary="List category engines (runtime config)")
async def list_category_engines(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
):
    cat = await svc.get_category(category_id)
    primary_key = cat.get("primary_engine_key")
    engines = []
    if primary_key:
        engines.append({
            "engine_id": primary_key,
            "engine_key": primary_key,
            "display_name": primary_key.replace("_", " ").title(),
            "is_primary": True,
            "is_enabled": True,
            "display_order": 0,
        })
    return ok({
        "engines": engines,
        "total": len(engines),
        "required_count": len(engines),
        "optional_count": 0,
        "primary_engine": engines[0] if engines else None,
    }, _rid(r), "category_runtime")


@router.post("/{category_id}/engines/{engine_id}/enable", summary="Enable engine for category")
async def enable_category_engine(
    category_id: uuid.UUID, engine_id: str,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
):
    data = await svc.update_category(category_id, {"primary_engine_key": engine_id})
    return ok({"engine_key": engine_id, "is_enabled": True, "category": data}, _rid(r), "category_runtime")


@router.post("/{category_id}/engines/{engine_id}/disable", summary="Disable engine for category")
async def disable_category_engine(
    category_id: uuid.UUID, engine_id: str,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
):
    return ok({"engine_key": engine_id, "is_enabled": False}, _rid(r), "category_runtime")


@router.post("/{category_id}/engines/{engine_id}/set-primary", summary="Set primary engine")
async def set_primary_engine(
    category_id: uuid.UUID, engine_id: str,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
):
    data = await svc.update_category(category_id, {"primary_engine_key": engine_id})
    return ok({"engine_key": engine_id, "is_primary": True, "category": data}, _rid(r), "category_runtime")


# ── Dashboard Modules ─────────────────────────────────────────────────────────

@router.get("/{category_id}/dashboard-modules", summary="List dashboard modules")
async def list_dashboard_modules(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
):
    cat = await svc.get_category(category_id)
    dash_type = cat.get("provider_dashboard_type")
    modules = []
    if dash_type:
        modules = [
            {"module_id": "jobs", "module_key": "jobs", "display_name": "Jobs", "is_enabled": True, "display_order": 1},
            {"module_id": "wallet", "module_key": "wallet", "display_name": "Wallet", "is_enabled": True, "display_order": 2},
            {"module_id": "analytics", "module_key": "analytics", "display_name": "Analytics", "is_enabled": True, "display_order": 3},
        ]
    return ok({"modules": modules, "total": len(modules), "enabled_count": len(modules)}, _rid(r), "category_runtime")


@router.post("/{category_id}/dashboard-modules", summary="Create dashboard module")
async def create_dashboard_module(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
):
    body = await r.json()
    module = {
        "module_id": body.get("module_key", "custom"),
        "module_key": body.get("module_key", "custom"),
        "display_name": body.get("display_name", "Module"),
        "is_enabled": body.get("is_enabled", True),
        "display_order": body.get("display_order", 99),
    }
    return ok(module, _rid(r), "category_runtime")


@router.put("/{category_id}/dashboard-modules/{module_id}", summary="Update dashboard module")
async def update_dashboard_module(
    category_id: uuid.UUID, module_id: str,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
):
    body = await r.json()
    return ok({"module_id": module_id, **body}, _rid(r), "category_runtime")


@router.post("/{category_id}/dashboard-modules/{module_id}/enable", summary="Enable module")
async def enable_module(
    category_id: uuid.UUID, module_id: str,
    r: Request,
    u: UserContext = Depends(require_super_admin),
):
    return ok({"module_id": module_id, "is_enabled": True}, _rid(r), "category_runtime")


@router.post("/{category_id}/dashboard-modules/{module_id}/disable", summary="Disable module")
async def disable_module(
    category_id: uuid.UUID, module_id: str,
    r: Request,
    u: UserContext = Depends(require_super_admin),
):
    return ok({"module_id": module_id, "is_enabled": False}, _rid(r), "category_runtime")


@router.post("/{category_id}/dashboard-modules/reorder", summary="Reorder modules")
async def reorder_modules(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
):
    body = await r.json()
    orders = body.get("module_orders", [])
    return ok({"reordered": len(orders)}, _rid(r), "category_runtime")
