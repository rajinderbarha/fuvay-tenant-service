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
from sqlalchemy import bindparam, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin, get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.admin_catalog.service import AdminCatalogService
from app.engines.admin_catalog.models import ServiceCategory
from app.exceptions import ServiceOSException
from app.schemas.base import ok

router = APIRouter(prefix="/v1/admin/categories", tags=["Category Runtime"])

HOME_SERVICES_RUNTIME_ENGINE_OVERLAYS: list[dict] = [
    {"engine_key": "auth_iam", "display_name": "Auth & IAM Engine", "is_required": True, "source": "runtime_identity", "runtime_reason": "Admin, tenant, staff and customer identity for every flow.", "dependencies": []},
    {"engine_key": "service_catalog", "display_name": "Service Catalog Engine", "is_required": True, "source": "vertical_registry", "runtime_reason": "Category, service group, master service, type/brand and customer catalog runtime.", "dependencies": ["auth_iam"]},
    {"engine_key": "booking", "display_name": "Booking Engine", "is_required": True, "source": "vertical_registry", "runtime_reason": "Native customer booking creation, quote decisions and booking lifecycle.", "dependencies": ["service_catalog", "job_dispatch"]},
    {"engine_key": "field_ops", "display_name": "Field Ops Engine", "is_required": True, "source": "vertical_registry", "runtime_reason": "Staff app job execution, status transitions, checklists and evidence.", "dependencies": ["booking"]},
    {"engine_key": "job_dispatch", "display_name": "Job Dispatch Engine", "is_required": True, "source": "vertical_registry", "runtime_reason": "Provider matching, technician assignment, availability and service-area routing.", "dependencies": ["service_catalog", "field_ops"]},
    {"engine_key": "finance", "display_name": "Finance Engine", "is_required": True, "source": "vertical_registry", "runtime_reason": "Home Services monetization, credit top-ups, invoices, refunds and financial operations.", "dependencies": ["booking", "payment"]},
    {"engine_key": "usage_credits", "display_name": "Usage Credit Engine", "is_required": True, "source": "runtime_finance", "runtime_reason": "Credit top-ups, ledger, completion/consultation deduction and provider-funded remedies.", "dependencies": ["finance", "payment"]},
    {"engine_key": "payment", "display_name": "Payment Engine", "is_required": True, "source": "vertical_registry", "runtime_reason": "Top-up payment records, refunds and reconciliation references.", "dependencies": ["finance"]},
    {"engine_key": "commission", "display_name": "Commission Engine", "is_required": True, "source": "runtime_finance", "runtime_reason": "Customer-side and provider-side percentage/fixed charge calculation.", "dependencies": ["finance", "service_catalog"]},
    {"engine_key": "customer_svc_credit", "display_name": "Customer Service Credit Engine", "is_required": True, "source": "runtime_support", "runtime_reason": "Warranty/refund compensation as customer service points funded from provider balances.", "dependencies": ["finance", "complaint_dispute"]},
    {"engine_key": "complaint_dispute", "display_name": "Complaint & Dispute Engine", "is_required": True, "source": "vertical_registry", "runtime_reason": "Customer complaints, warranty escalations, refund review and provider liability.", "dependencies": ["booking", "customer_svc_credit"]},
    {"engine_key": "review_rating", "display_name": "Review & Rating Engine", "is_required": False, "source": "vertical_registry", "runtime_reason": "Post-job ratings, provider quality signal and admin review moderation.", "dependencies": ["booking"]},
    {"engine_key": "notification", "display_name": "Notification Engine", "is_required": True, "source": "vertical_registry", "runtime_reason": "Booking, job, support, finance and admin decision notifications.", "dependencies": ["auth_iam"]},
    {"engine_key": "media_vault", "display_name": "Media Vault Engine", "is_required": False, "source": "vertical_registry", "runtime_reason": "Documents, job evidence, profile media and support attachments.", "dependencies": ["auth_iam"]},
    {"engine_key": "chat", "display_name": "Chat Engine", "is_required": False, "source": "vertical_registry", "runtime_reason": "Customer/provider/staff support and job conversations where enabled.", "dependencies": ["auth_iam"]},
    {"engine_key": "pricing", "display_name": "Pricing Engine", "is_required": True, "source": "runtime_pricing", "runtime_reason": "Provider price setup, customer price preview, visit fee and job-type pricing rules.", "dependencies": ["service_catalog", "commission"]},
    {"engine_key": "compliance", "display_name": "Compliance Engine", "is_required": True, "source": "runtime_governance", "runtime_reason": "Provider onboarding review, document checks and admin approval policy.", "dependencies": ["auth_iam", "media_vault"]},
    {"engine_key": "audit", "display_name": "Audit Engine", "is_required": True, "source": "runtime_governance", "runtime_reason": "Admin changes, finance decisions, setup approvals and support actions are audit-backed.", "dependencies": ["auth_iam"]},
    {"engine_key": "security", "display_name": "Security Engine", "is_required": True, "source": "runtime_governance", "runtime_reason": "Permission checks and safe access across admin, tenant and app APIs.", "dependencies": ["auth_iam"]},
    {"engine_key": "settings_config", "display_name": "Settings & Config Engine", "is_required": True, "source": "runtime_configuration", "runtime_reason": "Published configuration, policy switches and app/runtime flags.", "dependencies": ["audit"]},
    {"engine_key": "analytics", "display_name": "Analytics Engine", "is_required": False, "source": "runtime_observability", "runtime_reason": "Provider, customer, booking, finance and service quality dashboards.", "dependencies": ["booking", "finance"]},
    {"engine_key": "trust_quality_engine", "display_name": "Trust & Quality Engine", "is_required": False, "source": "runtime_quality", "runtime_reason": "Provider trust, health, badges and quality controls.", "dependencies": ["review_rating", "complaint_dispute"]},
    {"engine_key": "health_engine", "display_name": "Health Engine", "is_required": False, "source": "runtime_observability", "runtime_reason": "Operational health/readiness signal for vertical runtime surfaces.", "dependencies": ["analytics"]},
]

HOME_SERVICES_RUNTIME_MODULE_OVERLAYS: list[dict] = [
    {"module_key": "hs_providers", "module_name": "Providers", "description": "Provider directory, onboarding state, activation and tenant health.", "dashboard_area": "business", "engine_key": "service_catalog", "route_path": "/admin/home-services/providers", "is_required": True, "display_order": 100},
    {"module_key": "hs_bookings_jobs", "module_name": "Bookings & Jobs", "description": "Enterprise booking/job command center with assignment, status and finance context.", "dashboard_area": "operations", "engine_key": "booking", "route_path": "/admin/home-services/bookings-jobs", "is_required": True, "display_order": 110},
    {"module_key": "hs_customers", "module_name": "Customers", "description": "Home Services customer directory, repeat behavior and payment reliability.", "dashboard_area": "operations", "engine_key": "booking", "route_path": "/admin/home-services/customers", "is_required": False, "display_order": 120},
    {"module_key": "hs_staff", "module_name": "Staff & Technicians", "description": "Cross-provider staff visibility and technician operational controls.", "dashboard_area": "operations", "engine_key": "field_ops", "route_path": "/admin/home-services/staff", "is_required": False, "display_order": 130},
    {"module_key": "hs_finance", "module_name": "Home Services Finance", "description": "Single Home Services finance authority: monetization, credits, top-ups, invoices, refunds and warranty funding.", "dashboard_area": "finance", "engine_key": "finance", "route_path": "/admin/home-services/finance", "is_required": True, "display_order": 150},
    {"module_key": "hs_provider_matching", "module_name": "Provider Matching", "description": "Matching rules, ranking logic and provider eligibility controls.", "dashboard_area": "operations", "engine_key": "job_dispatch", "route_path": "/admin/home-services/provider-matching", "is_required": True, "display_order": 170},
    {"module_key": "hs_matching_diagnostics", "module_name": "Matching Diagnostics", "description": "Explain why a provider was or was not eligible for a customer request.", "dashboard_area": "operations", "engine_key": "job_dispatch", "route_path": "/admin/home-services/matching-diagnostics", "is_required": False, "display_order": 180},
    {"module_key": "hs_service_area_requests", "module_name": "Service Area Requests", "description": "Provider coverage expansion requests and admin approval workflow.", "dashboard_area": "coverage", "engine_key": "job_dispatch", "route_path": "/admin/service-area-requests", "is_required": False, "display_order": 190},
    {"module_key": "hs_bookability", "module_name": "Bookability & Availability", "description": "Provider availability, capacity and bookability diagnostics.", "dashboard_area": "coverage", "engine_key": "job_dispatch", "route_path": "/admin/bookability/providers", "is_required": False, "display_order": 200},
    {"module_key": "hs_settings", "module_name": "Home Services Settings", "description": "Runtime settings and policy switches for the Home Services vertical.", "dashboard_area": "admin", "engine_key": "settings_config", "route_path": "/admin/home-services/settings", "is_required": False, "display_order": 210},
    {"module_key": "hs_reviews", "module_name": "Reviews & Quality", "description": "Ratings, review moderation and quality feedback signals.", "dashboard_area": "quality", "engine_key": "review_rating", "route_path": "/admin/reviews", "is_required": False, "display_order": 220},
]

HOME_SERVICES_REGISTRY_MODULE_ENGINE_MAP: dict[str, str] = {
    "categories": "service_catalog",
    "service_groups": "service_catalog",
    "master_services": "service_catalog",
    "types_brands": "service_catalog",
    "checklist_templates": "field_ops",
    "hs_service_catalog": "service_catalog",
}


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
    vertical_key = cat.get("vertical_type")

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

    # Home Services no longer uses category-level service_pricing_rules as the
    # authority. Provider-owned service pricing lives in Catalog Workspace and
    # platform/customer/provider charges live in Home Services Finance >
    # Monetization. Keeping the old category pricing rule here made the Home
    # Services category appear broken even after the real finance/catalog setup
    # was complete.
    uses_category_pricing_rules = vertical_key not in {"home_services"}
    if uses_category_pricing_rules and cat.get("pricing_supported") and counts.get("pricing_rules", 0) == 0:
        items.append({"key": "pricing_rules", "status": "missing", "message": "No active pricing rule configured for this category."})

    uses_service_packages = vertical_key not in {"home_services"}
    if uses_service_packages and cat.get("tenant_selectable") and counts.get("packages", 0) == 0:
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

    sql = text("""
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
            WHERE deleted_at IS NULL AND category_id IN :category_ids
            GROUP BY category_id
        ) sg ON sg.category_id = sc.id
        LEFT JOIN (
            SELECT category_id, COUNT(*) AS cnt
            FROM master_services
            WHERE is_active = TRUE AND deleted_at IS NULL AND category_id IN :category_ids
            GROUP BY category_id
        ) ms ON ms.category_id = sc.id
        LEFT JOIN (
            SELECT category_id, COUNT(*) AS cnt
            FROM service_pricing_rules
            WHERE is_active = TRUE AND deleted_at IS NULL AND category_id IN :category_ids
            GROUP BY category_id
        ) pr ON pr.category_id = sc.id
        LEFT JOIN (
            SELECT category_id, COUNT(*) AS cnt
            FROM brands
            WHERE is_active = TRUE AND deleted_at IS NULL AND category_id IN :category_ids
            GROUP BY category_id
        ) br ON br.category_id = sc.id
        LEFT JOIN (
            SELECT sc2.id AS category_id, COUNT(DISTINCT sp.id) AS cnt
            FROM service_categories sc2
            JOIN service_packages sp ON sp.vertical_type = sc2.vertical_type
            WHERE sp.is_active = TRUE AND sp.deleted_at IS NULL
              AND sc2.id IN :category_ids
            GROUP BY sc2.id
        ) pkg ON pkg.category_id = sc.id
        LEFT JOIN (
            SELECT ts2.category_id, COUNT(DISTINCT ts2.tenant_id) AS cnt
            FROM tenant_services ts2
            WHERE ts2.is_active = TRUE AND ts2.deleted_at IS NULL
              AND ts2.category_id IN :category_ids
            GROUP BY ts2.category_id
        ) ts ON ts.category_id = sc.id
        WHERE sc.id IN :category_ids
    """).bindparams(bindparam("category_ids", expanding=True))
    ids = [uuid.UUID(str(cid)) for cid in category_ids]
    rows = (await db.execute(sql, {"category_ids": ids})).mappings().all()
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


async def _vertical_engine_mappings(db: AsyncSession, vertical_key: str | None, primary_key: str | None) -> list[dict]:
    """Resolve engines from the vertical registry plus proven runtime usage.

    The vertical registry is the configuration authority.  For Home Services,
    however, a category runtime view must also show engines that are consumed by
    live routes/services but are not represented as ``vertical_engine_mappings``
    rows (for example usage credits, compliance, audit, settings, analytics).
    Otherwise the admin page under-reports the real dependency surface.
    """
    primary_aliases = {primary_key} if primary_key else set()
    if primary_key == "booking_engine":
        primary_aliases.add("booking")
    elif primary_key == "appointment_engine":
        primary_aliases.add("appointment")
    elif primary_key == "lead_engine":
        primary_aliases.add("leads")
    rows = []
    if vertical_key:
        rows = (await db.execute(text("""
            SELECT
                vem.engine_key,
                COALESCE(pe.display_name, vem.engine_key) AS display_name,
                pe.lifecycle_status,
                vem.is_required,
                vem.sort_order
            FROM verticals v
            JOIN vertical_engine_mappings vem ON vem.vertical_id = v.id
            LEFT JOIN platform_engines pe ON pe.engine_key = vem.engine_key
            WHERE v.key = :vertical_key
            ORDER BY vem.sort_order, vem.engine_key
        """), {"vertical_key": vertical_key})).mappings().all()
    engines = [
        {
            "engine_id": row["engine_key"],
            "engine_key": row["engine_key"],
            "name": row["display_name"] or str(row["engine_key"]).replace("_", " ").title(),
            "display_name": row["display_name"] or str(row["engine_key"]).replace("_", " ").title(),
            "is_primary": row["engine_key"] in primary_aliases or (not primary_key and idx == 0),
            "is_required": bool(row["is_required"]),
            "is_optional": not bool(row["is_required"]),
            "is_enabled": True,
            "display_order": int(row["sort_order"] or idx),
            "health_status": "configured" if (row["lifecycle_status"] or "active") in ("active", "core", "locked") else "attention",
            "status": row["lifecycle_status"] or "available",
            "config": {},
            "dependencies": [],
            "source": "vertical_registry",
            "runtime_reason": "Mapped in vertical_engine_mappings.",
        }
        for idx, row in enumerate(rows)
    ]

    if vertical_key == "home_services":
        by_key = {e["engine_key"]: e for e in engines}
        next_order = (max((int(e["display_order"]) for e in engines), default=-1) + 1)
        for overlay in HOME_SERVICES_RUNTIME_ENGINE_OVERLAYS:
            key = overlay["engine_key"]
            if key in by_key:
                existing = by_key[key]
                existing["is_required"] = bool(existing.get("is_required")) or bool(overlay.get("is_required"))
                existing["is_optional"] = not existing["is_required"]
                existing["display_name"] = overlay.get("display_name") or existing.get("display_name")
                existing["name"] = existing["display_name"]
                existing["source"] = "vertical_registry+runtime_usage"
                existing["runtime_reason"] = overlay.get("runtime_reason")
                existing["dependencies"] = sorted(set(existing.get("dependencies") or []) | set(overlay.get("dependencies") or []))
                continue
            engines.append({
                "engine_id": key,
                "engine_key": key,
                "name": overlay.get("display_name") or key.replace("_", " ").title(),
                "display_name": overlay.get("display_name") or key.replace("_", " ").title(),
                "is_primary": key in primary_aliases,
                "is_required": bool(overlay.get("is_required")),
                "is_optional": not bool(overlay.get("is_required")),
                "is_enabled": True,
                "display_order": next_order,
                "health_status": "runtime_used",
                "status": "runtime_used",
                "config": {},
                "dependencies": overlay.get("dependencies") or [],
                "source": overlay.get("source") or "runtime_usage",
                "runtime_reason": overlay.get("runtime_reason"),
            })
            next_order += 1

    if not engines and primary_key:
        engines.append({
            "engine_id": primary_key,
            "engine_key": primary_key,
            "name": primary_key.replace("_", " ").title(),
            "display_name": primary_key.replace("_", " ").title(),
            "is_primary": True,
            "is_required": True,
            "is_optional": False,
            "is_enabled": True,
            "display_order": 0,
            "health_status": "configured",
            "status": "available",
            "config": {},
            "dependencies": [],
            "source": "category_primary",
            "runtime_reason": "Configured as the category primary engine.",
        })
    if engines and not any(e["is_primary"] for e in engines):
        preferred = next((e for e in engines if e["engine_key"] in primary_aliases), engines[0])
        preferred["is_primary"] = True
    return sorted(engines, key=lambda e: (int(e.get("display_order") or 0), str(e.get("engine_key") or "")))


async def _vertical_dashboard_modules(db: AsyncSession, category_id: uuid.UUID, vertical_key: str | None) -> list[dict]:
    """Resolve category modules from the registry plus live Home Services routes."""
    if not vertical_key:
        return []
    rows = (await db.execute(text("""
        SELECT
            cmd.id AS module_id,
            cmd.key AS module_key,
            COALESCE(vcm.custom_label, cmd.label) AS module_name,
            cmd.description,
            cmd.icon,
            cmd.admin_path AS route_path,
            cmd.module_group AS dashboard_area,
            cmd.is_universal,
            cmd.navigation_status,
            cmd.navigation_status_reason,
            vcm.is_enabled,
            vcm.is_required,
            vcm.sort_order
        FROM verticals v
        JOIN vertical_catalog_modules vcm ON vcm.vertical_id = v.id
        JOIN catalog_module_definitions cmd ON cmd.id = vcm.module_id
        WHERE v.key = :vertical_key
          AND cmd.navigation_status = 'available'
        ORDER BY vcm.sort_order, cmd.sort_order, cmd.label
    """), {"vertical_key": vertical_key})).mappings().all()
    retired_keys: set[str] = set()
    if vertical_key == "home_services":
        retired_rows = (await db.execute(text("""
            SELECT cmd.key AS module_key
            FROM verticals v
            JOIN vertical_catalog_modules vcm ON vcm.vertical_id = v.id
            JOIN catalog_module_definitions cmd ON cmd.id = vcm.module_id
            WHERE v.key = :vertical_key
              AND cmd.navigation_status <> 'available'
        """), {"vertical_key": vertical_key})).mappings().all()
        retired_keys = {str(row["module_key"]) for row in retired_rows}
    modules = [
        {
            "module_id": str(row["module_id"]),
            "category_id": str(category_id),
            "module_key": row["module_key"],
            "module_name": row["module_name"],
            "display_name": row["module_name"],
            "module_type": row["dashboard_area"] or "admin",
            "dashboard_area": row["dashboard_area"],
            "engine_key": HOME_SERVICES_REGISTRY_MODULE_ENGINE_MAP.get(str(row["module_key"])) if vertical_key == "home_services" else None,
            "api_endpoint": None,
            "route_path": row["route_path"],
            "required_permission": "super_admin",
            "frontend_component_key": None,
            "description": row["description"],
            "icon": row["icon"],
            "is_enabled": bool(row["is_enabled"]),
            "is_required": bool(row["is_required"]),
            "display_order": int(row["sort_order"] or idx),
            "config": {},
            "navigation_status": row["navigation_status"],
            "navigation_status_reason": row["navigation_status_reason"],
            "is_universal": bool(row["is_universal"]),
            "source": "vertical_registry",
        }
        for idx, row in enumerate(rows)
    ]
    if vertical_key == "home_services":
        by_key = {m["module_key"]: m for m in modules}
        for overlay in HOME_SERVICES_RUNTIME_MODULE_OVERLAYS:
            key = overlay["module_key"]
            # If the vertical registry explicitly retired a module key, do not
            # resurrect it just because an old page route still exists.  This
            # keeps the category Modules tab aligned to certified/current
            # Home Services scope instead of stale navigation history.
            if key in retired_keys:
                continue
            if key in by_key:
                existing = by_key[key]
                existing["source"] = "vertical_registry+runtime_route"
                existing["engine_key"] = existing.get("engine_key") or overlay.get("engine_key")
                existing["description"] = existing.get("description") or overlay.get("description")
                existing["route_path"] = existing.get("route_path") or overlay.get("route_path")
                existing["is_required"] = bool(existing.get("is_required")) or bool(overlay.get("is_required"))
                continue
            modules.append({
                "module_id": key,
                "category_id": str(category_id),
                "module_key": key,
                "module_name": overlay["module_name"],
                "display_name": overlay["module_name"],
                "module_type": overlay.get("dashboard_area") or "admin",
                "dashboard_area": overlay.get("dashboard_area"),
                "engine_key": overlay.get("engine_key"),
                "api_endpoint": None,
                "route_path": overlay.get("route_path"),
                "required_permission": "super_admin",
                "frontend_component_key": None,
                "description": overlay.get("description"),
                "icon": None,
                "is_enabled": True,
                "is_required": bool(overlay.get("is_required")),
                "display_order": int(overlay.get("display_order") or 999),
                "config": {},
                "navigation_status": "available",
                "navigation_status_reason": None,
                "is_universal": False,
                "source": "runtime_route",
            })
    return sorted(modules, key=lambda m: (int(m.get("display_order") or 0), str(m.get("module_name") or m.get("module_key") or "")))


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
    # This endpoint previously loaded every category, filtered/sorted it in
    # Python, fetched relationship counts for every match, and only then
    # sliced a page. The UI looked paginated but memory and query work grew
    # with the entire catalog. Keep the response contract while making the
    # database own filtering, counting, sorting, and pagination.
    conditions = []
    if q and q.strip():
        needle = f"%{q.strip()}%"
        conditions.append(or_(ServiceCategory.name.ilike(needle), ServiceCategory.slug.ilike(needle),
                              ServiceCategory.description.ilike(needle)))
    if vertical_type:
        conditions.append(ServiceCategory.vertical_type == vertical_type)
    if finance_model:
        conditions.append(ServiceCategory.finance_model == finance_model)
    if customer_flow_type:
        conditions.append(ServiceCategory.customer_flow_type == customer_flow_type)
    if category_type:
        conditions.append(ServiceCategory.category_type == category_type)
    if status == "active":
        conditions.append(ServiceCategory.is_active.is_(True))
    elif status == "inactive":
        conditions.append(ServiceCategory.is_active.is_(False))
    elif isinstance(is_active, bool):
        conditions.append(ServiceCategory.is_active == is_active)
    if customer_visible is not None:
        conditions.append(ServiceCategory.is_customer_visible == customer_visible)
    if tenant_selectable is not None:
        conditions.append(ServiceCategory.tenant_selectable == tenant_selectable)
    if pricing_supported is not None:
        conditions.append(ServiceCategory.pricing_supported == pricing_supported)

    # Readiness is a derived state. Express its precedence rules in SQL so a
    # readiness filter is still applied before COUNT/LIMIT (never to one page).
    has_services = "(EXISTS (SELECT 1 FROM master_services ms WHERE ms.category_id = service_categories.id AND ms.is_active AND ms.deleted_at IS NULL) OR EXISTS (SELECT 1 FROM service_groups sg WHERE sg.category_id = service_categories.id AND sg.deleted_at IS NULL))"
    has_pricing = "EXISTS (SELECT 1 FROM service_pricing_rules pr WHERE pr.category_id = service_categories.id AND pr.is_active AND pr.deleted_at IS NULL)"
    # Package readiness means an administratively configured, active package
    # exists for the category's vertical type. Tenant assignments are usage
    # records and intentionally do not own category identity.
    has_packages = "EXISTS (SELECT 1 FROM service_packages sp WHERE sp.vertical_type = service_categories.vertical_type AND sp.is_active AND sp.deleted_at IS NULL)"
    package_ready = f"(service_categories.vertical_type = 'home_services' OR NOT service_categories.tenant_selectable OR {has_packages})"
    pricing_ready = f"(service_categories.vertical_type = 'home_services' OR NOT service_categories.pricing_supported OR {has_pricing})"
    readiness_filters = {
        "inactive": "NOT service_categories.is_active",
        "missing_services": f"service_categories.is_active AND NOT {has_services}",
        "missing_pricing": f"service_categories.is_active AND {has_services} AND service_categories.vertical_type <> 'home_services' AND service_categories.pricing_supported AND NOT {has_pricing}",
        "missing_flow_config": f"service_categories.is_active AND {has_services} AND {pricing_ready} AND service_categories.customer_flow_type IS NULL",
        "missing_package": f"service_categories.is_active AND {has_services} AND {pricing_ready} AND service_categories.vertical_type <> 'home_services' AND service_categories.customer_flow_type IS NOT NULL AND service_categories.tenant_selectable AND NOT {has_packages}",
        "ready": f"service_categories.is_active AND {has_services} AND {pricing_ready} AND service_categories.customer_flow_type IS NOT NULL AND service_categories.finance_model IS NOT NULL AND {package_ready}",
        "incomplete": f"service_categories.is_active AND {has_services} AND {pricing_ready} AND service_categories.customer_flow_type IS NOT NULL AND service_categories.finance_model IS NULL AND {package_ready}",
    }
    if readiness_status in readiness_filters:
        conditions.append(text(readiness_filters[readiness_status]))

    total = int((await db.execute(select(func.count()).select_from(ServiceCategory).where(*conditions))).scalar_one())
    sort_columns = {
        "display_order": ServiceCategory.display_order, "name": ServiceCategory.name,
        "vertical_type": ServiceCategory.vertical_type, "finance_model": ServiceCategory.finance_model,
        "updated_at": ServiceCategory.updated_at,
    }
    sort_column = sort_columns.get(sort_by, ServiceCategory.display_order)
    ordering = sort_column.desc().nullslast() if sort_dir == "desc" else sort_column.asc().nullsfirst()
    rows = (await db.execute(
        select(ServiceCategory).where(*conditions).order_by(ordering, ServiceCategory.id.asc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    cats = [svc._cat_dict(c) for c in rows]
    counts_map = await _linked_counts(db, [c["category_id"] for c in cats])
    page_items = []
    for cat in cats:
        linked = counts_map.get(cat["category_id"], {"service_groups": 0, "services": 0, "pricing_rules": 0, "brands": 0, "packages": 0, "providers": 0})
        item = {**cat, "linked_counts": linked}
        item.update(_compute_readiness(item))
        page_items.append(item)

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

    # The detail console consumes a composite runtime view, not the flat
    # category record returned by GET /{id}. Resolve engines/modules from the
    # canonical vertical registry so this page mirrors the actual admin menu
    # and runtime capability contract instead of stale category-local stubs.
    engines = await _vertical_engine_mappings(db, data.get("vertical_type"), data.get("primary_engine_key"))
    modules = await _vertical_dashboard_modules(db, category_id, data.get("vertical_type"))
    tenant_row = (await db.execute(text("""
        SELECT COUNT(DISTINCT tenant_id) AS total,
               COUNT(DISTINCT tenant_id) FILTER (WHERE is_active = TRUE AND deleted_at IS NULL) AS active
        FROM tenant_services WHERE category_id = :category_id
    """), {"category_id": category_id})).mappings().one()
    return ok({
        "category": data,
        "running_engines": engines,
        "engine_summary": {"total": len(engines),
                           "required": sum(1 for e in engines if e.get("is_required")),
                           "optional": sum(1 for e in engines if not e.get("is_required")),
                           "primary": next((e for e in engines if e.get("is_primary")), None)},
        "dashboard_modules": modules,
        "tenant_count": int(tenant_row["total"] or 0),
        "active_tenant_count": int(tenant_row["active"] or 0),
    }, _rid(r), "category_runtime")


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
    db: AsyncSession = Depends(get_db),
    svc: AdminCatalogService = Depends(_svc),
):
    cat = await svc.get_category(category_id)
    engines = await _vertical_engine_mappings(db, cat.get("vertical_type"), cat.get("primary_engine_key"))
    return ok({
        "engines": engines,
        "total": len(engines),
        "required_count": sum(1 for e in engines if e.get("is_required")),
        "optional_count": sum(1 for e in engines if not e.get("is_required")),
        "primary_engine": next((e for e in engines if e.get("is_primary")), None),
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
    db: AsyncSession = Depends(get_db),
    svc: AdminCatalogService = Depends(_svc),
):
    cat = await svc.get_category(category_id)
    modules = await _vertical_dashboard_modules(db, category_id, cat.get("vertical_type"))
    return ok({
        "modules": modules,
        "total": len(modules),
        "enabled_count": sum(1 for m in modules if m.get("is_enabled")),
        "required_count": sum(1 for m in modules if m.get("is_required")),
    }, _rid(r), "category_runtime")


@router.post("/{category_id}/dashboard-modules", summary="Create dashboard module")
async def create_dashboard_module(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
):
    raise ServiceOSException(
        "CATEGORY_MODULES_VERTICAL_OWNED",
        "Category dashboard modules are owned by the vertical module registry. Manage them from the vertical Modules tab.",
        status_code=409,
    )


@router.put("/{category_id}/dashboard-modules/{module_id}", summary="Update dashboard module")
async def update_dashboard_module(
    category_id: uuid.UUID, module_id: str,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: AdminCatalogService = Depends(_svc),
):
    raise ServiceOSException(
        "CATEGORY_MODULES_VERTICAL_OWNED",
        "Category dashboard modules are owned by the vertical module registry. Manage them from the vertical Modules tab.",
        status_code=409,
    )


@router.post("/{category_id}/dashboard-modules/{module_id}/enable", summary="Enable module")
async def enable_module(
    category_id: uuid.UUID, module_id: str,
    r: Request,
    u: UserContext = Depends(require_super_admin),
):
    raise ServiceOSException(
        "CATEGORY_MODULES_VERTICAL_OWNED",
        "Use /v1/admin/verticals/{vertical_key}/modules/{module_key}/enable so module changes stay vertical-scoped.",
        status_code=409,
    )


@router.post("/{category_id}/dashboard-modules/{module_id}/disable", summary="Disable module")
async def disable_module(
    category_id: uuid.UUID, module_id: str,
    r: Request,
    u: UserContext = Depends(require_super_admin),
):
    raise ServiceOSException(
        "CATEGORY_MODULES_VERTICAL_OWNED",
        "Use /v1/admin/verticals/{vertical_key}/modules/{module_key}/disable so module changes stay vertical-scoped.",
        status_code=409,
    )


@router.post("/{category_id}/dashboard-modules/reorder", summary="Reorder modules")
async def reorder_modules(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
):
    raise ServiceOSException(
        "CATEGORY_MODULES_VERTICAL_OWNED",
        "Module ordering is owned by the vertical module registry.",
        status_code=409,
    )
