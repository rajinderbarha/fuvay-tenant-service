"""Home Services Dashboard — /admin/home-services/dashboard.

Category-specific dashboard, NOT a modification of the generic platform
/admin/dashboard. Composes existing canonical summary sources (the
Home Services Customer Directory's own get_summary, plus direct
operational counts from ServiceJob/StaffBusinessVertical/CustomerComplaint/
Tenant) rather than introducing a second metric-calculation engine.

Every card here must use IDENTICAL definitions to the pages it deep-links
to (Home Services Customers, the Home Services Providers directory) --
this service simply composes those, it doesn't recompute anything with
different logic.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.tenant_engine.models import Tenant
from app.engines.tenant_engine.hs_customer_directory_service import HomeServicesCustomerDirectoryService
from app.engines.final_records.models import ServiceJob
from app.engines.complaints.models import CustomerComplaint

HOME_SERVICES_VERTICAL = "home_services"

ACTIVE_JOB_STATUSES_EXCLUDED = ("completed", "cancelled", "failed", "closed_estimate_declined")
QUOTE_PENDING_STATUS = "awaiting_customer_quote_approval"


class HomeServicesDashboardService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role

    async def get_customer_intelligence(self) -> dict:
        """Delegates entirely to HomeServicesCustomerDirectoryService.get_summary
        -- identical definitions to /admin/home-services/customers, never a
        second calculation."""
        customer_svc = HomeServicesCustomerDirectoryService(db=self.db)
        return await customer_svc.get_summary()

    async def get_operational_metrics(self) -> dict:
        active_providers = (await self.db.execute(
            select(func.count(Tenant.id)).where(Tenant.vertical == HOME_SERVICES_VERTICAL, Tenant.status == "active")
        )).scalar() or 0

        from app.engines.vertical_directory.models import StaffBusinessVertical
        from app.engines.vertical_catalog.models import Vertical
        vertical = (await self.db.execute(select(Vertical).where(Vertical.key == HOME_SERVICES_VERTICAL))).scalar_one_or_none()
        available_staff = 0
        if vertical:
            available_staff = (await self.db.execute(
                select(func.count(StaffBusinessVertical.id)).where(
                    StaffBusinessVertical.vertical_id == vertical.id,
                    StaffBusinessVertical.availability_status == "available",
                    StaffBusinessVertical.is_active == True,
                )
            )).scalar() or 0

        active_jobs = (await self.db.execute(
            select(func.count(ServiceJob.id)).where(ServiceJob.status.notin_(ACTIVE_JOB_STATUSES_EXCLUDED))
        )).scalar() or 0
        unassigned_jobs = (await self.db.execute(
            select(func.count(ServiceJob.id)).where(
                ServiceJob.assignment_status == "unassigned",
                ServiceJob.status.notin_(ACTIVE_JOB_STATUSES_EXCLUDED),
            )
        )).scalar() or 0
        pending_quotes = (await self.db.execute(
            select(func.count(ServiceJob.id)).where(ServiceJob.status == QUOTE_PENDING_STATUS)
        )).scalar() or 0

        # HS tenants scoped via Tenant.vertical (structural HS-only join,
        # matching the pattern already established across this codebase).
        open_complaints = (await self.db.execute(
            select(func.count(CustomerComplaint.id))
            .join(Tenant, Tenant.id == CustomerComplaint.tenant_id)
            .where(Tenant.vertical == HOME_SERVICES_VERTICAL,
                   CustomerComplaint.status.notin_(("resolved", "closed", "rejected")))
        )).scalar() or 0

        return {
            "active_providers": active_providers,
            "available_staff": available_staff,
            "active_jobs": active_jobs,
            "unassigned_jobs": unassigned_jobs,
            "pending_quotes": pending_quotes,
            "open_complaints": open_complaints,
            # No SLA-breach field exists on ServiceJob today (grep-verified)
            # -- reported as not-available rather than computed from a
            # guessed proxy (e.g. "overdue scheduled_date").
            "jobs_at_risk": None,
            "jobs_at_risk_available": False,
            "sla_breached": None,
            "sla_breached_available": False,
        }

    async def get_summary(self) -> dict:
        """Composes both sections; each is independently try/except-able by
        the router so one failing section doesn't break the whole page."""
        return {
            "customer_intelligence": await self.get_customer_intelligence(),
            "operational_metrics": await self.get_operational_metrics(),
        }
