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

logger = structlog.get_logger("customer_home.service")

HOME_RESPONSE_VERSION = 1


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
        active_booking = await self._safe_call(self._get_active_booking_summary(customer_id), default=None)
        unread_count = await self._safe_call(self._get_unread_notification_count(customer_id), default=0)
        campaigns = await self._safe_call(self._get_active_campaigns(zipcode), default=[])

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

        return {
            "response_version": HOME_RESPONSE_VERSION,
            "address": address,
            "serviceability": serviceability_summary,
            "enabled_verticals": verticals,
            "bookable_categories": categories,
            "active_booking": active_booking,
            "unread_notification_count": unread_count,
            "campaigns": campaigns,
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
        return [
            {
                "category_id": c["id"],
                "name": c["name"],
                "slug": c.get("slug"),
                "icon_url": c.get("icon_url"),
            }
            for c in result.get("items", [])
        ]

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

    async def _get_active_booking_summary(self, customer_id: uuid.UUID) -> dict | None:
        from app.engines.final_records.models import ServiceBooking
        from app.engines.final_records.constants import (
            BOOKING_STATUS_COMPLETED, BOOKING_STATUS_CANCELLED,
        )
        terminal = {BOOKING_STATUS_COMPLETED, BOOKING_STATUS_CANCELLED}
        q = (
            select(ServiceBooking)
            .where(ServiceBooking.customer_id == customer_id, ServiceBooking.status.notin_(terminal))
            .order_by(ServiceBooking.created_at.desc())
            .limit(1)
        )
        row = (await self.db.execute(q)).scalars().first()
        if not row:
            return None
        return {
            "booking_id": str(row.id),
            "booking_number": getattr(row, "booking_number", None),
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    async def _get_unread_notification_count(self, customer_id: uuid.UUID) -> int:
        from app.engines.platform_notifications.notification_service import NotificationService
        svc = NotificationService()
        return await svc.get_unread_count(self.db, customer_id)

    async def _get_active_campaigns(self, zipcode: str | None) -> list[dict]:
        from app.engines.customer_campaigns.service import CampaignService
        svc = CampaignService(db=self.db)
        return await svc.list_active_for_customer(zipcode=zipcode)
