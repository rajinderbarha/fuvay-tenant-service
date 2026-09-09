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
    JS_INSPECTION_DONE, JS_QUOTE_REQUIRED, JS_SERVICE_STARTED,
)
from app.engines.final_records.bookings_jobs_stage_mapping import TERMINAL_STATUSES
from app.engines.final_records.sla_summary import sla_filter_condition


async def compute_bookings_jobs_kpis(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    from app.engines.final_records.models import ServiceJob

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    risk_condition = (
        sla_filter_condition(ServiceJob, "AT_RISK") |
        sla_filter_condition(ServiceJob, "BREACHED")
    )
    # One indexed tenant scan and one round-trip for the entire KPI strip.
    # Conditional aggregates remain exact at high volume and avoid the six
    # sequential COUNT queries the workspace previously issued per refresh.
    row = (await db.execute(
        select(
            func.count().filter(ServiceJob.status.notin_(TERMINAL_STATUSES)).label("total_active"),
            func.count().filter(
                ServiceJob.status.notin_(TERMINAL_STATUSES),
                ServiceJob.assigned_staff_id.is_(None),
            ).label("unassigned"),
            func.count().filter(ServiceJob.status == JS_SERVICE_STARTED).label("in_progress"),
            func.count().filter(
                ServiceJob.status.in_((JS_INSPECTION_DONE, JS_QUOTE_REQUIRED)),
            ).label("awaiting_approval"),
            func.count().filter(risk_condition).label("at_risk"),
            func.count().filter(
                ServiceJob.status == "completed", ServiceJob.updated_at >= today_start,
            ).label("completed_today"),
        ).where(ServiceJob.tenant_id == tenant_id)
    )).one()

    return {
        "total_active":      int(row.total_active or 0),
        "unassigned":        int(row.unassigned or 0),
        "in_progress":       int(row.in_progress or 0),
        "awaiting_approval": int(row.awaiting_approval or 0),
        "at_risk":           int(row.at_risk or 0),
        "completed_today":   int(row.completed_today or 0),
    }
