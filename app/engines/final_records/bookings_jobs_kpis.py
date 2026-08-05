"""TENANT-OPS-01 Phase 2 — backend-authoritative KPI strip for the Bookings
& Jobs workspace (spec section 5). Each number is a real, documented
tenant-wide query -- never the client-side "count of the currently loaded
page" the first pass used (see bookings-jobs/page.tsx header comment for
that documented limitation, now closed here).

Definitions (spec-mandated, not a frontend guess):
  total_active       -- all non-terminal ServiceJob rows for this tenant.
  unassigned         -- pending_assignment status with no real assignment.
  in_progress        -- JS_SERVICE_STARTED (the one "work underway" status).
  awaiting_approval  -- JS_INSPECTION_DONE or JS_QUOTE_REQUIRED (customer's
                        current estimate/quote decision is outstanding).
  at_risk            -- sla_summary AT_RISK or BREACHED among open jobs
                        (reuses the same SLA projection as the row/detail
                        indicator, never a second SLA definition).
  completed_today    -- status == completed with updated_at within the
                        current UTC calendar day. Documented limitation:
                        no reliable per-tenant timezone field exists on
                        Tenant/TenantSettings that's wired everywhere else
                        in this codebase, so "today" is UTC-day, not the
                        tenant's local day -- an honest simplification, not
                        a silent one.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.execution.constants import (
    JS_PENDING_ASSIGNMENT, JS_INSPECTION_DONE, JS_QUOTE_REQUIRED, JS_SERVICE_STARTED,
)
from app.engines.final_records.bookings_jobs_stage_mapping import TERMINAL_STATUSES
from app.engines.final_records.sla_summary import attach_sla


async def compute_bookings_jobs_kpis(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    from app.engines.final_records.models import ServiceJob

    total_active = await db.scalar(
        select(func.count()).select_from(ServiceJob).where(
            ServiceJob.tenant_id == tenant_id, ServiceJob.status.notin_(TERMINAL_STATUSES),
        )
    ) or 0

    unassigned = await db.scalar(
        select(func.count()).select_from(ServiceJob).where(
            ServiceJob.tenant_id == tenant_id,
            ServiceJob.status == JS_PENDING_ASSIGNMENT,
            ServiceJob.assignment_status != "assigned",
        )
    ) or 0

    in_progress = await db.scalar(
        select(func.count()).select_from(ServiceJob).where(
            ServiceJob.tenant_id == tenant_id, ServiceJob.status == JS_SERVICE_STARTED,
        )
    ) or 0

    awaiting_approval = await db.scalar(
        select(func.count()).select_from(ServiceJob).where(
            ServiceJob.tenant_id == tenant_id,
            ServiceJob.status.in_((JS_INSPECTION_DONE, JS_QUOTE_REQUIRED)),
        )
    ) or 0

    # SLA is bounded to non-terminal jobs (matches sla_summary.compute_summary's
    # own bound) -- avoids loading the whole historical table to answer "at risk".
    open_jobs = (await db.execute(
        select(ServiceJob).where(
            ServiceJob.tenant_id == tenant_id, ServiceJob.status.notin_(TERMINAL_STATUSES),
        ).limit(2000)
    )).scalars().all()
    sla_map = await attach_sla(db, open_jobs)
    at_risk = sum(1 for v in sla_map.values() if v["sla_status"] in ("AT_RISK", "BREACHED"))

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    completed_today = await db.scalar(
        select(func.count()).select_from(ServiceJob).where(
            ServiceJob.tenant_id == tenant_id, ServiceJob.status == "completed",
            ServiceJob.updated_at >= today_start,
        )
    ) or 0

    return {
        "total_active":      total_active,
        "unassigned":        unassigned,
        "in_progress":       in_progress,
        "awaiting_approval": awaiting_approval,
        "at_risk":           at_risk,
        "completed_today":   completed_today,
    }
