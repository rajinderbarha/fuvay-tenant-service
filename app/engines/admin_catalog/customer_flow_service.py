"""Sprint 34J — Customer Flow Service.

Rules:
  AI can talk. Backend decides. Database validates. Engines execute.
  Customer sees only active, backend-approved choices.
  AI cannot invent entity IDs. All selections validated before save.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    CustomerBookingDraft,
    CustomerFlowConfig,
    ServiceCategory,
    MasterService,
)

logger = structlog.get_logger("customer_flow_service")

VALID_FLOW_TYPES = {"service_booking", "appointment_booking", "lead_capture", "subscription_only"}
VALID_STATUSES   = {"draft", "estimated", "confirmed", "cancelled"}


class CustomerFlowService:
    """
    Unified customer booking flow service.

    Provides:
    - Flow config (which UX flow a category uses)
    - Catalog APIs (active categories, services — delegates to existing catalog tables)
    - Draft CRUD with catalog validation
    - Estimate computation
    - Booking confirmation
    """

    def __init__(self, db: AsyncSession, request_id: str = "—") -> None:
        self.db = db
        self.request_id = request_id

    # ── Flow Config ────────────────────────────────────────────────────────────

    async def get_flow_config(self, category_id: uuid.UUID) -> dict:
        """Return flow config for a category; default service_booking if none configured."""
        row = await self.db.execute(
            select(CustomerFlowConfig).where(
                CustomerFlowConfig.category_id == category_id,
                CustomerFlowConfig.is_active == True,
            )
        )
        cfg = row.scalars().first()
        if cfg is None:
            return {
                "category_id":            str(category_id),
                "customer_flow_type":      "service_booking",
                "frontend_component_key":  "default_booking",
                "primary_engine_key":      "home_service_booking",
                "required_steps":          ["category", "service", "address", "confirm"],
                "optional_steps":          ["brand", "issue_type", "service_options"],
                "config":                  {},
                "configured":              False,
            }
        return {
            "category_id":            str(cfg.category_id),
            "customer_flow_type":      cfg.customer_flow_type,
            "frontend_component_key":  cfg.frontend_component_key,
            "primary_engine_key":      cfg.primary_engine_key,
            "required_steps":          cfg.required_steps,
            "optional_steps":          cfg.optional_steps,
            "config":                  cfg.config,
            "configured":              True,
        }

    async def list_flow_configs(self, page: int = 1, page_size: int = 50) -> dict:
        """List all configured customer flow configs."""
        offset = (page - 1) * page_size
        rows = await self.db.execute(
            select(CustomerFlowConfig)
            .where(CustomerFlowConfig.is_active == True)
            .offset(offset).limit(page_size)
        )
        items = rows.scalars().all()
        return {
            "items": [
                {
                    "category_id":            str(c.category_id),
                    "customer_flow_type":      c.customer_flow_type,
                    "frontend_component_key":  c.frontend_component_key,
                    "primary_engine_key":      c.primary_engine_key,
                    "required_steps":          c.required_steps,
                    "optional_steps":          c.optional_steps,
                }
                for c in items
            ],
            "total": len(items),
        }

    # ── Active Catalog ─────────────────────────────────────────────────────────

    async def list_active_categories(self) -> dict:
        """Return active categories visible to customers."""
        rows = await self.db.execute(
            select(ServiceCategory).where(
                ServiceCategory.is_active == True
            ).order_by(ServiceCategory.display_order)
        )
        cats = rows.scalars().all()
        return {
            "items": [
                {
                    "id":          str(c.id),
                    "name":        c.name,
                    "code":        c.code,
                    "description": c.description,
                    "icon_url":    c.icon_url,
                    "vertical_type": c.vertical_type,
                    "customer_flow_type": c.customer_flow_type,
                }
                for c in cats
            ],
            "total": len(cats),
        }

    async def list_active_services(self, category_id: uuid.UUID | None = None) -> dict:
        """Return active master services, optionally filtered by category."""
        q = select(MasterService).where(MasterService.is_active == True)
        if category_id:
            q = q.where(MasterService.category_id == category_id)
        rows = await self.db.execute(q.order_by(MasterService.name))
        svcs = rows.scalars().all()
        return {
            "items": [
                {
                    "id":          str(s.id),
                    "name":        s.name,
                    "code":        s.code,
                    "category_id": str(s.category_id),
                    "description": s.description,
                    "job_type":    s.job_type,
                    "base_price":  float(s.base_price) if s.base_price else None,
                }
                for s in svcs
            ],
            "total": len(svcs),
        }

    # ── Draft CRUD ─────────────────────────────────────────────────────────────

    async def create_draft(
        self,
        flow_type: str,
        customer_id: uuid.UUID | None = None,
        guest_session_id: str | None = None,
        ai_session_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        service_id: uuid.UUID | None = None,
        extra_fields: dict | None = None,
    ) -> dict:
        if flow_type not in VALID_FLOW_TYPES:
            raise ValueError(f"Invalid flow_type: {flow_type}. Must be one of {sorted(VALID_FLOW_TYPES)}")

        # Validate category if provided
        if category_id:
            await self._assert_category_active(category_id)

        # Validate service if provided
        if service_id:
            await self._assert_service_active(service_id)

        draft = CustomerBookingDraft(
            flow_type=flow_type,
            customer_id=customer_id,
            guest_session_id=guest_session_id,
            ai_session_id=ai_session_id,
            category_id=category_id,
            service_id=service_id,
            status="draft",
            extra_fields=extra_fields,
        )
        self.db.add(draft)
        await self.db.commit()
        await self.db.refresh(draft)
        logger.info("draft_created", draft_id=str(draft.id), flow_type=flow_type)
        return draft.to_dict()

    async def get_draft(self, draft_id: uuid.UUID, customer_id: uuid.UUID | None = None) -> dict:
        draft = await self._load_draft(draft_id, customer_id)
        return draft.to_dict()

    async def update_draft(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
        **fields: Any,
    ) -> dict:
        draft = await self._load_draft(draft_id, customer_id)

        if draft.status == "confirmed":
            raise ValueError("Cannot update a confirmed draft")

        # Validate catalog IDs before applying
        if "category_id" in fields and fields["category_id"]:
            await self._assert_category_active(uuid.UUID(str(fields["category_id"])))
        if "service_id" in fields and fields["service_id"]:
            await self._assert_service_active(uuid.UUID(str(fields["service_id"])))

        allowed = {
            "category_id", "service_id", "brand_id", "issue_type_id",
            "service_option_ids", "customer_name", "customer_phone", "customer_email",
            "city", "zipcode", "address_text", "issue_summary", "issue_details",
            "preferred_date", "preferred_time_slot", "lead_notes", "lead_details",
            "selected_tenant_id", "extra_fields",
        }
        for k, v in fields.items():
            if k in allowed:
                setattr(draft, k, v)

        await self.db.commit()
        await self.db.refresh(draft)
        return draft.to_dict()

    async def list_drafts(
        self,
        customer_id: uuid.UUID | None = None,
        guest_session_id: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        q = select(CustomerBookingDraft)
        filters = []
        if customer_id:
            filters.append(CustomerBookingDraft.customer_id == customer_id)
        if guest_session_id:
            filters.append(CustomerBookingDraft.guest_session_id == guest_session_id)
        if status:
            filters.append(CustomerBookingDraft.status == status)
        if filters:
            q = q.where(and_(*filters))
        q = q.order_by(CustomerBookingDraft.created_at.desc())
        offset = (page - 1) * page_size
        rows = await self.db.execute(q.offset(offset).limit(page_size))
        items = rows.scalars().all()
        return {"items": [d.to_dict() for d in items], "total": len(items)}

    async def cancel_draft(self, draft_id: uuid.UUID, customer_id: uuid.UUID | None = None) -> dict:
        draft = await self._load_draft(draft_id, customer_id)
        if draft.status == "confirmed":
            raise ValueError("Cannot cancel a confirmed booking")
        draft.status = "cancelled"
        await self.db.commit()
        await self.db.refresh(draft)
        return draft.to_dict()

    # ── Estimate ───────────────────────────────────────────────────────────────

    async def estimate_draft(self, draft_id: uuid.UUID, customer_id: uuid.UUID | None = None) -> dict:
        """Compute a price estimate for the draft based on service base_price."""
        draft = await self._load_draft(draft_id, customer_id)

        estimate_min: Decimal | None = None
        estimate_max: Decimal | None = None

        if draft.service_id:
            row = await self.db.execute(
                select(MasterService).where(MasterService.id == draft.service_id)
            )
            svc = row.scalars().first()
            if svc and svc.base_price:
                base = svc.base_price
                estimate_min = round(base * Decimal("0.9"), 2)
                estimate_max = round(base * Decimal("1.3"), 2)

        draft.estimate_min = estimate_min
        draft.estimate_max = estimate_max
        draft.estimate_currency = "INR"
        if draft.status == "draft" and estimate_min is not None:
            draft.status = "estimated"

        await self.db.commit()
        await self.db.refresh(draft)
        return {
            **draft.to_dict(),
            "estimate": {
                "min":      float(estimate_min) if estimate_min else None,
                "max":      float(estimate_max) if estimate_max else None,
                "currency": "INR",
                "note":     "Backend estimate only. Final price confirmed by provider.",
            },
        }

    # ── Confirm ────────────────────────────────────────────────────────────────

    async def confirm_draft(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
        customer_name: str | None = None,
        customer_phone: str | None = None,
        customer_email: str | None = None,
    ) -> dict:
        """Confirm the draft and mark it ready for final record creation."""
        draft = await self._load_draft(draft_id, customer_id)

        if draft.status == "confirmed":
            raise ValueError("Draft already confirmed")
        if draft.status == "cancelled":
            raise ValueError("Cannot confirm a cancelled draft")

        # Require at minimum a service selection and contact info
        if not draft.service_id:
            raise ValueError("service_id required before confirmation")
        contact = customer_name or draft.customer_name
        phone   = customer_phone or draft.customer_phone
        if not contact or not phone:
            raise ValueError("customer_name and customer_phone required for confirmation")

        if customer_name:  draft.customer_name  = customer_name
        if customer_phone: draft.customer_phone = customer_phone
        if customer_email: draft.customer_email = customer_email

        draft.status = "confirmed"
        await self.db.commit()
        await self.db.refresh(draft)
        logger.info("draft_confirmed", draft_id=str(draft.id))
        return {
            **draft.to_dict(),
            "confirmed":     True,
            "next_step":     "pending_provider_assignment",
            "message":       "Booking confirmed. A provider will be assigned shortly.",
        }

    # ── Admin Oversight ────────────────────────────────────────────────────────

    async def admin_list_drafts(
        self,
        status: str | None = None,
        flow_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        q = select(CustomerBookingDraft)
        filters = []
        if status:
            filters.append(CustomerBookingDraft.status == status)
        if flow_type:
            filters.append(CustomerBookingDraft.flow_type == flow_type)
        if filters:
            q = q.where(and_(*filters))
        q = q.order_by(CustomerBookingDraft.created_at.desc())
        offset = (page - 1) * page_size
        rows = await self.db.execute(q.offset(offset).limit(page_size))
        items = rows.scalars().all()
        return {"items": [d.to_dict() for d in items], "total": len(items)}

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _load_draft(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
    ) -> CustomerBookingDraft:
        row = await self.db.execute(
            select(CustomerBookingDraft).where(CustomerBookingDraft.id == draft_id)
        )
        draft = row.scalars().first()
        if not draft:
            raise ValueError(f"Booking draft {draft_id} not found")
        if customer_id and draft.customer_id and draft.customer_id != customer_id:
            raise PermissionError("Access denied to this draft")
        return draft

    async def _assert_category_active(self, category_id: uuid.UUID) -> None:
        row = await self.db.execute(
            select(ServiceCategory).where(
                ServiceCategory.id == category_id,
                ServiceCategory.is_active == True,
            )
        )
        if not row.scalars().first():
            raise ValueError(f"Category {category_id} is not active or does not exist")

    async def _assert_service_active(self, service_id: uuid.UUID) -> None:
        row = await self.db.execute(
            select(MasterService).where(
                MasterService.id == service_id,
                MasterService.is_active == True,
            )
        )
        if not row.scalars().first():
            raise ValueError(f"Service {service_id} is not active or does not exist")
