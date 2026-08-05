"""HOME-SERVICES-TOPUP-PLAN: draft/publish workflow for the starter credit
package (top-up plan) + security deposit amounts admins actually set.

Until this file, `HomeServicesActivationFinancePolicy` (finance_policy_
models.py) had a real, already-versioned table (draft/published/is_current,
same idiom as VerticalMonetizationPolicy) and a real resolver
(finance_policy_service.resolve_published_policy, used by activation.py,
tenant_hs_finance_service.py's actual top-up pricing) -- but NO service
method and NO router ever let an admin create, edit, or publish a version.
Every tenant's top-up price (credit_package_base_amount/gst_percent) and
security deposit (deposit_amount_per_technician) were fixed at whatever the
first auto-created row's column defaults happened to be, with no admin UI
or write path at all.

Mirrors VerticalMonetizationPolicyService's exact draft/publish idiom
(vertical_monetization/policy_service.py) rather than inventing a second
versioning scheme.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.vertical_catalog.models import Vertical, VerticalAuditLog
from app.engines.vertical_catalog.finance_policy_models import HomeServicesActivationFinancePolicy
from app.exceptions import ServiceOSException

_DRAFT_FIELDS = {
    "deposit_required", "deposit_calculation_mode", "deposit_amount_per_technician", "minimum_deposit",
    "technician_count_policy", "initial_credit_purchase_required", "credit_package_base_amount",
    "credit_package_gst_percent", "credited_wallet_amount", "completion_deduction_policy",
    "currency", "effective_from", "change_summary",
}


class HomeServicesTopupPlanService:

    async def _vertical(self, db: AsyncSession, key: str) -> Vertical:
        v = (await db.execute(select(Vertical).where(Vertical.key == key))).scalar_one_or_none()
        if not v:
            raise ServiceOSException("NOT_FOUND", f"Vertical '{key}' not found", status_code=404)
        return v

    def _validate(self, payload: dict) -> list[str]:
        errors = []
        base = payload.get("credit_package_base_amount")
        if base is not None and float(base) <= 0:
            errors.append("credit_package_base_amount must be greater than 0.")
        gst = payload.get("credit_package_gst_percent")
        if gst is not None and not (0 <= float(gst) <= 100):
            errors.append("credit_package_gst_percent must be between 0 and 100.")
        credited = payload.get("credited_wallet_amount")
        if credited is not None and float(credited) <= 0:
            errors.append("credited_wallet_amount must be greater than 0.")
        deposit = payload.get("deposit_amount_per_technician")
        if deposit is not None and float(deposit) < 0:
            errors.append("deposit_amount_per_technician cannot be negative.")
        return errors

    async def get_current(self, db: AsyncSession, key: str) -> dict | None:
        v = await self._vertical(db, key)
        p = (await db.execute(select(HomeServicesActivationFinancePolicy).where(
            HomeServicesActivationFinancePolicy.vertical_id == v.id,
            HomeServicesActivationFinancePolicy.is_current == True,  # noqa: E712
        ))).scalar_one_or_none()
        return p.to_dict() if p else None

    async def get_draft(self, db: AsyncSession, key: str) -> dict | None:
        v = await self._vertical(db, key)
        p = (await db.execute(select(HomeServicesActivationFinancePolicy).where(
            HomeServicesActivationFinancePolicy.vertical_id == v.id,
            HomeServicesActivationFinancePolicy.status == "draft",
        ).order_by(HomeServicesActivationFinancePolicy.version_number.desc()))).scalars().first()
        return p.to_dict() if p else None

    async def list_history(self, db: AsyncSession, key: str) -> list[dict]:
        v = await self._vertical(db, key)
        rows = (await db.execute(select(HomeServicesActivationFinancePolicy).where(
            HomeServicesActivationFinancePolicy.vertical_id == v.id,
        ).order_by(HomeServicesActivationFinancePolicy.version_number.desc()))).scalars().all()
        return [p.to_dict() for p in rows]

    async def discard_draft(self, db: AsyncSession, key: str, *, actor_id: uuid.UUID | None) -> dict:
        """Hard-deletes the pending draft row -- see the equivalent method
        on VerticalMonetizationPolicyService for why this deletes rather
        than supersedes (a draft that never published has no audit value)."""
        v = await self._vertical(db, key)
        draft = (await db.execute(select(HomeServicesActivationFinancePolicy).where(
            HomeServicesActivationFinancePolicy.vertical_id == v.id,
            HomeServicesActivationFinancePolicy.status == "draft",
        ))).scalar_one_or_none()
        if not draft:
            raise ServiceOSException("NOT_FOUND", "No draft to discard.", status_code=404)
        draft_id = str(draft.id)
        await db.delete(draft)
        db.add(VerticalAuditLog(
            vertical_id=v.id, actor_id=actor_id, action_type="topup_plan.discard_draft",
            before_state={"id": draft_id, "version_number": draft.version_number}, after_state=None,
            notes="Draft discarded before publish.",
        ))
        await db.commit()
        return {"discarded": True, "draft_id": draft_id}

    def validate(self, payload: dict) -> dict:
        return {"errors": self._validate(payload), "warnings": []}

    async def save_draft(self, db: AsyncSession, key: str, payload: dict, *, actor_id: uuid.UUID | None) -> dict:
        v = await self._vertical(db, key)
        errors = self._validate(payload)
        if errors:
            raise ServiceOSException("VALIDATION_ERROR", "; ".join(errors), status_code=422)

        existing_draft = (await db.execute(select(HomeServicesActivationFinancePolicy).where(
            HomeServicesActivationFinancePolicy.vertical_id == v.id,
            HomeServicesActivationFinancePolicy.status == "draft",
        ))).scalar_one_or_none()
        if existing_draft:
            for k in _DRAFT_FIELDS:
                if k in payload:
                    setattr(existing_draft, k, payload[k])
            await db.flush()
            await db.commit()
            return existing_draft.to_dict()

        # A first draft, with no prior published row at all, starts from the
        # column defaults (documented starter values) rather than requiring
        # every field up front.
        current = (await db.execute(select(HomeServicesActivationFinancePolicy).where(
            HomeServicesActivationFinancePolicy.vertical_id == v.id,
            HomeServicesActivationFinancePolicy.is_current == True,  # noqa: E712
        ))).scalar_one_or_none()
        base_fields = {k: getattr(current, k) for k in _DRAFT_FIELDS if current and hasattr(current, k)}
        base_fields.update({k: payload[k] for k in _DRAFT_FIELDS if k in payload})

        max_version = (await db.execute(select(func.max(HomeServicesActivationFinancePolicy.version_number)).where(
            HomeServicesActivationFinancePolicy.vertical_id == v.id))).scalar() or 0
        p = HomeServicesActivationFinancePolicy(
            vertical_id=v.id, version_number=max_version + 1, status="draft", is_current=False,
            created_by_user_id=actor_id, **base_fields,
        )
        db.add(p)
        await db.flush()
        await db.commit()
        return p.to_dict()

    async def publish(self, db: AsyncSession, key: str, *, actor_id: uuid.UUID | None, reason: str) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "A reason is required to publish a policy change.", status_code=422)
        v = await self._vertical(db, key)
        draft = (await db.execute(select(HomeServicesActivationFinancePolicy).where(
            HomeServicesActivationFinancePolicy.vertical_id == v.id,
            HomeServicesActivationFinancePolicy.status == "draft",
        ))).scalar_one_or_none()
        if not draft:
            raise ServiceOSException("NOT_FOUND", "No draft top-up plan to publish.", status_code=404)
        errors = self._validate(draft.to_dict())
        if errors:
            raise ServiceOSException("VALIDATION_ERROR", "; ".join(errors), status_code=422)

        prior = (await db.execute(select(HomeServicesActivationFinancePolicy).where(
            HomeServicesActivationFinancePolicy.vertical_id == v.id,
            HomeServicesActivationFinancePolicy.is_current == True,  # noqa: E712
        ))).scalar_one_or_none()
        before = prior.to_dict() if prior else None
        if prior:
            # Two flushes, never one -- the partial unique index on
            # is_current is checked per-statement in Postgres, so flipping
            # both rows' is_current in the same flush can transiently
            # violate it depending on statement ordering.
            prior.is_current = False
            prior.status = "retired"
            await db.flush()

        draft.status = "published"
        draft.is_current = True
        draft.published_by_user_id = actor_id
        draft.published_at = datetime.now(timezone.utc)
        await db.flush()

        db.add(VerticalAuditLog(
            vertical_id=v.id, actor_id=actor_id, action_type="topup_plan.publish",
            before_state=before, after_state=draft.to_dict(), notes=reason,
        ))
        await db.commit()
        await db.refresh(draft)
        return draft.to_dict()
