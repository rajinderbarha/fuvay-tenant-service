"""Sprint 16 — HomeServiceChatbotBookingService.

15 public methods covering the full booking draft lifecycle.

Rules:
- Backend is source of truth (pricing, serviceability, providers)
- DeepSeek only collects field values — never decides anything
- No final job assignment in this sprint (Sprint 19)
- Required fields driven by MasterOffering flags, not hardcoded
"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import and_, desc, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.home_service_booking.constants import (
    ACTOR_AI, ACTOR_BACKEND, ACTOR_CUSTOMER, ACTOR_SYSTEM,
    ALLOWED_PHOTO_TYPES, DRAFT_EXPIRY_HOURS, DRAFT_MAX_PHOTOS,
    DRAFT_STATUS_CANCELLED, DRAFT_STATUS_COLLECTING_DETAILS,
    DRAFT_STATUS_CONFIRMED, DRAFT_STATUS_DRAFT, DRAFT_STATUS_EXPIRED,
    DRAFT_STATUS_FAILED, DRAFT_STATUS_PRICE_ESTIMATED,
    DRAFT_STATUS_PROVIDER_MATCHED, DRAFT_STATUS_READY_FOR_CONFIRMATION,
    DRAFT_STATUS_SERVICEABILITY_CHECKED, EVENT_DRAFT_CANCELLED,
    EVENT_DRAFT_CONFIRMED, EVENT_DRAFT_CREATED, EVENT_DRAFT_FAILED,
    EVENT_FIELD_COLLECTED, EVENT_PHOTO_UPLOADED, EVENT_PHOTO_REMOVED, EVENT_PRICE_ESTIMATED,
    EVENT_PROVIDER_MATCHED, EVENT_PROVIDER_SELECTED,
    EVENT_SERVICEABILITY_CHECKED, EVENT_SUMMARY_GENERATED,
    ERR_ADDRESS_REQUIRED, ERR_BRAND_REQUIRED, ERR_CATEGORY_INVALID,
    ERR_CONFIRMATION_NOT_READY, ERR_DRAFT_ACCESS_DENIED,
    ERR_DRAFT_NOT_FOUND, ERR_DRAFT_TERMINAL, ERR_NO_PROVIDER_AVAILABLE,
    ERR_PROVIDER_ENTITLEMENT_CHANGED,
    ERR_OFFERING_INVALID, ERR_PHOTO_UPLOAD_FAILED,
    ERR_PRICE_ESTIMATE_FAILED, ERR_PROVIDER_NOT_IN_AREA,
    ERR_REQUIRED_FIELD_MISSING, ERR_TYPE_REQUIRED, MAX_PHOTO_SIZE_BYTES,
    ERR_INVALID_JOB_TYPE_FOR_SERVICE,
    PRICE_STATUS_ESTIMATED, PRICE_STATUS_FAILED, PRICE_STATUS_PENDING,
    PRICING_MODEL_FIXED, PRICING_MODEL_VISIT_FEE,
    PROVIDER_MATCH_MATCHED, PROVIDER_MATCH_NO_PROVIDER,
    PROVIDER_MATCH_PENDING, SVCABILITY_NOT_SERVICEABLE,
    SVCABILITY_PENDING, SVCABILITY_SERVICEABLE, TERMINAL_STATUSES,
)
from app.engines.home_service_booking.models import (
    HomeServiceBookingDraft,
    HomeServiceBookingDraftEvent,
)
from app.engines.home_service_booking.serviceability_service import (
    HomeServiceServiceabilityService,
)
from app.engines.home_service_booking.provider_matching import (
    find_bookable_home_service_providers,
)
from app.exceptions import ServiceOSException

logger = structlog.get_logger("home_service.booking.service")
utcnow = lambda: datetime.now(timezone.utc)


class HomeServiceChatbotBookingService:
    """
    Manages the full booking draft lifecycle for Home Services.
    All business decisions (pricing, serviceability, provider selection)
    are made here. DeepSeek only supplies text/field values via the chat layer.
    """

    def __init__(self, db: AsyncSession, request_id: str = "—"):
        self.db         = db
        self.request_id = request_id
        self._svc_svc   = HomeServiceServiceabilityService(db)

    # ══════════════════════════════════════════════════════════════════════════
    # 1. START DRAFT
    # ══════════════════════════════════════════════════════════════════════════

    async def start_booking_draft(
        self,
        customer_id: uuid.UUID | None,
        ai_session_id: uuid.UUID | None,
        category_slug: str,
        offering_slug: str,
    ) -> dict:
        """Create a new booking draft for a Home Service offering."""
        from app.engines.admin_catalog.models import ServiceCategory, MasterService

        # Resolve category
        cat = (await self.db.execute(
            select(ServiceCategory).where(
                ServiceCategory.is_active.is_(True),
                ServiceCategory.slug == category_slug,
            )
        )).scalars().first()
        if not cat:
            raise ServiceOSException(
                ERR_CATEGORY_INVALID,
                f"Category '{category_slug}' is not available.",
                status_code=422,
            )

        # Resolve offering.
        #
        # HS7 fix: this previously queried `MasterOffering`, a legacy table
        # that is completely empty in the real database (confirmed via
        # direct query — 0 rows). Every customer catalog surface actually
        # in use (admin catalog, HS6/HS6B provider-first matching/pricing,
        # `/v1/catalog/master/services`) reads from `MasterService`, so
        # `start_booking_draft` — the very first step of the customer
        # booking flow — could never succeed for any real service. Fixed to
        # resolve against the real, populated `MasterService` table.
        offering = (await self.db.execute(
            select(MasterService).where(
                MasterService.is_active.is_(True),
                MasterService.category_id == cat.id,
                MasterService.slug == offering_slug,
            )
        )).scalars().first()
        if not offering:
            raise ServiceOSException(
                ERR_OFFERING_INVALID,
                f"Offering '{offering_slug}' is not available under '{category_slug}'.",
                status_code=422,
            )

        # A category can carry orphaned/legacy MasterService rows
        # (is_active=True, but no tenant has ever actually published an
        # offering against them -- confirmed live, e.g. a leftover "AC
        # Service" entry alongside the real "AC Repair"/"AC Installation"
        # tenant offerings). Failing closed here, not just at the DeepSeek
        # tool-listing layer, means a draft can never be started for
        # something no tenant could ever actually fulfill, regardless of
        # how the offering_slug was supplied.
        from app.engines.admin_catalog.models import TenantService, ServiceIssueMapping
        has_publisher = (await self.db.execute(
            select(TenantService.id).where(
                TenantService.master_service_id == offering.id,
                TenantService.is_enabled.is_(True),
                TenantService.is_active.is_(True),
                TenantService.setup_status == "published",
            ).limit(1)
        )).scalars().first()
        if not has_publisher:
            raise ServiceOSException(
                ERR_OFFERING_INVALID,
                f"Offering '{offering_slug}' is not currently offered by any provider.",
                status_code=422,
            )

        # A published offering can still have ZERO real problem/issue-type
        # wiring (confirmed live: "AC Service" is published by a tenant but
        # has no ServiceIssueMapping rows at all) -- DeepSeek's
        # get_service_problems would then always return empty, job_type_id
        # could never resolve, and the whole question-flow would
        # permanently fall back to plain-text chat. Same fail-closed
        # principle as the publisher check above, just for catalog content
        # completeness instead of tenant enablement.
        has_problems = (await self.db.execute(
            select(ServiceIssueMapping.id).where(
                ServiceIssueMapping.master_service_id == offering.id,
                ServiceIssueMapping.status == "active",
            ).limit(1)
        )).scalars().first()
        if not has_problems:
            raise ServiceOSException(
                ERR_OFFERING_INVALID,
                f"Offering '{offering_slug}' is not fully configured for booking yet.",
                status_code=422,
            )

        expires_at = utcnow() + timedelta(hours=DRAFT_EXPIRY_HOURS)
        draft = HomeServiceBookingDraft(
            id=uuid.uuid4(),
            customer_id=customer_id,
            ai_session_id=ai_session_id,
            category_id=cat.id,
            offering_id=offering.id,
            status=DRAFT_STATUS_DRAFT,
            serviceability_status=SVCABILITY_PENDING,
            price_status=PRICE_STATUS_PENDING,
            provider_match_status=PROVIDER_MATCH_PENDING,
            expires_at=expires_at,
        )

        self.db.add(draft)
        await self.db.flush()

        # Auto-fill city/zipcode/address from the customer's own default
        # address (via the existing _resolve_address_snapshot helper --
        # already used elsewhere on this service, just never called at
        # draft-creation time) rather than asking DeepSeek to collect city
        # in plain chat. The app already knows this the moment the customer
        # is logged in (same source Home's own zipcode/address display
        # uses); previously every draft asked "confirm your city" even
        # though the backend already had it, with no tap-to-select way to
        # answer -- just a redundant free-text round trip.
        if customer_id:
            from app.engines.serviceability.models import CustomerAddress
            addr = (await self.db.execute(
                select(CustomerAddress)
                .where(CustomerAddress.customer_id == customer_id, CustomerAddress.is_active == True)
                .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc())
                .limit(1)
            )).scalars().first()
            if addr:
                await self._resolve_address_snapshot(draft, addr.id)

        await self._emit_event(
            draft_id=draft.id,
            actor_type=ACTOR_CUSTOMER,
            event_type=EVENT_DRAFT_CREATED,
            new_value={"category_slug": category_slug, "offering_slug": offering_slug},
            message=f"Draft created for {offering.service_name}",
        )
        await self.db.commit()
        await self.db.refresh(draft)

        result = draft.to_dict()
        result["offering_name"]          = offering.service_name
        result["offering_slug"]          = offering.slug
        result["category_name"]          = cat.name
        result["category_slug"]          = cat.slug
        result["required_fields"]        = self._get_required_field_list(offering)
        result["pricing_model"]          = offering.pricing_model
        result["default_visit_fee"]      = float(offering.visit_fee)
        result["default_base_price"]     = float(offering.base_price)
        return result

    # ══════════════════════════════════════════════════════════════════════════
    # 2. GET DRAFT
    # ══════════════════════════════════════════════════════════════════════════

    async def get_booking_draft(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """Return a draft, enforcing customer ownership."""
        draft = await self._require_draft(draft_id, customer_id)
        return await self._enrich_draft(draft)

    async def get_booking_draft_by_ai_session(
        self,
        ai_session_id: uuid.UUID,
        customer_id: uuid.UUID,
    ) -> dict | None:
        """Resolve the customer's own non-terminal draft (if any) linked to
        an AI conversation session -- the Booking Assistant's own bootstrap
        call, used to resume a draft DeepSeek's tool call created mid-
        conversation. A genuinely missing route here (confirmed absent --
        the customer app has called this exact path since it was built,
        always hitting a raw framework 404) meant the Assistant crashed to
        a generic error on EVERY category tap, since "no draft yet" is the
        normal first-load state, not a real error. Returns None (never
        raises) when no matching draft exists -- that is a valid state, not
        a not-found error; ownership is enforced in the query itself rather
        than via `_require_draft`'s raise-on-missing behavior."""
        result = await self.db.execute(
            select(HomeServiceBookingDraft).where(
                HomeServiceBookingDraft.ai_session_id == ai_session_id,
                HomeServiceBookingDraft.customer_id == customer_id,
                HomeServiceBookingDraft.status.notin_(TERMINAL_STATUSES),
            ).order_by(HomeServiceBookingDraft.created_at.desc())
        )
        draft = result.scalars().first()
        if not draft:
            return None

        # A draft created against an offering that's since become
        # unpublished (or was always an orphaned catalog entry no tenant
        # ever offered -- confirmed live: "AC Service" alongside the real
        # "AC Repair"/"AC Installation") must never be silently resumed.
        # Without this, a customer's app can get permanently stuck re-
        # opening a dead conversation about an offering that structurally
        # has no admin-catalog wiring (no issue types, no job type), which
        # falls back to DeepSeek asking everything in free chat forever --
        # returning None here instead makes the app treat it as "no draft
        # yet" and start a genuinely fresh, bookable one.
        from app.engines.admin_catalog.models import TenantService
        has_publisher = (await self.db.execute(
            select(TenantService.id).where(
                TenantService.master_service_id == draft.offering_id,
                TenantService.is_enabled.is_(True),
                TenantService.is_active.is_(True),
                TenantService.setup_status == "published",
            ).limit(1)
        )).scalars().first()
        if not has_publisher:
            return None

        return await self._enrich_draft(draft)

    async def get_assistant_bootstrap(
        self, customer_id: uuid.UUID, category_slug: str, zipcode: str | None,
    ) -> dict:
        """Backend-first Booking Assistant bootstrap -- ISSUE-first (real
        customer intent: "what's wrong with your AC", never an internal
        offering/job-type split, and never Brand or any other follow-up
        attribute). Returns everything the Customer App needs to render
        the FIRST screen of a structured booking conversation without
        ever consulting DeepSeek: the category, the real zipcode-
        serviceable issues (see offering_catalog_service.list_serviceable_
        issues), and the customer's own resumable draft for this category,
        if one exists and is still genuinely bookable.

        Never includes another tenant's data, internal readiness reasons,
        or an issue whose only real offering isn't currently bookable in
        this zipcode."""
        from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues

        catalog = await list_serviceable_issues(self.db, category_slug, zipcode)
        issues = catalog.get("issues", [])

        resumable_draft = None
        if catalog.get("category_id"):
            result = await self.db.execute(
                select(HomeServiceBookingDraft).where(
                    HomeServiceBookingDraft.customer_id == customer_id,
                    HomeServiceBookingDraft.category_id == uuid.UUID(catalog["category_id"]),
                    HomeServiceBookingDraft.status.notin_(TERMINAL_STATUSES),
                ).order_by(HomeServiceBookingDraft.created_at.desc())
            )
            draft = result.scalars().first()
            if draft:
                # Same "still genuinely bookable" guard as the AI-session
                # resume path -- never resume a draft against an offering
                # that's since become unpublished or was never real. A
                # draft is resumable if ANY currently-serviceable issue
                # still resolves to the same master service it was
                # created against (an issue's own id can't be compared --
                # the draft only stores selected_problem_id once an issue
                # has actually been answered onto it, and a draft can
                # legitimately exist with no problem selected yet).
                offering_ids = {i["master_service_id"] for i in issues}
                if str(draft.offering_id) in offering_ids:
                    resumable_draft = await self._enrich_draft(draft)

        return {
            "schema_version": 1,
            "category": {"id": catalog.get("category_id"), "slug": catalog.get("category_slug"), "name": catalog.get("category")},
            "zipcode": zipcode,
            "serviceable": len(issues) > 0,
            "issues": [
                {
                    "id": i["id"], "label": i["label"],
                    "selection_mode": i["selection_mode"], "compatibility_group": i["compatibility_group"],
                }
                for i in issues
            ],
            "resumable_draft": resumable_draft,
            "current_stage": "issue_selection" if resumable_draft is None else "questions",
        }

    async def select_issue(
        self, customer_id: uuid.UUID, ai_session_id: uuid.UUID | None,
        category_slug: str, zipcode: str | None, issue_id: str,
        additional_issue_ids: list[str] | None = None,
    ) -> dict:
        """Canonical issue-selection operation (Phase 7): validates the
        issue(s) against the SAME real, zipcode-serviceable list bootstrap
        just returned, resolves the real master service, creates (or
        reuses, via start_booking_draft's existing ai_session_id
        idempotency) the canonical draft, stores `selected_problem_id` via
        the exact same `update_draft_fields` path a manual chat turn uses
        (which already resolves job_type_id/workflow from it), and returns
        the resulting question-flow envelope. DeepSeek is never involved
        anywhere in this call; the frontend never infers the offering from
        the issue label.

        Multiple problems: a customer may report more than one real issue
        at once (e.g. both "AC Not Cooling" and "Water Leakage" on the
        same unit). All selected issue ids are stored on the draft's
        existing `service_option_ids_json` column (already modeled, never
        previously wired to this flow) for full customer-safe visibility
        in Booking Review / final records. Job type/workflow resolution
        still keys off exactly ONE canonical problem -- the first selected
        issue -- so every additional issue must resolve to that SAME
        master service; issues spanning genuinely different services
        (e.g. "New AC Installation" + "AC Not Cooling") have no single
        shared workflow and are rejected rather than silently merged or
        silently dropped."""
        from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues
        from app.engines.home_service_booking.question_flow_service import QuestionFlowService

        catalog = await list_serviceable_issues(self.db, category_slug, zipcode)
        issues = catalog.get("issues", [])
        issues_by_id = {i["id"]: i for i in issues}

        all_ids = [issue_id, *(additional_issue_ids or [])]

        # Reject duplicate ids outright (AC-ISSUE-DATA-01 section 3) --
        # never silently collapsed, so a client bug that sends the same id
        # twice is surfaced rather than masked.
        if len(all_ids) != len(set(all_ids)):
            raise ServiceOSException(
                "QI_DUPLICATE_ISSUE_ID",
                "The same issue was submitted more than once.",
                status_code=422,
            )

        matched_list = []
        for iid in all_ids:
            # A hidden/deprecated issue (customer_visible=False -- e.g. the
            # legacy ac-gas-refilling entry point superseded by ac-service's
            # "Gas Refill Needed") is simply absent from `issues_by_id`,
            # exactly like an invented or out-of-area id: never selectable
            # for a NEW draft, regardless of whether it was real once.
            matched = issues_by_id.get(iid)
            if matched is None:
                raise ServiceOSException(
                    ERR_OFFERING_INVALID,
                    "This issue is not available for booking right now.",
                    status_code=422,
                )
            matched_list.append(matched)

        if len(matched_list) > 1:
            # An "exclusive" issue (e.g. New AC Installation) can never be
            # combined with anything else, regardless of compatibility
            # group -- it represents a whole distinct service intent, not
            # one of several diagnostic symptoms on the same unit.
            if any(m["selection_mode"] == "exclusive" for m in matched_list):
                raise ServiceOSException(
                    "QI_EXCLUSIVE_ISSUE_COMBINED",
                    "This service must be booked on its own, not combined with other issues.",
                    status_code=422,
                )
            distinct_groups = {m["compatibility_group"] for m in matched_list}
            if len(distinct_groups) > 1:
                raise ServiceOSException(
                    "QI_MIXED_ISSUE_SERVICES",
                    "These issues can't be booked together yet -- please book them as separate requests.",
                    status_code=422,
                )

        primary = matched_list[0]
        draft_dict = await self.start_booking_draft(
            customer_id=customer_id, ai_session_id=ai_session_id,
            category_slug=category_slug, offering_slug=primary["master_service_slug"],
        )
        draft_id = uuid.UUID(draft_dict["id"])
        await self.update_draft_fields(
            draft_id=draft_id, customer_id=customer_id,
            payload={
                "selected_problem_id": primary["id"],
                # Real bug fixed here: `issue_summary` is an unconditionally
                # REQUIRED field in `_compute_missing_fields`, but the
                # issue-first flow never populated it -- so every booking
                # failed confirmation with "Missing required fields:
                # issue_summary", even though the customer had explicitly
                # told us exactly what was wrong. The selected issue label(s)
                # ARE the issue summary; there is nothing further to ask.
                "issue_summary": " + ".join(m["label"] for m in matched_list),
            },
        )

        if len(matched_list) > 1:
            draft = await self._require_draft(draft_id, customer_id)
            draft.service_option_ids_json = [m["id"] for m in matched_list]
            draft.updated_at = utcnow()
            await self.db.commit()

        qf = QuestionFlowService(db=self.db)
        envelope = await qf.get_current_question(draft_id=draft_id, customer_id=customer_id)
        return {"draft_id": str(draft_id), "envelope": envelope, "selected_issue_ids": [m["id"] for m in matched_list]}

    # ══════════════════════════════════════════════════════════════════════════
    # 3. UPDATE DRAFT FIELDS
    # ══════════════════════════════════════════════════════════════════════════

    async def update_draft_fields(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        payload: dict,
    ) -> dict:
        """Merge customer-supplied fields into the draft. Backend re-validates."""
        draft = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)

        updatable = [
            "customer_name", "customer_phone",
            "city", "zipcode",
            "issue_summary", "issue_details",
            "preferred_date", "preferred_time_window",
        ]
        uuid_fields = ["offering_type_id", "brand_id", "address_id"]
        changes: dict = {}

        # HOME-SERVICES-RUNTIME-SAFETY Phase 2A.2 (spec section 7): if the
        # Master Service itself changes, any Job Type/Problem/Blueprint
        # context resolved against the OLD service is now stale and must be
        # cleared, never carried over to the new one -- along with matching/
        # price snapshots that were computed against the old service.
        if "offering_id" in payload and payload["offering_id"]:
            new_offering_id = uuid.UUID(str(payload["offering_id"]))
            if new_offering_id != draft.offering_id:
                draft.offering_id = new_offering_id
                draft.job_type_id = None
                draft.master_service_job_type_id = None
                draft.service_job_workflow_id = None
                draft.selected_problem_id = None
                draft.price_snapshot = None
                draft.selected_provider_snapshot = None
                draft.selected_tenant_id = None
                draft.provider_options = None
                draft.provider_match_status = PROVIDER_MATCH_PENDING
                draft.price_status = PRICE_STATUS_PENDING
                changes["offering_id"] = str(new_offering_id)
                changes["cleared_stale_context"] = True

        for field in updatable:
            if field in payload and payload[field] is not None:
                val = payload[field]
                # MODULE-L5-02: preferred_date is a DATE column; a raw string
                # ("2026-08-01") from the client crashed the UPDATE with an
                # asyncpg DataError ('str' has no attribute 'toordinal'). Parse
                # ISO date strings to a date object before persisting.
                if field == "preferred_date" and isinstance(val, str):
                    from datetime import date, datetime as _dt
                    try:
                        val = date.fromisoformat(val)
                    except ValueError:
                        val = _dt.fromisoformat(val).date()
                setattr(draft, field, val)
                changes[field] = payload[field]

        for field in uuid_fields:
            if field in payload and payload[field]:
                val = uuid.UUID(str(payload[field]))
                setattr(draft, field, val)
                changes[field] = str(val)

        # HOME-SERVICES-RUNTIME-SAFETY Phase 2A.2 (spec section 4): the
        # PREFERRED path is the customer's Problem/Intent selection --
        # selected_problem_id -> ServiceIssueMapping -> exact job_type_id.
        # This is what the real customer flow drives ("AC Not Cooling"),
        # never a raw job_type_id typed/guessed by the client. A direct
        # job_type_id is still accepted for non-problem actions (Install/
        # Uninstall/General Service) that don't go through a Problem at all,
        # per section 4's "or another proven catalog mapping" allowance --
        # both paths are validated identically via _resolve_job_type_snapshot.
        if "selected_problem_id" in payload and payload["selected_problem_id"]:
            problem_id = uuid.UUID(str(payload["selected_problem_id"]))
            from app.engines.admin_catalog.models import ServiceIssueMapping
            mapping = (await self.db.execute(
                select(ServiceIssueMapping).where(
                    ServiceIssueMapping.issue_type_id == problem_id,
                    ServiceIssueMapping.master_service_id == draft.offering_id,
                    ServiceIssueMapping.status == "active",
                    ServiceIssueMapping.deleted_at.is_(None),
                )
            )).scalars().first()
            if mapping is None:
                raise ServiceOSException(
                    "PROBLEM_NOT_AVAILABLE_FOR_SERVICE",
                    "The selected problem is not available for this service.",
                    status_code=422,
                )
            draft.selected_problem_id = problem_id
            changes["selected_problem_id"] = str(problem_id)
            if mapping.job_type_id is None:
                # This Problem applies to "all job types" -- it does NOT
                # resolve an EXACT Job Type (spec section 4: "mapping has an
                # exact Job Type for new canonical bookings"). Leave
                # job_type_id unresolved rather than guess; readiness will
                # report JOB_TYPE_REQUIRED until the customer/admin context
                # provides an exact one another way.
                draft.job_type_id = None
                draft.master_service_job_type_id = None
                draft.service_job_workflow_id = None
                changes["job_type_resolution"] = "problem_has_no_exact_job_type"
            else:
                await self._resolve_job_type_snapshot(draft, mapping.job_type_id)
                changes["job_type_id"] = str(draft.job_type_id) if draft.job_type_id else None
        elif "job_type_id" in payload and payload["job_type_id"]:
            job_type_id = uuid.UUID(str(payload["job_type_id"]))
            await self._resolve_job_type_snapshot(draft, job_type_id)
            changes["job_type_id"] = str(draft.job_type_id) if draft.job_type_id else None

        # Resolve address if address_id provided
        if "address_id" in payload and payload["address_id"]:
            await self._resolve_address_snapshot(draft, uuid.UUID(str(payload["address_id"])))
            changes["address_snapshot"] = draft.address_snapshot

        draft.status = DRAFT_STATUS_COLLECTING_DETAILS
        draft.updated_at = utcnow()

        if changes:
            await self._emit_event(
                draft_id=draft.id,
                actor_type=ACTOR_CUSTOMER,
                event_type=EVENT_FIELD_COLLECTED,
                new_value=changes,
                message=f"Customer updated {len(changes)} field(s)",
            )

        await self.db.commit()
        await self.db.refresh(draft)
        return await self._enrich_draft(draft)

    # ══════════════════════════════════════════════════════════════════════════
    # 4. SYNC DRAFT FROM AI SESSION
    # ══════════════════════════════════════════════════════════════════════════

    async def sync_draft_from_ai_session(
        self,
        ai_session_id: uuid.UUID,
    ) -> dict | None:
        """Pull collected_fields from an AI session into the linked draft."""
        from app.engines.ai_conversation.models import AIConversationSession

        session = (await self.db.execute(
            select(AIConversationSession).where(
                AIConversationSession.id == ai_session_id,
                AIConversationSession.is_active.is_(True),
            )
        )).scalars().first()
        if not session:
            return None

        draft = (await self.db.execute(
            select(HomeServiceBookingDraft).where(
                HomeServiceBookingDraft.ai_session_id == ai_session_id,
                HomeServiceBookingDraft.status.not_in(list(TERMINAL_STATUSES)),
            )
        )).scalars().first()
        if not draft:
            return None

        fields = session.collected_fields or {}
        changed = False

        simple_map = {
            "city": "city", "zipcode": "zipcode",
            "issue_summary": "issue_summary",
            "customer_name": "customer_name", "customer_phone": "customer_phone",
            "preferred_date": "preferred_date",
            "preferred_time_window": "preferred_time_window",
        }
        for ai_key, draft_key in simple_map.items():
            if fields.get(ai_key) and not getattr(draft, draft_key):
                setattr(draft, draft_key, fields[ai_key])
                changed = True

        if changed:
            draft.status = DRAFT_STATUS_COLLECTING_DETAILS
            draft.updated_at = utcnow()
            await self._emit_event(
                draft_id=draft.id,
                actor_type=ACTOR_AI,
                event_type=EVENT_FIELD_COLLECTED,
                new_value=fields,
                message="Fields synced from AI session",
            )
            await self.db.commit()
            await self.db.refresh(draft)

        return await self._enrich_draft(draft)

    # ══════════════════════════════════════════════════════════════════════════
    # 5. VALIDATE REQUIRED FIELDS
    # ══════════════════════════════════════════════════════════════════════════

    async def validate_required_fields(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None = None,
    ) -> dict:
        """Return validation result with missing field names."""
        draft   = await self._require_draft(draft_id, customer_id)
        offering = await self._get_offering(draft.offering_id)
        missing = self._compute_missing_fields(draft, offering)
        return {
            "valid": len(missing) == 0,
            "missing_fields": missing,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # 6. GET MISSING FIELDS
    # ══════════════════════════════════════════════════════════════════════════

    async def get_missing_fields(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None = None,
    ) -> list[str]:
        """Return a list of field names still needed to proceed."""
        draft    = await self._require_draft(draft_id, customer_id)
        offering = await self._get_offering(draft.offering_id)
        return self._compute_missing_fields(draft, offering)

    # ══════════════════════════════════════════════════════════════════════════
    # 7. CHECK SERVICEABILITY
    # ══════════════════════════════════════════════════════════════════════════

    async def check_serviceability(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """Run real serviceability check and update draft."""
        draft = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)

        if not draft.city:
            raise ServiceOSException(
                ERR_ADDRESS_REQUIRED,
                "City is required for serviceability check.",
                status_code=422,
            )

        result = await self._svc_svc.check(
            category_id=draft.category_id,
            offering_id=draft.offering_id,
            city=draft.city,
            zipcode=draft.zipcode,
        )

        draft.serviceability_status = (
            SVCABILITY_SERVICEABLE if result["serviceable"] else SVCABILITY_NOT_SERVICEABLE
        )
        if result["serviceable"]:
            draft.status = DRAFT_STATUS_SERVICEABILITY_CHECKED
        else:
            draft.failure_code    = result.get("reason_code")
            draft.failure_message = result.get("message")

        draft.updated_at = utcnow()
        await self._emit_event(
            draft_id=draft.id,
            actor_type=ACTOR_BACKEND,
            event_type=EVENT_SERVICEABILITY_CHECKED,
            new_value=result,
            message=result["message"],
        )
        await self.db.commit()
        await self.db.refresh(draft)
        return {**result, "draft_status": draft.status}

    # ══════════════════════════════════════════════════════════════════════════
    # 8. RESOLVE PRICE ESTIMATE
    # ══════════════════════════════════════════════════════════════════════════

    async def resolve_price_estimate(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """
        Compute price estimate using offering defaults + city-tier floor.
        Backend is source of truth. Frontend price is NEVER trusted.
        """
        draft    = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)
        offering = await self._get_offering(draft.offering_id)

        try:
            snapshot = await self._compute_price_snapshot(draft, offering)
            draft.price_snapshot = snapshot
            draft.price_status   = PRICE_STATUS_ESTIMATED
            draft.status         = DRAFT_STATUS_PRICE_ESTIMATED
            draft.updated_at     = utcnow()

            await self._emit_event(
                draft_id=draft.id,
                actor_type=ACTOR_BACKEND,
                event_type=EVENT_PRICE_ESTIMATED,
                new_value=snapshot,
                message=f"Price estimated: {snapshot.get('display_price')}",
            )
            await self.db.commit()
            await self.db.refresh(draft)
            return {"price_snapshot": snapshot, "draft_status": draft.status}

        except Exception as exc:
            logger.warning("home_service.price_estimate_failed", error=str(exc))
            draft.price_status = PRICE_STATUS_FAILED
            draft.updated_at   = utcnow()
            await self.db.commit()
            raise ServiceOSException(
                ERR_PRICE_ESTIMATE_FAILED,
                "Unable to estimate price at this time. Please try again.",
                status_code=503,
            )

    # ══════════════════════════════════════════════════════════════════════════
    # 9. FIND BOOKABLE PROVIDERS
    # ══════════════════════════════════════════════════════════════════════════

    async def find_bookable_providers(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """Find real bookable providers for the draft's city/zipcode."""
        draft = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)

        if not draft.city:
            raise ServiceOSException(
                ERR_ADDRESS_REQUIRED,
                "City is required before matching providers.",
                status_code=422,
            )

        providers = await find_bookable_home_service_providers(
            db=self.db,
            category_id=draft.category_id,
            offering_id=draft.offering_id,
            city=draft.city,
            zipcode=draft.zipcode,
            offering_type_id=draft.offering_type_id,
            brand_id=draft.brand_id,
        )

        if providers:
            draft.provider_options      = providers
            draft.provider_match_status = PROVIDER_MATCH_MATCHED
            draft.status                = DRAFT_STATUS_PROVIDER_MATCHED

            # Auto-select top provider
            if not draft.selected_tenant_id and providers:
                top = providers[0]
                draft.selected_tenant_id        = uuid.UUID(top["provider_ref"])
                draft.selected_provider_snapshot = top
        else:
            draft.provider_match_status = PROVIDER_MATCH_NO_PROVIDER

        draft.updated_at = utcnow()
        await self._emit_event(
            draft_id=draft.id,
            actor_type=ACTOR_BACKEND,
            event_type=EVENT_PROVIDER_MATCHED,
            new_value={"count": len(providers)},
            message=f"{len(providers)} provider(s) found",
        )
        await self.db.commit()
        await self.db.refresh(draft)

        if not providers:
            raise ServiceOSException(
                ERR_NO_PROVIDER_AVAILABLE,
                f"No providers available in {draft.city}. Try a nearby city.",
                status_code=422,
            )
        return {"providers": providers, "draft_status": draft.status}

    # ══════════════════════════════════════════════════════════════════════════
    # 10. SELECT PROVIDER
    # ══════════════════════════════════════════════════════════════════════════

    async def select_provider(
        self,
        draft_id: uuid.UUID,
        provider_ref: str,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """Customer selects a specific provider from the options list."""
        draft = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)

        options = draft.provider_options or []
        match   = next((p for p in options if p["provider_ref"] == provider_ref), None)
        if not match:
            raise ServiceOSException(
                ERR_PROVIDER_NOT_IN_AREA,
                "Selected provider is not available for this booking.",
                status_code=422,
            )

        draft.selected_tenant_id       = uuid.UUID(match["provider_ref"])
        draft.selected_provider_snapshot = match
        draft.updated_at               = utcnow()

        await self._emit_event(
            draft_id=draft.id,
            actor_type=ACTOR_CUSTOMER,
            event_type=EVENT_PROVIDER_SELECTED,
            new_value=match,
            message=f"Customer selected: {match.get('business_name')}",
        )
        await self.db.commit()
        await self.db.refresh(draft)
        return {"selected_provider": match, "draft_status": draft.status}

    # ══════════════════════════════════════════════════════════════════════════
    # 10B. PROVIDER-FIRST MATCHING + CUSTOMER PRICE CHOICE
    # ══════════════════════════════════════════════════════════════════════════
    # Corrects the list-based flow above (find_bookable_providers + select_provider,
    # which let the customer pick a provider manually from a list). The backend
    # now selects exactly one provider via full eligibility gating + scoring,
    # THEN computes that provider's Low/Mid/High price options. The customer
    # never sees or picks from a provider list in this flow.

    async def match_provider_and_price(
        self,
        *,
        category_id: uuid.UUID,
        master_service_id: uuid.UUID,
        city: str,
        zipcode: str | None,
        offering_type_id: uuid.UUID | None = None,
        brand_id: uuid.UUID | None = None,
        job_type_id: uuid.UUID | None = None,
        draft_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        reveal_internal_score: bool = False,
    ) -> dict:
        """Steps 3-8 of the corrected flow, atomically: find eligible providers,
        rank them, select the single best one, compute its price options, and
        compute a separate area comparison. Returns the ticket-required response
        shape. If draft_id is given, persists a snapshot onto the draft.

        Home Services scope guard: this entire flow — provider-first matching,
        Low/Mid/High bargain pricing, "customer pays provider directly" — is
        Home-Services-only. Raises VerticalFlowNotSupported for any other
        vertical (CA/professional services, IELTS/coaching, restaurants, real
        estate, education, listing/menu/subscription businesses)."""
        from app.engines.home_service_booking.matching_engine import (
            select_best_provider, get_area_market_comparison,
            build_customer_safe_provider, build_admin_provider, compute_price_tiers,
            assert_home_services_vertical, _round2,
        )
        from app.engines.admin_catalog.bargain_engine import BargainValidationError
        from app.engines.admin_catalog.models import BargainRule, ServicePricingRule, ServiceCategory

        category = await self.db.get(ServiceCategory, category_id)
        assert_home_services_vertical(category.vertical_type if category else None)

        # MODULE-L5-02: require a city before matching (a draft with no address
        # previously reached the matching engine and crashed with a NoneType
        # .strip() 500). Return the same clean error as serviceability-check.
        if not city:
            raise ServiceOSException(
                "HOME_BOOKING_ADDRESS_REQUIRED",
                "Please set your service address (city) before matching a provider.",
                status_code=422,
            )

        match = await select_best_provider(
            self.db, category_id=category_id, offering_id=master_service_id,
            city=city, zipcode=zipcode, offering_type_id=offering_type_id, brand_id=brand_id,
            job_type_id=job_type_id,
        )

        if not match or not match.get("signals"):
            raise ServiceOSException(
                ERR_NO_PROVIDER_AVAILABLE,
                f"No eligible providers available in {city}. Try a nearby city.",
                status_code=422,
            )

        signals, score = match["signals"], match["score"]
        selected_tenant_id = uuid.UUID(signals.tenant_id)

        # MODULE-L5-58 — canonical audit trail for real matching decisions
        # (Live Decisions view), reusing the same append-only
        # MasterDataAuditLog the diagnostic path writes to. Rides along with
        # this function's own commit -- no extra transaction boundary.
        from app.engines.admin_catalog.models import MasterDataAuditLog
        from app.engines.home_service_booking.matching_engine import MATCHING_POLICY_VERSION
        self.db.add(MasterDataAuditLog(
            entity_type="matching_decision", entity_id=uuid.uuid4(), action="production_match",
            actor_user_id=customer_id, actor_role="customer",
            new_value={
                "policy_version": MATCHING_POLICY_VERSION,
                "master_service_id": str(master_service_id), "city": city,
                "job_type_id": str(job_type_id) if job_type_id else None,
                "candidate_count": match.get("candidate_count", 0),
                "excluded_count": match.get("excluded_count", 0),
                "selected_provider_id": signals.tenant_id,
                "draft_id": str(draft_id) if draft_id else None,
                "outcome": "selected",
            },
        ))

        # Inspection-first offerings (pricing_model == visit_fee_plus_quote)
        # must NEVER have a fixed/bargain "standard_price" computed for them
        # at all -- real defect fixed here: this function previously ran the
        # ServicePricingRule/BargainRule lookup unconditionally for every
        # offering, so Guramrit's AC Gas Refilling (inspection-mode) got a
        # `standard_price` of literally ₹0.00 from an unrelated, tenant-
        # agnostic global pricing rule, which then reached the customer-
        # facing Booking Review as if it were a real price. The visit fee /
        # `requires_inspection_estimate` flag was already correctly resolved
        # earlier by `resolve_price_estimate` (`_compute_price_snapshot`)
        # and lives in `draft.price_snapshot` -- this function must leave it
        # untouched, not overwrite it with a spurious fixed number.
        offering = await self._get_offering(master_service_id)
        inspection_mode = offering.pricing_model == PRICING_MODEL_VISIT_FEE

        bargain_available = False
        price_options: dict | None = None
        standard_price: Decimal | None = None

        if inspection_mode:
            pass  # bargain_available/price_options/standard_price stay None/False.
        else:
            # Resolve the selected provider's bargain rule (customer range + fee)
            # and its linked pricing rule (admin range) — real, tenant-scoped data.
            #
            # HS6 fix: previously matched ONLY on master_service_id, completely
            # ignoring offering_type_id/brand_id even though they were already
            # passed into select_best_provider() for eligibility filtering — the
            # exact "Window AC brand price used for Split AC" bug this whole
            # Home Services pricing lineage exists to prevent, except it was
            # still live in the actual matching/booking price-resolution path.
            # Fixed: join the linked ServicePricingRule and prefer the most
            # specific match — type+brand > type-only > service-only — mirroring
            # the hierarchy already used by _find_admin_pricing_rule elsewhere.
            bargain_candidates = (await self.db.execute(
                select(BargainRule, ServicePricingRule)
                .join(ServicePricingRule, ServicePricingRule.id == BargainRule.pricing_rule_id, isouter=True)
                .where(
                    BargainRule.master_service_id == master_service_id,
                    BargainRule.status == "active", BargainRule.deleted_at.is_(None),
                )
            )).all()

            def _specificity(row) -> int:
                spr = row[1]
                if spr is None:
                    return 0
                has_type = offering_type_id is not None and spr.service_type_id == offering_type_id
                has_brand = brand_id is not None and spr.brand_id == brand_id
                if has_type and has_brand:
                    return 3
                if has_type:
                    return 2
                if spr.service_type_id is None and spr.brand_id is None:
                    return 1
                return -1  # a type/brand-scoped rule that doesn't match this request — never usable here

            eligible_candidates = [row for row in bargain_candidates if _specificity(row) >= 0]
            eligible_candidates.sort(key=lambda row: (_specificity(row), row[0].created_at), reverse=True)
            bargain_rule = eligible_candidates[0][0] if eligible_candidates else None

            bargain_available = bool(
                bargain_rule and bargain_rule.customer_min_price is not None
                and bargain_rule.customer_max_price is not None
            )

        if inspection_mode:
            pass
        elif bargain_available:
            pricing_rule = None
            if bargain_rule.pricing_rule_id:
                pricing_rule = await self.db.get(ServicePricingRule, bargain_rule.pricing_rule_id)
            try:
                price_options = compute_price_tiers(
                    admin_min_price=pricing_rule.min_price if pricing_rule else None,
                    admin_max_price=pricing_rule.max_price if pricing_rule else None,
                    admin_base_price=pricing_rule.base_price if pricing_rule else None,
                    customer_min_price=bargain_rule.customer_min_price,
                    customer_max_price=bargain_rule.customer_max_price,
                    platform_fee_percent=bargain_rule.platform_fee_percent or (pricing_rule.platform_fee_percent if pricing_rule else 0),
                    platform_fee_fixed_amount=bargain_rule.platform_fee_fixed_amount,
                )
            except BargainValidationError as e:
                raise ServiceOSException(e.code, e.message, status_code=422) from e
        else:
            # Optional-bargain path (fix/bargain-optional-price-path): no active
            # BargainRule is configured for this offering/type/brand. Per product
            # policy, bargaining is ALLOWED but never MANDATORY — the customer
            # must still be able to book at the ordinary, server-authoritative
            # price. Resolve that price the same way the admin/tenant pricing
            # console already does (_find_admin_pricing_rule's hierarchy:
            # type+brand > type-only > service-only), then apply the SAME
            # fee-inclusive formula used elsewhere (fee on top of the raw
            # provider-facing base price) so the customer-facing number is
            # computed identically regardless of whether a BargainRule exists.
            # NOTE: unlike _find_admin_pricing_rule (which only reads the
            # global, city=NULL admin-console rule), real tenant pricing here
            # may be city-scoped — confirmed live: ac_repair's seeded rules
            # carry city='Ludhiana', not NULL. Accept both a city-exact match
            # and a global (city IS NULL) rule, preferring the city-exact one.
            spr_candidates = (await self.db.execute(
                select(ServicePricingRule).where(
                    ServicePricingRule.master_service_id == master_service_id,
                    ServicePricingRule.deleted_at.is_(None),
                    ServicePricingRule.is_active == True,
                    ServicePricingRule.tier_id.is_(None),
                    or_(ServicePricingRule.city.is_(None), ServicePricingRule.city == city),
                )
            )).scalars().all()

            def _spr_specificity(spr) -> int:
                # A row is only usable if every scoping column it DOES set
                # actually matches this request — a type/brand-scoped rule for
                # a different type/brand must never be selected. Rows whose
                # scoping columns are all None are the global fallback.
                if spr.service_type_id is not None and spr.service_type_id != offering_type_id:
                    return -1
                if spr.brand_id is not None and spr.brand_id != brand_id:
                    return -1
                has_type = offering_type_id is not None and spr.service_type_id == offering_type_id
                has_brand = brand_id is not None and spr.brand_id == brand_id
                has_city  = bool(city) and spr.city == city
                if has_type and has_brand:
                    base = 4
                elif has_type:
                    base = 3
                elif has_brand:
                    base = 2
                else:
                    base = 1  # global rule: no type/brand scoping at all
                return base * 2 + (1 if has_city else 0)

            eligible_sprs = [s for s in spr_candidates if _spr_specificity(s) >= 0]
            eligible_sprs.sort(key=lambda s: _spr_specificity(s), reverse=True)
            pricing_rule = eligible_sprs[0] if eligible_sprs else None

            # The selected tenant's OWN configured price takes precedence
            # over the tenant-agnostic global ServicePricingRule fallback --
            # a tenant with a real min/max range configured (e.g. Guramrit's
            # own TenantService.tenant_min_price/max_price) must never be
            # priced off an unrelated, possibly-unconfigured global rule.
            tenant_price = await self._resolve_tenant_price_for(
                selected_tenant_id, master_service_id, offering_type_id, brand_id,
            )
            if tenant_price is not None:
                base = Decimal(str(tenant_price["minimum_price"]))
                fee_amount = Decimal("0")
                standard_price = _round2(base + fee_amount)
            elif pricing_rule is not None and pricing_rule.base_price is not None and pricing_rule.base_price > 0:
                fee_percent = pricing_rule.platform_fee_percent or Decimal("0")
                fee_fixed = Decimal("0")  # ServicePricingRule has no separate fixed-fee column; only BargainRule does.
                base = pricing_rule.base_price
                fee_amount = _round2(base * fee_percent / Decimal("100") + fee_fixed)
                standard_price = _round2(base + fee_amount)
            else:
                # Genuinely no valid pricing configuration for this offering
                # -- not a bargain-specific gap, a real absence of any usable
                # price (a `base_price` of exactly 0 counts as absent, never
                # as a real free/zero price). This is the one case that must
                # still fail; there is no authoritative number to show the
                # customer, and Review must never proceed with an invalid
                # price (spec: "Zero or missing price makes the offering
                # temporarily unbookable").
                raise ServiceOSException(
                    "PRICE_OPTIONS_UNAVAILABLE",
                    "This service does not have valid pricing configured yet.",
                    status_code=422,
                )

        area_comparison = await get_area_market_comparison(
            self.db, category_id=category_id, offering_id=master_service_id,
            city=city, zipcode=zipcode, exclude_tenant_id=selected_tenant_id,
        )

        selected_provider_public = build_customer_safe_provider(signals, score)
        # Real, countable facts about this provider for the customer's booking
        # card -- rating backed by approved reviews, actual verification status,
        # completed-job count. Deliberately excludes the internal score, its
        # sub-scores (hard gate 9) AND tenants.health_score, which defaults to
        # 100 and would read to a customer as an earned quality rating.
        from app.engines.home_service_booking.matching_engine import customer_provider_facts
        selected_provider_public["facts"] = await customer_provider_facts(
            self.db, selected_tenant_id,
        )
        selected_provider_admin = build_admin_provider(signals, score) if reveal_internal_score else None

        result = {
            "selected_provider": selected_provider_public,
            "pricing_mode": "inspection" if inspection_mode else "fixed",
            "bargain_available": bargain_available,
            "selected_provider_price_options": price_options,
            # Present only when bargain_available is False — the ordinary,
            # server-authoritative, fee-inclusive price the customer may book
            # at directly. Never present alongside price_options, and never
            # present at all under inspection mode (None, not 0 -- the
            # inspection-mode visit fee/requires_inspection_estimate already
            # resolved earlier in draft.price_snapshot is what Review shows).
            "standard_price": float(standard_price) if standard_price is not None else None,
            "area_market_comparison": area_comparison,
        }
        if reveal_internal_score:
            result["selected_provider_admin"] = selected_provider_admin

        if draft_id is not None:
            draft = await self._require_draft(draft_id, customer_id)
            self._assert_not_terminal(draft)
            draft.selected_tenant_id = selected_tenant_id
            # matching_score_snapshot is internal — stored on the draft (backend-
            # only field), never returned verbatim by the customer-facing API.
            draft.selected_provider_snapshot = {
                **selected_provider_public,
                "matching_score_snapshot": build_admin_provider(signals, score)["internal_score_breakdown"],
                "internal_score": float(score),
            }
            draft.price_snapshot = {
                **(draft.price_snapshot or {}),
                "bargain_available": bargain_available,
                "price_options": price_options,
                "standard_price": float(standard_price) if standard_price is not None else None,
            }
            draft.provider_match_status = PROVIDER_MATCH_MATCHED
            draft.status = DRAFT_STATUS_PROVIDER_MATCHED
            draft.updated_at = utcnow()
            await self._emit_event(
                draft_id=draft.id, actor_type=ACTOR_BACKEND, event_type=EVENT_PROVIDER_MATCHED,
                new_value={"selected_tenant_id": str(selected_tenant_id), "candidate_count": match["candidate_count"]},
                message=f"Backend selected provider: {signals.provider_name}",
            )
            await self.db.commit()
            await self.db.refresh(draft)
            result["draft_status"] = draft.status

        return result

    async def confirm_price_choice(
        self,
        draft_id: uuid.UUID,
        price_tier: str,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """Customer chooses Low/Mid/High when bargain is available, or
        'standard' to continue at the ordinary server-authoritative price
        when no BargainRule is configured (fix/bargain-optional-price-path).
        Never a raw amount, never a provider-set price. Re-validates the
        stored price snapshot before storing the offer (hard gate 10: no
        assignment change without revalidation)."""
        from app.engines.home_service_booking.matching_engine import resolve_customer_offer_for_tier

        draft = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)

        if price_tier not in ("low", "mid", "high", "standard"):
            raise ServiceOSException("INVALID_PRICE_TIER",
                "price_tier must be 'low', 'mid', 'high', or 'standard'.", status_code=422)
        if not draft.selected_tenant_id or not draft.price_snapshot:
            raise ServiceOSException(ERR_NO_PROVIDER_AVAILABLE,
                "No matched provider/price found for this draft. Run provider matching first.",
                status_code=422)

        bargain_available = draft.price_snapshot.get("bargain_available", "price_options" in draft.price_snapshot)

        if price_tier == "standard":
            if bargain_available or draft.price_snapshot.get("standard_price") is None:
                raise ServiceOSException("INVALID_PRICE_TIER",
                    "'standard' is only valid when bargain is unavailable for this offering.",
                    status_code=422)
            customer_offer = Decimal(str(draft.price_snapshot["standard_price"]))
            allowed_min = allowed_max = float(customer_offer)
            platform_fee_amount = 0.0  # already folded into standard_price server-side; no separate fee shown
        else:
            if not bargain_available or "price_options" not in draft.price_snapshot:
                raise ServiceOSException(ERR_NO_PROVIDER_AVAILABLE,
                    "Bargain is not available for this offering. Use price_tier='standard' instead.",
                    status_code=422)
            price_options = draft.price_snapshot["price_options"]
            customer_offer = resolve_customer_offer_for_tier(price_options, price_tier)
            allowed_min = price_options["allowed_offer_min"]
            allowed_max = price_options["allowed_offer_max"]
            platform_fee_amount = price_options["platform_fee_amount"]

        # HS7 fix: matching_score_snapshot (internal per-signal scoring) was
        # being copied into booking_summary and returned verbatim to the
        # customer by this endpoint and by /summary — a direct violation of
        # the "never show internal provider scoring" hard gate. Removed;
        # internal scoring remains available to admin-only surfaces via
        # draft.selected_provider_snapshot, never via booking_summary.
        draft.booking_summary = {
            **(draft.booking_summary or {}),
            "selected_tenant_id": str(draft.selected_tenant_id),
            "selected_provider_name": (draft.selected_provider_snapshot or {}).get("provider_name"),
            "selected_zipcode": draft.zipcode,
            "selected_price_tier": price_tier,
            "bargain_available": bargain_available,
            "customer_offer": float(customer_offer),
            "allowed_offer_min": allowed_min,
            "allowed_offer_max": allowed_max,
            "platform_fee_amount": platform_fee_amount,
            "payment_mode": "customer_pays_provider_directly",
        }
        draft.updated_at = utcnow()
        await self._emit_event(
            draft_id=draft.id, actor_type=ACTOR_CUSTOMER, event_type=EVENT_PRICE_ESTIMATED,
            new_value={"price_tier": price_tier, "customer_offer": float(customer_offer)},
            message=f"Customer chose {price_tier} price: {customer_offer}",
        )
        await self.db.commit()
        await self.db.refresh(draft)
        return {"booking_summary": draft.booking_summary, "draft_status": draft.status}

    # ══════════════════════════════════════════════════════════════════════════
    # 11. BUILD BOOKING SUMMARY
    # ══════════════════════════════════════════════════════════════════════════

    async def build_booking_summary(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """Build the customer-facing booking summary card.

        HS7 fixes:
        1. This previously *overwrote* draft.booking_summary wholesale,
           destroying the selected_price_tier/customer_offer that
           confirm_price_choice had just written there — a real bug that
           would make the later /confirm call fail with
           INVALID_SELECTED_PRICE_OPTION even after the customer legitimately
           picked a tier, if the Review step (which calls this endpoint)
           runs after price selection as the ticket's flow requires. Fixed
           to merge on top of the existing summary instead of replacing it.
        2. `selected_provider` was the raw `selected_provider_snapshot`,
           which includes `internal_score` and `matching_score_snapshot` —
           a direct customer-safety leak of internal provider scoring
           (explicitly forbidden by the ticket). Fixed to strip those keys.
        """
        draft    = await self._require_draft(draft_id, customer_id)
        offering = await self._get_offering(draft.offering_id)

        customer_safe_provider = None
        if draft.selected_provider_snapshot:
            customer_safe_provider = {
                k: v for k, v in draft.selected_provider_snapshot.items()
                if k not in ("internal_score", "matching_score_snapshot")
            }

        existing = draft.booking_summary or {}
        job_type_error = await self._validate_job_type_context(draft)

        # Pricing readiness has two genuinely different, mutually exclusive
        # shapes: a fixed/bargain offering is ready once the customer has
        # picked a price tier (`confirm_price_choice`); an inspection-first
        # offering has no tier to pick at all -- the frontend controller
        # correctly never calls `confirm_price_choice` when `standard_price`
        # is null (see useBookingReviewController.ts), so requiring
        # `selected_price_tier` here would make EVERY inspection-mode
        # offering permanently unconfirmable. Ready instead once a real,
        # positive visit fee has been resolved into `draft.price_snapshot`
        # by `resolve_price_estimate`.
        price_snapshot = draft.price_snapshot or {}
        pricing_ready = bool(existing.get("selected_price_tier") in ("low", "mid", "high", "standard")) or bool(
            price_snapshot.get("requires_inspection_estimate")
            and price_snapshot.get("visit_fee")
            and price_snapshot.get("visit_fee") > 0
        )

        # Resolve the promise BEFORE building the summary: the customer sees
        # a real slot and its SLA on the review screen and decides from
        # there. Provider-level capacity only -- technician allocation is
        # the provider's own downstream responsibility.
        promised_slot = None
        # The catalog's own per-service duration is authoritative when an
        # admin has set it. When they have not, the promised slot length IS
        # the commitment -- fall back to it rather than reporting no SLA at
        # all (which would leave the provider with nothing to be held to).
        sla_minutes = offering.estimated_duration_minutes
        if draft.selected_tenant_id:
            from app.engines.home_service_booking.provider_slot_service import (
                find_earliest_available_slot,
            )
            try:
                promised_slot = await find_earliest_available_slot(
                    self.db, tenant_id=draft.selected_tenant_id,
                )
            except Exception as exc:  # noqa: BLE001 -- never block the summary
                logger.warning("home_service.promised_slot_failed", error=str(exc))
        if not sla_minutes and promised_slot:
            sla_minutes = promised_slot.get("slot_minutes")

        summary = {
            **existing,
            "offering_name":    offering.service_name,
            "offering_slug":    offering.slug,
            "issue_summary":    draft.issue_summary,
            "address":          draft.address_snapshot,
            "city":             draft.city,
            "zipcode":          draft.zipcode,
            "preferred_date":   draft.preferred_date.isoformat() if draft.preferred_date else None,
            "preferred_time_window": draft.preferred_time_window,
            "price_estimate":   draft.price_snapshot,
            "selected_provider":customer_safe_provider,
            "serviceability":   {
                "serviceable": draft.serviceability_status == SVCABILITY_SERVICEABLE,
                "status":      draft.serviceability_status,
            },
            "ready_for_confirmation": (
                draft.serviceability_status == SVCABILITY_SERVICEABLE
                and bool(draft.selected_tenant_id)
                and pricing_ready
                and job_type_error is None
            ),
            # HOME-SERVICES-RUNTIME-SAFETY Phase 2A.2 (spec section 6): the
            # customer-facing field-level readiness contract.
            "missing": (["job_type"] if job_type_error else []),
            "errors":  ([job_type_error] if job_type_error else []),
            # The real, capacity-checked slot this provider can actually
            # honour -- resolved BEFORE the customer confirms so they make
            # the final call on a promise rather than confirming blind and
            # waiting to find out. Today first, then the next day, and so
            # on. `None` means the provider has no capacity in the search
            # horizon; the customer is told that rather than being given a
            # date nobody can keep.
            "promised_slot": promised_slot,
            # What the provider is actually committing to, in customer terms:
            # the service is done by the END of the promised slot. The clock
            # runs from when the booking request is created, not from when a
            # technician happens to pick the job up -- so provider-side
            # allocation delay is the provider's problem, never the
            # customer's wait.
            "service_sla_minutes": sla_minutes,
            "service_due_at": (promised_slot or {}).get("ends_at"),
        }

        draft.booking_summary = summary
        draft.updated_at      = utcnow()
        await self._emit_event(
            draft_id=draft.id, actor_type=ACTOR_BACKEND,
            event_type=EVENT_SUMMARY_GENERATED,
            new_value={"ready_for_confirmation": summary["ready_for_confirmation"]},
            message="Booking summary generated",
        )
        await self.db.commit()
        await self.db.refresh(draft)
        return {"booking_summary": summary, "draft_status": draft.status}

    # ══════════════════════════════════════════════════════════════════════════
    # 11b. AVAILABLE SLOTS — let the customer pick, instead of the system
    # ══════════════════════════════════════════════════════════════════════════

    async def list_available_slots(self, draft_id: uuid.UUID, customer_id: uuid.UUID, emergency: bool = False) -> dict:
        """Every real slot this provider has capacity for, not just the one
        `build_booking_summary` already promised -- lets Review show a
        picker instead of a single system-chosen time.

        `emergency=True` shortens the minimum lead time from 6 hours to 2
        (product-specified), applied on top of -- never instead of -- the
        provider's own configured business hours: this still only ever
        walks the same real availability rules, so it can offer a slot
        outside the provider's hours no more than the normal path can.

        Empty list (never an error) when no provider is assigned yet, or
        when the provider genuinely has no capacity anywhere in the search
        horizon -- both are real states the customer should see plainly,
        not a fabricated slot.
        """
        draft = await self._require_draft(draft_id, customer_id)
        if not draft.selected_tenant_id:
            return {"slots": []}
        from app.engines.home_service_booking.provider_slot_service import list_available_slots
        # The notice period, same-day rule, horizon and whether emergency is
        # permitted at all come from the provider's own booking-window
        # settings -- see provider_slot_service.booking_window_settings.
        slots = await list_available_slots(
            self.db, tenant_id=draft.selected_tenant_id, emergency=emergency,
        )
        return {"slots": slots}

    async def select_promised_slot(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID, date_iso: str, time_window: str, emergency: bool = False,
    ) -> dict:
        """Overwrites the summary's `promised_slot` with the one the
        customer actually picked, in the exact shape `build_booking_summary`
        already produces -- `service_due_at`/`service_sla_minutes` are
        recomputed from it so every field the confirm step and the Review
        UI read stays consistent with the new choice.

        Re-validated against live capacity right here, not trusted from the
        list response the customer may have been looking at for a while --
        the same discipline `creation_service.py` already applies a second
        time at confirm. A slot that lost capacity between the list call
        and this one is rejected with a clear reason rather than silently
        booked anyway.
        """
        import datetime as _dt
        from app.engines.home_service_booking.provider_slot_service import (
            slot_has_capacity, list_available_slots, booking_window_settings, _tenant_now,
        )

        draft = await self._require_draft(draft_id, customer_id)
        if not draft.selected_tenant_id:
            raise ValueError("NO_PROVIDER_ASSIGNED_YET")

        day = _dt.date.fromisoformat(date_iso)
        if not await slot_has_capacity(self.db, tenant_id=draft.selected_tenant_id, day=day, time_window=time_window):
            raise ValueError("SLOT_NO_LONGER_AVAILABLE")

        # Re-fetch the full slot dict (date/time_window/starts_at/ends_at/
        # slot_minutes/capacity/already_booked/days_ahead) from the SAME
        # walk `list_available_slots` uses, rather than reconstructing a
        # partial shape here by hand -- guarantees this always matches the
        # exact contract `promised_slot` carries everywhere else, and the
        # capacity check just above means it genuinely must be in this list.
        # Real `now` on the TENANT's clock (not the server's, and not
        # day-midnight), so a same-day window that has already started, OR
        # falls inside the provider's notice period, is still correctly
        # excluded by the walk's own rule -- `slot_has_capacity` above checks
        # capacity only, never timing.
        now = _tenant_now(await booking_window_settings(self.db, draft.selected_tenant_id))
        days_needed = (day - now.date()).days + 1
        if days_needed < 1:
            raise ValueError("SLOT_NO_LONGER_AVAILABLE")  # a past date was requested
        # `max_days` must span every day up to the requested one, otherwise
        # re-deriving a slot the customer legitimately picked on a later day
        # would fail as "no longer available" purely because the walk stopped
        # counting days early.
        candidates = await list_available_slots(
            self.db, tenant_id=draft.selected_tenant_id,
            from_datetime=now, search_days=days_needed, max_days=days_needed,
            emergency=emergency,
        )
        promised_slot = next(
            (s for s in candidates if s["date"] == day.isoformat() and s["time_window"] == time_window),
            None,
        )
        if not promised_slot:
            # slot_has_capacity said yes but the walk (which also checks
            # "not already started"/lead-time) didn't reproduce it -- only
            # possible if the window passed, or fell inside the lead-time
            # cutoff, between the two calls. Same customer-facing outcome
            # either way: this slot cannot be booked now.
            raise ValueError("SLOT_NO_LONGER_AVAILABLE")

        # Persist the urgency. Picking from the emergency list is the only way
        # a booking becomes an emergency -- it is a real customer choice, so it
        # is recorded on the draft (and carried to the booking/job at
        # confirmation) rather than left as a transient request parameter the
        # provider would never see. Choosing a normal slot clears it again, so
        # a customer who changes their mind is not silently surcharged.
        draft.is_emergency = bool(emergency)
        surcharge = await self._emergency_surcharge_for(draft) if emergency else None

        existing = draft.booking_summary or {}
        summary = {
            **existing,
            "promised_slot": promised_slot,
            "service_sla_minutes": promised_slot.get("slot_minutes") or existing.get("service_sla_minutes"),
            "service_due_at": promised_slot.get("ends_at") or existing.get("service_due_at"),
            "is_emergency": bool(emergency),
            # Shown to the customer BEFORE they confirm -- an emergency must
            # never be a surprise line on the final bill.
            "emergency_surcharge": str(surcharge) if surcharge is not None else None,
        }
        draft.booking_summary = summary
        draft.updated_at = utcnow()
        await self._emit_event(
            draft_id=draft.id, actor_type=ACTOR_CUSTOMER,
            event_type=EVENT_SUMMARY_GENERATED,
            new_value={"selected_slot": promised_slot, "is_emergency": bool(emergency)},
            message=f"Customer chose {'EMERGENCY ' if emergency else ''}slot {date_iso} {time_window}",
        )
        await self.db.commit()
        await self.db.refresh(draft)
        return {"booking_summary": summary, "draft_status": draft.status}

    async def _emergency_surcharge_for(self, draft) -> "Decimal | None":
        """The tenant's own configured emergency surcharge for this offering.

        Read from `tenant_services.tenant_emergency_surcharge` -- the field
        that already existed for exactly this and was never used by anything.
        Returns None when the tenant has not set one, which means an emergency
        is simply free for them; it NEVER invents a rate or falls back to a
        platform default, because charging a customer money nobody configured
        would be indefensible.
        """
        if not (draft.selected_tenant_id and draft.offering_id):
            return None
        row = (await self.db.execute(text(
            "SELECT tenant_emergency_surcharge FROM tenant_services "
            "WHERE tenant_id=:tid AND master_service_id=:sid "
            "AND is_active=true AND deleted_at IS NULL"
        ), {"tid": str(draft.selected_tenant_id), "sid": str(draft.offering_id)})).fetchone()
        if not row:
            return None
        value = row._mapping.get("tenant_emergency_surcharge")
        if value is None:
            return None
        surcharge = Decimal(str(value))
        return surcharge if surcharge > 0 else None

    # ══════════════════════════════════════════════════════════════════════════
    # 12. MARK READY FOR CONFIRMATION
    # ══════════════════════════════════════════════════════════════════════════

    async def mark_ready_for_confirmation(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """Advance draft to ready_for_confirmation if all checks pass.

        HS7 fix: this was previously dead code (never called from any
        router) and, when unwired, additionally checked the legacy flat
        `price_status`/`resolve_price_estimate` gate rather than the
        provider-first flow's own readiness signals (selected provider +
        confirmed price tier). Rewritten to require the real HS6/HS6B
        provider-first sequence — match-and-price then
        confirm-price-choice — and to re-validate the selected provider is
        still bookable right now (a booking must never be created against a
        provider that became non-bookable while the customer was reviewing).
        """
        draft    = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)
        offering = await self._get_offering(draft.offering_id)
        missing  = self._compute_missing_fields(draft, offering)

        if missing:
            raise ServiceOSException(
                ERR_REQUIRED_FIELD_MISSING,
                f"Missing required fields: {', '.join(missing)}",
                status_code=422,
            )

        # HOME-SERVICES-RUNTIME-SAFETY Phase 2A.2 (spec section 6/8): a new
        # canonical draft must not become ready_for_confirmation without a
        # resolved, still-valid Job Type and a published workflow snapshot.
        # This is the SAME check finalize() re-runs independently -- not
        # relying on this gate alone (defense in depth, spec section 8).
        job_type_error = await self._validate_job_type_context(draft)
        if job_type_error:
            raise ServiceOSException(job_type_error["code"], job_type_error["message"], status_code=422)

        if draft.serviceability_status != SVCABILITY_SERVICEABLE:
            raise ServiceOSException(
                "SERVICE_NOT_AVAILABLE_IN_AREA",
                "This service is not available in your area yet.",
                status_code=422,
            )

        # A draft may have reached a genuinely priced, matched state through
        # THREE distinct paths -- bargain-available ("price_options" in the
        # snapshot), standard fixed-price ("standard_price" in the snapshot,
        # bargain_available: False), or inspection-first (no tier at all;
        # `requires_inspection_estimate` + a real positive `visit_fee` is
        # the whole story -- see `_compute_price_snapshot`/`match_provider_
        # and_price`). Only a draft with NONE of the three has genuinely not
        # been through provider matching / pricing yet. Requiring
        # `standard_price` or `price_options` unconditionally previously
        # made confirm() permanently reject every inspection-mode offering,
        # since match_provider_and_price correctly never computes a
        # standard_price for one.
        price_snapshot = draft.price_snapshot or {}
        is_inspection_priced = bool(
            price_snapshot.get("requires_inspection_estimate")
            and price_snapshot.get("visit_fee")
            and price_snapshot.get("visit_fee") > 0
        )
        if not draft.selected_tenant_id or not price_snapshot or (
            "price_options" not in price_snapshot
            and price_snapshot.get("standard_price") is None
            and not is_inspection_priced
        ):
            raise ServiceOSException(
                ERR_NO_PROVIDER_AVAILABLE,
                "No matched provider/price options found for this draft. Run provider matching first.",
                status_code=422,
            )

        selected_tier = (draft.booking_summary or {}).get("selected_price_tier")
        if selected_tier not in ("low", "mid", "high", "standard") and not is_inspection_priced:
            raise ServiceOSException(
                "INVALID_SELECTED_PRICE_OPTION",
                "Selected price option is no longer valid.",
                status_code=422,
            )

        from sqlalchemy import text
        bookable_row = (await self.db.execute(
            text(
                "SELECT is_bookable FROM provider_visibility_statuses "
                "WHERE tenant_id = :tid ORDER BY created_at DESC LIMIT 1"
            ),
            {"tid": str(draft.selected_tenant_id)},
        )).first()
        if not bookable_row or not bookable_row[0]:
            raise ServiceOSException(
                "SELECTED_PROVIDER_NOT_BOOKABLE",
                "Selected provider is no longer available. Please match again.",
                status_code=422,
            )

        draft.status     = DRAFT_STATUS_READY_FOR_CONFIRMATION
        draft.updated_at = utcnow()
        await self.db.commit()
        await self.db.refresh(draft)
        return {"draft_status": draft.status, "ready_for_confirmation": True}

    # ══════════════════════════════════════════════════════════════════════════
    # 13. CONFIRM DRAFT
    # ══════════════════════════════════════════════════════════════════════════

    async def confirm_draft(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """
        Customer confirms booking intent. Returns booking-ready payload for Sprint 19.
        Does NOT create a final job or booking in this sprint.
        """
        draft = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)

        if draft.status != DRAFT_STATUS_READY_FOR_CONFIRMATION:
            raise ServiceOSException(
                ERR_CONFIRMATION_NOT_READY,
                f"Draft must be in 'ready_for_confirmation' status. Current: {draft.status}",
                status_code=422,
            )

        # FINAL-L5-04C — re-validate the selected provider's entitlement at
        # confirmation time, not just at match time (Part 6). Entitlement
        # could have been disabled by an admin in the window between the
        # customer being matched and confirming — a controlled 409, not a
        # stale confirmation or an unhandled 500.
        if draft.selected_tenant_id and draft.offering_id:
            from app.engines.admin_catalog.models import MasterService
            from app.engines.entitlement.service import entitlement_service
            svc_group_id = (await self.db.execute(
                select(MasterService.service_group_id).where(MasterService.id == draft.offering_id)
            )).scalar_one_or_none()
            if svc_group_id:
                still_entitled = await entitlement_service.has_category_entitlement(
                    self.db, draft.selected_tenant_id, svc_group_id
                )
                if not still_entitled:
                    raise ServiceOSException(
                        ERR_PROVIDER_ENTITLEMENT_CHANGED,
                        "The selected provider is no longer available for this category. Please search again.",
                        status_code=409,
                    )

        draft.status     = DRAFT_STATUS_CONFIRMED
        draft.updated_at = utcnow()
        await self._emit_event(
            draft_id=draft.id, actor_type=ACTOR_CUSTOMER,
            event_type=EVENT_DRAFT_CONFIRMED,
            new_value={"status": DRAFT_STATUS_CONFIRMED},
            message="Customer confirmed booking intent",
        )
        await self.db.commit()
        await self.db.refresh(draft)

        booking_ready_payload = {
            "draft_id":         str(draft.id),
            "category_id":      str(draft.category_id),
            "offering_id":      str(draft.offering_id),
            "tenant_id":        str(draft.selected_tenant_id) if draft.selected_tenant_id else None,
            "price_snapshot":   draft.price_snapshot,
            "address_snapshot": draft.address_snapshot,
            "issue_details":    {
                "issue_summary":      draft.issue_summary,
                "offering_type_id":   str(draft.offering_type_id) if draft.offering_type_id else None,
                "brand_id":           str(draft.brand_id) if draft.brand_id else None,
                "preferred_date":     draft.preferred_date.isoformat() if draft.preferred_date else None,
                "preferred_time_window": draft.preferred_time_window,
                "photo_urls":         draft.photo_urls or [],
            },
        }

        return {
            "success": True,
            "data": {
                "draft_id":             str(draft.id),
                "status":               DRAFT_STATUS_CONFIRMED,
                "next_step":            "final_booking_creation_in_sprint_19",
                "booking_ready_payload": booking_ready_payload,
            },
        }

    # ══════════════════════════════════════════════════════════════════════════
    # 14. CANCEL DRAFT
    # ══════════════════════════════════════════════════════════════════════════

    async def cancel_draft(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
        reason: str | None = None,
    ) -> dict:
        """Cancel a draft (customer-initiated)."""
        draft = await self._require_draft(draft_id, customer_id)
        if draft.status in TERMINAL_STATUSES:
            return {"draft_status": draft.status, "message": "Draft already closed."}

        draft.status     = DRAFT_STATUS_CANCELLED
        draft.updated_at = utcnow()
        await self._emit_event(
            draft_id=draft.id, actor_type=ACTOR_CUSTOMER,
            event_type=EVENT_DRAFT_CANCELLED,
            new_value={"reason": reason},
            message=reason or "Customer cancelled",
        )
        await self.db.commit()
        return {"draft_status": draft.status, "message": "Booking draft cancelled."}

    # ══════════════════════════════════════════════════════════════════════════
    # 15. EXPIRE OLD DRAFTS (system job)
    # ══════════════════════════════════════════════════════════════════════════

    async def expire_old_drafts(self) -> int:
        """Mark expired drafts. Intended to be called by a scheduler."""
        now = utcnow()
        rows = (await self.db.execute(
            select(HomeServiceBookingDraft).where(
                HomeServiceBookingDraft.expires_at <= now,
                HomeServiceBookingDraft.status.not_in(list(TERMINAL_STATUSES)),
            )
        )).scalars().all()

        count = 0
        for draft in rows:
            draft.status     = DRAFT_STATUS_EXPIRED
            draft.updated_at = now
            await self._emit_event(
                draft_id=draft.id, actor_type=ACTOR_SYSTEM,
                event_type=EVENT_DRAFT_FAILED,
                new_value={"reason": "expired"},
                message="Draft expired",
            )
            count += 1

        if count:
            await self.db.commit()
        return count

    # ══════════════════════════════════════════════════════════════════════════
    # ADMIN METHODS
    # ══════════════════════════════════════════════════════════════════════════

    async def admin_list_drafts(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        city: str | None = None,
        offering_id: str | None = None,
    ) -> dict:
        """Admin: list all drafts with optional filters."""
        q = select(HomeServiceBookingDraft).order_by(
            HomeServiceBookingDraft.created_at.desc()
        )
        if status:
            q = q.where(HomeServiceBookingDraft.status == status)
        if city:
            q = q.where(HomeServiceBookingDraft.city.ilike(f"%{city}%"))
        if offering_id:
            q = q.where(HomeServiceBookingDraft.offering_id == uuid.UUID(offering_id))

        offset = (page - 1) * page_size
        rows   = (await self.db.execute(q.offset(offset).limit(page_size))).scalars().all()
        return {
            "drafts": [d.to_dict() for d in rows],
            "page": page, "page_size": page_size,
        }

    async def admin_get_draft(self, draft_id: uuid.UUID) -> dict:
        """Admin: get any draft without ownership check."""
        draft = await self.db.get(HomeServiceBookingDraft, draft_id)
        if not draft:
            raise ServiceOSException(ERR_DRAFT_NOT_FOUND,
                f"Draft '{draft_id}' not found.", status_code=404)
        return await self._enrich_draft(draft)

    async def admin_get_draft_events(self, draft_id: uuid.UUID) -> list[dict]:
        """Admin: get all events for a draft."""
        rows = (await self.db.execute(
            select(HomeServiceBookingDraftEvent)
            .where(HomeServiceBookingDraftEvent.draft_id == draft_id)
            .order_by(HomeServiceBookingDraftEvent.created_at)
        )).scalars().all()
        return [e.to_dict() for e in rows]

    # ══════════════════════════════════════════════════════════════════════════
    # PHOTO UPLOAD
    # ══════════════════════════════════════════════════════════════════════════

    async def add_photo(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        photo_url: str,
        content_type: str = "image/jpeg",
    ) -> dict:
        """Add a photo URL to the draft (after media upload)."""
        draft = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)

        if content_type not in ALLOWED_PHOTO_TYPES:
            raise ServiceOSException(
                ERR_PHOTO_UPLOAD_FAILED,
                f"Invalid file type: {content_type}. Allowed: jpg, png, webp.",
                status_code=422,
            )

        existing = list(draft.photo_urls or [])
        if len(existing) >= DRAFT_MAX_PHOTOS:
            raise ServiceOSException(
                ERR_PHOTO_UPLOAD_FAILED,
                f"Maximum {DRAFT_MAX_PHOTOS} photos allowed per booking.",
                status_code=422,
            )

        existing.append(photo_url)
        draft.photo_urls = existing
        draft.updated_at = utcnow()

        await self._emit_event(
            draft_id=draft.id, actor_type=ACTOR_CUSTOMER,
            event_type=EVENT_PHOTO_UPLOADED,
            new_value={"url": photo_url},
            message="Photo added to draft",
        )
        await self.db.commit()
        await self.db.refresh(draft)
        return {"photo_urls": draft.photo_urls, "draft_status": draft.status}

    async def remove_photo(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        photo_url: str,
    ) -> dict:
        """Detach a photo from the draft.

        Added because attaching was one-way: a customer who picked the wrong
        image had no way to take it back and would have had to abandon the
        draft. Only the draft's reference is dropped -- the media asset
        itself is owned by the media engine and is left to its own
        retention rules rather than being deleted from under it.
        """
        draft = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)

        existing = list(draft.photo_urls or [])
        if photo_url not in existing:
            raise ServiceOSException(
                ERR_PHOTO_UPLOAD_FAILED,
                "That photo is not attached to this booking.",
                status_code=404,
            )

        existing.remove(photo_url)
        draft.photo_urls = existing
        draft.updated_at = utcnow()

        await self._emit_event(
            draft_id=draft.id, actor_type=ACTOR_CUSTOMER,
            event_type=EVENT_PHOTO_REMOVED,
            new_value={"url": photo_url},
            message="Photo removed from draft",
        )
        await self.db.commit()
        await self.db.refresh(draft)
        return {"photo_urls": draft.photo_urls, "draft_status": draft.status}

    # ══════════════════════════════════════════════════════════════════════════
    # PRIVATE HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    async def _require_draft(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
    ) -> HomeServiceBookingDraft:
        draft = await self.db.get(HomeServiceBookingDraft, draft_id)
        if not draft:
            raise ServiceOSException(ERR_DRAFT_NOT_FOUND,
                f"Booking draft '{draft_id}' not found.", status_code=404)
        if customer_id and draft.customer_id and draft.customer_id != customer_id:
            raise ServiceOSException(ERR_DRAFT_ACCESS_DENIED,
                "You do not have access to this booking draft.", status_code=403)
        return draft

    def _assert_not_terminal(self, draft: HomeServiceBookingDraft) -> None:
        if draft.status in TERMINAL_STATUSES:
            raise ServiceOSException(
                ERR_DRAFT_TERMINAL,
                f"Draft is in terminal status '{draft.status}' and cannot be modified.",
                status_code=422,
            )

    async def _get_offering(self, offering_id: uuid.UUID):
        from app.engines.admin_catalog.models import MasterService
        offering = await self.db.get(MasterService, offering_id)
        if not offering or not offering.is_active:
            raise ServiceOSException(ERR_OFFERING_INVALID,
                "Offering not found or inactive.", status_code=404)
        return offering

    def _get_required_field_list(self, offering) -> list[str]:
        """Return list of required field names based on offering config."""
        fields = ["issue_summary", "city"]
        if offering.is_type_required:
            fields.append("offering_type_id")
        if offering.is_brand_required:
            fields.append("brand_id")
        if offering.requires_schedule:
            fields.append("preferred_date")
        return fields

    def _compute_missing_fields(self, draft: HomeServiceBookingDraft, offering) -> list[str]:
        """Return names of required fields not yet filled."""
        missing = []
        if not draft.issue_summary:
            missing.append("issue_summary")
        if not draft.city:
            missing.append("city")
        if offering.is_type_required and not draft.offering_type_id:
            missing.append("offering_type_id")
        if offering.is_brand_required and not draft.brand_id:
            missing.append("brand_id")
        if offering.requires_schedule and not draft.preferred_date:
            missing.append("preferred_date")
        return missing

    async def _resolve_selected_tenant_price(self, draft: HomeServiceBookingDraft) -> dict | None:
        """When a specific tenant is already selected on this draft, prefer
        THAT tenant's own resolved price (TenantCatalogService.resolve_tenant_price
        -- type+brand override precedence, tenant-owned, never invents a
        price) over the admin's generic MasterService estimate. Admin's
        base_price/min_price/max_price/visit_fee remain the fallback for
        drafts with no tenant selected yet (pre-assignment estimate) or for
        a tenant that has not configured its own price -- so no existing
        booking flow is broken by this change.

        Scoped deliberately narrow: this wires only the booking-draft
        estimate. Provider assignment and invoice generation are a separate,
        dedicated follow-up (not touched here -- see MODULE-L5-56 report)."""
        if not draft.selected_tenant_id:
            return None
        return await self._resolve_tenant_price_for(
            draft.selected_tenant_id, draft.offering_id, draft.offering_type_id, draft.brand_id,
        )

    async def _resolve_tenant_price_for(
        self, tenant_id: uuid.UUID, master_service_id: uuid.UUID,
        offering_type_id: uuid.UUID | None, brand_id: uuid.UUID | None,
    ) -> dict | None:
        """Tenant-id-based counterpart to `_resolve_selected_tenant_price`,
        for call sites (e.g. `match_provider_and_price`) that resolve a
        provider before a draft necessarily exists yet."""
        from app.engines.admin_catalog.models import TenantService
        from app.engines.admin_catalog.tenant_service import TenantCatalogService

        ts = (await self.db.execute(
            select(TenantService).where(
                TenantService.tenant_id == tenant_id,
                TenantService.master_service_id == master_service_id,
                TenantService.is_active.is_(True),
            )
        )).scalars().first()
        if ts is None:
            return None
        svc = TenantCatalogService(db=self.db)
        result = await svc.resolve_tenant_price(
            ts.id, service_type_id=offering_type_id, brand_id=brand_id,
        )
        return result if result.get("resolved") else None

    async def _resolve_selected_tenant_visit_fee(self, draft: HomeServiceBookingDraft) -> float | None:
        """Inspection-mode counterpart to `_resolve_selected_tenant_price`:
        a tenant may configure their own `tenant_visit_fee`, which takes
        precedence over the offering's admin-default `visit_fee` -- never
        the tenant's `tenant_min_price`/`tenant_max_price` range, which is
        fixed/bargain-mode pricing and must never be surfaced as a number
        under inspection mode (see `_compute_price_snapshot`)."""
        if not draft.selected_tenant_id:
            return None
        from app.engines.admin_catalog.models import TenantService
        ts = (await self.db.execute(
            select(TenantService).where(
                TenantService.tenant_id == draft.selected_tenant_id,
                TenantService.master_service_id == draft.offering_id,
                TenantService.is_active.is_(True),
            )
        )).scalars().first()
        if ts is None or ts.tenant_visit_fee is None:
            return None
        return float(ts.tenant_visit_fee)

    async def _compute_price_snapshot(self, draft: HomeServiceBookingDraft, offering) -> dict:
        """
        Build price estimate: prefers the selected tenant's own resolved
        price when one exists (see _resolve_selected_tenant_price), else
        falls back to offering (admin) defaults + optional city floor check.
        Backend is source of truth. Frontend/DeepSeek price is NEVER used.
        """
        from app.engines.pricing.models import CityTierConfig
        from app.engines.admin_catalog.models import ServiceCategory

        cat = await self.db.get(ServiceCategory, draft.category_id)
        cat_name = cat.name if cat else "home_services"

        # Check city tier floor
        floor_row = (await self.db.execute(
            select(CityTierConfig).where(
                CityTierConfig.city_name.ilike(draft.city or ""),
                CityTierConfig.service_category.ilike(cat_name),
                CityTierConfig.is_active.is_(True),
            )
        )).scalars().first()

        floor_price  = float(floor_row.floor_price) if floor_row else 0.0
        pricing_model = offering.pricing_model or "visit_fee_plus_quote"

        # Pricing MODE is decided by the offering's own `pricing_model` --
        # never by whether a tenant happens to have configured a price range.
        # This was a real defect: `_resolve_selected_tenant_price` resolves
        # ANY tenant-configured min/max price regardless of pricing_model,
        # so an inspection-first offering (visit_fee_plus_quote) whose
        # selected tenant had ALSO configured a tenant_min_price/max_price
        # (e.g. Guramrit's AC Gas Refilling: 500/700, likely left over from
        # a bargain-style config) got silently reclassified as a fixed,
        # numeric price -- the exact customer-facing ₹0/wrong-number defect
        # this fix closes. Inspection mode is checked FIRST and always wins;
        # tenant/admin numeric prices are only ever used to fill in the
        # actual number for a genuinely fixed/range offering.
        if pricing_model == PRICING_MODEL_VISIT_FEE:
            tenant_visit_fee = await self._resolve_selected_tenant_visit_fee(draft)
            visit_fee_value = tenant_visit_fee if tenant_visit_fee and tenant_visit_fee > 0 else float(offering.visit_fee)
            base  = max(visit_fee_value, floor_price)
            min_price = base
            max_price = None
            # The visit fee is not an extra charge on top of the repair --
            # it is adjusted against the final bill if the customer goes
            # ahead. Saying so up front is what makes an inspection-first
            # price feel fair rather than like a surprise call-out charge.
            note  = ("The technician will inspect your service and provide an estimate before starting the work. "
                     "Your approval will be required before repair begins. "
                     "This visit fee is adjusted against your final bill if you continue with the service.")
            tenant_price = None
        else:
            tenant_price = await self._resolve_selected_tenant_price(draft)

        if pricing_model == PRICING_MODEL_VISIT_FEE:
            pass  # base/min_price/max_price/note already set above.
        elif tenant_price is not None:
            base = max(tenant_price["minimum_price"], floor_price)
            min_price = tenant_price["minimum_price"]
            max_price = tenant_price["maximum_price"]
            note = f"Tenant-set price ({tenant_price['source']})."
        elif pricing_model == PRICING_MODEL_FIXED:
            base  = max(float(offering.base_price), floor_price)
            min_price = float(offering.min_price) if offering.min_price else base
            max_price = float(offering.max_price) if offering.max_price else None
            note  = "Fixed price service (admin estimate — no tenant assigned yet)."
        else:
            base  = max(float(offering.base_price), floor_price)
            min_price = float(offering.min_price) if offering.min_price else base
            max_price = float(offering.max_price) if offering.max_price else None
            note  = "Estimated price (admin estimate — no tenant assigned yet)."

        # MODULE-L5-10: per-category customer charge (platform fee). The platform
        # earns from both sides — a commission from the provider AND this charge
        # added to what the customer pays, shown to them as an included fee.
        # e.g. Rs.500 service + 10% = Rs.550 ("Rs.50 platform fee included").
        charge_pct = float(cat.customer_charge_pct) if (cat and cat.customer_charge_pct is not None) else 0.0
        def _with_fee(x):
            return round(x * (1 + charge_pct / 100.0), 2) if x is not None else None
        platform_fee = round(base * charge_pct / 100.0, 2)
        customer_total = round(base + platform_fee, 2)

        requires_inspection_estimate = pricing_model == PRICING_MODEL_VISIT_FEE

        return {
            "pricing_model":   pricing_model,
            # Canonical, explicit mode flag (Level-5 pricing-contract fix) --
            # "inspection" vs "fixed" -- so downstream consumers (match-and-
            # price, confirm-price-choice, booking summary) never have to
            # re-derive the mode from `requires_inspection_estimate` alone.
            "pricing_mode":    "inspection" if pricing_model == PRICING_MODEL_VISIT_FEE else "fixed",
            "visit_fee":       base if pricing_model == PRICING_MODEL_VISIT_FEE else 0,
            # Repair/inspection-based pricing must never present Low/Mid/High
            # as a promised repair amount before inspection -- the customer
            # sees this disclosure instead; the visit fee is the only amount
            # shown as a number. Final repair cost is a tenant-prepared
            # estimate the customer approves later (Work Start Approval Gate,
            # _assert_quote_approval_satisfied, remains the sole runtime
            # authority for whether work may start).
            "requires_inspection_estimate": requires_inspection_estimate,
            "customer_message": note if requires_inspection_estimate else None,
            # PLATFORM guarantee about the visit fee, authored here next to
            # the rule that actually enforces it
            # (invoice_payment.direct_payments_service._expected_amount:
            # approving the post-inspection estimate credits the visit fee
            # against the work; declining leaves only the visit fee payable).
            #
            # Emitted as structured data rather than left to a tenant's
            # free-text `customer_message`, which is what the app used to
            # render -- so the promise the customer reads can never drift
            # from the code that honours it, and is never absent just
            # because a tenant did not type it.
            #
            # `condition` states the real limit: the credit applies when the
            # work amount EXCEEDS the visit fee (the code guards
            # `work_amount > visit_fee`, so a bill can never go negative).
            "visit_fee_policy": {
                "credited_against_work": True,
                "credited_when":  "customer_approves_estimate",
                "condition":      "work_amount_exceeds_visit_fee",
                "if_declined":    "visit_fee_only",
            } if requires_inspection_estimate and base else None,
            "base_price":      base,          # service price (provider basis)
            "min_price":       min_price,
            "max_price":       max_price,
            "currency":        "INR",
            "city_tier":       floor_row.tier if floor_row else "tier_3",
            "note":            note,
            # ── customer-facing platform fee (inclusive) ──────────────────────
            "platform_fee_pct":       charge_pct,
            "platform_fee":           platform_fee,
            "customer_total":         customer_total,      # what the customer pays
            "customer_min_price":     _with_fee(min_price),
            "customer_max_price":     _with_fee(max_price),
            "fee_included_note":      (f"Includes ₹{int(platform_fee)} platform fee ({charge_pct:g}%)"
                                       if charge_pct else None),
            # display the inclusive total the customer actually pays
            "display_price":   f"₹{int(customer_total)}",
            "source":          "backend_catalog",
        }

    async def _validate_job_type_context(self, draft: HomeServiceBookingDraft) -> dict | None:
        """HOME-SERVICES-RUNTIME-SAFETY Phase 2A.2: independently re-validate
        the draft's Job Type/Blueprint context (spec sections 6, 8, 12).
        Returns None if valid, or a structured {"code","message"} error.
        Shared by mark_ready_for_confirmation (draft-side gate) and
        finalize() (independent revalidation -- defense in depth, not trust
        of the earlier draft-side check alone).
        """
        if not draft.job_type_id:
            return {"code": "JOB_TYPE_REQUIRED",
                    "message": "Select a service problem or job type before confirming."}

        from app.engines.admin_catalog.models import MasterServiceJobType, ServiceJobWorkflow, JobTypeDefinition
        link = (await self.db.execute(
            select(MasterServiceJobType).where(
                MasterServiceJobType.master_service_id == draft.offering_id,
                MasterServiceJobType.job_type_id == draft.job_type_id,
            )
        )).scalars().first()
        if link is None:
            return {"code": "INVALID_JOB_TYPE_FOR_SERVICE",
                    "message": "The selected job type is not available for this service."}
        if not link.is_active:
            return {"code": "JOB_TYPE_INACTIVE",
                    "message": "The selected job type is no longer active."}

        jt = await self.db.get(JobTypeDefinition, draft.job_type_id)
        if jt is not None and not jt.is_active:
            return {"code": "JOB_TYPE_INACTIVE",
                    "message": "The selected job type is no longer active."}

        current_workflow = (await self.db.execute(
            select(ServiceJobWorkflow).where(
                ServiceJobWorkflow.master_service_id == draft.offering_id,
                ServiceJobWorkflow.job_type_id == draft.job_type_id,
                ServiceJobWorkflow.is_current.is_(True),
            )
        )).scalars().first()
        if current_workflow is None:
            return {"code": "BLUEPRINT_NOT_PUBLISHED",
                    "message": "This job type has no published workflow configuration yet."}

        if draft.service_job_workflow_id != current_workflow.id:
            # Phase 2A.2 section 12: the snapshot captured earlier has been
            # superseded by an admin publishing a new version since this
            # draft selected its Job Type. Do NOT silently re-snapshot and
            # proceed -- the new version may have different requirements the
            # customer never saw. Re-running _resolve_job_type_snapshot (via
            # update_draft_fields) refreshes the snapshot explicitly.
            return {"code": "BLUEPRINT_VERSION_INVALID",
                    "message": "This service's requirements have been updated. Please reselect to continue."}

        if draft.selected_problem_id:
            from app.engines.admin_catalog.models import ServiceIssueMapping
            mapping = (await self.db.execute(
                select(ServiceIssueMapping).where(
                    ServiceIssueMapping.issue_type_id == draft.selected_problem_id,
                    ServiceIssueMapping.master_service_id == draft.offering_id,
                    ServiceIssueMapping.deleted_at.is_(None),
                )
            )).scalars().first()
            if mapping is not None and mapping.job_type_id is not None and mapping.job_type_id != draft.job_type_id:
                return {"code": "PROBLEM_JOB_TYPE_MISMATCH",
                        "message": "The selected problem no longer matches the selected job type."}

        return None

    async def _resolve_job_type_snapshot(
        self, draft: HomeServiceBookingDraft, job_type_id: uuid.UUID,
    ) -> None:
        """HOME-SERVICES-RUNTIME-SAFETY Phase 2A.2: validate job_type_id
        against the catalog (belongs to draft.offering_id, active link) and
        snapshot the exact CURRENT ServiceJobWorkflow version -- this is the
        one-time "Blueprint Version" capture point (spec section 10). A
        later admin edit creates a NEW workflow row (job_type_blueprint_
        service.set_workflow is now append-only); this draft keeps pointing
        at the version captured here until the customer explicitly re-picks
        the job type or the offering changes.
        """
        from app.engines.admin_catalog.models import MasterServiceJobType, ServiceJobWorkflow
        link = (await self.db.execute(
            select(MasterServiceJobType).where(
                MasterServiceJobType.master_service_id == draft.offering_id,
                MasterServiceJobType.job_type_id == job_type_id,
                MasterServiceJobType.is_active.is_(True),
            )
        )).scalars().first()
        if link is None:
            raise ServiceOSException(
                ERR_INVALID_JOB_TYPE_FOR_SERVICE,
                "The selected job type is not available for this service.",
                status_code=422,
            )
        workflow = (await self.db.execute(
            select(ServiceJobWorkflow).where(
                ServiceJobWorkflow.master_service_id == draft.offering_id,
                ServiceJobWorkflow.job_type_id == job_type_id,
                ServiceJobWorkflow.is_current.is_(True),
            )
        )).scalars().first()
        draft.job_type_id = job_type_id
        draft.master_service_job_type_id = link.id
        draft.service_job_workflow_id = workflow.id if workflow else None

    async def _resolve_address_snapshot(
        self, draft: HomeServiceBookingDraft, address_id: uuid.UUID,
    ) -> None:
        """Load address record and copy into draft snapshot."""
        from app.engines.serviceability.models import CustomerAddress
        addr = await self.db.get(CustomerAddress, address_id)
        if addr:
            draft.address_id = addr.id
            draft.city       = addr.city
            draft.zipcode    = addr.zipcode
            draft.address_snapshot = {
                "address_line_1": addr.address_line_1,
                "address_line_2": addr.address_line_2,
                "landmark":       addr.landmark,
                "city":           addr.city,
                "state":          addr.state,
                "zipcode":        addr.zipcode,
                "country":        addr.country,
                "name":           addr.name,
                "phone":          addr.phone,
            }

    async def _enrich_draft(self, draft: HomeServiceBookingDraft) -> dict:
        """Return draft dict with offering name/slug attached."""
        from app.engines.admin_catalog.models import MasterService, ServiceCategory
        result = draft.to_dict()
        offering = await self.db.get(MasterService, draft.offering_id)
        if offering:
            result["offering_name"]      = offering.service_name
            result["offering_slug"]      = offering.slug
            result["required_fields"]    = self._get_required_field_list(offering)
            result["pricing_model"]      = offering.pricing_model
        cat = await self.db.get(ServiceCategory, draft.category_id)
        if cat:
            result["category_name"] = cat.name
            result["category_slug"] = cat.slug
        if draft.job_type_id:
            from app.engines.admin_catalog.models import JobTypeDefinition
            jt = await self.db.get(JobTypeDefinition, draft.job_type_id)
            if jt:
                result["job_type_key"]   = jt.key
                result["job_type_label"] = jt.label
        return result

    async def _emit_event(
        self,
        draft_id: uuid.UUID,
        actor_type: str,
        event_type: str,
        old_value: dict | None = None,
        new_value: dict | None = None,
        message: str | None = None,
    ) -> None:
        try:
            event = HomeServiceBookingDraftEvent(
                id=uuid.uuid4(),
                draft_id=draft_id,
                actor_type=actor_type,
                event_type=event_type,
                old_value=old_value,
                new_value=new_value,
                message=message,
                request_id=self.request_id,
            )
            self.db.add(event)
            await self.db.flush()
        except Exception as exc:
            logger.warning("home_service.event_failed", error=str(exc))
