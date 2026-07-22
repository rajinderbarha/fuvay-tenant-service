"""Sprint 22 — ServiceChecklistService: checklist lifecycle management."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.quote_checklist.constants import (
    CL_PENDING, CL_IN_PROGRESS, CL_COMPLETED, CL_SKIPPED,
    CLI_PENDING, CLI_COMPLETED, CLI_SKIPPED, CLI_FAILED,
    VALID_CHECKLIST_TYPES, VALID_INPUT_TYPES,
    ERR_CHECKLIST_NOT_FOUND, ERR_CHECKLIST_ACCESS_DENIED,
    ERR_CHECKLIST_ALREADY_COMPLETED, ERR_CHECKLIST_ITEM_NOT_FOUND,
    ERR_CHECKLIST_ITEM_VALUE_REQUIRED, ERR_CHECKLIST_PHOTO_REQUIRED,
    ERR_CHECKLIST_TEMPLATE_NOT_FOUND,
    ERR_QUOTE_JOB_NOT_FOUND,
)
from app.engines.quote_checklist.models import (
    SjChecklistTemplate, SjChecklistTemplateItem,
    ServiceJobChecklist, ServiceJobChecklistItem,
)
from app.engines.final_records.models import ServiceJob


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ServiceChecklistService:

    async def _get_checklist(self, db: AsyncSession, checklist_id: str) -> ServiceJobChecklist:
        res = await db.execute(
            select(ServiceJobChecklist).where(ServiceJobChecklist.id == uuid.UUID(checklist_id))
        )
        cl = res.scalar_one_or_none()
        if not cl:
            raise ValueError(ERR_CHECKLIST_NOT_FOUND)
        return cl

    # ── Admin: create template ─────────────────────────────────────────────────

    async def create_template(
        self, db: AsyncSession, template_name: str, template_type: str,
        applies_to: str, category_id: str | None, offering_id: str | None,
        tenant_id: str | None, is_required: bool,
    ) -> dict:
        t = SjChecklistTemplate(
            id=uuid.uuid4(),
            template_name=template_name,
            template_type=template_type,
            applies_to=applies_to,
            category_id=uuid.UUID(category_id) if category_id else None,
            offering_id=uuid.UUID(offering_id) if offering_id else None,
            tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
            is_required=is_required,
            is_active=True,
        )
        db.add(t)
        await db.commit()
        await db.refresh(t)
        return t.to_dict()

    async def add_template_item(
        self, db: AsyncSession, template_id: str, item_label: str,
        item_description: str | None, input_type: str, is_required: bool,
        sort_order: int, options: dict | None,
    ) -> dict:
        res = await db.execute(
            select(SjChecklistTemplate).where(SjChecklistTemplate.id == uuid.UUID(template_id))
        )
        if not res.scalar_one_or_none():
            raise ValueError(ERR_CHECKLIST_TEMPLATE_NOT_FOUND)
        item = SjChecklistTemplateItem(
            id=uuid.uuid4(),
            template_id=uuid.UUID(template_id),
            item_label=item_label,
            item_description=item_description,
            input_type=input_type,
            is_required=is_required,
            sort_order=sort_order,
            options=options,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item.to_dict()

    async def list_templates(self, db: AsyncSession) -> list[dict]:
        res = await db.execute(
            select(SjChecklistTemplate).where(SjChecklistTemplate.is_active == True)
            .order_by(SjChecklistTemplate.template_name)
        )
        return [t.to_dict() for t in res.scalars().all()]

    async def get_template(self, db: AsyncSession, template_id: str) -> dict:
        res = await db.execute(
            select(SjChecklistTemplate).where(SjChecklistTemplate.id == uuid.UUID(template_id))
        )
        t = res.scalar_one_or_none()
        if not t:
            raise ValueError(ERR_CHECKLIST_TEMPLATE_NOT_FOUND)
        res2 = await db.execute(
            select(SjChecklistTemplateItem)
            .where(SjChecklistTemplateItem.template_id == t.id)
            .order_by(SjChecklistTemplateItem.sort_order)
        )
        data = t.to_dict()
        data["items"] = [i.to_dict() for i in res2.scalars().all()]
        return data

    # ── Staff: create checklist for job ───────────────────────────────────────

    async def create_checklist(
        self, db: AsyncSession, job_id: str, booking_id: str, tenant_id: str,
        checklist_type: str, template_id: str | None,
        user_id: str, custom_items: list[dict] | None,
    ) -> dict:
        # Slice 2F-16: previously trusted job_id/booking_id/tenant_id from
        # the request body with NO validation that the job exists or belongs
        # to the caller's tenant -- a checklist could be fabricated against
        # an arbitrary/nonexistent job_id, or one belonging to a different
        # tenant. Mirrors ServiceJobQuoteService.create_quote's own
        # job-ownership check.
        res = await db.execute(select(ServiceJob).where(ServiceJob.id == uuid.UUID(job_id)))
        job = res.scalar_one_or_none()
        if not job:
            raise ValueError(ERR_QUOTE_JOB_NOT_FOUND)
        if str(job.tenant_id) != tenant_id:
            raise ValueError(ERR_CHECKLIST_ACCESS_DENIED)
        cl = ServiceJobChecklist(
            id=uuid.uuid4(),
            booking_id=uuid.UUID(booking_id),
            job_id=uuid.UUID(job_id),
            tenant_id=uuid.UUID(tenant_id),
            template_id=uuid.UUID(template_id) if template_id else None,
            status=CL_PENDING,
            checklist_type=checklist_type,
            created_by_user_id=uuid.UUID(user_id),
        )
        db.add(cl)
        await db.flush()

        # Seed from template if provided
        if template_id:
            res = await db.execute(
                select(SjChecklistTemplateItem)
                .where(SjChecklistTemplateItem.template_id == uuid.UUID(template_id))
                .order_by(SjChecklistTemplateItem.sort_order)
            )
            for titem in res.scalars().all():
                ci = ServiceJobChecklistItem(
                    id=uuid.uuid4(),
                    checklist_id=cl.id,
                    booking_id=cl.booking_id,
                    job_id=cl.job_id,
                    tenant_id=cl.tenant_id,
                    item_label=titem.item_label,
                    input_type=titem.input_type,
                    is_required=titem.is_required,
                    status=CLI_PENDING,
                    sort_order=titem.sort_order,
                )
                db.add(ci)

        # Add any extra custom items
        if custom_items:
            for idx, ci_data in enumerate(custom_items):
                ci = ServiceJobChecklistItem(
                    id=uuid.uuid4(),
                    checklist_id=cl.id,
                    booking_id=cl.booking_id,
                    job_id=cl.job_id,
                    tenant_id=cl.tenant_id,
                    item_label=ci_data.get("item_label", ""),
                    input_type=ci_data.get("input_type", "checkbox"),
                    is_required=ci_data.get("is_required", False),
                    status=CLI_PENDING,
                    sort_order=ci_data.get("sort_order", idx),
                )
                db.add(ci)

        await db.commit()
        await db.refresh(cl)
        return cl.to_dict()

    # ── Staff: update checklist item ───────────────────────────────────────────

    async def update_checklist_item(
        self, db: AsyncSession, checklist_id: str, item_id: str,
        tenant_id: str, user_id: str,
        value_text: str | None, value_number: float | None,
        value_json: dict | None, media_url: str | None,
        status: str | None,
    ) -> dict:
        cl = await self._get_checklist(db, checklist_id)
        if str(cl.tenant_id) != tenant_id:
            raise ValueError(ERR_CHECKLIST_ACCESS_DENIED)
        if cl.status == CL_COMPLETED:
            raise ValueError(ERR_CHECKLIST_ALREADY_COMPLETED)
        res = await db.execute(
            select(ServiceJobChecklistItem).where(
                ServiceJobChecklistItem.id == uuid.UUID(item_id),
                ServiceJobChecklistItem.checklist_id == cl.id,
            )
        )
        item = res.scalar_one_or_none()
        if not item:
            raise ValueError(ERR_CHECKLIST_ITEM_NOT_FOUND)
        if value_text is not None:   item.value_text = value_text
        if value_number is not None: item.value_number = Decimal(str(value_number))
        if value_json is not None:   item.value_json = value_json
        if media_url is not None:    item.media_url = media_url
        if status is not None:
            item.status = status
            if status == CLI_COMPLETED:
                item.completed_at = _utcnow()
                item.completed_by_user_id = uuid.UUID(user_id)
        # update checklist to in_progress if it was pending
        if cl.status == CL_PENDING:
            await db.execute(
                update(ServiceJobChecklist)
                .where(ServiceJobChecklist.id == cl.id)
                .values(status=CL_IN_PROGRESS, updated_at=_utcnow())
            )
        await db.commit()
        await db.refresh(item)
        return item.to_dict()

    # ── Staff: complete checklist ──────────────────────────────────────────────

    async def complete_checklist(
        self, db: AsyncSession, checklist_id: str, tenant_id: str, user_id: str,
    ) -> dict:
        cl = await self._get_checklist(db, checklist_id)
        if str(cl.tenant_id) != tenant_id:
            raise ValueError(ERR_CHECKLIST_ACCESS_DENIED)
        if cl.status == CL_COMPLETED:
            raise ValueError(ERR_CHECKLIST_ALREADY_COMPLETED)
        now = _utcnow()
        await db.execute(
            update(ServiceJobChecklist)
            .where(ServiceJobChecklist.id == cl.id)
            .values(
                status=CL_COMPLETED,
                completed_at=now,
                completed_by_user_id=uuid.UUID(user_id),
                updated_at=now,
            )
        )
        await db.commit()
        await db.refresh(cl)
        return cl.to_dict()

    # ── Get checklist with items ───────────────────────────────────────────────

    async def get_checklist(
        self, db: AsyncSession, checklist_id: str, tenant_id: str | None = None,
    ) -> dict:
        """Slice 2F-16: previously had NO tenant ownership filter -- any
        authenticated user of any tenant could fetch ANY job's checklist by
        ID alone. Callers now pass their own tenant_id to scope the read.

        Slice 2F-16A: foreign-tenant ownership now raises the same
        ERR_CHECKLIST_NOT_FOUND as a genuinely missing checklist (was
        ERR_CHECKLIST_ACCESS_DENIED, externally distinguishable via a
        different HTTP status) -- privacy-safe 404, matching get_quote."""
        cl = await self._get_checklist(db, checklist_id)
        if tenant_id is not None and str(cl.tenant_id) != tenant_id:
            raise ValueError(ERR_CHECKLIST_NOT_FOUND)
        res = await db.execute(
            select(ServiceJobChecklistItem)
            .where(ServiceJobChecklistItem.checklist_id == cl.id)
            .order_by(ServiceJobChecklistItem.sort_order)
        )
        data = cl.to_dict()
        data["items"] = [i.to_dict() for i in res.scalars().all()]
        return data

    # ── List checklists for job ────────────────────────────────────────────────

    async def list_checklists_for_job(
        self, db: AsyncSession, job_id: str, tenant_id: str,
    ) -> list[dict]:
        res = await db.execute(
            select(ServiceJobChecklist).where(
                ServiceJobChecklist.job_id == uuid.UUID(job_id),
                ServiceJobChecklist.tenant_id == uuid.UUID(tenant_id),
            ).order_by(ServiceJobChecklist.created_at.desc())
        )
        return [cl.to_dict() for cl in res.scalars().all()]
