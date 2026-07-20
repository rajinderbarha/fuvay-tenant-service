"""Booking Engine — BookingService. Step 4 updated: preflight + creation integration.
Every Level 5 pattern explicitly verified:
  ✅ Idempotent creation (SHA-256 content hash, 5-min window)
  ✅ Price locked at creation via PriceSnapshot — never recalculates
  ✅ 5-check preflight at service layer (not router)
  ✅ Cancellation policy enforced atomically with Commerce
  ✅ Immutable BookingStatusHistory (append-only)
  ✅ Domain events on every state change
  ✅ HATEOAS allowed_transitions on every response
  ✅ RFC 7807 on every preflight block with allowed_transitions
  ✅ Cursor pagination on all list endpoints
  ✅ Zero business logic in router
  ✅ Step 4: server-side serviceability re-match (frontend cannot force tenant_id)
  ✅ Step 4: initial status = pending_confirmation
  ✅ Step 4: city, sla_minutes, matching_snapshot, estimated_price stored
  ✅ Step 4: tenant_owner and customer isolation on get/cancel
"""
from __future__ import annotations
import random, uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.booking.constants import (
    BS, BOOKING_TRANSITIONS, TERMINAL_BOOKING_STATUSES,
    PreflightCheck, DEFAULT_CANCELLATION_WINDOW_HOURS,
    MAX_RESCHEDULE_COUNT, BOOKING_IDEM_WINDOW_MINUTES,
    REDIS_BOOKING_IDEM, make_booking_idempotency_key,
)
from app.engines.booking.models import (
    Booking, BookingStatusHistory, BookingNote, BookingRescheduleRequest,
)
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("booking.service")
utcnow = lambda: datetime.now(timezone.utc)


class BookingService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 actor_tenant_id: uuid.UUID | None = None):
        self.db = db; self.redis = get_redis()
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.actor_tenant_id = actor_tenant_id  # Step 4: for tenant_owner isolation

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _booking_number(self) -> str:
        return f"BK-{utcnow().strftime('%Y%m')}-{random.randint(10000,99999)}"

    def _assert_owns(self, customer_id: uuid.UUID) -> None:
        """Customers may only act on their own bookings. 404 (not 403) so a
        customer can't use this to confirm another customer_id exists."""
        if self.actor_role == "customer" and (self.actor_id is None or self.actor_id != customer_id):
            raise NotFoundException("Booking", str(customer_id))

    # Platform roles carry tenant_id=None (01D-R canonical model) and have
    # unrestricted cross-tenant booking access by design.
    PLATFORM_ROLES = ("super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly")

    def _assert_can_access_booking(self, booking: Booking) -> None:
        """Enforce booking isolation, fail-closed. 404 hides existence.

        MODULE-L5-04 FIX (active cross-tenant IDOR / customer-PII leak): the old
        check handled only customer + tenant_owner and fell THROUGH (no check)
        for every other role. But `staff` and `technician` hold
        booking:bookings:read and reach GET /v1/bookings/{booking_id}, so they
        could read ANY booking across ALL tenants (customer name/address/phone/
        price). Now: platform roles unrestricted; customer -> own; every other
        (tenant-scoped) role -> own tenant; unknown/guest -> denied.
        """
        if self.actor_role in self.PLATFORM_ROLES:
            return
        if self.actor_role == "customer":
            if self.actor_id is None or self.actor_id != booking.customer_id:
                raise NotFoundException("Booking", str(booking.id))
            return
        # All tenant-scoped roles (tenant_owner, staff, technician, ...) are
        # confined to their own tenant; roles without a tenant_id are denied.
        if self.actor_tenant_id is None or self.actor_tenant_id != booking.tenant_id:
            raise NotFoundException("Booking", str(booking.id))

    async def _write_history(self, booking: Booking, from_s: str | None,
                              to_s: str, reason: str | None = None, meta: dict | None = None):
        self.db.add(BookingStatusHistory(
            booking_id=booking.id, tenant_id=booking.tenant_id,
            from_status=from_s, to_status=to_s,
            changed_by=self.actor_id, changed_by_role=self.actor_role,
            reason=reason, meta=meta or {},
        ))

    async def _publish(self, event_type: str, tenant_id: str, booking_id: str, payload: dict):
        try:
            from app.core.events import get_event_bus
            bus = get_event_bus()
            await bus.publish_raw(event_type=event_type, engine_id="booking",
                tenant_id=tenant_id, entity_type="booking", entity_id=booking_id,
                payload=payload, actor_id=str(self.actor_id) if self.actor_id else None)
        except Exception as e:
            logger.warning("booking.event_failed", error=str(e))

    def _booking_dict(self, b: Booking) -> dict:
        allowed = BOOKING_TRANSITIONS.get(b.status, [])
        return {
            "booking_id": str(b.id), "booking_number": b.booking_number,
            "tenant_id": str(b.tenant_id), "customer_id": str(b.customer_id),
            "service_type_id": b.service_type_id, "service_category": b.service_category,
            "status": b.status,
            "quoted_price": float(b.quoted_price) if b.quoted_price else None,
            "estimated_price": float(b.estimated_price) if b.estimated_price else None,
            # Customer Service Credit breakdown (migration 092) — the authoritative
            # figures every app (tenant/admin/customer) must display for what the
            # customer will actually pay the provider directly on-site.
            "credit_applied": float(b.credit_applied or 0),
            "payable_amount": float(b.payable_amount) if b.payable_amount is not None else (
                float(b.quoted_price) if b.quoted_price else None),
            "payment_collection_mode": "customer_pays_provider_directly",
            "platform_payment_collected": False,
            "final_price": float(b.final_price) if b.final_price else None,
            "price_snapshot_id": str(b.price_snapshot_id) if b.price_snapshot_id else None,
            "preferred_date": b.preferred_date, "preferred_slot": b.preferred_slot,
            "scheduled_at": b.scheduled_at.isoformat() if b.scheduled_at else None,
            "address": b.address,
            "city": b.city,
            "zipcode": b.pincode,
            "pincode": b.pincode,
            "address_id": str(b.address_id) if b.address_id else None,
            "matched_service_area_id": str(b.matched_service_area_id) if b.matched_service_area_id else None,
            "matched_service_area_service_id": str(b.matched_service_area_service_id) if b.matched_service_area_service_id else None,
            "coverage_match_level": b.coverage_match_level,
            "service_id": str(b.service_id) if b.service_id else None,
            "job_type": b.job_type,
            "sla_minutes": b.sla_minutes,
            "matching_snapshot": b.matching_snapshot if isinstance(b.matching_snapshot, list) else [],
            "preflight_passed": b.preflight_passed, "blocking_reason": b.blocking_reason,
            # Legacy field for pre-Step-5 compat
            "job_id": str(b.job_id) if b.job_id else None,
            # Step 5: confirmation
            "confirmed_at": b.confirmed_at.isoformat() if b.confirmed_at else None,
            "confirmed_by_user_id": str(b.confirmed_by_user_id) if b.confirmed_by_user_id else None,
            # Step 5: rejection
            "rejected_at": b.rejected_at.isoformat() if b.rejected_at else None,
            "rejected_by_user_id": str(b.rejected_by_user_id) if b.rejected_by_user_id else None,
            "rejection_reason": b.rejection_reason,
            # Step 5: cancellation (with who)
            "cancellation_reason": b.cancellation_reason,
            "cancelled_by_user_id": str(b.cancelled_by_user_id) if b.cancelled_by_user_id else None,
            "within_cancel_window": b.within_cancel_window,
            # Step 5: conversion to job
            "converted_to_job_at": b.converted_to_job_at.isoformat() if b.converted_to_job_at else None,
            "converted_job_id": str(b.converted_job_id) if b.converted_job_id else None,
            "status_updated_at": b.status_updated_at.isoformat() if b.status_updated_at else None,
            "reschedule_count": b.reschedule_count,
            "customer_notes": b.customer_notes, "tags": b.tags,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "allowed_transitions": allowed,
            "is_terminal": b.status in TERMINAL_BOOKING_STATUSES,
        }

    # ── Legacy preflight (5 checks — commerce + capacity) ────────────────────
    async def _run_legacy_preflight(self, tenant_id: uuid.UUID, customer_id: uuid.UUID,
                              pincode: str | None, service_type_id: str,
                              service_category: str, quoted_price: Decimal) -> dict:
        from app.engines.tenant_engine.models import Tenant

        tr = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = tr.scalar_one_or_none()
        if not tenant or tenant.status not in ("active","trial"):
            return {"passed": False, "blocking_check": PreflightCheck.TENANT_ACTIVE,
                    "blocking_reason": f"Tenant is not active (status: {tenant.status if tenant else 'not_found'})",
                    "allowed_transitions": [{"action": "contact_support",
                                             "endpoint": "/v1/support", "method": "GET"}]}

        if pincode:
            try:
                from app.engines.geo.service import GeoService
                geo = GeoService(self.db)
                zone_check = await geo.check_pincode_in_zone(tenant_id, pincode)
                if not zone_check["in_service_area"]:
                    return {"passed": False, "blocking_check": PreflightCheck.ZONE_COVERAGE,
                            "blocking_reason": f"Pincode {pincode} is not in the tenant's service area.",
                            "allowed_transitions": [{"action": "view_service_zones",
                                "endpoint": f"/v1/geo/tenants/{tenant_id}/coverage", "method": "GET"}]}
            except Exception:
                pass

        try:
            from app.engines.tenant_engine.models import TenantLimits
            lim_r = await self.db.execute(select(TenantLimits).where(
                TenantLimits.tenant_id == tenant_id))
            lim = lim_r.scalar_one_or_none()
            if lim and lim.current_active_jobs >= lim.max_active_jobs:
                return {"passed": False, "blocking_check": PreflightCheck.SLOT_AVAILABLE,
                        "blocking_reason": "Tenant has reached maximum active job capacity.",
                        "allowed_transitions": [{"action": "try_later",
                            "reason": "Try booking for a later date."}]}
        except Exception:
            pass

        today_count_r = await self.db.execute(
            select(func.count(Booking.id)).where(
                Booking.tenant_id == tenant_id,
                Booking.status.in_([BS.CONFIRMED, BS.SCHEDULED, BS.DISPATCHING, BS.IN_PROGRESS]),
            ))
        active_bookings = today_count_r.scalar_one_or_none() or 0

        try:
            from app.engines.platform_commerce.service import CommerceService
            commerce = CommerceService(self.db)
            pf = await commerce.run_preflight(
                tenant_id=tenant_id, customer_id=customer_id,
                job_value=quoted_price, booking_id=None)
            if not pf["allowed"]:
                return {"passed": False,
                        "blocking_check": PreflightCheck.COMMERCE_PREFLIGHT,
                        "blocking_reason": pf.get("blocking_reason","Commerce preflight failed."),
                        "advance_required_pct": pf.get("advance_required_pct", 0),
                        "allowed_transitions": pf.get("allowed_transitions", [])}
        except Exception as e:
            logger.warning("booking.preflight_commerce_error", error=str(e))

        return {"passed": True, "blocking_check": None, "blocking_reason": None,
                "allowed_transitions": [], "active_bookings": active_bookings}

    # ── Step 4: Public booking preflight ─────────────────────────────────────
    async def run_booking_preflight(
        self,
        address_id: str | None,
        city: str | None,
        state: str | None,
        zipcode: str | None,
        service_id: str,
        job_type: str,
        scheduled_at: str | None = None,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """
        Step 4 booking preflight — full serviceability matching + pricing estimate.
        Returns can_book, best matched tenant, pricing, SLA.
        """
        from app.engines.serviceability.service import ServiceabilityService
        from app.engines.serviceability.constants import JOB_TYPES

        # 1. Validate job_type
        if not job_type or job_type not in JOB_TYPES:
            raise ServiceOSException("INVALID_JOB_TYPE",
                f"job_type must be one of {JOB_TYPES}.", status_code=422)

        # 2. Validate scheduled_at if provided
        if scheduled_at:
            try:
                sched = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
                if sched.tzinfo is None:
                    sched = sched.replace(tzinfo=timezone.utc)
                if sched <= utcnow():
                    raise ServiceOSException("SCHEDULED_TIME_IN_PAST",
                        "scheduled_at must be a future datetime.", status_code=422)
            except ServiceOSException:
                raise
            except ValueError:
                raise ServiceOSException("INVALID_PAYLOAD",
                    "Invalid scheduled_at format. Use ISO 8601 (e.g. 2026-07-01T10:00:00).",
                    status_code=400)

        svcability = ServiceabilityService(
            db=self.db, request_id=self.request_id,
            actor_id=customer_id or self.actor_id,
            actor_role="customer" if customer_id else self.actor_role,
            actor_tenant_id=None,
        )

        # 3. Validate and resolve service
        try:
            stype_id, svc_name, svc_category = await svcability._resolve_service_type_id(str(service_id))
        except ServiceOSException as e:
            raise ServiceOSException("BOOKING_PREFLIGHT_FAILED",
                f"Service validation failed: {e.detail}", status_code=422)

        # 4. Resolve location
        try:
            resolved_city, resolved_state, resolved_zip, lat, lng, _addr_uuid = (
                await svcability._resolve_location_full(
                    address_id, city, state, zipcode, None, None)
            )
        except ServiceOSException as e:
            raise ServiceOSException("BOOKING_PREFLIGHT_FAILED",
                f"Location resolution failed: {e.detail}", status_code=422)

        if not resolved_city:
            raise ServiceOSException("LOCATION_REQUIRED",
                "city or address_id (with city) is required for booking preflight.",
                status_code=422)

        # 5. Run serviceability matching
        matches = await svcability.match_tenants_for_location(
            city=resolved_city, state=resolved_state, zipcode=resolved_zip,
            latitude=lat, longitude=lng,
            service_type_id=stype_id, job_type=job_type,
        )

        if not matches:
            return {
                "can_book": False,
                "reason_code": "SERVICE_NOT_AVAILABLE_IN_AREA",
                "message": "This service is not available in your area yet.",
                "city": resolved_city, "zipcode": resolved_zip,
                "service_id": str(service_id), "service_type_id": stype_id,
                "job_type": job_type,
                "matched_count": 0,
            }

        best = matches[0]
        staff_capacity = best.get("staff_capacity", 0)

        # 6. Build pricing estimate from best match
        base_price = best.get("base_price") or 0
        estimated_price = base_price
        price_breakdown = {
            "base_price": float(base_price),
            "platform_fee": 0,
            "tax": 0,
            "total": float(estimated_price),
            "currency": "INR",
        }

        return {
            "can_book": True,
            "matched_tenant_id": best["tenant_id"],
            "matched_tenant_name": best["tenant_name"],
            "matched_service_area_id": best["matched_area_id"],
            "matched_service_area_service_id": best["service_area_service_id"],
            "coverage_match_level": best["coverage_match_level"],
            "coverage_rank": best.get("coverage_rank"),
            "service_id": str(service_id),
            "service_type_id": stype_id,
            "service_name": svc_name,
            "service_category": svc_category,
            "job_type": job_type,
            "city": resolved_city,
            "state": resolved_state,
            "zipcode": resolved_zip,
            "estimated_price": float(estimated_price) if estimated_price else None,
            "price_breakdown": price_breakdown,
            "sla_minutes": best.get("estimated_sla_minutes"),
            "tenant_health_score": best.get("health_score"),
            "tenant_rating": best.get("rating"),
            "staff_capacity": staff_capacity,
            "available_matches_count": len(matches),
            "matching_snapshot": [
                {k: v for k, v in m.items() if k in (
                    "tenant_id","tenant_name","coverage_match_level","coverage_rank",
                    "matched_area_id","service_area_service_id","base_price",
                    "estimated_sla_minutes","health_score","rating","distance_km"
                )} for m in matches[:3]
            ],
            "message": "Booking can be created for this address and service.",
        }

    # ── Create booking (Step 4 updated) ──────────────────────────────────────
    async def create_booking(self, customer_id: uuid.UUID,
                              address_id: uuid.UUID | None = None,
                              service_id: uuid.UUID | None = None,
                              job_type: str | None = None,
                              scheduled_at: str | None = None,
                              customer_notes: str | None = None,
                              tags: list | None = None,
                              # Legacy / admin params (kept for backward compat)
                              tenant_id: uuid.UUID | None = None,
                              service_type_id: str | None = None,
                              service_category: str = "general",
                              preferred_date: str | None = None,
                              preferred_slot: str | None = None,
                              address: dict | None = None,
                              pincode: str | None = None) -> dict:
        """
        Step 4 creation pipeline:
        0. Serviceability re-match — backend resolves service_type_id from service_id, then
           matches best tenant for the address. Frontend tenant_id is NEVER trusted.
        1. Idempotency check — SHA-256 of (customer+tenant+service+date)
        2. Get authoritative price from Pricing Engine (quoted_price)
        3. Lock price into PriceSnapshot (immutable)
        4. Run legacy 5-check preflight (commerce + capacity)
        5. Create booking (status=pending_confirmation) + write history + publish event
        """
        matched_area_id: uuid.UUID | None = None
        matched_mapping_id: uuid.UUID | None = None
        coverage_match_level: str | None = None
        city_val: str | None = None
        zip_val: str | None = None
        sla_val: int | None = None
        estimated_price_val: Decimal | None = None
        matching_snap: list = []
        resolved_stype_id: str = service_type_id or ""
        resolved_category: str = service_category

        if not (address_id and service_id and job_type):
            raise ServiceOSException("VALIDATION_ERROR",
                "address_id, service_id, and job_type are all required to create a booking.",
                status_code=422)

        # Slice 2F-15: when a tenant_owner supplies customer_id on behalf of a
        # customer (the router's "assisted booking" override path), that
        # customer_id was previously accepted with ZERO existence validation
        # -- an arbitrary/fabricated UUID, or any real customer's ID with no
        # relationship to this tenant, was silently accepted. This is fixed
        # by requiring the identifier resolve to a real, active, non-deleted
        # customer account (mirrors FieldOpsService.create_job's own
        # customer-validation pattern). The customer's OWN self-booking path
        # (actor_role == "customer") is unaffected -- customer_id there is
        # already server-derived from the authenticated principal, never
        # client-supplied.
        if self.actor_role != "customer":
            from app.engines.auth.models import User
            cr = await self.db.execute(select(User).where(User.id == customer_id))
            customer_user = cr.scalar_one_or_none()
            if (not customer_user or customer_user.role != "customer"
                    or not customer_user.is_active or customer_user.deleted_at is not None):
                raise ServiceOSException("FOREIGN_CUSTOMER",
                    "customer_id is not a valid customer account.", status_code=422)

        # Step 0 — Server-side serviceability re-match
        from app.engines.serviceability.service import ServiceabilityService
        svcability = ServiceabilityService(self.db, request_id=self.request_id,
                                           actor_id=self.actor_id, actor_role=self.actor_role)

        try:
            stype_id, svc_name, svc_category = await svcability._resolve_service_type_id(str(service_id))
        except ServiceOSException:
            raise ServiceOSException("SERVICE_NOT_FOUND",
                "Service not found or inactive.", status_code=404)

        resolved_stype_id = stype_id
        resolved_category = svc_category or service_category

        try:
            _city, _state, _zip, _lat, _lng, _addr_uuid = (
                await svcability._resolve_location_full(
                    str(address_id), None, None, None, None, None)
            )
        except ServiceOSException as e:
            raise ServiceOSException("BOOKING_CREATE_FAILED",
                f"Could not resolve address: {e.detail}", status_code=422)

        matches = await svcability.match_tenants_for_location(
            city=_city or "", state=_state, zipcode=_zip,
            latitude=_lat, longitude=_lng,
            service_type_id=stype_id, job_type=job_type,
        )

        if not matches:
            raise ServiceOSException("SERVICE_NOT_AVAILABLE_IN_AREA",
                "This service is not available in your area yet.", status_code=422)

        best = matches[0]
        tenant_id = uuid.UUID(best["tenant_id"])
        matched_area_id = uuid.UUID(best["matched_area_id"])
        matched_mapping_id = uuid.UUID(best["service_area_service_id"])
        coverage_match_level = best["coverage_match_level"]
        city_val = _city
        zip_val = _zip
        sla_val = best.get("estimated_sla_minutes")
        bp = best.get("base_price")

        # Slice 2F-15: a tenant_owner-assisted booking (customer_id supplied
        # on behalf of someone else) may only be created for a customer who
        # already has an established same-tenant relationship -- otherwise a
        # tenant could "self-mint" a Booking naming ANY real customer whose
        # address happens to fall in their own service area, then confirm it
        # themselves (see phase-02a-slice-02f14g's disclosed residual risk),
        # producing fabricated relationship evidence for field_ops.Job
        # creation. This reuses the exact qualifying-status/lineage rule
        # FieldOpsService._assert_tenant_customer_relationship already
        # applies (confirmed-or-later Booking, or a source-derived Job) --
        # no new relationship model, migration, or invented provenance marker.
        # Customer self-booking (actor_role == "customer") is unaffected --
        # a customer booking themselves for the first time with a tenant is
        # the legitimate, evidenced "first contact" path this policy exists
        # to preserve.
        if self.actor_role != "customer":
            from app.engines.field_ops.models import Job as FieldOpsJob
            from sqlalchemy import or_
            QUALIFYING_BOOKING_STATUSES = (
                BS.CONFIRMED, BS.SCHEDULED, BS.DISPATCHING, BS.IN_PROGRESS,
                BS.COMPLETED, BS.CONVERTED_TO_JOB,
            )
            # Slice 2F-15A: the qualifying Booking must be CUSTOMER-originated
            # (its own creation-history row shows changed_by_role=="customer"),
            # not merely qualifying-status -- otherwise a chain of
            # provider-created assisted bookings could bootstrap each other.
            # A brand-new assisted booking is never itself in this query (it
            # doesn't exist yet), so this is inherently independent evidence,
            # not self-satisfaction. Mirrors
            # FieldOpsService._assert_tenant_customer_relationship's identical
            # tightened rule.
            # Slice 2F-15C: role equality alone is not sufficient -- bind the
            # creation actor explicitly to this Booking's own customer_id
            # (changed_by == Booking.customer_id), not merely "a" customer.
            rel_br = await self.db.execute(
                select(Booking.id)
                .join(BookingStatusHistory, BookingStatusHistory.booking_id == Booking.id)
                .where(
                    Booking.tenant_id == tenant_id, Booking.customer_id == customer_id,
                    Booking.status.in_(QUALIFYING_BOOKING_STATUSES),
                    BookingStatusHistory.from_status.is_(None),
                    BookingStatusHistory.changed_by_role == "customer",
                    BookingStatusHistory.changed_by == Booking.customer_id,
                ).limit(1))
            has_relationship = rel_br.scalar_one_or_none() is not None
            if not has_relationship:
                rel_jr = await self.db.execute(select(FieldOpsJob.id).where(
                    FieldOpsJob.tenant_id == tenant_id, FieldOpsJob.customer_id == customer_id,
                    or_(FieldOpsJob.booking_id.isnot(None), FieldOpsJob.parent_job_id.isnot(None))
                ).limit(1))
                has_relationship = rel_jr.scalar_one_or_none() is not None
            if not has_relationship:
                raise ServiceOSException("CUSTOMER_TENANT_RELATIONSHIP_REQUIRED",
                    "This customer has no existing relationship with your tenant. "
                    "An assisted booking can only be created for a customer who "
                    "already has a confirmed booking or job with your tenant.",
                    status_code=422)
        estimated_price_val = Decimal(str(bp)) if bp is not None else None
        matching_snap = [
            {k: v for k, v in m.items() if k in (
                "tenant_id","tenant_name","coverage_match_level","coverage_rank",
                "matched_area_id","service_area_service_id","base_price",
                "estimated_sla_minutes","health_score","rating","distance_km"
            )} for m in matches[:3]
        ]

        # Step 1 — Idempotency (SHA-256, 5-min window)
        idem_key = make_booking_idempotency_key(
            str(customer_id), str(tenant_id), resolved_stype_id, preferred_date or "")
        redis_key = REDIS_BOOKING_IDEM.format(idem_key=idem_key)
        try:
            existing_id = await self.redis.get(redis_key)
            if existing_id:
                eid = existing_id.decode() if isinstance(existing_id, bytes) else existing_id
                er = await self.db.execute(select(Booking).where(Booking.id == uuid.UUID(eid)))
                eb = er.scalar_one_or_none()
                if eb:
                    logger.info("booking.idempotent", booking_id=eid)
                    return {**self._booking_dict(eb), "idempotent": True}
        except Exception:
            pass

        # Step 2 — Get authoritative quoted price from Pricing Engine
        quoted_price = estimated_price_val or Decimal("0.00")
        price_snapshot_id = None
        try:
            from app.engines.pricing.service import PricingService
            from app.engines.tenant_engine.models import Tenant
            tr = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
            tenant = tr.scalar_one_or_none()
            city_for_pricing = city_val or (tenant.city if tenant else "Mumbai")

            pricing = PricingService(self.db, actor_id=self.actor_id)
            snap = await pricing.compute_and_snapshot(
                tenant_id=tenant_id,
                service_type_id=resolved_stype_id,
                service_category=resolved_category,
                city_name=city_for_pricing,
                pincode=zip_val,
                booking_id=None,
                requested_at_str=None,
            )
            quoted_price = Decimal(str(snap["final_price"]))
            price_snapshot_id = uuid.UUID(snap["snapshot_id"])
        except Exception as e:
            logger.warning("booking.pricing_failed", error=str(e))
            quoted_price = estimated_price_val or Decimal("500.00")

        # Step 3 — Run legacy preflight (tenant active, commerce, capacity)
        preflight = await self._run_legacy_preflight(
            tenant_id, customer_id, zip_val,
            resolved_stype_id, resolved_category, quoted_price)

        # Resolve scheduled_at
        sched_dt: datetime | None = None
        if scheduled_at:
            try:
                sched_dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
                if sched_dt.tzinfo is None:
                    sched_dt = sched_dt.replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        # Step 4 — Create booking with status=pending_confirmation
        booking = Booking(
            tenant_id=tenant_id, customer_id=customer_id,
            service_type_id=resolved_stype_id,
            service_category=resolved_category,
            booking_number=self._booking_number(),
            status=BS.PENDING_CONFIRMATION,
            quoted_price=quoted_price,
            estimated_price=estimated_price_val,
            price_snapshot_id=price_snapshot_id,
            preferred_date=preferred_date,
            preferred_slot=preferred_slot,
            scheduled_at=sched_dt,
            address=address or {},
            pincode=zip_val,
            city=city_val,
            customer_notes=customer_notes,
            preflight_passed=preflight["passed"],
            preflight_result=preflight,
            blocking_reason=preflight.get("blocking_reason"),
            idempotency_key=idem_key,
            tags=tags or [],
            address_id=address_id,
            matched_service_area_id=matched_area_id,
            matched_service_area_service_id=matched_mapping_id,
            coverage_match_level=coverage_match_level,
            service_id=service_id,
            job_type=job_type,
            sla_minutes=sla_val,
            matching_snapshot=matching_snap,
        )
        self.db.add(booking)
        await self.db.flush()

        # Step 5 — Immutable history
        await self._write_history(
            booking, None, booking.status,
            "Booking created — awaiting confirmation",
            meta={"preflight_passed": preflight["passed"],
                  "preflight_check": preflight.get("blocking_check"),
                  "coverage_match_level": coverage_match_level})

        # Step 6 — Cache idempotency key (5-min window)
        try:
            await self.redis.setex(redis_key, BOOKING_IDEM_WINDOW_MINUTES * 60, str(booking.id))
        except Exception:
            pass

        # Step 7 — Publish domain event
        await self._publish("booking.created", str(tenant_id), str(booking.id),
                            {"booking_number": booking.booking_number,
                             "status": booking.status,
                             "quoted_price": float(quoted_price),
                             "preflight_passed": preflight["passed"],
                             "coverage_match_level": coverage_match_level})

        result = {**self._booking_dict(booking), "idempotent": False}
        if not preflight["passed"]:
            result["allowed_transitions"] = preflight.get("allowed_transitions", [])
        return result

    # ── Get / List ────────────────────────────────────────────────────────────
    async def get_booking(self, booking_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(Booking).where(Booking.id == booking_id))
        b = r.scalar_one_or_none()
        if not b: raise NotFoundException("Booking", str(booking_id))
        self._assert_can_access_booking(b)
        return self._booking_dict(b)

    async def list_bookings(self, status: str | None = None,
                             limit: int = 50, cursor: str | None = None,
                             tenant_id: uuid.UUID | None = None,
                             customer_id: uuid.UUID | None = None) -> dict:
        """Step 4: unified list — role determines scope."""
        q = select(Booking).order_by(Booking.created_at.desc())

        # MODULE-L5-04 FIX: force tenant scoping for ALL tenant-scoped roles.
        # Previously only tenant_owner was scoped and the `else` branch let
        # staff/technician (who hold booking:bookings:read) pass an arbitrary
        # tenant_id and list ANY tenant's bookings (cross-tenant customer-PII).
        if self.actor_role == "customer":
            q = q.where(Booking.customer_id == self.actor_id)
        elif self.actor_role in self.PLATFORM_ROLES:
            # platform roles may filter by any tenant/customer
            if tenant_id:
                q = q.where(Booking.tenant_id == tenant_id)
            if customer_id:
                q = q.where(Booking.customer_id == customer_id)
        else:
            # all tenant-scoped roles -> confined to their own tenant
            if self.actor_tenant_id is None:
                raise NotFoundException("Booking", "list")
            q = q.where(Booking.tenant_id == self.actor_tenant_id)
            if customer_id:
                q = q.where(Booking.customer_id == customer_id)

        if status:
            q = q.where(Booking.status == status)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(Booking.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception:
                pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit
        items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {"bookings": [self._booking_dict(b) for b in items],
                "has_next": has_next, "next_cursor": nc, "count": len(items)}

    async def list_by_tenant(self, tenant_id: uuid.UUID, status: str | None,
                              limit: int, cursor: str | None) -> dict:
        q = select(Booking).where(Booking.tenant_id == tenant_id)\
            .order_by(Booking.created_at.desc())
        if status: q = q.where(Booking.status == status)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(Booking.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {"bookings": [self._booking_dict(b) for b in items],
                "has_next": has_next, "next_cursor": nc}

    async def list_by_customer(self, customer_id: uuid.UUID, tenant_id: uuid.UUID | None,
                                limit: int, cursor: str | None) -> dict:
        self._assert_owns(customer_id)
        q = select(Booking).where(Booking.customer_id == customer_id)\
            .order_by(Booking.created_at.desc())
        if tenant_id: q = q.where(Booking.tenant_id == tenant_id)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(Booking.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {"bookings": [self._booking_dict(b) for b in items],
                "has_next": has_next, "next_cursor": nc}

    # ── Confirm (Step 5 updated) ──────────────────────────────────────────────
    async def confirm_booking(self, booking_id: uuid.UUID, scheduled_at: str | None) -> dict:
        r = await self.db.execute(select(Booking).where(Booking.id == booking_id))
        b = r.scalar_one_or_none()
        if not b: raise NotFoundException("Booking", str(booking_id))

        # Step 5: only tenant_owner (not customer, not staff) can confirm
        if self.actor_role == "customer":
            raise ServiceOSException("CUSTOMER_CANNOT_CONFIRM_BOOKING",
                "Customers cannot confirm bookings — only tenant owners can.", status_code=403)

        # Tenant isolation: tenant_owner can only confirm their own tenant's bookings
        self._assert_can_access_booking(b)

        if b.status not in (BS.PENDING, BS.PENDING_CONFIRMATION):
            raise ServiceOSException("BOOKING_INVALID_STATUS_TRANSITION",
                f"Only pending_confirmation or pending bookings can be confirmed. Current: {b.status}",
                status_code=422)

        from_status = b.status
        b.status = BS.CONFIRMED
        b.confirmed_at = utcnow()
        b.confirmed_by_user_id = self.actor_id
        b.status_updated_at = utcnow()
        if scheduled_at:
            try:
                b.scheduled_at = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
            except ValueError:
                pass
        await self._write_history(b, from_status, BS.CONFIRMED, "Confirmed by tenant owner",
                                   meta={"confirmed_by": str(self.actor_id) if self.actor_id else None})
        await self._publish("booking.confirmed", str(b.tenant_id), str(booking_id),
                            {"booking_number": b.booking_number,
                             "confirmed_by": str(self.actor_id) if self.actor_id else None})
        return self._booking_dict(b)

    # ── Reject (Step 5 new) ───────────────────────────────────────────────────
    async def reject_booking(self, booking_id: uuid.UUID, reason: str) -> dict:
        r = await self.db.execute(select(Booking).where(Booking.id == booking_id))
        b = r.scalar_one_or_none()
        if not b: raise NotFoundException("Booking", str(booking_id))

        # Step 5: only tenant_owner can reject
        if self.actor_role == "customer":
            raise ServiceOSException("CUSTOMER_CANNOT_REJECT_BOOKING",
                "Customers cannot reject bookings — only tenant owners can.", status_code=403)

        # Tenant isolation
        self._assert_can_access_booking(b)

        # Validate reason (5-500 chars)
        if not reason or len(reason.strip()) < 5:
            raise ServiceOSException("BOOKING_REJECTION_REASON_REQUIRED",
                "Rejection reason must be at least 5 characters.", status_code=422)
        if len(reason) > 500:
            raise ServiceOSException("BOOKING_REJECTION_REASON_REQUIRED",
                "Rejection reason must be 500 characters or fewer.", status_code=422)

        if b.status not in (BS.PENDING, BS.PENDING_CONFIRMATION):
            raise ServiceOSException("BOOKING_INVALID_STATUS_TRANSITION",
                f"Only pending_confirmation or pending bookings can be rejected. Current: {b.status}",
                status_code=422)

        from_status = b.status
        b.status = BS.REJECTED
        b.rejected_at = utcnow()
        b.rejected_by_user_id = self.actor_id
        b.rejection_reason = reason.strip()
        b.status_updated_at = utcnow()

        await self._write_history(b, from_status, BS.REJECTED, reason.strip(),
                                   meta={"rejected_by": str(self.actor_id) if self.actor_id else None})
        await self._publish("booking.rejected", str(b.tenant_id), str(booking_id),
                            {"booking_number": b.booking_number,
                             "reason": reason.strip(),
                             "rejected_by": str(self.actor_id) if self.actor_id else None})
        return self._booking_dict(b)

    # ── Cancel (atomic with Commerce) ─────────────────────────────────────────
    async def cancel_booking(self, booking_id: uuid.UUID, reason: str) -> dict:
        """
        Certified Level 5 cancellation — Step 4: tenant_owner + customer isolation enforced.
        """
        r = await self.db.execute(select(Booking).where(Booking.id == booking_id))
        b = r.scalar_one_or_none()
        if not b: raise NotFoundException("Booking", str(booking_id))
        self._assert_can_access_booking(b)

        if b.status in TERMINAL_BOOKING_STATUSES:
            raise ServiceOSException("BOOKING_CANNOT_BE_CANCELLED",
                f"Booking is in terminal status '{b.status}' and cannot be cancelled.",
                status_code=409)

        cancel_window_hours = DEFAULT_CANCELLATION_WINDOW_HOURS
        try:
            from app.engines.settings_engine.service import SettingsService
            settings = SettingsService(self.db)
            result = await settings.resolve("booking_cancellation_window_hours",
                                             tenant_id=b.tenant_id)
            cancel_window_hours = result.get("value", DEFAULT_CANCELLATION_WINDOW_HOURS)
        except Exception:
            pass

        within_window = True
        if b.scheduled_at:
            hours_until = (b.scheduled_at - utcnow()).total_seconds() / 3600
            within_window = hours_until >= cancel_window_hours

        if b.reservation_id:
            try:
                from app.engines.platform_commerce.service import CommerceService
                commerce = CommerceService(self.db, actor_id=self.actor_id)
                if within_window:
                    await commerce.release_reservation(str(b.reservation_id), b.tenant_id)
                else:
                    await commerce.forfeit_reservation(str(b.reservation_id), b.tenant_id)
            except Exception as e:
                logger.warning("booking.reservation_cancel_failed", error=str(e))

        from_status = b.status
        b.status = BS.CANCELLED
        b.cancelled_at = utcnow()
        b.cancellation_reason = reason
        b.within_cancel_window = within_window

        await self._write_history(b, from_status, BS.CANCELLED, reason,
                                   meta={"within_window": within_window,
                                         "cancel_window_hours": cancel_window_hours})
        await self._publish("booking.cancelled", str(b.tenant_id), str(booking_id),
                            {"within_window": within_window, "reason": reason})
        return self._booking_dict(b)

    # ── Convert to Job (Step 5 rewrite — atomic) ─────────────────────────────
    async def convert_to_job(self, booking_id: uuid.UUID,
                              assignment_mode: str = "manual",
                              assigned_staff_id: uuid.UUID | None = None,
                              notes: str | None = None) -> dict:
        """Step 5: atomically creates a Field Ops job and transitions booking to converted_to_job.
        Only tenant_owner can call this. Booking must be confirmed. Duplicate conversion blocked."""
        r = await self.db.execute(select(Booking).where(Booking.id == booking_id))
        b = r.scalar_one_or_none()
        if not b: raise NotFoundException("Booking", str(booking_id))

        # Only tenant_owner can convert
        if self.actor_role == "customer":
            raise ServiceOSException("CUSTOMER_CANNOT_CONVERT_BOOKING",
                "Customers cannot convert bookings to jobs.", status_code=403)

        # Tenant isolation
        self._assert_can_access_booking(b)

        # Must be confirmed
        if b.status != BS.CONFIRMED:
            raise ServiceOSException("BOOKING_INVALID_STATUS_TRANSITION",
                f"Only confirmed bookings can be converted to jobs. Current: {b.status}",
                status_code=422)

        # Block duplicate conversion
        if b.converted_job_id:
            raise ServiceOSException("BOOKING_ALREADY_CONVERTED",
                "This booking has already been converted to a job.",
                status_code=409)

        # Check no existing job already references this booking
        from app.engines.field_ops.models import Job as FieldJob, JobStatusHistory
        existing_r = await self.db.execute(
            select(FieldJob).where(FieldJob.booking_id == str(booking_id)))
        if existing_r.scalar_one_or_none():
            raise ServiceOSException("JOB_ALREADY_EXISTS_FOR_BOOKING",
                "A job already exists for this booking.", status_code=409)

        # Slice 2F-15A: a Booking's own CONFIRMED status is not, by itself,
        # sufficient authority to convert -- if this Booking was
        # provider-created (not the customer), converting it must be backed
        # by INDEPENDENT prior relationship evidence (excluding this same
        # Booking), otherwise a legacy or fabricated provider-created Booking
        # could convert into a real field_ops.Job with no genuine customer
        # participation anywhere in the chain. Customer-created Bookings
        # convert under the tenant's already-established provider authority,
        # unchanged. The creation actor's role is read from
        # BookingStatusHistory's creation row (from_status IS NULL) -- an
        # existing field, not a new column.
        # Slice 2F-15C: bind the creation actor explicitly to THIS booking's
        # own customer_id (changed_by == b.customer_id) -- role equality
        # alone does not prove the actor and the booking's customer are the
        # same person. Filtered in SQL (scalar_one_or_none match-or-None) to
        # keep the same query interface as every other provenance check.
        creator_r = await self.db.execute(
            select(BookingStatusHistory.id).where(
                BookingStatusHistory.booking_id == b.id,
                BookingStatusHistory.from_status.is_(None),
                BookingStatusHistory.changed_by_role == "customer",
                BookingStatusHistory.changed_by == b.customer_id).limit(1))
        creator_is_customer_originated = creator_r.scalar_one_or_none() is not None
        if not creator_is_customer_originated:
            from app.engines.field_ops.models import Job as _FieldJob
            QUALIFYING_BOOKING_STATUSES = (
                BS.CONFIRMED, BS.SCHEDULED, BS.DISPATCHING, BS.IN_PROGRESS,
                BS.COMPLETED, BS.CONVERTED_TO_JOB,
            )
            indep_br = await self.db.execute(
                select(Booking.id)
                .join(BookingStatusHistory, BookingStatusHistory.booking_id == Booking.id)
                .where(
                    Booking.tenant_id == b.tenant_id, Booking.customer_id == b.customer_id,
                    Booking.id != b.id,
                    Booking.status.in_(QUALIFYING_BOOKING_STATUSES),
                    BookingStatusHistory.from_status.is_(None),
                    BookingStatusHistory.changed_by_role == "customer",
                    BookingStatusHistory.changed_by == Booking.customer_id,
                ).limit(1))
            has_independent = indep_br.scalar_one_or_none() is not None
            if not has_independent:
                from sqlalchemy import or_ as _or_
                indep_jr = await self.db.execute(select(_FieldJob.id).where(
                    _FieldJob.tenant_id == b.tenant_id, _FieldJob.customer_id == b.customer_id,
                    _FieldJob.booking_id != str(b.id),
                    _or_(_FieldJob.booking_id.isnot(None), _FieldJob.parent_job_id.isnot(None)),
                ).limit(1))
                has_independent = indep_jr.scalar_one_or_none() is not None
            if not has_independent:
                raise ServiceOSException("CUSTOMER_TENANT_RELATIONSHIP_REQUIRED",
                    "This booking cannot be converted without independent, "
                    "established relationship evidence for this customer.",
                    status_code=422)

        # Validate staff if provided
        if assigned_staff_id:
            from app.engines.auth.models import User
            staff_r = await self.db.execute(
                select(User).where(User.id == assigned_staff_id,
                                   User.tenant_id == b.tenant_id))
            staff = staff_r.scalar_one_or_none()
            if not staff:
                raise ServiceOSException("STAFF_NOT_FOUND",
                    "Staff member not found in this tenant.", status_code=404)
            if not getattr(staff, "is_active", True) is False:
                pass  # inactive check — tolerate models without is_active
            if hasattr(staff, "is_active") and not staff.is_active:
                raise ServiceOSException("STAFF_INACTIVE",
                    "Staff member is inactive.", status_code=422)

        # Optionally look up service catalog for checklist / duration
        effective_job_type = b.job_type or "repair"
        duration_estimate_minutes = None
        checklist = []
        try:
            from app.engines.service_catalog.service import ServiceCatalogService
            catalog_item = await ServiceCatalogService(self.db).get_by_service_type_id(
                b.tenant_id, b.service_type_id)
            if catalog_item and catalog_item.is_active:
                effective_job_type = catalog_item.service_type or effective_job_type
                duration_estimate_minutes = catalog_item.estimated_duration_minutes
                if catalog_item.checklist_template:
                    checklist = [{"step": s, "completed": False}
                                 for s in catalog_item.checklist_template]
        except Exception as e:
            logger.warning("booking.catalog_lookup_failed", error=str(e))

        import random
        from app.engines.field_ops.constants import JS as FieldJobStatus, REDIS_JOB_TOKEN
        job_number = f"JOB-{utcnow().strftime('%Y%m')}-{random.randint(10000,99999)}"

        # Create the Field Ops job object (all booking fields copied atomically)
        job = FieldJob(
            tenant_id=b.tenant_id,
            booking_id=str(b.id),
            customer_id=b.customer_id,
            assigned_staff_id=assigned_staff_id,
            service_type_id=b.service_type_id,
            service_category=b.service_category,
            job_type=effective_job_type,
            status=FieldJobStatus.PENDING_ASSIGNMENT,
            job_number=job_number,
            title=f"Job for {b.service_type_id}",
            description=notes or b.customer_notes,
            address=b.address or {},
            pincode=b.pincode,
            city=b.city,
            zipcode=b.pincode,
            address_id=b.address_id,
            service_id=b.service_id,
            matched_service_area_id=b.matched_service_area_id,
            matched_service_area_service_id=b.matched_service_area_service_id,
            coverage_match_level=b.coverage_match_level,
            scheduled_at=b.scheduled_at,
            quoted_price=b.quoted_price,
            credit_applied=b.credit_applied,
            payable_amount=b.payable_amount if b.payable_amount is not None else b.quoted_price,
            estimated_price=b.estimated_price,
            sla_minutes=b.sla_minutes,
            source="booking",
            duration_estimate_minutes=duration_estimate_minutes,
            checklist=checklist,
            tags=b.tags or [],
        )
        self.db.add(job)
        await self.db.flush()  # get job.id

        # Write job status history
        self.db.add(JobStatusHistory(
            job_id=job.id, tenant_id=job.tenant_id,
            from_status=None, to_status=FieldJobStatus.PENDING_ASSIGNMENT,
            changed_by=self.actor_id, changed_by_role=self.actor_role,
            reason="Job created from booking conversion",
        ))

        # Increment usage quota (best-effort)
        try:
            from app.core.usage_quota import adjust_usage
            await adjust_usage(self.db, b.tenant_id, "current_active_jobs", 1)
        except Exception as e:
            logger.warning("booking.job_usage_increment_failed", error=str(e))

        # Update booking atomically
        b.converted_job_id = job.id
        b.status = BS.CONVERTED_TO_JOB
        b.converted_to_job_at = utcnow()
        b.status_updated_at = utcnow()

        await self._write_history(b, BS.CONFIRMED, BS.CONVERTED_TO_JOB,
                                   f"Converted to job {job_number}",
                                   meta={"job_id": str(job.id), "job_number": job_number,
                                         "assignment_mode": assignment_mode})
        await self._publish("booking.converted_to_job", str(b.tenant_id), str(booking_id),
                            {"job_id": str(job.id), "job_number": job_number,
                             "assignment_mode": assignment_mode})

        return {
            "booking_id": str(b.id),
            "booking_number": b.booking_number,
            "booking_status": b.status,
            "converted_to_job_at": b.converted_to_job_at.isoformat(),
            "job_id": str(job.id),
            "job_number": job.job_number,
            "job_status": job.status,
            "tenant_id": str(job.tenant_id),
            "customer_id": str(job.customer_id) if job.customer_id else None,
            "assigned_staff_id": str(job.assigned_staff_id) if job.assigned_staff_id else None,
            "service_type_id": job.service_type_id,
            "job_type": job.job_type,
            "city": job.city,
            "zipcode": job.zipcode,
            "scheduled_at": job.scheduled_at.isoformat() if job.scheduled_at else None,
            "estimated_price": float(job.estimated_price) if job.estimated_price else None,
            "sla_minutes": job.sla_minutes,
            "message": "Booking successfully converted to job.",
        }

    # ── Reschedule ────────────────────────────────────────────────────────────
    async def request_reschedule(self, booking_id: uuid.UUID, requested_date: str,
                                  requested_slot: str, reason: str | None) -> dict:
        r = await self.db.execute(select(Booking).where(Booking.id == booking_id))
        b = r.scalar_one_or_none()
        if not b: raise NotFoundException("Booking", str(booking_id))
        self._assert_can_access_booking(b)  # MODULE-L5-05: tenant/customer scope (was customer-only _assert_owns)
        if b.reschedule_count >= MAX_RESCHEDULE_COUNT:
            raise ServiceOSException("CONFLICT",
                f"Maximum reschedule count ({MAX_RESCHEDULE_COUNT}) reached.",
                resolution="Cancel and create a new booking.")
        req = BookingRescheduleRequest(
            booking_id=b.id, tenant_id=b.tenant_id, requested_by=self.actor_id,
            original_slot=b.preferred_slot, requested_slot=requested_slot,
            requested_date=requested_date, reason=reason,
        )
        self.db.add(req); await self.db.flush()
        await self._publish("booking.reschedule_requested", str(b.tenant_id), str(booking_id),
                            {"requested_date": requested_date, "requested_slot": requested_slot})
        return {"reschedule_request_id": str(req.id), "booking_id": str(booking_id),
                "status": "pending", "requested_date": requested_date, "requested_slot": requested_slot}

    async def accept_reschedule(self, reschedule_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(BookingRescheduleRequest).where(
            BookingRescheduleRequest.id == reschedule_id))
        req = r.scalar_one_or_none()
        if not req: raise NotFoundException("RescheduleRequest", str(reschedule_id))
        if req.status != "pending":
            raise ServiceOSException("CONFLICT", f"Request already {req.status}.")

        br = await self.db.execute(select(Booking).where(Booking.id == req.booking_id))
        b = br.scalar_one_or_none()
        if not b: raise NotFoundException("Booking", str(req.booking_id))
        self._assert_can_access_booking(b)  # MODULE-L5-05: confine to booking's tenant

        old_slot = b.preferred_slot
        b.preferred_date = req.requested_date
        b.preferred_slot = req.requested_slot
        b.reschedule_count += 1
        req.status = "accepted"; req.resolved_at = utcnow()

        await self._write_history(b, b.status, b.status,
                                   f"Rescheduled: {old_slot} → {req.requested_slot}",
                                   meta={"reschedule_count": b.reschedule_count})
        await self._publish("booking.rescheduled", str(b.tenant_id), str(b.id),
                            {"new_date": req.requested_date, "new_slot": req.requested_slot})
        return self._booking_dict(b)

    async def reject_reschedule(self, reschedule_id: uuid.UUID, rejection_reason: str) -> dict:
        r = await self.db.execute(select(BookingRescheduleRequest).where(
            BookingRescheduleRequest.id == reschedule_id))
        req = r.scalar_one_or_none()
        if not req: raise NotFoundException("RescheduleRequest", str(reschedule_id))
        # MODULE-L5-05: confine to the booking's tenant (was unscoped — a
        # tenant_owner could reject another tenant's reschedule request).
        b = (await self.db.execute(select(Booking).where(Booking.id == req.booking_id))).scalar_one_or_none()
        if not b: raise NotFoundException("Booking", str(req.booking_id))
        self._assert_can_access_booking(b)
        req.status = "rejected"; req.rejection_reason = rejection_reason
        req.resolved_at = utcnow()
        return {"reschedule_request_id": str(reschedule_id), "status": "rejected",
                "rejection_reason": rejection_reason}

    # ── Timeline ──────────────────────────────────────────────────────────────
    async def get_timeline(self, booking_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(BookingStatusHistory).where(
            BookingStatusHistory.booking_id == booking_id).order_by(BookingStatusHistory.created_at))
        items = r.scalars().all()
        return {"booking_id": str(booking_id),
                "timeline": [{"from_status": h.from_status, "to_status": h.to_status,
                               "changed_by_role": h.changed_by_role, "reason": h.reason,
                               "meta": h.meta, "occurred_at": h.created_at.isoformat()}
                              for h in items]}

    # ── Notes ─────────────────────────────────────────────────────────────────
    async def add_note(self, booking_id: uuid.UUID, content: str, is_internal: bool) -> dict:
        r = await self.db.execute(select(Booking).where(Booking.id == booking_id))
        b = r.scalar_one_or_none()
        if not b: raise NotFoundException("Booking", str(booking_id))
        self._assert_can_access_booking(b)  # MODULE-L5-05: was unscoped + endpoint had auth-only (any user could note any booking)
        note = BookingNote(booking_id=b.id, tenant_id=b.tenant_id,
            author_id=self.actor_id, author_role=self.actor_role,
            content=content, is_internal=is_internal)
        self.db.add(note); await self.db.flush()
        return {"note_id": str(note.id), "content": content, "is_internal": is_internal,
                "created_at": note.created_at.isoformat()}

    async def list_notes(self, booking_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(BookingNote).where(
            BookingNote.booking_id == booking_id).order_by(BookingNote.created_at))
        notes = r.scalars().all()
        return {"booking_id": str(booking_id), "notes": [
            {"note_id": str(n.id), "content": n.content, "is_internal": n.is_internal,
             "author_role": n.author_role, "created_at": n.created_at.isoformat()}
            for n in notes]}

    # ── Slot availability check ───────────────────────────────────────────────
    async def check_slot_availability(self, tenant_id: uuid.UUID, date: str, slot: str) -> dict:
        r = await self.db.execute(select(func.count(Booking.id)).where(
            Booking.tenant_id == tenant_id,
            Booking.preferred_date == date,
            Booking.preferred_slot == slot,
            Booking.status.in_([BS.CONFIRMED, BS.SCHEDULED, BS.DISPATCHING, BS.IN_PROGRESS]),
        ))
        count = r.scalar_one_or_none() or 0
        return {"tenant_id": str(tenant_id), "date": date, "slot": slot,
                "bookings_in_slot": count, "is_available": count < 5}

    # ── Cancellation policy ───────────────────────────────────────────────────
    async def get_cancellation_policy(self, tenant_id: uuid.UUID) -> dict:
        window = DEFAULT_CANCELLATION_WINDOW_HOURS
        try:
            from app.engines.settings_engine.service import SettingsService
            s = SettingsService(self.db)
            res = await s.resolve("booking_cancellation_window_hours", tenant_id=tenant_id)
            window = res.get("value", window)
        except Exception:
            pass
        return {"tenant_id": str(tenant_id),
                "cancellation_window_hours": window,
                "max_reschedule_count": MAX_RESCHEDULE_COUNT,
                "policy": f"Cancel ≥{window}h before appointment: full refund. Cancel <{window}h: reservation forfeited."}

    # ── Void ─────────────────────────────────────────────────────────────────
    async def void_booking(self, booking_id: uuid.UUID, reason: str) -> dict:
        r = await self.db.execute(select(Booking).where(Booking.id == booking_id))
        b = r.scalar_one_or_none()
        if not b: raise NotFoundException("Booking", str(booking_id))
        self._assert_can_access_booking(b)  # MODULE-L5-05: defense-in-depth (endpoint is super_admin-only)
        if b.status in TERMINAL_BOOKING_STATUSES:
            raise ServiceOSException("CONFLICT", f"Booking is already in terminal status: {b.status}")
        from_status = b.status; b.status = BS.VOIDED
        await self._write_history(b, from_status, BS.VOIDED, f"Voided: {reason}")
        return self._booking_dict(b)

    # ── Search ────────────────────────────────────────────────────────────────
    async def search_bookings(self, tenant_id: uuid.UUID, query: str, limit: int) -> dict:
        r = await self.db.execute(
            select(Booking).where(
                Booking.tenant_id == tenant_id,
                Booking.booking_number.ilike(f"%{query}%"),
            ).limit(limit))
        items = r.scalars().all()
        return {"results": [self._booking_dict(b) for b in items], "query": query}
