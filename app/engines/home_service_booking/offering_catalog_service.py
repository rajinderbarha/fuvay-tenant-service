"""Backend-first Booking Assistant — shared, customer-safe offering
catalog resolution.

Extracted from `BackendToolExecutor._tool_get_category_offerings`
(app/engines/ai_conversation/backend_tools.py) so the EXACT SAME
zipcode-aware "is this offering genuinely bookable here, by a real
published tenant, with real question-flow content" query backs both:
  - the DeepSeek tool (unstructured chat still uses it for now), and
  - the new customer-facing assistant-bootstrap endpoint (backend-first,
    no DeepSeek call at all).

Never invents an offering, never returns a different tenant's coverage
gap as if it were serviceable, never includes an offering published by a
tenant whose actual service area doesn't cover the given zipcode (the
"AC Service" / Ludhiana-tenant leak this whole check exists to prevent).
"""
from __future__ import annotations
import uuid

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.provider_portal.bookability_query import latest_provider_bookable


logger = structlog.get_logger("home_service_booking.ready_catalog")


_READY_CATALOG_CACHE_PREFIX = "home_services.booking_ready_catalog"


def _request_cache(db: AsyncSession) -> dict:
    """A request/session-local cache; never survives into another customer request."""
    info = getattr(db, "info", None)
    return info if isinstance(info, dict) else {}


async def _booking_candidate_pairs(db: AsyncSession, zipcode: str):
    """Exact service/job-type pairs that have a published provider in the ZIP.

    This is deliberately only the inexpensive candidate query. The canonical
    matcher below remains the authority for health, trust, credits, skills,
    pricing, hours and live slot capacity.
    """
    from app.engines.admin_catalog.models import (
        MasterService, ServiceIssueMapping, TenantService,
    )
    from app.engines.serviceability.models import (
        TenantServiceArea, TenantServiceAreaService,
    )

    return (await db.execute(
        select(
            MasterService.category_id,
            TenantService.master_service_id,
            ServiceIssueMapping.job_type_id,
        )
        .join(TenantService, TenantService.master_service_id == MasterService.id)
        .join(
            TenantServiceArea,
            TenantServiceArea.tenant_id == TenantService.tenant_id,
        )
        .join(
            TenantServiceAreaService,
            and_(
                TenantServiceAreaService.tenant_service_area_id == TenantServiceArea.id,
                TenantServiceAreaService.tenant_id == TenantService.tenant_id,
                TenantServiceAreaService.service_id == TenantService.master_service_id,
            ),
        )
        .join(
            ServiceIssueMapping,
            ServiceIssueMapping.master_service_id == MasterService.id,
        )
        .where(
            TenantServiceArea.zipcode == str(zipcode),
            TenantServiceArea.is_active.is_(True),
            TenantServiceAreaService.is_available.is_(True),
            TenantServiceAreaService.status == "ACTIVE",
            TenantService.is_enabled.is_(True),
            TenantService.is_active.is_(True),
            TenantService.setup_status == "published",
            MasterService.is_active.is_(True),
            ServiceIssueMapping.status == "active",
            ServiceIssueMapping.deleted_at.is_(None),
            ServiceIssueMapping.customer_visible.is_(True),
        )
        .distinct()
        .order_by(
            MasterService.category_id,
            TenantService.master_service_id,
            ServiceIssueMapping.job_type_id,
        )
    )).all()


async def booking_ready_service_matches(
    db: AsyncSession, zipcode: str,
) -> dict[uuid.UUID, dict]:
    """Services with at least one provider the real matcher can book now.

    The postcode is checked before the customer chooses a service or shares a
    street address. A service enters the catalog only when at least one
    provider passes the same production gates used for final allocation and
    has real future slot capacity for an exact problem/job type.
    """
    normalized_zip = str(zipcode or "").strip()
    if not normalized_zip:
        return {}

    cache = _request_cache(db)
    cache_key = f"{_READY_CATALOG_CACHE_PREFIX}:{normalized_zip}"
    if cache_key in cache:
        return cache[cache_key]

    pairs = await _booking_candidate_pairs(db, normalized_zip)
    if not pairs:
        cache[cache_key] = {}
        return {}

    from app.engines.home_service_booking.matching_engine import select_best_provider

    # ZIP is authoritative. City is presentation/fallback data only, but the
    # matcher accepts it as a required argument for older non-ZIP callers.
    city = ""
    try:
        from app.engines.serviceability.models import TenantServiceArea
        city = str((await db.execute(
            select(TenantServiceArea.city)
            .where(
                TenantServiceArea.zipcode == normalized_zip,
                TenantServiceArea.is_active.is_(True),
            )
            .order_by(TenantServiceArea.city)
            .limit(1)
        )).scalar_one_or_none() or "")
    except Exception:
        # Matching still uses the exact ZIP; an absent display city must not
        # widen or invalidate coverage.
        city = ""

    ready: dict[uuid.UUID, dict] = {}
    for category_id, service_id, job_type_id in pairs:
        try:
            async with db.begin_nested():
                match = await select_best_provider(
                    db,
                    category_id=category_id,
                    offering_id=service_id,
                    city=city,
                    zipcode=normalized_zip,
                    job_type_id=job_type_id,
                )
        except Exception as exc:  # one malformed service must not hide the rest
            logger.warning(
                "booking_ready_catalog.match_failed",
                zipcode=normalized_zip,
                service_id=str(service_id),
                job_type_id=str(job_type_id) if job_type_id else None,
                error=str(exc),
            )
            continue
        if not match or match.get("signals") is None:
            continue

        current = ready.setdefault(service_id, {
            "category_id": category_id,
            "job_type_ids": set(),
            "best_score": None,
            "earliest_slot": None,
        })
        current["job_type_ids"].add(job_type_id)
        score = match.get("score")
        if current["best_score"] is None or (score is not None and score > current["best_score"]):
            current["best_score"] = score
        slot = match.get("earliest_slot")
        if slot and (
            current["earliest_slot"] is None
            or str(slot.get("starts_at") or "")
            < str(current["earliest_slot"].get("starts_at") or "")
        ):
            current["earliest_slot"] = slot

    logger.info(
        "booking_ready_catalog.resolved",
        zipcode=normalized_zip,
        candidate_service_job_types=len(pairs),
        ready_services=len(ready),
        ready_job_types=sum(len(item["job_type_ids"]) for item in ready.values()),
    )
    cache[cache_key] = ready
    return ready


async def _resolve_category(db: AsyncSession, category_slug: str):
    from app.engines.admin_catalog.models import ServiceCategory

    normalized = category_slug.lower().strip()
    cat_q = select(ServiceCategory).where(
        ServiceCategory.is_active == True,  # noqa: E712
        ServiceCategory.is_customer_visible == True,  # noqa: E712
    )
    cat = (await db.execute(cat_q.where(ServiceCategory.slug == normalized))).scalars().first()
    if not cat:
        cat = (await db.execute(
            cat_q.where(ServiceCategory.name.ilike(normalized.replace("-", " ")))
        )).scalars().first()
    return cat


async def _resolve_service_group(
    db: AsyncSession, category_id: uuid.UUID, service_group_slug: str,
):
    """Resolve an active group inside the already-resolved category.

    A group slug is a navigation hint from the native app, not authority.
    Resolving it here prevents a crafted request from using a group that
    belongs to another category (or a retired group) to widen the catalog.
    """
    from app.engines.admin_catalog.models import ServiceGroup

    normalized = service_group_slug.lower().strip()
    return (await db.execute(
        select(ServiceGroup).where(
            ServiceGroup.category_id == category_id,
            ServiceGroup.slug == normalized,
            ServiceGroup.status == "active",
            ServiceGroup.deleted_at.is_(None),
        )
    )).scalars().first()


def _publisher_filter(zipcode: str | None):
    """A MasterService.id filter expression: real, published, enabled
    tenant offering -- and, when `zipcode` is given, actually covered by a
    published tenant's real service area at that exact zipcode. Shared by
    both offering- and issue-level catalog queries. ZIP-aware callers then
    intersect this coverage set with ``booking_ready_service_matches`` so a
    stale tenant-wide technician blocker cannot hide unrelated staffed
    services, while every returned service still passes exact live matching.
    """
    from app.engines.admin_catalog.models import MasterService, TenantService
    from app.engines.serviceability.models import TenantServiceArea, TenantServiceAreaService

    if not zipcode:
        return MasterService.id.in_(
            select(TenantService.master_service_id).where(
                TenantService.is_enabled == True,  # noqa: E712
                TenantService.is_active == True,  # noqa: E712
                TenantService.setup_status == "published",
                latest_provider_bookable(TenantService.tenant_id),
            )
        )
    return MasterService.id.in_(
        select(TenantServiceAreaService.service_id)
        .join(TenantServiceArea, TenantServiceArea.id == TenantServiceAreaService.tenant_service_area_id)
        .where(
            TenantServiceArea.zipcode == zipcode,
            TenantServiceArea.is_active == True,  # noqa: E712
            TenantServiceArea.tenant_id == TenantServiceAreaService.tenant_id,
            TenantServiceAreaService.is_available == True,  # noqa: E712
            TenantServiceAreaService.status == "ACTIVE",
            TenantServiceAreaService.tenant_id.in_(
                select(TenantService.tenant_id).where(
                    TenantService.master_service_id == TenantServiceAreaService.service_id,
                    TenantService.is_enabled == True,  # noqa: E712
                    TenantService.is_active == True,  # noqa: E712
                    TenantService.setup_status == "published",
                )
            ),
        )
    )


async def list_serviceable_offerings(
    db: AsyncSession, category_slug: str, zipcode: str | None,
) -> dict:
    """Returns {"category": ..., "category_slug": ..., "offerings": [...]}
    or {"offerings": [], "note": ...} if the category doesn't resolve.
    Every offering returned is: active, published by at least one enabled
    tenant, has real ServiceIssueMapping content, and -- when `zipcode` is
    given -- is actually covered by a published tenant's real service area
    at that exact zipcode."""
    from app.engines.admin_catalog.models import MasterService, ServiceIssueMapping

    cat = await _resolve_category(db, category_slug)
    if not cat:
        return {"offerings": [], "note": f"Category '{category_slug}' not found."}

    rows = (await db.execute(
        select(MasterService)
        .where(
            MasterService.category_id == cat.id,
            MasterService.is_active == True,  # noqa: E712
            _publisher_filter(zipcode),
            MasterService.id.in_(
                select(ServiceIssueMapping.master_service_id).where(ServiceIssueMapping.status == "active")
            ),
        )
        .order_by(MasterService.display_order, MasterService.service_name)
    )).scalars().all()

    # Publication and coverage are necessary, but they are not enough to ask
    # a customer to continue. At the postcode step require a healthy/bookable
    # provider with exact job support, valid pricing, an assignable technician
    # and real future capacity. This is the production matcher, not a second
    # catalog-specific approximation.
    if zipcode and rows:
        ready = await booking_ready_service_matches(db, zipcode)
        rows = [row for row in rows if row.id in ready]

    return {
        "category": cat.name,
        "category_slug": cat.slug,
        "category_id": str(cat.id),
        "offerings": [
            {
                "id": str(r.id),
                "slug": r.slug,
                "name": r.service_name,
                "job_type": r.job_type,
                "description": r.description,
                # Customer APIs expose the compact app icon only. The separate
                # Instagram card image is resolved inside the Instagram
                # webhook path and never leaks into the mobile app contract.
                "image_url": r.icon_url,
                "icon_url": r.icon_url,
                "requires_address": r.requires_address,
                "requires_schedule": r.requires_schedule,
            }
            for r in rows
        ],
        "total": len(rows),
    }


async def list_serviceable_issues(
    db: AsyncSession, category_slug: str, zipcode: str | None,
    service_group_slug: str | None = None,
    master_service_id: uuid.UUID | None = None,
) -> dict:
    """Issue-first catalog resolution (real customer intent -- "what's
    wrong with your AC", not an internal offering/job-type split). Returns
    {"category", "category_slug", "category_id", "issues": [...]}. Every
    issue returned:
      - has an active ServiceIssueMapping to a real, active job type,
      - belongs to a master service that is active, published by an
        enabled tenant, and (when `zipcode` is given) actually covered by
        that tenant's real service area at that exact zipcode,
      - carries the resolved master_service_id/job_type_id so a later
        "select this issue" call never has to re-derive or guess them.
    Never returns an issue whose only publisher doesn't cover `zipcode`
    (the exact "AC Service published only by a different tenant" leak
    this whole module exists to prevent) -- confirmed live: this is what
    makes Guramrit's real ac-service issue catalog (Not Cooling, Water
    Leakage, Noise Issue, ...) show up for 140412 once THAT tenant
    publishes it, and not before."""
    from app.engines.admin_catalog.models import MasterService

    cat = await _resolve_category(db, category_slug)
    if not cat:
        return {"issues": [], "note": f"Category '{category_slug}' not found."}

    service_group = None
    if service_group_slug:
        service_group = await _resolve_service_group(db, cat.id, service_group_slug)
        if not service_group:
            return {
                "category": cat.name,
                "category_slug": cat.slug,
                "category_id": str(cat.id),
                "service_group": None,
                "issues": [],
                "total": 0,
                "note": "The selected service group is not available in this category.",
            }

    serviceable_services = select(MasterService.id).where(
            MasterService.category_id == cat.id,
            MasterService.is_active == True,  # noqa: E712
            _publisher_filter(zipcode),
        )
    if service_group is not None:
        serviceable_services = serviceable_services.where(
            MasterService.service_group_id == service_group.id
        )
    if master_service_id is not None:
        # A Master Service card on Home must open only that service's real
        # problem set. The id remains a hint: this query revalidates category,
        # group, publication, entitlement and ZIP coverage before exposing it.
        serviceable_services = serviceable_services.where(
            MasterService.id == master_service_id
        )
    serviceable_ms_ids = (await db.execute(serviceable_services)).scalars().all()
    if zipcode and serviceable_ms_ids:
        ready = await booking_ready_service_matches(db, zipcode)
        serviceable_ms_ids = [
            service_id for service_id in serviceable_ms_ids
            if service_id in ready
        ]
    if not serviceable_ms_ids:
        return {
            "category": cat.name,
            "category_slug": cat.slug,
            "category_id": str(cat.id),
            "service_group": (
                {"id": str(service_group.id), "slug": service_group.slug, "name": service_group.name}
                if service_group else None
            ),
            "issues": [],
            "total": 0,
        }

    rows = (await db.execute(
        _serviceable_issue_rows_query(serviceable_ms_ids)
    )).all()

    def _compat(mapping) -> tuple[str, str]:
        # AC-ISSUE-DATA-01 section 3: selection_mode/compatibility_group,
        # stamped onto ServiceIssueMapping.metadata_json by
        # `ensure_gas_refill_deduplication_and_compatibility_metadata`
        # (setup script) -- backend-derived from real workflow facts
        # (installation vs. diagnostic), never inferred from a label.
        # Falls back to "compatible_multi" grouped by the issue's own
        # master_service_id for any mapping this hasn't been stamped onto
        # yet (a different category/service this sprint didn't touch) --
        # never fails closed to "nothing is selectable together".
        meta = mapping.metadata_json or {}
        mode = meta.get("selection_mode")
        group = meta.get("compatibility_group")
        if mode and group:
            return mode, group
        return "compatible_multi", f"ms:{mapping.master_service_id}"

    issues = []
    for issue, mapping, ms in rows:
        selection_mode, compatibility_group = _compat(mapping)
        issues.append({
            "id": str(issue.id),
            "label": issue.name,
            "description": issue.description,
            "image_url": issue.icon_url,
            "master_service_id": str(mapping.master_service_id),
            "master_service_slug": ms.slug,
            "job_type_id": str(mapping.job_type_id) if mapping.job_type_id else None,
            "selection_mode": selection_mode,
            "compatibility_group": compatibility_group,
        })
    return {
        "category": cat.name, "category_slug": cat.slug, "category_id": str(cat.id),
        "service_group": (
            {"id": str(service_group.id), "slug": service_group.slug, "name": service_group.name}
            if service_group else None
        ),
        "issues": issues, "total": len(issues),
    }


def _serviceable_issue_rows_query(serviceable_ms_ids):
    """Build the canonical problem-list query for serviceable offerings.

    ``service_issue_mappings.master_service_id`` is the authoritative link.
    Older/global ``master_issue_types`` rows legitimately have a NULL
    ``master_service_id``; requiring that denormalized legacy column to match
    as well discarded every otherwise valid problem and made Instagram say a
    covered PIN code was unavailable.
    """
    from app.engines.admin_catalog.models import (
        MasterIssueType, MasterService, ServiceIssueMapping,
    )

    return (
        select(MasterIssueType, ServiceIssueMapping, MasterService)
        .join(ServiceIssueMapping, ServiceIssueMapping.issue_type_id == MasterIssueType.id)
        .join(MasterService, MasterService.id == ServiceIssueMapping.master_service_id)
        .where(
            MasterIssueType.is_active == True,  # noqa: E712
            MasterIssueType.status == "active",
            MasterIssueType.customer_visible == True,  # noqa: E712
            MasterService.id.in_(serviceable_ms_ids),
            MasterService.is_active == True,  # noqa: E712
            ServiceIssueMapping.status == "active",
            ServiceIssueMapping.deleted_at.is_(None),
            ServiceIssueMapping.customer_visible == True,  # noqa: E712
        )
        .order_by(MasterService.display_order, MasterIssueType.display_order, MasterIssueType.name)
    )


async def list_serviceable_issues_across_categories(
    db: AsyncSession, zipcode: str | None, *, limit_per_category: int | None = None,
) -> dict:
    """Every issue bookable at this zipcode, in ANY customer-visible category.

    Why this exists: the assistant's DeepSeek interpreter was given one category's
    issue list, so a customer who typed "my tap is leaking" while the conversation
    happened to be scoped to Air Conditioning could only ever be matched against AC
    problems -- the model was not at fault, it was never shown the rest of the
    catalogue. Confirmed live: every interpretation came back AC-shaped.

    Reuses `list_serviceable_issues` per category rather than writing a second,
    wider query. That matters: the serviceability rules (active mapping, active
    master service, a publisher whose real service area covers this exact zipcode)
    are the whole point of that function, and a parallel query would be a second
    place for them to drift -- which is exactly the leak it was written to prevent.

    Each issue carries its own category, so a match outside the conversation's
    current category can still be acted on: the caller knows which category to
    start the draft in.
    """
    from app.engines.admin_catalog.models import ServiceCategory

    categories = (await db.execute(
        select(ServiceCategory)
        .where(
            ServiceCategory.is_active == True,  # noqa: E712
            ServiceCategory.is_customer_visible == True,  # noqa: E712
        )
        .order_by(ServiceCategory.display_order, ServiceCategory.name)
    )).scalars().all()

    issues: list[dict] = []
    for cat in categories:
        if not cat.slug:
            # Without a slug the assistant cannot be entered for this category, so
            # offering its issues would produce a match nothing could act on.
            continue
        catalog = await list_serviceable_issues(db, cat.slug, zipcode)
        found = catalog.get("issues") or []
        if limit_per_category is not None:
            found = found[:limit_per_category]
        for issue in found:
            issues.append({
                **issue,
                "category_id": catalog.get("category_id"),
                "category_slug": catalog.get("category_slug"),
                "category_name": catalog.get("category"),
            })

    return {"issues": issues, "total": len(issues)}
