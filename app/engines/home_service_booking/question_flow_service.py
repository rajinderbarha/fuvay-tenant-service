"""LEVEL-5 REMEDIATION (2026-08-01, Phase 3) — Deterministic Question Flow.

Binds admin_catalog's `CatalogQuestionService.resolve_applicable_questions`
(already deterministic, DB-configured, admin-editable) to the canonical
`HomeServiceBookingDraft`, producing one versioned, allowlisted structured
envelope. The backend selects every question and every allowed answer;
DeepSeek may only phrase the resolved question naturally and interpret a
free-text reply into one of the allowed option ids — it never chooses a
different question, invents an option, or advances the flow itself.

Unknown question ids, missing workflow definitions (no job_type_id
resolved yet), and invalid answers all fail closed (422/404/409), never
silently accepted or guessed.
"""
from __future__ import annotations
import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.question_service import CatalogQuestionService
from app.engines.home_service_booking.models import HomeServiceBookingDraft
from app.exceptions import ServiceOSException
from app.core.security import enforce_booking_action_limits

QUESTION_FLOW_ENVELOPE_VERSION = 1

ERR_DRAFT_NOT_FOUND = "QF_DRAFT_NOT_FOUND"
ERR_DRAFT_ACCESS_DENIED = "QF_DRAFT_ACCESS_DENIED"
ERR_OFFERING_UNAVAILABLE = "QF_OFFERING_UNAVAILABLE"
ERR_JOB_TYPE_REQUIRED = "QF_JOB_TYPE_REQUIRED"
ERR_QUESTION_NOT_APPLICABLE = "QF_QUESTION_NOT_APPLICABLE"
ERR_INVALID_OPTION = "QF_INVALID_OPTION"
ERR_ANSWER_REQUIRED = "QF_ANSWER_REQUIRED"
ERR_STALE_VERSION = "QF_STALE_QUESTION_FLOW_VERSION"

_CHOICE_TYPES = ("single_select", "multi_select")


class QuestionFlowService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.catalog = CatalogQuestionService(db=db)

    # ── Draft access ─────────────────────────────────────────────────────────

    async def _require_draft(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None,
    ) -> HomeServiceBookingDraft:
        draft = await self.db.get(HomeServiceBookingDraft, draft_id)
        if not draft:
            raise ServiceOSException(
                ERR_DRAFT_NOT_FOUND, f"Booking draft '{draft_id}' not found.", status_code=404,
            )
        if customer_id and draft.customer_id and draft.customer_id != customer_id:
            raise ServiceOSException(
                ERR_DRAFT_ACCESS_DENIED, "You do not have access to this booking draft.", status_code=403,
            )
        return draft

    async def _require_publisher(self, draft: HomeServiceBookingDraft) -> None:
        """A client can hand back a draft_id it cached locally (e.g. an
        AsyncStorage pointer from an earlier session) for an offering that
        has since become unpublished, or was always an orphaned catalog
        entry no tenant ever offered. Without this, a customer's app can
        get permanently stuck resuming a dead conversation whose offering
        structurally has no admin-catalog wiring (no issue types, no job
        type) -- confirmed live ("AC Service" alongside the real "AC
        Repair"/"AC Installation"). Fails closed with a distinct code the
        client can react to by discarding its cached draft_id and starting
        fresh, rather than a generic error."""
        from sqlalchemy import select
        from app.engines.admin_catalog.models import TenantService, ServiceIssueMapping
        has_publisher = (await self.db.execute(
            select(TenantService.id).where(
                TenantService.master_service_id == draft.offering_id,
                TenantService.is_enabled.is_(True),
                TenantService.is_active.is_(True),
                TenantService.setup_status == "published",
            ).limit(1)
        )).scalars().first()
        # A published offering can still have zero real problem/issue-type
        # wiring (confirmed live: "AC Service" is published by a tenant but
        # has no ServiceIssueMapping rows) -- job_type_id could then never
        # resolve, permanently trapping the client in plain-text fallback.
        has_problems = has_publisher and (await self.db.execute(
            select(ServiceIssueMapping.id).where(
                ServiceIssueMapping.master_service_id == draft.offering_id,
                ServiceIssueMapping.status == "active",
            ).limit(1)
        )).scalars().first()
        if not has_publisher or not has_problems:
            raise ServiceOSException(
                ERR_OFFERING_UNAVAILABLE,
                "This service is no longer offered. Start a new request.",
                status_code=410,
            )

    def _require_scope(self, draft: HomeServiceBookingDraft) -> None:
        if not draft.job_type_id:
            raise ServiceOSException(
                ERR_JOB_TYPE_REQUIRED,
                "Select a service problem or job type before questions can be resolved.",
                status_code=422,
            )

    async def _resolve(self, draft: HomeServiceBookingDraft) -> dict:
        prior = draft.catalog_question_answers or {}
        context = {
            "selected_problem_id": draft.selected_problem_id,
            "enabled_dimension_ids": [],
            "prior_answers": prior,
        }
        return await self.catalog.resolve_applicable_questions(
            master_service_id=draft.offering_id, job_type_id=draft.job_type_id, context=context,
        )

    def _build_envelope(self, draft: HomeServiceBookingDraft, resolved: dict) -> dict:
        questions = resolved["questions"]
        known = resolved["known"]
        current = questions[0] if questions else None
        complete = current is None

        envelope: dict[str, Any] = {
            "envelope_version": QUESTION_FLOW_ENVELOPE_VERSION,
            "session_id": str(draft.ai_session_id) if draft.ai_session_id else None,
            "draft_id": str(draft.id),
            "workflow_version": str(draft.service_job_workflow_id) if draft.service_job_workflow_id else None,
            "question_flow_version": draft.question_flow_version,
            "scope": {
                "category_id": str(draft.category_id),
                "offering_id": str(draft.offering_id),
                "job_type_id": str(draft.job_type_id) if draft.job_type_id else None,
            },
            "current_question": None,
            "progress": {
                "answered_count": len(known),
                "remaining_count": len(questions),
                "complete": complete,
            },
            "next_permitted_actions": (
                ["proceed_to_serviceability"] if complete else ["submit_answer"]
            ),
        }
        if current:
            envelope["current_question"] = {
                "question_id": current["id"],
                "question_key": current["question_key"],
                "question_type": current["input_type"],
                "text": current["label"],
                "help_text": current.get("help_text"),
                "required": current["required"],
                "options": [
                    {"id": o.get("id"), "label": o.get("label") or o.get("code")}
                    for o in current.get("options", [])
                ],
                "validation_metadata": current.get("validation"),
                "photo_capable": current["input_type"] == "photo",
            }
        return envelope

    async def _bridge_to_draft_columns(
        self, draft: HomeServiceBookingDraft, question_key: str, answer_value: Any,
    ) -> None:
        """The catalog-question answer store (catalog_question_answers JSON)
        and the draft's own structured columns (brand_id, offering_type_id)
        are two separate systems -- the OLDER required-field validation
        (_compute_missing_fields, finalize()) only ever reads the columns,
        never the JSON answers. Without this, tapping a real brand/type
        option would save the answer but finalize() would still report
        brand/type as permanently missing -- the tap would silently do
        nothing toward actually completing the booking.

        Which column an answer belongs to is decided by the DIMENSION the
        question draws its options from (`CatalogDimension.legacy_source`),
        not by the question's name. Matching on names was a real bug: the
        list was ("ac_type", "service_type", "offering_type"), while the
        catalog names the same dimension-backed question `equipment_type` on
        every non-AC offering -- 14 of the 18 published services. For all of
        those `offering_type_id` was never written, so EVERY chimney, geyser,
        RO, washing-machine and refrigerator booking failed confirmation with
        "Missing required fields: offering_type_id". Confirmed live on a real
        WhatsApp booking for Chimney Repair.
        """
        source = await self._answer_target(draft, question_key)
        if not answer_value or source is None:
            return

        # `answer_value` is the option's own `code` -- Brand.slug /
        # ServiceType.slug by construction. Match case-insensitively: option
        # codes are authored in upper case ("LG", "SAMSUNG") while the slugs
        # are lower case, so an exact compare never succeeded and left the
        # column NULL. Fall back to the display name for options an admin
        # authored by hand.
        needle = str(answer_value).strip().lower()
        if source == "brands":
            from app.engines.admin_catalog.models import Brand
            model, column = Brand, "brand_id"
        else:
            from app.engines.admin_catalog.models import ServiceType
            model, column = ServiceType, "offering_type_id"

        row = (await self.db.execute(
            select(model).where(func.lower(model.slug) == needle)
        )).scalars().first()
        if not row:
            row = (await self.db.execute(
                select(model).where(func.lower(model.name) == needle)
            )).scalars().first()
        if row:
            setattr(draft, column, row.id)

    async def _answer_target(
        self, draft: HomeServiceBookingDraft, question_key: str,
    ) -> str | None:
        """"brands", "service_types", or None when the answer is just an answer.

        Read from the question's own dimension so a renamed or newly added
        question bridges correctly without this module being edited. The two
        legacy key names are kept as a fallback for static-option questions
        that carry no dimension at all.
        """
        from app.engines.admin_catalog.models import CatalogDimension, CatalogQuestion

        legacy_source = (await self.db.execute(
            select(CatalogDimension.legacy_source)
            .join(CatalogQuestion, CatalogQuestion.dimension_id == CatalogDimension.id)
            .where(
                CatalogQuestion.master_service_id == draft.offering_id,
                CatalogQuestion.question_key == question_key,
                CatalogQuestion.is_active.is_(True),
            )
            .limit(1)
        )).scalars().first()
        if legacy_source in ("brands", "service_types"):
            return legacy_source
        if question_key == "brand":
            return "brands"
        if question_key in ("ac_type", "service_type", "offering_type"):
            return "service_types"
        return None

    # ── Historical answer snapshot (finalize()-time only) ───────────────────

    async def build_answer_snapshot(self, draft: HomeServiceBookingDraft) -> dict | None:
        """BOOKING-DETAILS-CONTRACT-FIXES (2026-08-01): versioned, immutable
        snapshot of every answered question -- called ONCE at finalize()
        time and frozen onto `ServiceBooking.answer_snapshot`. Resolves
        each question's label/type/order and the answered option's display
        label NOW, from the live catalog, so a later catalog edit (a
        question re-labeled, an option renamed or removed) can never alter
        what a historical, already-confirmed booking shows it was
        confirmed with. `draft.catalog_question_answers` alone (question_key
        -> business code) is not sufficient for that guarantee -- it has no
        label, type, order, or catalog-version context.

        Unlike `_resolve()`/`resolve_applicable_questions` (which
        deliberately excludes already-answered questions -- see
        CatalogQuestionService.resolve_applicable_questions), this queries
        every CatalogQuestion for the scope directly so every answered
        question, not just the currently-applicable ones, is captured.
        """
        from sqlalchemy import select
        from app.engines.admin_catalog.models import CatalogQuestion

        answers = draft.catalog_question_answers or {}
        if not answers:
            return None

        job_type_filter = (
            CatalogQuestion.job_type_id == draft.job_type_id
            if draft.job_type_id else CatalogQuestion.job_type_id.is_(None)
        )
        rows = (await self.db.execute(
            select(CatalogQuestion).where(
                CatalogQuestion.master_service_id == draft.offering_id,
                job_type_filter,
            ).order_by(CatalogQuestion.display_order)
        )).scalars().all()

        snapshot_answers: list[dict] = []
        for qn in rows:
            if qn.question_key not in answers:
                continue
            raw_value = answers[qn.question_key]
            options = await self.catalog._resolved_options(qn)
            by_code = {
                str(o.get("code") or o.get("id")): o.get("label")
                for o in options if o.get("code") or o.get("id")
            }
            if isinstance(raw_value, list):
                answer_label = ", ".join(by_code.get(str(v), str(v)) for v in raw_value)
            else:
                answer_label = by_code.get(str(raw_value), str(raw_value))
            snapshot_answers.append({
                "question_id": str(qn.id),
                "question_key": qn.question_key,
                "question_label": qn.label,
                "question_type": qn.input_type,
                "answer_code": raw_value,
                "answer_label": answer_label,
                "sequence": qn.display_order,
            })

        return {"schema_version": 1, "answers": snapshot_answers}

    # ── Public API ───────────────────────────────────────────────────────────

    async def get_current_question(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None,
    ) -> dict:
        draft = await self._require_draft(draft_id, customer_id)
        await self._require_publisher(draft)
        self._require_scope(draft)
        resolved = await self._resolve(draft)
        envelope = self._build_envelope(draft, resolved)
        envelope["answered_questions"] = await self._answered_summary(draft)
        return envelope

    async def _answered_summary(self, draft: HomeServiceBookingDraft) -> list[dict]:
        """Confirmed-answer rows for already-answered questions, so the UI
        can collapse them into a one-line "Brand: LG ✓" chip instead of
        only ever showing the single next unanswered question -- reuses
        build_answer_snapshot's own label resolution (same source of
        truth as the finalize()-time immutable snapshot) rather than a
        second, divergent implementation."""
        snapshot = await self.build_answer_snapshot(draft)
        if not snapshot:
            return []
        return [
            {
                "question_id": a["question_id"],
                "question_key": a["question_key"],
                "question_label": a["question_label"],
                "answer_label": a["answer_label"],
            }
            for a in sorted(snapshot["answers"], key=lambda a: a["sequence"])
        ]

    async def submit_answer(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        question_id: str,
        option_id: str | list[str] | None = None,
        value: Any = None,
        expected_version: int | None = None,
    ) -> dict:
        draft = await self._require_draft(draft_id, customer_id)
        await enforce_booking_action_limits(
            "answer", actor_id=str(customer_id or draft.ai_session_id or draft_id)
        )
        self._require_scope(draft)

        # Duplicate-submission / stale-view protection: a client that fetched
        # the question before someone else (or a retried request) already
        # answered it must be told to refetch, not silently double-apply.
        if expected_version is not None and expected_version != draft.question_flow_version:
            raise ServiceOSException(
                ERR_STALE_VERSION,
                "This question set has changed since you last saw it. Fetch the current question again.",
                status_code=409,
            )

        resolved = await self._resolve(draft)
        questions_by_id = {q["id"]: q for q in resolved["questions"]}
        question = questions_by_id.get(str(question_id))
        if question is None:
            # Fails closed: either an unknown id, an id belonging to a
            # different service/job-type, or a question that's no longer
            # applicable (already answered, or a rule now excludes it).
            raise ServiceOSException(
                ERR_QUESTION_NOT_APPLICABLE,
                "This question is not currently applicable — fetch the current question again.",
                status_code=422,
            )

        answer_value = value
        if question["input_type"] in _CHOICE_TYPES:
            # CUSTOMER WORKFLOW REGRESSION CLOSURE (2026-08-01): admin_catalog's
            # own dependent-question rule engine (_rules_pass, "answer_equals")
            # compares a rule's expected_value against prior_answers' stored
            # VALUES — and expected_value is authored by an admin as a
            # business-meaningful code (e.g. "LG"), never as an opaque option
            # UUID. Storing the raw option_id here (as originally written)
            # meant no answer_equals rule could ever match, so a real
            # type/brand-dependent question (e.g. "capacity" shown only when
            # brand=LG) silently never appeared — confirmed live against a
            # real configured rule. Store the option's own `code` (falling
            # back to its id only for dimension-sourced options that have no
            # code, e.g. Brand/ServiceType lookups) so dependent questions
            # resolve exactly as an admin configuring the rule would expect.
            by_id = {o["id"]: o for o in question.get("options", [])}
            allowed_ids = set(by_id.keys())
            if question["input_type"] == "single_select":
                if not option_id or option_id not in allowed_ids:
                    raise ServiceOSException(
                        ERR_INVALID_OPTION, "The selected option is not valid for this question.", status_code=422,
                    )
                answer_value = by_id[option_id].get("code") or option_id
            else:  # multi_select
                chosen = option_id if isinstance(option_id, list) else ([option_id] if option_id else [])
                if not chosen or not set(chosen).issubset(allowed_ids):
                    raise ServiceOSException(
                        ERR_INVALID_OPTION,
                        "One or more selected options are not valid for this question.", status_code=422,
                    )
                answer_value = [by_id[cid].get("code") or cid for cid in chosen]
        elif question["required"] and answer_value in (None, ""):
            raise ServiceOSException(
                ERR_ANSWER_REQUIRED, "This question requires an answer.", status_code=422,
            )

        prior = dict(draft.catalog_question_answers or {})
        prior[question["question_key"]] = answer_value
        draft.catalog_question_answers = prior
        await self._bridge_to_draft_columns(draft, question["question_key"], answer_value)
        draft.question_flow_version = (draft.question_flow_version or 1) + 1
        await self.db.commit()
        await self.db.refresh(draft)

        # Re-evaluate dependent answers: re-resolving from scratch with the
        # updated prior_answers naturally drops/reveals questions whose
        # show-when rules reference the answer that just changed.
        resolved_after = await self._resolve(draft)
        envelope = self._build_envelope(draft, resolved_after)
        envelope["answered_questions"] = await self._answered_summary(draft)
        return envelope
