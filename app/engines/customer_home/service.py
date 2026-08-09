"""LEVEL-5 REMEDIATION (2026-08-01, Phase 10) — Customer Home Aggregation.

Prior audit (G8) confirmed no backend-driven "Home screen" aggregation
endpoint existed — a customer app would need multiple separate calls
(categories, services, address, bookings, notifications) with no single
purpose-built composition. This service COMPOSES existing engines' own
service classes/queries rather than duplicating their business logic —
per Phase 10's explicit requirement not to re-implement serviceability,
catalog, or booking logic here.

Only ZIP-serviceable, enabled, customer-visible categories/services are
returned. No provider list or internal matching scores are ever exposed.
"""
from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.customer_home.intent import classify_intent
from app.engines.customer_home.seasonality import (
    SEASON_LABELS, current_season, sort_by_season,
)

logger = structlog.get_logger("customer_home.service")

# v2 adds `global_services` (always-visible promotional lead-capture cards).
HOME_RESPONSE_VERSION = 2


# How many live bookings the Home strip carries. Three fits the slider without
# turning Home into a second Bookings tab.
MAX_HOME_ACTIVE_BOOKINGS = 3


class CustomerHomeService:
    def __init__(self, db: AsyncSession, request_id: str = "—"):
        self.db = db
        self.request_id = request_id

    async def get_home(
        self,
        customer_id: uuid.UUID,
        zipcode: str | None = None,
    ) -> dict[str, Any]:
        """Compose the Home screen payload. These lookups share ONE
        AsyncSession (self.db) -- a SQLAlchemy AsyncSession cannot run
        concurrent operations on a single underlying connection
        ("This session is provisioning a new connection; concurrent
        operations are not permitted"). `asyncio.gather` here silently
        failed every section, every time, for every customer -- run
        sequentially instead. Each section still fails safe to a
        type-correct empty default (never crashes the whole payload) via
        `_fail_safe`.
        """
        address = await self._safe_call(self._get_default_address(customer_id), default=None)
        verticals = await self._safe_call(self._get_enabled_verticals(), default=[])
        # The ZIP these categories must actually be bookable in: an explicit
        # override wins, otherwise the customer's default address.
        effective_zip = zipcode or (address or {}).get("zipcode")
        categories = await self._safe_call(
            self._get_bookable_categories(effective_zip), default=[],
        )
        # Several, not one. A customer with three live jobs saw only the newest
        # and had no way to tell the card was hiding the others.
        active_bookings = await self._safe_call(
            self._get_active_booking_summaries(customer_id), default=[])
        active_booking = active_bookings[0] if active_bookings else None
        active_booking_total = await self._safe_call(
            self._count_active_bookings(customer_id), default=len(active_bookings or []))
        unread_count = await self._safe_call(self._get_unread_notification_count(customer_id), default=0)
        campaigns = await self._safe_call(self._get_active_campaigns(zipcode), default=[])
        # Global Services are promotional platform-run offerings shown to
        # EVERY customer regardless of ZIP/vertical/serviceability -- they are
        # deliberately not gated like `bookable_categories`, because they are
        # lead-capture cards (admin calls the customer back), not bookable
        # catalog entries. See global_services/customer_router.py.
        global_services = await self._safe_call(self._get_global_services(), default=[])
        # Scoped to the categories resolved above, so a shortcut can never
        # lead somewhere this ZIP cannot book. The id is read with .get():
        # building the argument list happens OUTSIDE _safe_call, so a
        # category dict missing the key would crash the entire payload
        # rather than degrading this one section.
        quick_issues = await self._safe_call(
            self._get_quick_issues(
                [cid for c in (categories or []) if (cid := (c or {}).get("category_id"))]
            ),
            default=[],
        )

        # Seasonal ordering, applied to BOTH surfaces so the screen is coherent:
        # what a household needs in Ludhiana in January is not what it needs in
        # May. Only reorders -- nothing is hidden, and an unrecognised service
        # stays where the catalogue put it. See seasonality.py.
        season = current_season()
        categories = sort_by_season(list(categories or []), name_key="name", season=season)
        quick_issues = sort_by_season(list(quick_issues or []), name_key="label", season=season)

        serviceability_summary = None
        if zipcode:
            serviceability_summary = {
                "zipcode": zipcode,
                # Category-level bookability for this ZIP is already reflected
                # in `categories` below (each entry only appears if
                # customer-visible/active); a fuller per-service breakdown
                # requires POST /v1/customer/services/available with a
                # specific service — intentionally not duplicated here.
                "checked": True,
            }
        elif address and address.get("zipcode"):
            serviceability_summary = {"zipcode": address["zipcode"], "checked": True}

        # Which sections the app should draw, and in what order. Falls back to
        # an empty list rather than a guessed order: the app then renders its own
        # shipped layout, which is a working screen -- a half-invented order
        # would silently move things around for every customer.
        sections = await self._safe_call(self._get_home_sections(), default=[])

        return {
            "response_version": HOME_RESPONSE_VERSION,
            "sections": sections,
            # Named so the app can say WHY the order is what it is ("Monsoon
            # picks") rather than silently rearranging the screen each quarter.
            "season": season,
            "season_label": SEASON_LABELS[season],
            "address": address,
            "serviceability": serviceability_summary,
            "enabled_verticals": verticals,
            "bookable_categories": categories,
            # Kept for older clients: the first of the list below, never a
            # separately-derived record, so the two cannot disagree.
            "active_booking": active_booking,
            "active_bookings": active_bookings,
            # The REAL total, which can exceed what is returned -- that is what
            # decides whether the app offers "View all", so it must not be
            # inferred from the length of a capped list.
            "active_booking_total": active_booking_total,
            "unread_notification_count": unread_count,
            "campaigns": campaigns,
            "global_services": global_services,
            "quick_issues": quick_issues,
            "capabilities": {
                "bargain_available": True,
                "photo_attach_available": True,
                "chatbot_language_selectable": True,
            },
        }

    async def _safe_call(self, coro, default):
        """Runs one section's lookup; a failure there must never crash the
        whole Home payload, but the fallback must match the field's real
        type (empty list for list fields, 0 for the count, None for
        nullable objects) -- returning None uniformly (the previous
        `_fail_safe` behavior) violated the response schema's required
        array/number fields whenever a section failed."""
        try:
            return await coro
        except Exception as exc:
            logger.warning("customer_home.section_failed", error=str(exc))
            return default

    async def _get_default_address(self, customer_id: uuid.UUID) -> dict | None:
        from app.engines.serviceability.models import CustomerAddress
        q = (
            select(CustomerAddress)
            .where(CustomerAddress.customer_id == customer_id, CustomerAddress.is_active == True)
            .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc())
            .limit(1)
        )
        row = (await self.db.execute(q)).scalars().first()
        if not row:
            return None
        return {
            "address_id": str(row.id),
            "city": row.city,
            "zipcode": row.zipcode,
            "is_default": row.is_default,
        }

    async def _get_enabled_verticals(self) -> list[dict]:
        from app.engines.vertical_catalog.service import VerticalCatalogService
        svc = VerticalCatalogService()
        verticals = await svc.list_verticals(self.db, include_disabled=False)
        return [
            {"vertical_id": v["id"], "key": v["key"], "label": v["label"], "icon": v.get("icon")}
            for v in verticals
        ]

    async def _get_bookable_categories(self, zipcode: str | None = None) -> list[dict]:
        """Categories the customer can genuinely book at their address.

        Real bug fixed here: this returned `list_active_categories()` -- the
        GLOBAL catalog of active categories -- with no regard for the
        customer's ZIP, whether any provider covers it, or whether any
        covering provider is ENTITLED to that category. The field is called
        `bookable_categories` and the app renders it as "Services near you",
        so a customer in a ZIP served only by an AC provider was still shown
        Electrical, Plumbing, Painting and the rest.

        Tapping one of those was a dead end: the draft was created, every
        question answered, a price shown, and only at the final
        match-and-price step did the backend say
        `HOME_BOOKING_NO_PROVIDER_AVAILABLE` -- surfacing in the app as
        "could not load" after the customer had done all the work. That is
        the worst possible place to discover a service is unavailable.

        A category now appears only if at least one active, non-suspended
        home-services provider covering this ZIP has a published service in
        it AND holds the entitlement the matcher itself checks. The same
        gates as `select_best_provider`, applied up front.

        With no ZIP known (customer has not set an address yet) there is
        nothing to filter against, so the full list is returned unchanged --
        the app shows its own "no address" state in that case.
        """
        from app.engines.admin_catalog.customer_flow_service import CustomerFlowService
        svc = CustomerFlowService(db=self.db, request_id=self.request_id)
        result = await svc.list_active_categories()

        bookable_category_ids = await self._category_ids_with_an_eligible_provider(zipcode)
        if bookable_category_ids is not None:
            result = {
                **result,
                "items": [
                    c for c in result.get("items", [])
                    if str(c["id"]) in bookable_category_ids
                ],
            }
        # Only forward customer-safe fields — never internal admin flags.
        #
        # BOOKING-ASSISTANT FOUNDATION (2026-08-01): this previously read
        # `c.get("code")`, a key `list_active_categories` never returns
        # (its real items carry `slug`, not `code` — same class of bug
        # already fixed there for the admin_catalog access, see that
        # method's own comment). The effect here was silent, not a
        # crash: `code` was always None, so every Home category card was
        # missing the one field (`slug`) required by
        # `POST /v1/customer/home-services/booking-drafts`
        # (`category_slug`) — a customer tapping a Home service card had
        # no way to actually start a booking draft for it.
        items = result.get("items", [])
        meta = await self._get_category_meta([c["id"] for c in items])
        return [
            {
                "category_id": c["id"],
                "name": c["name"],
                "slug": c.get("slug"),
                "icon_url": c.get("icon_url"),
                **meta.get(str(c["id"]), {"description": None, "starting_price": None}),
            }
            for c in items
        ]

    async def _get_category_meta(self, category_ids: list) -> dict[str, dict]:
        """Per-category `description` and a real "starting at" price.

        The Home card shows a one-line description and a "Starting at ₹X"
        under each service. Neither existed in this payload before, so the
        app had nothing to render there.

        `starting_price` is the lowest genuinely-configured price across the
        category's ACTIVE master services -- `min_price` where an admin set
        one, otherwise `base_price`. Zeroes are treated as "not configured"
        rather than a real ₹0 (several services carry base_price 0 and price
        via visit_fee instead). A category with no configured price at all
        returns None so the card omits the price row entirely rather than
        inventing or showing ₹0 -- the same rule the rest of this screen
        already follows.
        """
        if not category_ids:
            return {}
        from app.engines.admin_catalog.models import MasterService, ServiceCategory

        price_col = func.min(
            func.coalesce(
                func.nullif(MasterService.min_price, 0),
                func.nullif(MasterService.base_price, 0),
            )
        )
        price_rows = (await self.db.execute(
            select(MasterService.category_id, price_col)
            .where(MasterService.category_id.in_(category_ids), MasterService.is_active.is_(True))
            .group_by(MasterService.category_id)
        )).all()
        prices = {str(r[0]): (float(r[1]) if r[1] is not None else None) for r in price_rows}

        desc_rows = (await self.db.execute(
            select(ServiceCategory.id, ServiceCategory.description)
            .where(ServiceCategory.id.in_(category_ids))
        )).all()
        descriptions = {str(r[0]): r[1] for r in desc_rows}

        return {
            str(cid): {
                "description": descriptions.get(str(cid)),
                "starting_price": prices.get(str(cid)),
            }
            for cid in category_ids
        }

    async def _category_ids_with_an_eligible_provider(self, zipcode: str | None) -> set[str] | None:
        """Category ids that have at least one bookable provider at this ZIP.

        Returns None when no filtering can be done (no ZIP), which the
        caller treats as "leave the list alone" rather than "nothing is
        bookable" -- failing open is right here, because the matcher still
        has the final say and an empty Home screen would be worse than an
        occasional optimistic card.

        Deliberately bulk: a handful of queries total, never one per
        category or per tenant.
        """
        if not zipcode:
            return None

        from sqlalchemy import or_, func as sa_func
        from app.engines.tenant_engine.models import Tenant
        from app.engines.serviceability.models import TenantServiceArea
        from app.engines.admin_catalog.models import MasterService, TenantService
        from app.engines.entitlement.service import entitlement_service

        strip_zip = zipcode.strip()

        # 1. Providers covering this ZIP -- same gates the matcher applies.
        tenant_ids = set((await self.db.execute(
            select(Tenant.id)
            .join(TenantServiceArea, TenantServiceArea.tenant_id == Tenant.id)
            .where(
                Tenant.status == "active",
                Tenant.vertical == "home_services",
                Tenant.suspended_at.is_(None),
                TenantServiceArea.is_active.is_(True),
                TenantServiceArea.zipcode == strip_zip,
            )
        )).scalars().all())
        if not tenant_ids:
            return set()

        # 2. What those providers actually publish, with the service group
        #    that entitlement is keyed on.
        rows = (await self.db.execute(
            select(TenantService.category_id, MasterService.service_group_id, TenantService.tenant_id)
            .join(MasterService, MasterService.id == TenantService.master_service_id)
            .where(
                TenantService.tenant_id.in_(tenant_ids),
                TenantService.is_enabled.is_(True),
                TenantService.deleted_at.is_(None),
            )
        )).all()
        if not rows:
            return set()

        # 3. Entitlement, resolved once per service group rather than per row.
        group_ids = {r.service_group_id for r in rows if r.service_group_id}
        entitled_by_group: dict = {}
        for gid in group_ids:
            entitled_by_group[gid] = await entitlement_service.get_entitled_tenant_ids_for_category(
                self.db, gid, tenant_ids=list(tenant_ids),
            )

        bookable: set[str] = set()
        for r in rows:
            if r.service_group_id is None:
                # No group means no entitlement gate for the matcher either.
                bookable.add(str(r.category_id))
            elif r.tenant_id in entitled_by_group.get(r.service_group_id, set()):
                bookable.add(str(r.category_id))
        return bookable

    async def _count_active_bookings(self, customer_id: uuid.UUID) -> int:
        """How many live bookings there really are.

        Counted separately from the returned list because the list is capped:
        deciding "is there more than this?" from the length of a capped list
        would make the app's "View all" appear exactly when it is least needed.
        """
        from sqlalchemy import func
        from app.engines.final_records.models import ServiceBooking
        from app.engines.final_records.constants import (
            BOOKING_STATUS_COMPLETED, BOOKING_STATUS_CANCELLED,
        )
        terminal = {BOOKING_STATUS_COMPLETED, BOOKING_STATUS_CANCELLED}
        return int((await self.db.execute(
            select(func.count()).select_from(ServiceBooking).where(
                ServiceBooking.customer_id == customer_id,
                ServiceBooking.status.notin_(terminal),
            )
        )).scalar() or 0)

    async def _get_active_booking_summaries(self, customer_id: uuid.UUID) -> list[dict]:
        """The customer's live bookings, newest first, capped.

        The cap exists because each summary resolves a service name, a provider's
        facts and badges and an assigned technician -- worth doing for the few the
        Home card can show, not for an unbounded history. Anything beyond it lives
        on the Bookings tab, which is paginated.
        """
        from app.engines.final_records.models import ServiceBooking
        from app.engines.final_records.constants import (
            BOOKING_STATUS_COMPLETED, BOOKING_STATUS_CANCELLED,
        )
        terminal = {BOOKING_STATUS_COMPLETED, BOOKING_STATUS_CANCELLED}
        rows = (await self.db.execute(
            select(ServiceBooking)
            .where(ServiceBooking.customer_id == customer_id, ServiceBooking.status.notin_(terminal))
            .order_by(ServiceBooking.created_at.desc())
            .limit(MAX_HOME_ACTIVE_BOOKINGS)
        )).scalars().all()
        summaries = []
        for row in rows:
            # One failing booking must not empty the whole strip.
            summary = await self._safe_call(self._summarise_booking(row), default=None)
            if summary:
                summaries.append(summary)
        return summaries

    async def _summarise_booking(self, row) -> dict | None:
        if not row:
            return None
        # The Home card renders this as a live "your job right now" strip, so
        # it needs enough to be meaningful on its own -- a bare status slug
        # ("pending_assignment") tells the customer nothing. All of these are
        # already columns/snapshots on the booking; no extra query.
        provider = row.provider_snapshot if isinstance(row.provider_snapshot, dict) else {}

        # Service name: the card's title. Resolved from the catalog by id,
        # like the bookings list does -- `issue_summary` is the customer's
        # own words, not the service they booked.
        service_name = None
        from app.engines.admin_catalog.models import MasterService, ServiceCategory
        if row.offering_id:
            offering = await self.db.get(MasterService, row.offering_id)
            service_name = offering.service_name if offering else None
        if not service_name and row.category_id:
            category = await self.db.get(ServiceCategory, row.category_id)
            service_name = category.name if category else None

        from app.engines.final_records.models import ServiceJob
        job = (await self.db.execute(
            select(ServiceJob).where(ServiceJob.booking_id == row.id)
        )).scalars().first()

        technician = await self._get_active_booking_technician(job)
        provider_block = await self._get_active_booking_provider(
            row.tenant_id, provider, row.offering_id,
        )

        return {
            "booking_id": str(row.id),
            "booking_number": getattr(row, "booking_number", None),
            "status": row.status,
            "assignment_status": getattr(row, "assignment_status", None),
            "issue_summary": getattr(row, "issue_summary", None),
            "service_name": service_name,
            "preferred_date": row.preferred_date.isoformat() if getattr(row, "preferred_date", None) else None,
            "preferred_time_window": getattr(row, "preferred_time_window", None),
            # The slot the provider actually COMMITTED to, from the job. The
            # preferred_* fields above are what the customer asked for; showing
            # those as "your appointment" would present a request as a promise.
            # Null until a slot is scheduled, so the card can stay quiet.
            "scheduled_date": (
                job.scheduled_date.isoformat() if job and job.scheduled_date else None
            ),
            "scheduled_time_window": job.scheduled_time_window if job else None,
            "provider": provider_block,
            # Kept for older clients; same resolution as provider.name above, so
            # the two can never disagree.
            "provider_name": (provider_block or {}).get("name"),
            "technician": technician,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    async def _get_active_booking_provider(
        self, tenant_id, provider_snapshot: dict, offering_id,
    ) -> dict | None:
        """The provider behind this booking, with the same earned facts and
        badges the booking-review card shows.

        Deliberately the SAME two functions the review screen uses
        (`customer_provider_facts`, `_public_badges`) rather than a second
        derivation: a provider that reads "Verified, 4.8" while being booked
        must not read differently once the job is live. Read fresh rather than
        from `provider_snapshot`, which was frozen at match time.
        """
        # `provider_name` is the key the customer-safe matching snapshot actually
        # writes (build_customer_safe_provider); reading only business_name/name
        # left the card with no provider at all on every real booking.
        name = (
            provider_snapshot.get("business_name")
            or provider_snapshot.get("name")
            or provider_snapshot.get("provider_name")
        )
        if not tenant_id:
            return {"name": name, "verified": False, "rating": None,
                    "review_count": 0, "badges": []} if name else None
        if not name:
            # The tenant row is authoritative when the snapshot predates that key.
            from app.engines.tenant_engine.models import Tenant
            tenant = await self.db.get(Tenant, tenant_id)
            name = tenant.business_name if tenant else None
        from app.engines.home_service_booking.matching_engine import (
            customer_provider_facts, _public_badges,
        )
        facts = await customer_provider_facts(self.db, tenant_id, offering_id=offering_id)
        badges = await _public_badges(self.db, tenant_id, None, facts.get("rating"))
        return {
            "name": name,
            "verified": facts["verified"],
            "rating": facts["rating"],
            "review_count": facts["review_count"],
            "badges": badges,
        }

    async def _get_active_booking_technician(self, job) -> dict | None:
        """Name, photo and review standing of the technician actually
        assigned to this booking's job.

        Name/photo/role only -- never a phone number, mirroring
        `HomeServiceJobAssignmentService._customer_safe_technician`, which
        is the established customer-safe shape for this data.

        `rating`/`review_count` come from the real `staff_rating_summaries`
        table and are null when that technician has no reviews yet: a
        rating is either earned or absent, never defaulted to a flattering
        number. Returns None entirely when no technician is assigned, so
        the card omits the row rather than showing a placeholder person.
        """
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        from app.engines.customer_reviews.models import StaffRatingSummary

        if not job or not job.assigned_staff_id:
            return None

        staff_id = job.assigned_staff_id
        name = None
        role = None
        photo_url = None
        member = await self.db.get(ProviderTeamMember, staff_id)
        if member:
            name = member.full_name
            role = member.designation or "Service technician"
            photo_url = member.profile_photo_url
        else:
            # assigned_staff_id may hold a raw users.id depending on which
            # assignment path wrote it -- the same documented quirk
            # _customer_safe_technician handles. Fail closed rather than guess.
            from app.engines.auth.models import User
            user = await self.db.get(User, staff_id)
            if not user:
                return None
            name = user.full_name
            role = "Service technician"

        summary = (await self.db.execute(
            select(StaffRatingSummary).where(StaffRatingSummary.staff_member_id == staff_id)
        )).scalars().first()

        return {
            "name": name,
            "role": role,
            "photo_url": photo_url,
            "rating": float(summary.average_rating) if summary and summary.total_reviews else None,
            "review_count": summary.total_reviews if summary else None,
        }

    async def _get_unread_notification_count(self, customer_id: uuid.UUID) -> int:
        from app.engines.platform_notifications.notification_service import NotificationService
        svc = NotificationService()
        return await svc.get_unread_count(self.db, customer_id)

    async def _get_home_sections(self) -> list[dict]:
        from app.engines.customer_home.section_service import HomeSectionService
        return await HomeSectionService(self.db).customer_sections()

    async def _get_active_campaigns(self, zipcode: str | None) -> list[dict]:
        from app.engines.customer_campaigns.service import CampaignService
        svc = CampaignService(db=self.db)
        return await svc.list_active_for_customer(zipcode=zipcode)

    async def _get_global_services(self) -> list[dict]:
        from app.engines.global_services.service import GlobalServicesService
        svc = GlobalServicesService(self.db)
        return await svc.list_services(include_inactive=False)

    async def _get_quick_issues(self, category_ids: list) -> list[dict]:
        """Specific problems a customer can tap straight into, e.g.
        "AC Not Cooling" or "Drain Blocked".

        Today the only way in is category -> issue list -> answer questions.
        These let Home skip the first two steps: tapping one carries both the
        category AND the chosen issue into the Assistant, which then goes
        directly to the brand/detail questions.

        Scoped to the categories already resolved as bookable at this ZIP, so
        a shortcut can never lead somewhere the customer cannot book. No
        price is returned: the issue's linked service does carry one, but a
        single issue can map to different work at different prices once the
        details are known, so a figure here would set an expectation the
        booking flow may not honour.
        """
        if not category_ids:
            return []
        from app.engines.admin_catalog.models import MasterIssueType, ServiceCategory

        rows = (await self.db.execute(
            select(MasterIssueType, ServiceCategory.slug, ServiceCategory.name)
            .join(ServiceCategory, ServiceCategory.id == MasterIssueType.category_id)
            .where(
                MasterIssueType.category_id.in_(category_ids),
                MasterIssueType.is_active.is_(True),
                MasterIssueType.status == "active",
            )
            .order_by(MasterIssueType.display_order, MasterIssueType.name)
        )).all()

        return [
            {
                "issue_id": str(issue.id),
                "label": issue.name,
                "slug": issue.slug,
                "category_id": str(issue.category_id),
                "category_slug": cat_slug,
                "category_name": cat_name,
                # The admin-set artwork for this problem. Null is normal and the
                # app falls back to a wording-derived glyph, so a problem is
                # never rendered as a blank tile waiting for an upload.
                "icon_url": issue.icon_url,
                "severity": issue.severity,
                # "repair" / "consult" / null. Lets Home group by what the
                # customer is trying to DO; null means the wording says neither,
                # and the item simply appears in the general grids instead of
                # being forced into the wrong group.
                "intent": classify_intent(issue.name),
            }
            for issue, cat_slug, cat_name in rows
        ]
