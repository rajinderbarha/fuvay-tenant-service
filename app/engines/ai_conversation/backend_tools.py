"""Sprint 15 — Backend tool executor wired to real ServiceOS data (not mocked)."""
from __future__ import annotations
import json
import time
import uuid
from typing import Any

import structlog
from sqlalchemy import select, and_, desc, func, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger("ai_conversation.tools")


class BackendToolExecutor:
    """
    Executes tool calls from DeepSeek, fetching data from real ServiceOS backend.

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
                 session_id: str | None = None, zipcode: str | None = None):
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
        """Fetch real customer bookings from the bookings table."""
        if not self.customer_id:
            return {"bookings": [], "note": "Please log in to view your bookings."}

        try:
            from app.engines.booking.models import Booking
            limit = min(limit, 10)
            q = (
                select(Booking)
                .where(Booking.customer_id == self.customer_id)
                .order_by(desc(Booking.created_at))
                .limit(limit)
            )
            rows = (await self.db.execute(q)).scalars().all()
            if not rows:
                return {"bookings": [], "note": "No bookings found."}
            return {
                "bookings": [
                    {
                        "id":           str(r.id),
                        "status":       r.status,
                        "service_name": r.service_name if hasattr(r, "service_name") else "Service",
                        "scheduled_at": r.scheduled_at.isoformat() if hasattr(r, "scheduled_at") and r.scheduled_at else None,
                        "created_at":   r.created_at.isoformat() if r.created_at else None,
                    }
                    for r in rows
                ],
                "total": len(rows),
            }
        except Exception as exc:
            logger.warning("backend_tools.bookings_failed", error=str(exc))
            return {"bookings": [], "note": "Unable to load bookings at this time."}

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

    @staticmethod
    def _still_needed(draft_dict: dict) -> list[str]:
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
        return [
            f for f in draft_dict.get("required_fields", [])
            if not value_by_field.get(f) and f not in BackendToolExecutor._CHAT_UNASKABLE_FIELDS
        ]

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
            svc = HomeServiceChatbotBookingService(db=self.db)
            result = await svc.start_booking_draft(
                customer_id=self.customer_id,
                ai_session_id=ai_session_id,
                category_slug=category_slug,
                offering_slug=offering_slug,
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

            svc = HomeServiceChatbotBookingService(db=self.db)
            result = await svc.update_draft_fields(
                draft_id=_uuid.UUID(draft_id),
                customer_id=self.customer_id,
                payload=fields,
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
            result = await svc.resolve_price_estimate(
                draft_id=_uuid.UUID(draft_id),
                customer_id=self.customer_id,
            )
            snap = result.get("price_snapshot", {})
            return {
                "display_price":  snap.get("display_price"),
                "pricing_model":  snap.get("pricing_model"),
                "note":           snap.get("note"),
                "currency":       snap.get("currency", "INR"),
                "draft_status":   result.get("draft_status"),
            }
        except Exception as exc:
            logger.warning("backend_tools.price_estimate_failed", error=str(exc))
            return {"error": "Unable to estimate price.", "display_price": None}

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
