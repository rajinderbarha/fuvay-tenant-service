"""Sprint 15 — Backend tool executor wired to real Fuvay data (not mocked)."""
from __future__ import annotations
import json
import time
import uuid
from typing import Any

import structlog
from sqlalchemy import select, and_, desc, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.messaging_gateway.dev_identity import instagram_phone_bypass_enabled
from app.exceptions import ServiceOSException

logger = structlog.get_logger("ai_conversation.tools")


class BackendToolExecutor:
    """
    Executes tool calls from DeepSeek, fetching data from real Fuvay backend.

    Rules:
    - NEVER return provider_id, tenant_id, commission, credit_balance, payment_status
    - NEVER create bookings, appointments, or leads
    - Return only customer-safe public data
    """

    SAFE_FIELDS_BLACKLIST = {
        "provider_id", "tenant_id", "commission", "credit_balance",
        "payment_status", "subscription_status",
    }

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID | None,
                 session_id: str | None = None, zipcode: str | None = None,
                 channel: str | None = None, channel_user_id: str | None = None,
                 display_name: str | None = None):
        self.db          = db
        self.customer_id = customer_id
        self.session_id  = session_id
        # The conversation's own known zipcode (session.context_data) --
        # used to filter get_category_offerings to what's ACTUALLY
        # serviceable there, not merely "published by some tenant
        # somewhere." Confirmed live: "AC Service" is published by a
        # different tenant (the old Ludhiana demo tenant), not the one
        # covering 140412 -- without this filter it still surfaced as a
        # bookable offering to a 140412 customer.
        self.zipcode     = zipcode
        self.channel     = channel
        self.channel_user_id = channel_user_id
        self.display_name = display_name

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Dispatch a tool call and return JSON string result."""
        start = time.monotonic()
        success = True
        result: Any = None

        try:
            handler = getattr(self, f"_tool_{tool_name}", None)
            if handler is None:
                return json.dumps({"error": f"Unknown tool: {tool_name}", "tool": tool_name})
            result = await handler(**arguments)
            result = self._scrub_forbidden(result)
            return json.dumps(result, default=str)
        except Exception as exc:
            success = False
            logger.warning("backend_tools.error", tool=tool_name, error=str(exc))
            return json.dumps({"error": "Tool execution failed", "tool": tool_name})
        finally:
            latency_ms = int((time.monotonic() - start) * 1000)
            await self._log_tool_call(
                tool_name=tool_name,
                input_params=arguments,
                output_data=result,
                success=success,
                latency_ms=latency_ms,
            )

    def _scrub_forbidden(self, data: Any) -> Any:
        """Recursively remove forbidden fields from any data structure."""
        if isinstance(data, dict):
            return {
                k: self._scrub_forbidden(v)
                for k, v in data.items()
                if k not in self.SAFE_FIELDS_BLACKLIST
            }
        if isinstance(data, list):
            return [self._scrub_forbidden(item) for item in data]
        return data

    # ── Tool implementations (real backend queries) ───────────────────────────

    async def _tool_get_service_categories(self, search: str | None = None) -> dict:
        """Return customer-visible service categories from real DB."""
        try:
            from app.engines.admin_catalog.models import ServiceCategory
            q = select(ServiceCategory).where(
                and_(
                    ServiceCategory.is_active == True,
                    ServiceCategory.is_customer_visible == True,
                )
            ).order_by(ServiceCategory.name)

            if search:
                q = q.where(ServiceCategory.name.ilike(f"%{search}%"))

            rows = (await self.db.execute(q)).scalars().all()
            return {
                "categories": [
                    {
                        "id":    str(r.id),
                        "name":  r.name,
                        "slug":  r.slug if hasattr(r, "slug") else r.name.lower().replace(" ", "-"),
                        "description": r.description if hasattr(r, "description") else None,
                        "icon":  r.icon_url if hasattr(r, "icon_url") else None,
                    }
                    for r in rows
                ],
                "total": len(rows),
            }
        except Exception as exc:
            logger.warning("backend_tools.categories_failed", error=str(exc))
            return {
                "categories": [],
                "note": "Unable to load categories at this time.",
            }

    async def _tool_get_category_offerings(
        self, category_slug: str, search: str | None = None
    ) -> dict:
        """Return active offerings for a category from real DB.

        Was reading the `master_offerings` table -- a dead, permanently-empty
        legacy table unrelated to the real catalog (MasterService, the same
        table start_home_service_draft/offering_slug actually books against)
        -- so this tool always returned zero offerings for every category,
        every time, regardless of what was actually bookable. Also used raw
        f-string SQL interpolation of `category_slug` (tool-call input, LLM-
        and ultimately user-influenced) directly into `text()`, a real SQL
        injection vector; replaced with parameterized ORM filters.
        """
        try:
            # Shared with the backend-first assistant-bootstrap endpoint
            # (offering_catalog_service.list_serviceable_offerings) -- same
            # zipcode-aware "real published tenant actually covers this
            # exact zipcode" query, so a customer never sees an offering
            # here in chat that the deterministic bootstrap would exclude,
            # or vice versa. Confirmed live: "AC Service" is published by a
            # real tenant, but that tenant's only service area is a
            # different city entirely -- without the zipcode filter it
            # still surfaced as bookable to a 140412 customer.
            from app.engines.home_service_booking.offering_catalog_service import list_serviceable_offerings
            result = await list_serviceable_offerings(self.db, category_slug, self.zipcode)
            if search and result.get("offerings"):
                needle = search.lower()
                result = {**result, "offerings": [o for o in result["offerings"] if needle in (o["name"] or "").lower()]}
                result["total"] = len(result["offerings"])
            result.pop("category_id", None)
            return result
        except Exception as exc:
            logger.warning("backend_tools.offerings_failed", error=str(exc))
            return {
                "offerings": [],
                "note": "Unable to load offerings at this time.",
            }

    async def _tool_get_service_faqs(self, category_slug: str) -> dict:
        """Return generic FAQs about a service category."""
        faq_map = {
            "ac": [
                {"q": "How long does AC service take?", "a": "Typically 1-2 hours for a standard service."},
                {"q": "What's included in AC service?", "a": "Filter cleaning, gas check, coil cleaning, performance test."},
                {"q": "Is AC repair price fixed?", "a": "No — technician inspects first and sends a quote. You approve before work begins."},
            ],
            "plumbing": [
                {"q": "Do you fix leaking pipes?", "a": "Yes, our plumbers handle all types of pipe repairs."},
                {"q": "Is there a visit fee?", "a": "Yes, a small visit/inspection fee applies for repair jobs."},
            ],
            "electrical": [
                {"q": "Do you handle fan installation?", "a": "Yes — fans, switches, sockets, wiring, and more."},
                {"q": "Are electricians certified?", "a": "All our electricians are verified and licensed."},
            ],
            "cleaning": [
                {"q": "What cleaning services are available?", "a": "Home deep cleaning, bathroom cleaning, kitchen cleaning, sofa cleaning, carpet cleaning."},
                {"q": "Are cleaning products included?", "a": "Yes, professional-grade cleaning supplies are brought by the team."},
            ],
        }
        slug = category_slug.lower().replace("-", "_").replace(" ", "_")
        faqs = faq_map.get(slug, [
            {"q": "How do I book a service?", "a": "Chat with me to find the right service, then confirm your slot in the app."},
            {"q": "What if I'm not satisfied?", "a": "We offer a satisfaction guarantee. Contact support within 24 hours."},
        ])
        return {"category": category_slug, "faqs": faqs}

    async def _tool_get_my_recent_bookings(self, limit: int = 5) -> dict:
        """Fetch the same final Home Services bookings the customer app uses."""
        if not self.customer_id:
            return {"bookings": [], "note": "Please log in to view your bookings."}

        try:
            from app.engines.final_records.models import ServiceBooking
            limit = min(limit, 10)
            q = (
                select(ServiceBooking)
                .where(ServiceBooking.customer_id == self.customer_id)
                .order_by(desc(ServiceBooking.created_at))
                .limit(limit)
            )
            rows = (await self.db.execute(q)).scalars().all()
            if not rows:
                return {"bookings": [], "note": "No bookings found."}
            return {
                "bookings": [
                    {
                        "booking_number": r.booking_number,
                        "status": r.status,
                        "issue_summary": r.issue_summary,
                        "city": r.city,
                        "preferred_date": r.preferred_date.isoformat() if r.preferred_date else None,
                        "preferred_time_window": r.preferred_time_window,
                        "assignment_status": r.assignment_status,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                    }
                    for r in rows
                ],
                "total": len(rows),
            }
        except Exception as exc:
            logger.warning("backend_tools.bookings_failed", error=str(exc))
            return {"bookings": [], "note": "Unable to load bookings at this time."}

    async def _tool_get_booking_tracking(self, booking_number: str | None = None) -> dict:
        """Return customer-safe status for one owned final booking."""
        if not self.customer_id:
            return {"booking": None, "note": "Link or sign in to your Fuvay account to track bookings."}
        try:
            from app.engines.final_records.models import ServiceBooking, ServiceJob

            query = select(ServiceBooking).where(ServiceBooking.customer_id == self.customer_id)
            if booking_number:
                query = query.where(ServiceBooking.booking_number == booking_number.strip())
            booking = (await self.db.execute(
                query.order_by(ServiceBooking.created_at.desc()).limit(1)
            )).scalars().first()
            if not booking:
                return {"booking": None, "note": "No matching booking was found on this account."}
            job = (await self.db.execute(
                select(ServiceJob).where(ServiceJob.booking_id == booking.id).limit(1)
            )).scalars().first()
            return {
                "booking": {
                    "booking_number": booking.booking_number,
                    "status": booking.status,
                    "assignment_status": booking.assignment_status,
                    "issue_summary": booking.issue_summary,
                    "city": booking.city,
                    "preferred_date": booking.preferred_date.isoformat() if booking.preferred_date else None,
                    "preferred_time_window": booking.preferred_time_window,
                    "job_status": job.status if job else None,
                    "scheduled_date": job.scheduled_date.isoformat() if job and job.scheduled_date else None,
                    "scheduled_time_window": job.scheduled_time_window if job else None,
                },
                "note": "This is the latest backend status. Do not invent an ETA or technician location.",
            }
        except Exception as exc:
            logger.warning("backend_tools.booking_tracking_failed", error=str(exc))
            return {"booking": None, "note": "Unable to load booking tracking right now."}

    async def _tool_check_service_area(
        self, city: str, category_slug: str | None = None
    ) -> dict:
        """Check if a service is available in a city using real geo zone data."""
        try:
            from app.engines.serviceability.models import TenantServiceArea
            q = select(TenantServiceArea).where(
                and_(
                    TenantServiceArea.is_active == True,
                    TenantServiceArea.city.ilike(f"%{city}%"),
                )
            ).limit(5)
            rows = (await self.db.execute(q)).scalars().all()
            if rows:
                return {
                    "city":      city,
                    "available": True,
                    "zones":     [r.zone_name or r.city for r in rows],
                    "message":   f"Great news! We serve {city}.",
                }
            return {
                "city":      city,
                "available": False,
                "message":   f"We're expanding to {city} soon. Currently limited availability.",
            }
        except Exception as exc:
            logger.warning("backend_tools.geo_check_failed", error=str(exc))
            return {
                "city":      city,
                "available": True,
                "message":   f"We operate in major cities across India including {city}.",
            }

    # Fields the deterministic question-flow's tap-select cards collect
    # (brand/type CatalogQuestions -> question_flow_service._bridge_to_draft_
    # columns) -- these must never appear as something DeepSeek asks about
    # in plain chat text, even while still empty.
    _CHAT_UNASKABLE_FIELDS = {"offering_type_id", "brand_id"}

    def _still_needed(self, draft_dict: dict) -> list[str]:
        """Diff `required_fields` (static, offering-driven) against the
        draft's own current values to get the genuinely-empty subset that
        DeepSeek may actually ask about via chat."""
        value_by_field = {
            "issue_summary":   draft_dict.get("issue_summary"),
            "city":            draft_dict.get("city"),
            "offering_type_id": draft_dict.get("offering_type_id"),
            "brand_id":        draft_dict.get("brand_id"),
            "preferred_date":  draft_dict.get("preferred_date"),
        }
        missing = [
            f for f in draft_dict.get("required_fields", [])
            if not value_by_field.get(f) and f not in BackendToolExecutor._CHAT_UNASKABLE_FIELDS
        ]
        # Native app bookings select a saved address in deterministic UI.
        # Social chats have no such screen, so the agent must collect the
        # minimum deliverable address and persist an immutable snapshot.
        if self.channel in {"whatsapp", "instagram"}:
            snapshot = draft_dict.get("address_snapshot") or {}
            social_required = {
                "address_line_1": snapshot.get("address_line_1"),
                "city": draft_dict.get("city"),
                "zipcode": draft_dict.get("zipcode"),
            }
            for field, value in social_required.items():
                if not value and field not in missing:
                    missing.append(field)
        return missing

    # ── Sprint 16 — Home Service Booking Draft tools ─────────────────────────

    async def _tool_start_home_service_draft(
        self,
        category_slug: str,
        offering_slug: str,
    ) -> dict:
        """
        Create a booking draft for a Home Service offering.
        Called when customer's intent is clearly booking a home service.
        Returns draft_id (opaque to DeepSeek) and required_fields list.
        DeepSeek must NOT use draft_id to make bookings — backend only.
        """
        try:
            from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
            import uuid as _uuid

            ai_session_id = _uuid.UUID(self.session_id) if self.session_id else None
            # Local: messaging_gateway is the adapter layered ON TOP of this
            # engine, so importing it at module scope would invert that.
            from app.engines.messaging_gateway.constants import VALID_CHANNELS

            svc = HomeServiceChatbotBookingService(db=self.db)
            result = await svc.start_booking_draft(
                customer_id=self.customer_id,
                ai_session_id=ai_session_id,
                category_slug=category_slug,
                offering_slug=offering_slug,
                zipcode=self.zipcode,
                channel=self.channel or "customer_app",
                # Stable across /fuvay, unlike session_id -- see
                # `enforce_social_draft_limit`.
                social_identity=(
                    f"{self.channel}:{self.channel_user_id}"
                    if self.channel in VALID_CHANNELS and self.channel_user_id
                    else None
                ),
            )
            # WhatsApp supplies a platform-verified sender number. Populate
            # contact fields without making the irreversible account/booking
            # records yet; those are created only after CONFIRM BOOKING.
            if self.channel == "whatsapp" and self.channel_user_id:
                digits = "".join(ch for ch in self.channel_user_id if ch.isdigit())
                result = await svc.update_draft_fields(
                    draft_id=_uuid.UUID(str(result["id"])),
                    customer_id=self.customer_id,
                    payload={
                        "customer_name": self.display_name or "WhatsApp Customer",
                        "customer_phone": f"+{digits}" if digits else self.channel_user_id,
                    },
                )
            # The real problems list is returned in THIS SAME response
            # (not a separate get_service_problems call DeepSeek has to
            # remember to make) -- confirmed live that DeepSeek's own tool-
            # chaining is inconsistent turn to turn: it sometimes narrates
            # "which brand?" in plain chat text instead of calling
            # get_service_problems + update_home_service_draft, which
            # means job_type_id never resolves and the tap-select question
            # cards can never appear, forcing the customer to type
            # everything. Collapsing this into one guaranteed round trip
            # removes an entire step DeepSeek could skip.
            problems = await self._tool_get_service_problems(draft_id=result["id"])
            return {
                "draft_id":        result["id"],
                "offering_name":   result.get("offering_name"),
                # `required_fields` lists every field this offering could
                # ever need; several (city) are commonly already auto-filled
                # from the customer's saved address at draft-creation time
                # (see start_booking_draft) -- only pass the STILL-EMPTY
                # ones through, so DeepSeek never re-asks something the
                # backend already knows.
                "still_needed":    self._still_needed(result),
                "pricing_model":   result.get("pricing_model"),
                "draft_status":    result.get("status"),
                "problems":        problems.get("problems", []),
                "message": (
                    f"Booking draft started for {result.get('offering_name')}. "
                    "Match the customer's issue to one of the `problems` above and immediately "
                    "call update_home_service_draft with selected_problem_id set to it -- "
                    "do NOT ask about brand/type yourself, the app shows tap-select cards for those."
                ),
            }
        except Exception as exc:
            logger.warning("backend_tools.start_draft_failed", error=str(exc))
            return {"error": str(exc), "draft_id": None}

    async def _tool_get_home_service_draft_status(
        self,
        draft_id: str,
    ) -> dict:
        """
        Get the current status and missing fields for a booking draft.
        Use this to tell the customer what's still needed.
        """
        try:
            from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
            import uuid as _uuid

            svc = HomeServiceChatbotBookingService(db=self.db)
            result = await svc.get_booking_draft(
                draft_id=_uuid.UUID(draft_id),
                customer_id=self.customer_id,
            )
            response = {
                "draft_status":    result.get("status"),
                # Was `result.get("required_fields", [])` -- the STATIC list
                # of everything this offering could ever need, regardless of
                # whether it's already filled (e.g. always included "city"
                # even once auto-filled from the customer's address), so
                # DeepSeek kept re-asking for data the backend already had.
                "missing_fields":  self._still_needed(result),
                "serviceability":  result.get("serviceability_status"),
                "price_status":    result.get("price_status"),
                "issue_summary":   result.get("issue_summary"),
                "city":            result.get("city"),
                "zipcode":         result.get("zipcode"),
            }
            # Same fix as start_home_service_draft: an OLDER, already-
            # existing draft (this conversation continuing rather than
            # just starting one) never got the merged `problems` list --
            # DeepSeek would call this status tool instead and see no way
            # to resolve the problem/job type at all, permanently falling
            # back to asking everything in plain chat text. If no problem
            # has been selected yet, surface the same real problems list
            # here too, with the same explicit instruction.
            if not result.get("job_type_id"):
                problems = await self._tool_get_service_problems(draft_id=draft_id)
                response["problems"] = problems.get("problems", [])
                if response["problems"]:
                    response["message"] = (
                        "No problem selected yet. Match the customer's issue to one of `problems` "
                        "and immediately call update_home_service_draft with selected_problem_id set "
                        "to it -- do not ask about brand/type yourself, tap-select cards handle those."
                    )
            return response
        except Exception as exc:
            logger.warning("backend_tools.get_draft_status_failed", error=str(exc))
            return {"error": "Unable to retrieve booking status.", "draft_status": None}

    async def _tool_get_service_problems(
        self,
        draft_id: str,
    ) -> dict:
        """
        Real, admin-defined problem/issue list for a draft's master service
        (ServiceIssueMapping -> MasterIssueType). Selecting one of these ids
        as selected_problem_id is what resolves the job type and unlocks the
        deterministic follow-up questions -- DeepSeek has no other way to do
        this, it must never guess a problem id.
        """
        try:
            import uuid as _uuid
            from app.engines.home_service_booking.models import HomeServiceBookingDraft
            from app.engines.admin_catalog.models import ServiceIssueMapping, MasterIssueType

            draft = await self.db.get(HomeServiceBookingDraft, _uuid.UUID(draft_id))
            if not draft:
                return {"error": "Draft not found", "problems": []}

            rows = (await self.db.execute(
                select(MasterIssueType.id, MasterIssueType.name, MasterIssueType.description)
                .join(ServiceIssueMapping, ServiceIssueMapping.issue_type_id == MasterIssueType.id)
                .where(
                    ServiceIssueMapping.master_service_id == draft.offering_id,
                    ServiceIssueMapping.status == "active",
                    ServiceIssueMapping.customer_visible == True,  # noqa: E712
                    MasterIssueType.is_active == True,  # noqa: E712
                )
                .order_by(ServiceIssueMapping.display_order)
            )).all()
            return {
                "problems": [
                    {"id": str(r.id), "name": r.name, "description": r.description} for r in rows
                ],
                "instruction": (
                    "As soon as you know which of these matches the customer's issue, call "
                    "update_home_service_draft NOW with selected_problem_id set to its id "
                    "(same turn if possible) -- do not just say you matched it in text."
                ) if rows else None,
            }
        except Exception as exc:
            logger.warning("backend_tools.get_service_problems_failed", error=str(exc))
            return {"error": "Unable to retrieve problem list.", "problems": []}

    async def _tool_update_home_service_draft(
        self,
        draft_id: str,
        **fields,
    ) -> dict:
        """
        Update booking draft fields extracted from conversation.
        Pass only fields that the customer has provided.
        NEVER include price, provider_id, or commission in fields.
        """
        try:
            from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
            import uuid as _uuid

            address_keys = {
                "address_line_1", "address_line_2", "landmark",
                "state", "country",
            }
            address_fields = {key: fields.pop(key) for key in list(fields) if key in address_keys}
            svc = HomeServiceChatbotBookingService(db=self.db)
            result = await svc.update_draft_fields(
                draft_id=_uuid.UUID(draft_id),
                customer_id=self.customer_id,
                payload=fields,
            )
            if address_fields:
                from app.engines.home_service_booking.models import HomeServiceBookingDraft

                draft = await self.db.get(HomeServiceBookingDraft, _uuid.UUID(draft_id))
                if draft:
                    snapshot = dict(draft.address_snapshot or {})
                    snapshot.update({key: value for key, value in address_fields.items() if value is not None})
                    snapshot.update({
                        "city": draft.city,
                        "zipcode": draft.zipcode,
                        "name": draft.customer_name,
                        "phone": draft.customer_phone,
                    })
                    snapshot.setdefault("country", "India")
                    draft.address_snapshot = snapshot
                    await self.db.commit()
                    result = await svc.get_booking_draft(
                        draft_id=_uuid.UUID(draft_id), customer_id=self.customer_id,
                    )
            return {
                "draft_status":  result.get("status"),
                # Was `result.get("required_fields", [])` -- the same
                # static-list-not-diffed bug already fixed on the other two
                # tools, missed here. This is the tool DeepSeek calls most
                # often (every field update), so its `still_needed` is what
                # actually drives the date-quick-replies detection in
                # send_message -- with the old key/value this NEVER
                # triggered, silently leaving "preferred_date" as a typed-
                # only field forever.
                "still_needed":  self._still_needed(result),
                "updated":       True,
                "message":       "Fields saved. Collecting remaining details.",
            }
        except Exception as exc:
            logger.warning("backend_tools.update_draft_failed", error=str(exc))
            return {"error": str(exc), "updated": False}

    async def _tool_check_home_service_availability(
        self,
        draft_id: str,
    ) -> dict:
        """
        Check if the home service is available at the customer's city/zipcode.
        Call this AFTER customer has provided city/address.
        Backend queries real provider service areas — not mocked.
        """
        try:
            from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
            import uuid as _uuid

            svc = HomeServiceChatbotBookingService(db=self.db)
            result = await svc.check_serviceability(
                draft_id=_uuid.UUID(draft_id),
                customer_id=self.customer_id,
            )
            return {
                "serviceable":            result.get("serviceable", False),
                "available_provider_count": result.get("available_provider_count", 0),
                "matched_by":             result.get("matched_by"),
                "message":                result.get("message"),
                "draft_status":           result.get("draft_status"),
            }
        except Exception as exc:
            logger.warning("backend_tools.serviceability_failed", error=str(exc))
            return {
                "serviceable": False,
                "message":     "Unable to check serviceability. Please try again.",
            }

    async def _tool_get_home_service_price_estimate(
        self,
        draft_id: str,
    ) -> dict:
        """
        Get backend-computed price estimate for the booking.
        NEVER quote a price yourself — use this tool only.
        Returns visit fee or base price from backend catalog.
        """
        try:
            from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
            import uuid as _uuid

            svc = HomeServiceChatbotBookingService(db=self.db)
            draft_uuid = _uuid.UUID(draft_id)
            draft = await svc.get_booking_draft(draft_id=draft_uuid, customer_id=self.customer_id)
            result = await svc.match_provider_and_price(
                category_id=_uuid.UUID(str(draft["category_id"])),
                master_service_id=_uuid.UUID(str(draft["offering_id"])),
                city=str(draft.get("city") or ""),
                zipcode=draft.get("zipcode"),
                offering_type_id=_uuid.UUID(str(draft["offering_type_id"])) if draft.get("offering_type_id") else None,
                brand_id=_uuid.UUID(str(draft["brand_id"])) if draft.get("brand_id") else None,
                job_type_id=_uuid.UUID(str(draft["job_type_id"])) if draft.get("job_type_id") else None,
                draft_id=draft_uuid,
                customer_id=self.customer_id,
            )
            snap = result.get("price_snapshot", {})
            # Fixed-price bookings have exactly one server-authoritative price.
            # Record that choice now; inspection-first bookings deliberately do
            # not have a fixed price tier.
            if snap.get("standard_price") is not None:
                await svc.confirm_price_choice(draft_uuid, "standard", self.customer_id)
            return {
                "display_price":  snap.get("display_price"),
                "pricing_model":  snap.get("pricing_model"),
                "note":           snap.get("note"),
                "currency":       snap.get("currency", "INR"),
                "draft_status":   result.get("draft_status"),
                "selected_provider": result.get("selected_provider"),
            }
        except Exception as exc:
            logger.warning("backend_tools.price_estimate_failed", error=str(exc))
            return {"error": "Unable to estimate price.", "display_price": None}

    async def _tool_get_available_home_service_slots(self, draft_id: str, emergency: bool = False) -> dict:
        """List real capacity-checked slots for a matched booking draft."""
        try:
            from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
            import uuid as _uuid
            if (
                not self.customer_id
                and self.channel != "whatsapp"
                and not instagram_phone_bypass_enabled(self.channel)
            ):
                return {"slots": [], "error": "Link your Fuvay account before choosing a slot."}
            return await HomeServiceChatbotBookingService(self.db).list_available_slots(
                draft_id=_uuid.UUID(draft_id), customer_id=self.customer_id, emergency=emergency,
            )
        except Exception as exc:
            logger.warning("backend_tools.slots_failed", error=str(exc))
            return {"slots": [], "error": "Unable to load available slots right now."}

    async def _tool_select_home_service_slot(
        self, draft_id: str, date: str, time_window: str, emergency: bool = False,
    ) -> dict:
        """Select one exact slot returned by get_available_home_service_slots."""
        try:
            from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
            import uuid as _uuid
            if (
                not self.customer_id
                and self.channel != "whatsapp"
                and not instagram_phone_bypass_enabled(self.channel)
            ):
                return {"selected": False, "error": "Link your Fuvay account before choosing a slot."}
            result = await HomeServiceChatbotBookingService(self.db).select_promised_slot(
                draft_id=_uuid.UUID(draft_id), customer_id=self.customer_id,
                date_iso=date, time_window=time_window, emergency=emergency,
            )
            return {"selected": True, **result}
        except Exception as exc:
            logger.warning("backend_tools.select_slot_failed", error=str(exc))
            return {"selected": False, "error": "That slot is no longer available. Please choose another."}

    async def _tool_get_home_service_booking_summary(self, draft_id: str) -> dict:
        """Build the real customer-safe summary before explicit confirmation."""
        try:
            from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
            import uuid as _uuid
            if (
                not self.customer_id
                and self.channel != "whatsapp"
                and not instagram_phone_bypass_enabled(self.channel)
            ):
                return {"summary": None, "error": "Link your Fuvay account before confirming a booking."}
            summary = await HomeServiceChatbotBookingService(self.db).build_booking_summary(
                draft_id=_uuid.UUID(draft_id), customer_id=self.customer_id,
            )
            return {
                "summary": summary,
                "confirmation_instruction": "Show this summary, then ask the customer to reply exactly CONFIRM BOOKING.",
            }
        except Exception as exc:
            logger.warning("backend_tools.booking_summary_failed", error=str(exc))
            return {"summary": None, "error": "Unable to prepare the booking summary right now."}

    async def _tool_confirm_home_service_booking(self, draft_id: str, confirmation_phrase: str) -> dict:
        """Create final records only after an exact explicit confirmation phrase."""
        if " ".join((confirmation_phrase or "").upper().split()) != "CONFIRM BOOKING":
            return {"confirmed": False, "error": "Ask the customer to reply exactly CONFIRM BOOKING first."}
        bypass_instagram_phone = instagram_phone_bypass_enabled(self.channel)
        if (
            not self.customer_id
            and self.channel != "whatsapp"
            and not bypass_instagram_phone
        ):
            return {"confirmed": False, "error": "Link your Fuvay account before confirming a booking."}
        try:
            import uuid as _uuid
            from app.engines.auth.models import User
            from app.engines.ai_conversation.models import AIConversationSession
            from app.engines.final_records.creation_service import HomeServiceFinalCreationService
            from app.engines.home_service_booking.models import HomeServiceBookingDraft
            from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

            draft_uuid = _uuid.UUID(draft_id)
            booking_service = HomeServiceChatbotBookingService(self.db)
            if not self.customer_id and self.channel == "whatsapp":
                digits = "".join(ch for ch in (self.channel_user_id or "") if ch.isdigit())
                if not digits:
                    return {"confirmed": False, "error": "Your WhatsApp number could not be verified."}
                draft_model = await self.db.get(HomeServiceBookingDraft, draft_uuid)
                if not draft_model:
                    return {"confirmed": False, "error": "Booking draft not found."}
                address = draft_model.address_snapshot or {}
                if not (
                    address.get("address_line_1")
                    and draft_model.city
                    and draft_model.zipcode
                ):
                    return {
                        "confirmed": False,
                        "error": "Collect the complete service address and postal code before confirming.",
                    }
                phone = f"+{digits}"
                tail = digits[-10:]
                # Match on the phone ALONE, not on `role == "customer"`.
                # `users.phone` is globally unique (uq_users_phone), so a
                # number already registered as a technician, tenant owner or
                # deactivated customer cannot be inserted a second time: the
                # role-filtered lookup missed those rows, the INSERT below
                # violated the constraint, and the poisoned session then took
                # the whole webhook down with a 500 — which Meta redelivers
                # forever. Confirmed live on a real WhatsApp booking whose
                # sender was also a technician account.
                # Ordered, not arbitrary: a customer account wins over any
                # other role, and the number the sender actually messaged from
                # wins over another row that merely shares its last ten digits
                # (confirmed live: +919041624576 and +9041624576 are two
                # different accounts with the same tail, and the untied query
                # attached the booking to whichever came back first).
                user = (await self.db.execute(select(User).where(
                    User.phone.isnot(None),
                    func.right(func.regexp_replace(User.phone, r"\D", "", "g"), 10) == tail,
                ).order_by(
                    (User.role == "customer").desc(),
                    (User.phone == phone).desc(),
                    User.is_active.desc(),
                ).limit(1))).scalars().first()
                if user and user.role != "customer":
                    logger.info("backend_tools.confirm_booking_existing_account",
                                role=user.role)
                if not user:
                    user = User(
                        email=f"customer_wa_{_uuid.uuid4().hex[:12]}@serviceos.internal",
                        phone=phone,
                        full_name=draft_model.customer_name or self.display_name or "WhatsApp Customer",
                        role="customer",
                        tenant_id=None,
                        is_active=True,
                        is_verified=True,
                        onboarding_complete=False,
                        meta={"registration_source": "whatsapp_booking"},
                    )
                    self.db.add(user)
                    await self.db.flush()
                self.customer_id = user.id
                draft_model.customer_id = user.id
                draft_model.customer_phone = draft_model.customer_phone or phone
                if self.session_id:
                    ai_session = await self.db.get(AIConversationSession, _uuid.UUID(self.session_id))
                    if ai_session:
                        ai_session.customer_id = user.id
                await self.db.flush()
            elif not self.customer_id and bypass_instagram_phone:
                # Development/staging only: Instagram provides a stable,
                # page-scoped sender id but no phone number. Create the
                # customer only after the sender explicitly confirms the
                # otherwise-complete booking, so abandoned conversations do
                # not create incomplete customer or booking records.
                import hashlib

                sender_id = str(self.channel_user_id or "").strip()
                if not sender_id:
                    return {
                        "confirmed": False,
                        "error": "Your Instagram identity could not be verified.",
                    }
                draft_model = await self.db.get(HomeServiceBookingDraft, draft_uuid)
                if not draft_model:
                    return {"confirmed": False, "error": "Booking draft not found."}
                address = draft_model.address_snapshot or {}
                if not (
                    address.get("address_line_1")
                    and draft_model.city
                    and draft_model.zipcode
                ):
                    return {
                        "confirmed": False,
                        "error": "Collect the complete service address and postal code before confirming.",
                    }
                identity_hash = hashlib.sha256(
                    f"instagram:{sender_id}".encode("utf-8")
                ).hexdigest()[:20]
                synthetic_email = f"customer_ig_{identity_hash}@serviceos.internal"
                user = (await self.db.execute(
                    select(User).where(User.email == synthetic_email).limit(1)
                )).scalars().first()
                if not user:
                    user = User(
                        email=synthetic_email,
                        phone=None,
                        full_name=(
                            draft_model.customer_name
                            or self.display_name
                            or "Instagram Customer"
                        ),
                        role="customer",
                        tenant_id=None,
                        is_active=True,
                        is_verified=True,
                        onboarding_complete=False,
                        meta={
                            "registration_source": "instagram_booking_dev",
                            "instagram_identity_hash": identity_hash,
                            "phone_verification_bypassed": True,
                        },
                    )
                    self.db.add(user)
                    await self.db.flush()
                self.customer_id = user.id
                draft_model.customer_id = user.id
                if self.session_id:
                    ai_session = await self.db.get(
                        AIConversationSession, _uuid.UUID(self.session_id)
                    )
                    if ai_session:
                        ai_session.customer_id = user.id
                await self.db.flush()
            existing = await booking_service.get_booking_draft(draft_uuid, self.customer_id)
            if existing.get("status") != "confirmed":
                await booking_service.mark_ready_for_confirmation(draft_uuid, self.customer_id)
            result = await HomeServiceFinalCreationService(self.db).finalize(
                draft_id=draft_uuid,
                customer_id=self.customer_id,
                idempotency_key=f"social:{self.session_id or self.customer_id}:{draft_id}",
                request_id=f"social:{self.session_id or 'chat'}",
                source_channel=self.channel,
                source_actor_id=self.channel_user_id,
            )
            await self.db.commit()
            return {"confirmed": True, **result}
        except ServiceOSException as exc:
            # Expected domain rejections are safe and useful to the customer.
            # Hiding RATE_LIMITED / duplicate / missing-detail failures behind
            # "could not be confirmed" made the button look broken and gave
            # neither the customer nor QA a next step.
            logger.info(
                "backend_tools.confirm_booking_rejected",
                error_code=exc.error_code,
                draft_id=draft_id,
                channel=self.channel,
            )
            if exc.error_code == "RATE_LIMITED":
                message = "Too many confirmation attempts. Please wait a little and try again."
            elif exc.error_code in {"DUPLICATE_ACTIVE_BOOKING", "REQUIRED_FIELD_MISSING"}:
                message = exc.detail
                if exc.resolution:
                    message = f"{message} {exc.resolution}"
            else:
                message = "The booking could not be confirmed. Review the details and try again."
            return {"confirmed": False, "error": message, "error_code": exc.error_code}
        except Exception as exc:
            logger.exception(
                "backend_tools.confirm_booking_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                draft_id=draft_id,
                channel=self.channel,
            )
            return {"confirmed": False, "error": "The booking could not be confirmed. Review the details and try again."}

    # ── Sprint 17 — Coaching Appointment Draft tools ─────────────────────────

    async def _tool_start_coaching_appointment_draft(
        self,
        category_slug: str,
        offering_slug: str,
    ) -> dict:
        """
        Create an appointment draft for a Coaching / IELTS offering.
        Called when customer clearly wants to book a coaching class or demo.
        Returns draft_id (opaque to DeepSeek) and required_fields list.
        DeepSeek must NOT select slots, decide fee, or create appointments.
        """
        try:
            from app.engines.coaching_appointment.service import CoachingAppointmentFlowService
            import uuid as _uuid

            ai_session_id = _uuid.UUID(self.session_id) if self.session_id else None
            svc    = CoachingAppointmentFlowService(db=self.db)
            result = await svc.start_appointment_draft(
                customer_id=self.customer_id,
                ai_session_id=ai_session_id,
                category_slug=category_slug,
                offering_slug=offering_slug,
            )
            return {
                "draft_id":       result["id"],
                "offering_name":  result.get("offering_name"),
                "required_fields": result.get("required_fields", []),
                "fee_type":       result.get("fee_type"),
                "draft_status":   result.get("status"),
                "message":        f"Appointment draft started for {result.get('offering_name')}. I need a few details.",
            }
        except Exception as exc:
            logger.warning("backend_tools.start_coaching_draft.failed", error=str(exc))
            return {"error": str(exc), "draft_id": None}

    async def _tool_get_coaching_draft_status(
        self,
        draft_id: str,
    ) -> dict:
        """
        Get current status and missing fields for a coaching appointment draft.
        Use to know what information still needs to be collected.
        """
        try:
            from app.engines.coaching_appointment.service import CoachingAppointmentFlowService
            import uuid as _uuid

            svc    = CoachingAppointmentFlowService(db=self.db)
            result = await svc.get_appointment_draft(
                draft_id=_uuid.UUID(draft_id),
                customer_id=self.customer_id,
            )
            return {
                "draft_status":     result.get("status"),
                "missing_fields":   result.get("missing_fields", []),
                "location_status":  result.get("location_status"),
                "slot_status":      result.get("slot_status"),
                "preferred_mode":   result.get("preferred_mode"),
                "city":             result.get("city"),
                "selected_date":    result.get("selected_date"),
            }
        except Exception as exc:
            logger.warning("backend_tools.get_coaching_draft_status.failed", error=str(exc))
            return {"error": "Unable to retrieve draft status.", "draft_status": None}

    async def _tool_update_coaching_appointment_draft(
        self,
        draft_id: str,
        **fields,
    ) -> dict:
        """
        Save student/appointment fields collected from conversation.
        Pass only fields the student has explicitly stated.
        NEVER include fee, slot_id, tenant_id, or commission.
        """
        try:
            from app.engines.coaching_appointment.service import CoachingAppointmentFlowService
            import uuid as _uuid

            svc    = CoachingAppointmentFlowService(db=self.db)
            result = await svc.update_draft_fields(
                draft_id=_uuid.UUID(draft_id),
                customer_id=self.customer_id,
                payload=fields,
            )
            return {
                "draft_status":   result.get("status"),
                "missing_fields": result.get("missing_fields", []),
                "updated":        True,
                "updated_fields": result.get("updated_fields", []),
                "message":        "Details saved.",
            }
        except Exception as exc:
            logger.warning("backend_tools.update_coaching_draft.failed", error=str(exc))
            return {"error": str(exc), "updated": False}

    async def _tool_find_coaching_centers(
        self,
        draft_id: str,
    ) -> dict:
        """
        Find bookable coaching centers for the appointment.
        Call this AFTER student has provided city/mode.
        Backend queries real providers — no fake centers.
        Returns safe center list with business_name, rating, city.
        """
        try:
            from app.engines.coaching_appointment.service import CoachingAppointmentFlowService
            import uuid as _uuid

            svc    = CoachingAppointmentFlowService(db=self.db)
            result = await svc.find_bookable_centers(
                draft_id=_uuid.UUID(draft_id),
                customer_id=self.customer_id,
            )
            return {
                "available":             result.get("available", False),
                "available_center_count": result.get("available_center_count", 0),
                "centers":               result.get("centers", []),
                "location_status":       result.get("location_status"),
                "draft_status":          result.get("status"),
                "message":               result.get("message"),
            }
        except Exception as exc:
            logger.warning("backend_tools.find_coaching_centers.failed", error=str(exc))
            return {"available": False, "centers": [], "message": "Unable to find centers."}

    async def _tool_get_coaching_appointment_slots(
        self,
        draft_id: str,
        preferred_date: str | None = None,
    ) -> dict:
        """
        Find next available appointment slots for the coaching offering.
        If requested date is full, backend finds next available slots.
        Returns backend-approved slots only. DeepSeek must NOT invent slots.
        Include conversion hint if requested date is unavailable.
        """
        try:
            from app.engines.coaching_appointment.service import CoachingAppointmentFlowService
            import uuid as _uuid

            svc    = CoachingAppointmentFlowService(db=self.db)
            result = await svc.find_next_available_slots(
                draft_id=_uuid.UUID(draft_id),
                customer_id=self.customer_id,
                preferred_date=preferred_date,
                search_days=14,
            )
            next_slots = result.get("next_available_slots", [])
            requested_ok = result.get("requested_date_available", False)
            return {
                "requested_date_available": requested_ok,
                "requested_date":           result.get("requested_date"),
                "next_available_slots":     next_slots,
                "fallback_available":       result.get("fallback_available", False),
                "message":                  result.get("message"),
                "assistant_conversion_hint": result.get("assistant_conversion_hint"),
                "draft_status":             result.get("status"),
            }
        except Exception as exc:
            logger.warning("backend_tools.get_coaching_slots.failed", error=str(exc))
            return {
                "requested_date_available": False,
                "next_available_slots": [],
                "message": "Unable to retrieve slots. Please try again.",
            }

    # ── Sprint 18 — Real Estate Lead Draft tools ─────────────────────────────

    async def _tool_start_real_estate_lead_draft(
        self,
        category_slug: str,
        offering_slug: str,
    ) -> dict:
        """
        Create a real estate lead draft when customer wants to buy/rent/sell property.
        Call this when intent is clearly real estate (buy house, rent flat, sell plot, etc.).
        Returns draft_id (opaque to DeepSeek) and required_fields list.
        DeepSeek must NOT select providers, decide prices, or create leads.
        """
        try:
            from app.engines.real_estate_lead.service import RealEstateLeadFlowService
            import uuid as _uuid

            ai_session_id = _uuid.UUID(self.session_id) if self.session_id else None
            svc    = RealEstateLeadFlowService(db=self.db)
            result = await svc.start_lead_draft(
                customer_id   = self.customer_id,
                ai_session_id = ai_session_id,
                category_slug = category_slug,
                offering_slug = offering_slug,
            )
            return {
                "draft_id":        result["id"],
                "offering_name":   result.get("offering_name"),
                "required_fields": result.get("required_fields", []),
                "draft_status":    result.get("status"),
                "message":         f"Lead draft started for {result.get('offering_name')}. I need a few details.",
            }
        except Exception as exc:
            logger.warning("backend_tools.start_real_estate_draft.failed", error=str(exc))
            return {"error": str(exc), "draft_id": None}

    async def _tool_get_real_estate_draft_status(
        self,
        draft_id: str,
    ) -> dict:
        """
        Get current status and missing fields for a real estate lead draft.
        Use to know what information still needs to be collected.
        """
        try:
            from app.engines.real_estate_lead.service import RealEstateLeadFlowService
            import uuid as _uuid

            svc    = RealEstateLeadFlowService(db=self.db)
            result = await svc.get_lead_draft(
                draft_id    = _uuid.UUID(draft_id),
                customer_id = self.customer_id,
            )
            return {
                "draft_status":   result.get("status"),
                "missing_fields": result.get("missing_fields", []),
                "lead_intent":    result.get("lead_intent"),
                "property_type":  result.get("property_type"),
                "city":           result.get("city"),
                "locality":       result.get("locality"),
            }
        except Exception as exc:
            logger.warning("backend_tools.get_real_estate_draft_status.failed", error=str(exc))
            return {"error": "Unable to retrieve draft status.", "draft_status": None}

    async def _tool_update_real_estate_lead_draft(
        self,
        draft_id: str,
        **fields,
    ) -> dict:
        """
        Save customer-provided fields into the real estate lead draft.
        Pass only fields the customer has explicitly stated.
        NEVER include provider_id, agent_id, commission, or price valuation.
        Allowed: lead_intent, property_type, city, locality, zipcode,
                 budget_min, budget_max, rent_min, rent_max, bedrooms,
                 furnishing, customer_name, customer_phone, customer_email,
                 preferred_contact_time, notes.
        """
        try:
            from app.engines.real_estate_lead.service import RealEstateLeadFlowService
            import uuid as _uuid

            svc    = RealEstateLeadFlowService(db=self.db)
            result = await svc.update_draft_fields(
                draft_id    = _uuid.UUID(draft_id),
                customer_id = self.customer_id,
                payload     = fields,
            )
            return {
                "draft_status":   result.get("status"),
                "missing_fields": result.get("missing_fields", []),
                "updated":        True,
                "updated_fields": result.get("updated_fields", []),
                "message":        "Details saved.",
            }
        except Exception as exc:
            logger.warning("backend_tools.update_real_estate_draft.failed", error=str(exc))
            return {"error": str(exc), "updated": False}

    async def _tool_find_real_estate_providers(
        self,
        draft_id: str,
    ) -> dict:
        """
        Find bookable real estate providers for the lead.
        Call AFTER customer has provided city/locality and lead_intent.
        Backend queries real providers — never fake agents or listings.
        Returns safe provider info with match_reason.
        If no exact match, returns city-level fallback with assistant_conversion_hint.
        """
        try:
            from app.engines.real_estate_lead.service import RealEstateLeadFlowService
            import uuid as _uuid

            svc    = RealEstateLeadFlowService(db=self.db)
            result = await svc.find_eligible_providers(
                draft_id    = _uuid.UUID(draft_id),
                customer_id = self.customer_id,
            )
            fallback_hint = None
            if not result.get("available") and result.get("fallback_available"):
                fallback_hint = {
                    "type":        "suggest_fallback_callback",
                    "message_key": "no_exact_match_city_level_available",
                    "city":        result.get("fallback_providers", [{}])[0].get("city") if result.get("fallback_providers") else None,
                }
            return {
                "available":               result.get("available", False),
                "available_provider_count": result.get("available_provider_count", 0),
                "matched_by":              result.get("matched_by"),
                "providers":               result.get("providers", []),
                "fallback_available":      result.get("fallback_available", False),
                "fallback_providers":      result.get("fallback_providers", []),
                "message":                 result.get("message"),
                "draft_status":            result.get("status"),
                "assistant_conversion_hint": fallback_hint,
            }
        except Exception as exc:
            logger.warning("backend_tools.find_real_estate_providers.failed", error=str(exc))
            return {"available": False, "providers": [], "message": "Unable to find providers."}

    async def _tool_get_real_estate_lead_summary(
        self,
        draft_id: str,
    ) -> dict:
        """
        Build and return the lead summary for customer confirmation.
        Call after required fields are collected and providers found/fallback ready.
        Returns structured summary + lead score + ready_for_confirmation flag.
        Backend calculates score — DeepSeek must NOT invent scores or prices.
        """
        try:
            from app.engines.real_estate_lead.service import RealEstateLeadFlowService
            import uuid as _uuid

            svc    = RealEstateLeadFlowService(db=self.db)
            result = await svc.build_lead_summary(
                draft_id    = _uuid.UUID(draft_id),
                customer_id = self.customer_id,
            )
            summary = result.get("summary", {})
            score   = summary.get("lead_score", {})
            return {
                "summary":               summary,
                "lead_score_label":      score.get("score_label"),
                "lead_score":            score.get("score"),
                "missing_fields":        [],
                "ready_for_confirmation": True,
                "draft_status":          summary.get("status"),
                "message":               "Your inquiry summary is ready. Please review and confirm.",
            }
        except Exception as exc:
            logger.warning("backend_tools.get_real_estate_summary.failed", error=str(exc))
            return {
                "summary": {},
                "ready_for_confirmation": False,
                "message": "Unable to build summary. Please try again.",
            }

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _log_tool_call(
        self,
        tool_name: str,
        input_params: dict,
        output_data: Any,
        success: bool,
        latency_ms: int,
    ) -> None:
        """Persist an AIToolCallLog row."""
        try:
            from app.engines.ai_conversation.models import AIToolCallLog
            log = AIToolCallLog(
                id=uuid.uuid4(),
                session_id=uuid.UUID(self.session_id) if self.session_id else None,
                tool_name=tool_name,
                input_params=input_params,
                output_data=output_data if isinstance(output_data, dict) else None,
                success=success,
                latency_ms=latency_ms,
            )
            self.db.add(log)
            await self.db.flush()
        except Exception as exc:
            logger.warning("backend_tools.log_failed", error=str(exc))
