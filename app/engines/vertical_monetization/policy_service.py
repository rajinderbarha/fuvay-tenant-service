"""VERTICAL-MONETIZATION: policy draft/validate/preview/publish/history.

One controlled edit workflow: Edit Draft -> Validate -> Preview Impact ->
Review Changes -> Publish. A published version is immutable — editing
always creates a new draft version, never mutates a published row in
place. Reuses the existing vertical_catalog audit log (VerticalAuditLog)
rather than creating a second audit table.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.vertical_catalog.models import Vertical, VerticalAuditLog
from app.engines.vertical_monetization.models import (
    VerticalMonetizationPolicy, MonetizationJobTypeRule, PROVIDER_MODELS, CUSTOMER_FEE_MODELS, COLLECTION_STAGES,
    PROVIDER_CHARGEABLE_EVENTS,
)
from app.engines.vertical_monetization.calculation_service import (
    calculate_customer_platform_fee, to_minor, to_major,
)
from app.exceptions import ServiceOSException

_DRAFT_FIELDS = {
    "provider_model", "provider_percentage", "provider_fixed_amount_minor",
    "provider_credit_units", "provider_subscription_plan_id", "provider_chargeable_event",
    "provider_min_charge_minor", "provider_max_charge_minor",
    "customer_fee_model", "customer_fee_percentage", "customer_fee_fixed_amount_minor",
    "customer_fee_min_minor", "customer_fee_max_minor", "customer_fee_basis",
    "collection_stage", "customer_fee_refund_policy", "currency", "effective_from", "change_summary",
    # SLA breach: what a late job costs, and where the money goes.
    "sla_breach_hours", "sla_penalty_amount", "sla_penalty_to_customer",
    "sla_penalty_debt_cap", "sla_auto_cancel", "sla_notify_provider",
    "sla_penalty_type", "sla_penalty_percentage", "sla_penalty_min",
    "sla_penalty_max", "sla_breachable_statuses",
    # Health: when a provider is stopped, for how long, and what they come back at.
    "health_suspension_threshold", "health_suspension_days", "health_reinstatement_score",
    # Media retention: how long each kind of job photo is kept.
    "customer_photo_retention_days", "completion_proof_retention_days",
    # How often a provider is reminded, per severity level.
    "credit_reminder_hours_low", "credit_reminder_hours_blocked",
    "credit_reminder_hours_arrears",
}


class VerticalMonetizationPolicyService:

    async def _vertical(self, db: AsyncSession, key: str) -> Vertical:
        v = (await db.execute(select(Vertical).where(Vertical.key == key))).scalar_one_or_none()
        if not v:
            raise ServiceOSException("NOT_FOUND", f"Vertical '{key}' not found", status_code=404)
        return v

    async def get_current(self, db: AsyncSession, key: str) -> dict | None:
        v = await self._vertical(db, key)
        p = (await db.execute(select(VerticalMonetizationPolicy).where(
            VerticalMonetizationPolicy.vertical_id == v.id, VerticalMonetizationPolicy.is_current == True,  # noqa: E712
        ))).scalar_one_or_none()
        return p.to_dict() if p else None

    async def get_draft(self, db: AsyncSession, key: str) -> dict | None:
        v = await self._vertical(db, key)
        p = (await db.execute(select(VerticalMonetizationPolicy).where(
            VerticalMonetizationPolicy.vertical_id == v.id, VerticalMonetizationPolicy.status == "draft",
        ).order_by(VerticalMonetizationPolicy.version_number.desc()))).scalars().first()
        return p.to_dict() if p else None

    async def list_history(self, db: AsyncSession, key: str) -> list[dict]:
        v = await self._vertical(db, key)
        rows = (await db.execute(select(VerticalMonetizationPolicy).where(
            VerticalMonetizationPolicy.vertical_id == v.id,
        ).order_by(VerticalMonetizationPolicy.version_number.desc()))).scalars().all()
        return [p.to_dict() for p in rows]

    async def get_impact(self, db: AsyncSession, key: str) -> dict:
        """Selected-policy-inspector impact numbers. `ServiceCategory` is the
        only existing bridge between a Business Vertical and its catalog
        (service groups / master services) -- linked by the free-text
        `vertical_type` string, not a real FK (see Phase 1 audit). Reported
        honestly as string-matched, not corrected here; correcting that is a
        separate catalog-model change, out of scope for a monetization read.
        `active_or_in_progress_jobs` is only real for home_services today
        (the only vertical with a live ServiceJob pipeline) -- every other
        vertical reports _available: false rather than a fabricated zero."""
        from app.engines.admin_catalog.models import ServiceCategory, ServiceGroup, MasterService
        from app.engines.tenant_engine.models import Tenant

        v = await self._vertical(db, key)

        category_ids = (await db.execute(
            select(ServiceCategory.id).where(ServiceCategory.vertical_type == key)
        )).scalars().all()

        affected_service_groups = 0
        affected_master_services = 0
        if category_ids:
            affected_service_groups = await db.scalar(
                select(func.count(ServiceGroup.id)).where(ServiceGroup.category_id.in_(category_ids))
            ) or 0
            affected_master_services = await db.scalar(
                select(func.count(MasterService.id)).where(MasterService.category_id.in_(category_ids))
            ) or 0

        active_providers = await db.scalar(
            select(func.count(Tenant.id)).where(Tenant.vertical == key, Tenant.status == "active")
        ) or 0

        active_jobs: int | None = None
        active_jobs_available = False
        if key == "home_services":
            from app.engines.final_records.models import ServiceJob
            active_jobs = await db.scalar(
                select(func.count(ServiceJob.id)).where(
                    ServiceJob.status.notin_(["completed", "cancelled", "failed", "closed_estimate_declined"]))
            ) or 0
            active_jobs_available = True

        return {
            "vertical_key": key,
            "affected_service_groups": affected_service_groups,
            "affected_master_services": affected_master_services,
            "category_bridge_is_string_match": True,
            "active_providers": active_providers,
            "active_or_in_progress_jobs": active_jobs,
            "active_or_in_progress_jobs_available": active_jobs_available,
        }

    def _validate(self, payload: dict) -> list[str]:
        errors = []
        def decimal_field(name: str, *, minimum: Decimal | None = None,
                          maximum: Decimal | None = None) -> Decimal | None:
            raw = payload.get(name)
            if raw is None or raw == "":
                return None
            try:
                value = Decimal(str(raw))
            except Exception:
                errors.append(f"{name} must be numeric")
                return None
            if minimum is not None and value < minimum:
                errors.append(f"{name} must be at least {minimum}")
            if maximum is not None and value > maximum:
                errors.append(f"{name} must be at most {maximum}")
            return value

        pm = payload.get("provider_model", "NONE")
        if pm not in PROVIDER_MODELS:
            errors.append(f"provider_model must be one of {sorted(PROVIDER_MODELS)}")
        if pm == "PERCENTAGE_COMMISSION" and payload.get("provider_percentage") in (None, ""):
            errors.append("provider_percentage is required for PERCENTAGE_COMMISSION")
        if pm == "FIXED_COMPLETION_CHARGE" and payload.get("provider_fixed_amount_minor") in (None, ""):
            errors.append("provider_fixed_amount_minor is required for FIXED_COMPLETION_CHARGE")
        if pm == "COMPLETION_CREDITS" and payload.get("provider_credit_units") in (None, ""):
            errors.append("provider_credit_units is required for COMPLETION_CREDITS")
        if pm == "SUBSCRIPTION" and not payload.get("provider_subscription_plan_id"):
            errors.append("provider_subscription_plan_id is required for SUBSCRIPTION")
        # WHEN the provider is charged. Optional: an unset value means the
        # runtime default (completion), which is how every policy behaved
        # before this became configurable.
        event = payload.get("provider_chargeable_event")
        if event not in (None, "") and event not in PROVIDER_CHARGEABLE_EVENTS:
            errors.append(
                "provider_chargeable_event must be one of "
                + ", ".join(sorted(PROVIDER_CHARGEABLE_EVENTS))
            )
        # A percentage can only be taken of a number that exists. Before
        # completion the final invoice has not been raised -- on an
        # inspection job the booking price is just the visit fee -- so a
        # percentage charged at work_started/work_done would be a percentage
        # of the wrong amount. Fixed credit models carry no such dependency.
        if pm == "PERCENTAGE_COMMISSION" and event in ("work_started", "work_done"):
            errors.append(
                "PERCENTAGE_COMMISSION can only be charged at job_completed or "
                "consultation_completed: the final invoiced value is not known "
                "before the job completes. Use a fixed credit model to charge earlier."
            )
        provider_pct = decimal_field("provider_percentage", minimum=Decimal("0"), maximum=Decimal("100"))
        provider_fixed = decimal_field("provider_fixed_amount_minor", minimum=Decimal("0"))
        provider_credits = decimal_field("provider_credit_units", minimum=Decimal("0"))
        provider_min = decimal_field("provider_min_charge_minor", minimum=Decimal("0"))
        provider_max = decimal_field("provider_max_charge_minor", minimum=Decimal("0"))
        if provider_min is not None and provider_max is not None and provider_min > provider_max:
            errors.append("provider_min_charge_minor cannot exceed provider_max_charge_minor")

        cf = payload.get("customer_fee_model", "NONE")
        if cf not in CUSTOMER_FEE_MODELS:
            errors.append(f"customer_fee_model must be one of {sorted(CUSTOMER_FEE_MODELS)}")
        if cf in ("PERCENTAGE", "PERCENTAGE_WITH_MIN_MAX") and payload.get("customer_fee_percentage") in (None, ""):
            errors.append("customer_fee_percentage is required for this customer_fee_model")
        if cf == "FIXED" and payload.get("customer_fee_fixed_amount_minor") in (None, ""):
            errors.append("customer_fee_fixed_amount_minor is required for FIXED")
        customer_pct = decimal_field("customer_fee_percentage", minimum=Decimal("0"), maximum=Decimal("100"))
        customer_fixed = decimal_field("customer_fee_fixed_amount_minor", minimum=Decimal("0"))
        customer_min = decimal_field("customer_fee_min_minor", minimum=Decimal("0"))
        customer_max = decimal_field("customer_fee_max_minor", minimum=Decimal("0"))
        if cf == "PERCENTAGE_WITH_MIN_MAX":
            if customer_min is None or customer_max is None:
                errors.append("customer_fee_min_minor and customer_fee_max_minor are required for PERCENTAGE_WITH_MIN_MAX")
            elif customer_min > customer_max:
                errors.append("customer_fee_min_minor cannot exceed customer_fee_max_minor")

        # SLA + health. All optional: an unset policy simply does not penalise
        # or suspend anyone, which is how every existing policy behaves.
        for name, minimum in (("sla_breach_hours", 1), ("health_suspension_days", 1)):
            raw = payload.get(name)
            if raw not in (None, ""):
                try:
                    if int(raw) < minimum:
                        errors.append(f"{name} must be at least {minimum}")
                except (TypeError, ValueError):
                    errors.append(f"{name} must be a whole number")
        ptype = payload.get("sla_penalty_type", "fixed") or "fixed"
        if ptype not in ("fixed", "percentage"):
            errors.append("sla_penalty_type must be fixed or percentage")
        pct = decimal_field("sla_penalty_percentage", minimum=Decimal("0"), maximum=Decimal("100"))
        pmin = decimal_field("sla_penalty_min", minimum=Decimal("0"))
        pmax = decimal_field("sla_penalty_max", minimum=Decimal("0"))
        if ptype == "percentage" and pct in (None, Decimal("0")):
            errors.append("sla_penalty_percentage is required when sla_penalty_type is percentage")
        if pmin is not None and pmax is not None and pmin > pmax:
            errors.append("sla_penalty_min cannot exceed sla_penalty_max")

        # A status that no job ever reaches would silently disable the penalty.
        statuses = payload.get("sla_breachable_statuses")
        if statuses not in (None, ""):
            from app.engines.execution.sla_breach_service import BREACHABLE_STATUSES
            if not isinstance(statuses, list) or not statuses:
                errors.append("sla_breachable_statuses must be a non-empty list")
            else:
                unknown = [x for x in statuses if x not in BREACHABLE_STATUSES]
                if unknown:
                    errors.append(
                        "sla_breachable_statuses contains statuses a job never breaches in: "
                        + ", ".join(map(str, unknown))
                    )
        decimal_field("sla_penalty_amount", minimum=Decimal("0"))
        decimal_field("sla_penalty_debt_cap", minimum=Decimal("0"))
        threshold = decimal_field("health_suspension_threshold", minimum=Decimal("0"), maximum=Decimal("100"))
        reinstate = decimal_field("health_reinstatement_score", minimum=Decimal("0"), maximum=Decimal("100"))

        # Reinstating BELOW the threshold re-suspends the provider the moment
        # they return -- permanently, because health is earned from work they
        # are barred from doing. The score they come back at must clear the bar.
        if threshold is not None and reinstate is not None and reinstate <= threshold:
            errors.append(
                "health_reinstatement_score must be greater than "
                "health_suspension_threshold, otherwise a reinstated provider is "
                "immediately re-suspended and can never recover"
            )
        if payload.get("sla_penalty_amount") not in (None, "") and not payload.get("sla_breach_hours"):
            errors.append("sla_breach_hours is required when an SLA penalty is set")

        stage = payload.get("collection_stage", "after_estimate_approval")
        if stage not in COLLECTION_STAGES:
            errors.append(f"collection_stage must be one of {sorted(COLLECTION_STAGES)}")
        return errors

    async def save_draft(self, db: AsyncSession, key: str, payload: dict, *, actor_id: uuid.UUID | None) -> dict:
        v = await self._vertical(db, key)
        errors = self._validate(payload)
        if errors:
            raise ServiceOSException("VALIDATION_ERROR", "; ".join(errors), status_code=422)

        existing_draft = (await db.execute(select(VerticalMonetizationPolicy).where(
            VerticalMonetizationPolicy.vertical_id == v.id, VerticalMonetizationPolicy.status == "draft",
        ))).scalar_one_or_none()
        if existing_draft:
            before = existing_draft.to_dict()
            for k in _DRAFT_FIELDS:
                if k in payload:
                    setattr(existing_draft, k, payload[k])
            await db.flush()
            db.add(VerticalAuditLog(
                vertical_id=v.id, actor_id=actor_id, action_type="monetization.policy.save_draft",
                before_state=before, after_state=existing_draft.to_dict(),
                notes=payload.get("change_summary") or "Draft updated.",
            ))
            await db.commit()
            return existing_draft.to_dict()

        max_version = (await db.execute(select(func.max(VerticalMonetizationPolicy.version_number)).where(
            VerticalMonetizationPolicy.vertical_id == v.id))).scalar() or 0

        # A new version CONTINUES the live policy; it does not start from
        # blank. Building it from `payload` alone silently reset every field
        # the caller happened not to send back to a column default, so an edit
        # to one field could quietly revert the others.
        live = (await db.execute(select(VerticalMonetizationPolicy).where(
            VerticalMonetizationPolicy.vertical_id == v.id,
            VerticalMonetizationPolicy.is_current == True,  # noqa: E712
        ))).scalar_one_or_none()
        seeded = {k: getattr(live, k) for k in _DRAFT_FIELDS} if live else {}
        seeded.update({k: payload[k] for k in _DRAFT_FIELDS if k in payload})

        p = VerticalMonetizationPolicy(
            vertical_id=v.id, version_number=max_version + 1, status="draft", is_current=False,
            created_by_user_id=actor_id,
            **seeded,
        )
        db.add(p)
        await db.flush()

        # Per-job-type rules belong to a policy VERSION, so a new version began
        # with none of them -- publishing it silently dropped every override the
        # admin had configured. Confirmed live: v5 carried a rule, v6 onwards
        # carried none. They are copied forward with the rest of the policy.
        cloned = 0
        if live is not None:
            for r in (await db.execute(select(MonetizationJobTypeRule).where(
                MonetizationJobTypeRule.policy_id == live.id,
                MonetizationJobTypeRule.status == "active",
            ))).scalars().all():
                db.add(MonetizationJobTypeRule(
                    policy_id=p.id, job_type_id=r.job_type_id,
                    customer_charge_enabled=r.customer_charge_enabled,
                    customer_charge_basis=r.customer_charge_basis,
                    provider_charge_enabled=r.provider_charge_enabled,
                    provider_charge_model=r.provider_charge_model,
                    provider_charge_credit_units=r.provider_charge_credit_units,
                    provider_chargeable_event=r.provider_chargeable_event,
                    status=r.status,
                ))
                cloned += 1
            await db.flush()

        db.add(VerticalAuditLog(
            vertical_id=v.id, actor_id=actor_id, action_type="monetization.policy.save_draft",
            before_state=live.to_dict() if live else None, after_state=p.to_dict(),
            notes=(payload.get("change_summary") or "Draft created.")
                  + (f" Carried forward {cloned} job-type rule(s)." if cloned else ""),
        ))
        await db.commit()
        return p.to_dict()

    async def discard_draft(self, db: AsyncSession, key: str, *, actor_id: uuid.UUID | None) -> dict:
        """Deletes the pending draft row outright. A draft is never
        published (status stays 'draft' the whole time it exists), so there
        is nothing to preserve -- unlike publish, this hard-deletes rather
        than superseding, since a discarded draft has no audit value of its
        own. Publishing remains the only irreversible step."""
        v = await self._vertical(db, key)
        draft = (await db.execute(select(VerticalMonetizationPolicy).where(
            VerticalMonetizationPolicy.vertical_id == v.id, VerticalMonetizationPolicy.status == "draft",
        ))).scalar_one_or_none()
        if not draft:
            raise ServiceOSException("NOT_FOUND", "No draft to discard.", status_code=404)
        draft_id = str(draft.id)
        await db.delete(draft)
        db.add(VerticalAuditLog(
            vertical_id=v.id, actor_id=actor_id, action_type="monetization.policy.discard_draft",
            before_state={"id": draft_id, "version_number": draft.version_number}, after_state=None,
            notes="Draft discarded before publish.",
        ))
        await db.commit()
        return {"discarded": True, "draft_id": draft_id}

    def validate(self, payload: dict) -> dict:
        errors = self._validate(payload)
        return {"valid": len(errors) == 0, "errors": errors}

    def preview(self, draft_dict: dict, example_service_amount: Decimal) -> dict:
        """Live server-calculated preview using an example amount. Never
        touches tenant service pricing — pure function over the DRAFT
        (unpublished) policy."""
        fake_policy = type("FakePolicy", (), {
            **{k: draft_dict.get(k) for k in _DRAFT_FIELDS},
            "id": draft_dict.get("id"), "version_number": draft_dict.get("version_number"),
            "customer_fee_percentage": Decimal(str(draft_dict["customer_fee_percentage"])) if draft_dict.get("customer_fee_percentage") is not None else None,
        })()
        result = calculate_customer_platform_fee(
            policy=fake_policy if draft_dict.get("customer_fee_model", "NONE") != "NONE" else None,
            service_subtotal_minor=to_minor(example_service_amount),
            calculation_basis="policy_preview",
            currency=draft_dict.get("currency", "INR"),
        )
        result["is_preview"] = True
        result["note"] = "This preview does not define or modify the tenant's service price."
        from app.engines.vertical_monetization.calculation_service import calculate_provider_completion_credits
        provider_result = calculate_provider_completion_credits(
            policy=fake_policy,
            service_amount=example_service_amount,
        )
        result.update(provider_result)
        customer_recovery_units = Decimal(to_major(result["fee_amount_minor"]))
        provider_units = Decimal(provider_result["provider_charge_credit_units"])
        result["customer_charge_recovery_credit_units"] = str(customer_recovery_units)
        result["total_credit_deduction"] = str((provider_units + customer_recovery_units).quantize(Decimal("0.01")))
        return result

    async def publish(self, db: AsyncSession, key: str, *, actor_id: uuid.UUID | None, reason: str) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "A reason is required to publish a policy change.", status_code=422)
        v = await self._vertical(db, key)
        draft = (await db.execute(select(VerticalMonetizationPolicy).where(
            VerticalMonetizationPolicy.vertical_id == v.id, VerticalMonetizationPolicy.status == "draft",
        ).with_for_update())).scalar_one_or_none()
        if not draft:
            raise ServiceOSException("NOT_FOUND", "No draft policy to publish.", status_code=404)
        errors = self._validate(draft.to_dict())
        if errors:
            raise ServiceOSException("VALIDATION_ERROR", "; ".join(errors), status_code=422)

        prior = (await db.execute(select(VerticalMonetizationPolicy).where(
            VerticalMonetizationPolicy.vertical_id == v.id, VerticalMonetizationPolicy.is_current == True,  # noqa: E712
        ).with_for_update())).scalar_one_or_none()
        before = prior.to_dict() if prior else None
        if prior:
            # Flushed BEFORE draft.is_current is set -- the partial unique
            # index ix_vmp_vertical_current is checked per-statement in
            # Postgres (not deferred), so setting both is_current values in
            # the same flush can transiently violate it depending on
            # statement ordering. Two flushes, never one, avoids that.
            prior.is_current = False
            prior.status = "superseded"
            await db.flush()

        draft.status = "published"
        draft.is_current = True
        draft.published_by_user_id = actor_id
        draft.published_at = datetime.now(timezone.utc)
        await db.flush()

        db.add(VerticalAuditLog(
            vertical_id=v.id, actor_id=actor_id, action_type="monetization.policy.publish",
            before_state=before, after_state=draft.to_dict(), notes=reason,
        ))
        await db.commit()
        await db.refresh(draft)
        return draft.to_dict()

    # ── Per-Job-Type rules (child of a specific policy version) ──────────────

    async def list_job_type_rules(self, db: AsyncSession, policy_id: uuid.UUID) -> list[dict]:
        rows = (await db.execute(select(MonetizationJobTypeRule).where(
            MonetizationJobTypeRule.policy_id == policy_id))).scalars().all()
        return [r.to_dict() for r in rows]

    async def upsert_job_type_rule(self, db: AsyncSession, policy_id: uuid.UUID, job_type_id: uuid.UUID,
                                   payload: dict) -> dict:
        policy = await db.get(VerticalMonetizationPolicy, policy_id)
        if not policy:
            raise ServiceOSException("NOT_FOUND", "Policy not found", status_code=404)
        if policy.status == "published":
            raise ServiceOSException("VALIDATION_ERROR",
                                     "Cannot modify job-type rules on a published policy -- create a new draft version.",
                                     status_code=422)
        from app.engines.admin_catalog.models import JobTypeDefinition
        if await db.get(JobTypeDefinition, job_type_id) is None:
            raise ServiceOSException("NOT_FOUND", "Job Type not found", status_code=404)
        if "provider_charge_credit_units" in payload and payload["provider_charge_credit_units"] not in (None, ""):
            try:
                credits = Decimal(str(payload["provider_charge_credit_units"]))
            except Exception:
                raise ServiceOSException("VALIDATION_ERROR", "provider_charge_credit_units must be numeric", status_code=422)
            if credits < 0:
                raise ServiceOSException("VALIDATION_ERROR", "provider_charge_credit_units cannot be negative", status_code=422)
        if payload.get("status", "active") not in {"active", "inactive"}:
            raise ServiceOSException("VALIDATION_ERROR", "status must be active or inactive", status_code=422)
        if payload.get("customer_charge_basis", "booking_price_snapshot") != "booking_price_snapshot":
            raise ServiceOSException(
                "VALIDATION_ERROR",
                "Home Services customer charge basis must be booking_price_snapshot",
                status_code=422,
            )
        if payload.get("provider_chargeable_event", "job_completed") not in PROVIDER_CHARGEABLE_EVENTS:
            raise ServiceOSException(
                "VALIDATION_ERROR",
                "provider_chargeable_event must be one of: "
                + ", ".join(sorted(PROVIDER_CHARGEABLE_EVENTS)),
                status_code=422,
            )
        if payload.get("provider_charge_model", "INHERIT") not in {"INHERIT", "FIXED_CREDITS"}:
            raise ServiceOSException(
                "VALIDATION_ERROR",
                "provider_charge_model must be INHERIT or FIXED_CREDITS",
                status_code=422,
            )
        if payload.get("provider_charge_model") == "FIXED_CREDITS" and payload.get("provider_charge_credit_units") in (None, ""):
            raise ServiceOSException(
                "VALIDATION_ERROR",
                "provider_charge_credit_units is required for a FIXED_CREDITS Job Type rule",
                status_code=422,
            )
        existing = (await db.execute(select(MonetizationJobTypeRule).where(
            MonetizationJobTypeRule.policy_id == policy_id, MonetizationJobTypeRule.job_type_id == job_type_id,
        ))).scalar_one_or_none()
        fields = {"customer_charge_enabled", "customer_charge_basis", "provider_charge_enabled",
                 "provider_charge_model", "provider_charge_credit_units", "provider_chargeable_event",
                 # Per-job-type SLA penalty: disable it for a job type, or set
                 # its own amount. A consultation and a full installation are
                 # not worth the same to abandon.
                 "sla_penalty_enabled", "sla_penalty_amount",
                 "status"}
        if existing:
            for k in fields:
                if k in payload:
                    setattr(existing, k, payload[k])
            await db.commit()
            return existing.to_dict()
        rule = MonetizationJobTypeRule(policy_id=policy_id, job_type_id=job_type_id,
                                       **{k: payload[k] for k in fields if k in payload})
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        return rule.to_dict()
