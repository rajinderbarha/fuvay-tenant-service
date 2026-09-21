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
        MasterIssueType, MasterService, ServiceIssueMapping, TenantService,
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
        .join(
            MasterIssueType,
            MasterIssueType.id == ServiceIssueMapping.issue_type_id,
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
            # A job type is worth matching only if the customer can reach it
            # through a problem they are actually shown.
            MasterIssueType.is_active.is_(True),
            MasterIssueType.status == "active",
            MasterIssueType.customer_visible.is_(True),
        )
        .distinct()
        .order_by(
            MasterService.category_id,
            TenantService.master_service_id,
            ServiceIssueMapping.job_type_id,
        )
    )).all()


async def _priceable_type_ids(
    db: AsyncSession,
    service_id: uuid.UUID,
    job_type_id: uuid.UUID,
) -> list[uuid.UUID]:
    """Return provider-configured leaf types with a valid exact price.

    Exact-type-priced services cannot pass the production matcher until the
    customer has selected a type.  The postcode catalog runs before that
    selection, so it must prove that *at least one* real type is bookable
    instead of treating ``TYPE_SELECTION_REQUIRED`` as provider
    unavailability.  Parent/group types are intentionally excluded: only a
    leaf can be selected and priced on the booking.
    """
    from sqlalchemy import text

    rows = (await db.execute(text("""
        SELECT DISTINCT tst.service_type_id
          FROM tenant_service_types tst
          JOIN tenant_services ts ON ts.id = tst.tenant_service_id
          JOIN service_types st ON st.id = tst.service_type_id
         WHERE ts.master_service_id = :service_id
           AND ts.job_type_id = :job_type_id
           AND ts.is_active IS TRUE
           AND ts.is_enabled IS TRUE
           AND ts.setup_status = 'published'
           AND tst.is_enabled IS TRUE
           AND tst.tenant_min_price > 0
           AND tst.tenant_max_price = tst.tenant_min_price
           AND st.is_active IS TRUE
           AND st.deleted_at IS NULL
           AND st.customer_visible IS TRUE
           AND NOT EXISTS (
               SELECT 1
                 FROM service_types child
                WHERE child.parent_type_id = st.id
                  AND child.is_active IS TRUE
                  AND child.deleted_at IS NULL
           )
         ORDER BY tst.service_type_id
    """), {
        "service_id": str(service_id),
        "job_type_id": str(job_type_id),
    })).scalars().all()
    return list(rows)


def customer_problem_query(*columns):
    """Customer-visible problems, each with its exact job type and built-in type.

    The one definition both the postcode readiness check and the chat's
    problem list use, so a service is never offered on the strength of a
    problem the customer would not then be shown.
    """
    from app.engines.admin_catalog.models import (
        MasterIssueType, ServiceIssueMapping, ServiceType,
    )

    # Some problems are already an exact, price-bearing type ("New pipeline
    # for appliance"); choosing one sets that type on the draft.
    default_type_id = (
        select(ServiceType.id)
        .where(
            ServiceType.slug
            == ServiceIssueMapping.metadata_json["default_service_type_slug"].astext,
            ServiceType.is_active.is_(True),
            ServiceType.deleted_at.is_(None),
        )
        .correlate(ServiceIssueMapping)
        .scalar_subquery()
    )
    return (
        select(
            *columns,
            ServiceIssueMapping.job_type_id.label("job_type_id"),
            default_type_id.label("default_type_id"),
        )
        .select_from(MasterIssueType)
        .join(ServiceIssueMapping, ServiceIssueMapping.issue_type_id == MasterIssueType.id)
        .where(
            ServiceIssueMapping.status == "active",
            ServiceIssueMapping.deleted_at.is_(None),
            ServiceIssueMapping.customer_visible.is_(True),
            MasterIssueType.is_active.is_(True),
            MasterIssueType.status == "active",
            MasterIssueType.customer_visible.is_(True),
        )
    )


async def _customer_problem_rows(db: AsyncSession, service_ids: list[uuid.UUID]):
    """(service_id, problem_id, job_type_id, default_type_id) for these services."""
    from app.engines.admin_catalog.models import MasterIssueType, ServiceIssueMapping

    return (await db.execute(
        customer_problem_query(
            ServiceIssueMapping.master_service_id.label("service_id"),
            MasterIssueType.id.label("problem_id"),
        ).where(ServiceIssueMapping.master_service_id.in_(service_ids))
    )).all()


async def _typed_match(
    db: AsyncSession,
    *,
    category_id: uuid.UUID,
    service_id: uuid.UUID,
    city: str,
    zipcode: str,
    job_type_id: uuid.UUID,
    type_id: uuid.UUID,
) -> dict | None:
    """The production matcher for one exact type, or None when nobody can take it."""
    from app.engines.home_service_booking.matching_engine import select_best_provider

    try:
        async with db.begin_nested():
            match = await select_best_provider(
                db,
                category_id=category_id,
                offering_id=service_id,
                city=city,
                zipcode=zipcode,
                job_type_id=job_type_id,
                offering_type_id=type_id,
            )
    except Exception as exc:  # one malformed type must not hide the rest
        logger.warning(
            "booking_ready_catalog.typed_match_failed",
            zipcode=zipcode,
            service_id=str(service_id),
            job_type_id=str(job_type_id) if job_type_id else None,
            service_type_id=str(type_id),
            error=str(exc),
        )
        return None
    return match if match and match.get("signals") is not None else None


async def _keep_services_with_bookable_problems(
    db: AsyncSession, ready: dict, *, zipcode: str, city: str,
) -> None:
    """Record each service's bookable problems; drop services that have none.

    A service is ready once one of its job types matches, but what the
    customer picks next is a PROBLEM. The problem fixes the job type, and
    some also fix an exact type. A service offered for a job type none of its
    visible problems reach, or whose problems all need a type no ready
    provider takes, left the customer on an empty problem list: "There is
    nothing bookable here at the moment."
    """
    proven: dict[tuple, bool] = {}
    for row in await _customer_problem_rows(db, list(ready)):
        service = ready.get(row.service_id)
        if service is None or row.job_type_id not in service["job_type_ids"]:
            continue
        type_id = row.default_type_id
        if type_id is None or row.job_type_id in service["type_job_type_ids"].get(type_id, ()):
            service["problem_ids"].add(row.problem_id)
            continue
        if row.job_type_id not in service["typeless_job_type_ids"]:
            # Matched only for its priced types, and this is not one of them.
            continue
        # The job type matched with no type at all, which does not prove any
        # provider takes THIS one — and the booking will match with it set.
        key = (row.service_id, row.job_type_id, type_id)
        if key not in proven:
            proven[key] = await _typed_match(
                db,
                category_id=service["category_id"],
                service_id=row.service_id,
                city=city,
                zipcode=zipcode,
                job_type_id=row.job_type_id,
                type_id=type_id,
            ) is not None
        if proven[key]:
            service["problem_ids"].add(row.problem_id)

    for service_id in [key for key, service in ready.items() if not service["problem_ids"]]:
        logger.info(
            "booking_ready_catalog.no_bookable_problem",
            zipcode=zipcode,
            service_id=str(service_id),
        )
        del ready[service_id]


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
        matched_type_ids: list[uuid.UUID | None] = []
        if match and match.get("signals") is not None:
            matched_type_ids.append(None)
        else:
            # A fixed-price service whose price lives on each type (for
            # example Plumbing -> Tap / Basin / Commode) is expected to fail
            # a type-less probe.  Prove readiness against its real configured
            # leaf types before hiding the service from the customer.
            exclusion_codes = {
                str(item.get("reason_code") or "")
                for item in ((match or {}).get("excluded_providers") or [])
                if isinstance(item, dict)
            }
            if "TYPE_SELECTION_REQUIRED" in exclusion_codes and job_type_id:
                for type_id in await _priceable_type_ids(db, service_id, job_type_id):
                    typed_match = await _typed_match(
                        db,
                        category_id=category_id,
                        service_id=service_id,
                        city=city,
                        zipcode=normalized_zip,
                        job_type_id=job_type_id,
                        type_id=type_id,
                    )
                    if typed_match is not None:
                        matched_type_ids.append(type_id)
                        # Keep the strongest typed match for the summary data.
                        if (
                            not match
                            or match.get("signals") is None
                            or (
                                typed_match.get("score") is not None
                                and (
                                    match.get("score") is None
                                    or typed_match["score"] > match["score"]
                                )
                            )
                        ):
                            match = typed_match

        if not matched_type_ids or not match or match.get("signals") is None:
            continue

        current = ready.setdefault(service_id, {
            "category_id": category_id,
            "job_type_ids": set(),
            "type_ids": set(),
            "type_job_type_ids": {},
            # Job types that matched with no type selected at all.
            "typeless_job_type_ids": set(),
            # Filled in below: the problems a customer can actually book.
            "problem_ids": set(),
            "best_score": None,
            "earliest_slot": None,
        })
        current["job_type_ids"].add(job_type_id)
        if None in matched_type_ids:
            current["typeless_job_type_ids"].add(job_type_id)
        for matched_type_id in matched_type_ids:
            if matched_type_id is None:
                continue
            current["type_ids"].add(matched_type_id)
            current["type_job_type_ids"].setdefault(matched_type_id, set()).add(job_type_id)
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

    if ready:
        await _keep_services_with_bookable_problems(
            db, ready, zipcode=normalized_zip, city=city,
        )

    logger.info(
        "booking_ready_catalog.resolved",
        zipcode=normalized_zip,
        candidate_service_job_types=len(pairs),
        ready_services=len(ready),
        ready_job_types=sum(len(item["job_type_ids"]) for item in ready.values()),
        ready_problems=sum(len(item["problem_ids"]) for item in ready.values()),
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
    if zipcode:
        # The same problems the chat offers: only those a ready provider takes.
        rows = [
            (issue, mapping, ms) for issue, mapping, ms in rows
            if issue.id in ready.get(ms.id, {}).get("problem_ids", ())
        ]

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
