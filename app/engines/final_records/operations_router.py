"""HOME-SERVICES-OPERATIONS: Unified Bookings & Jobs workspace — admin
read-only projection API. Backed exclusively by the canonical
home_service_booking_drafts -> service_bookings -> service_jobs pipeline
(see operations_service.py docstring for why the legacy /admin/bookings
pipeline is intentionally excluded).

This is observational: no endpoint here mutates a booking or job, approves
an estimate, or starts work. Row actions (assign/contact/etc.) are performed
through the existing canonical action endpoints (home_service_assignment,
quote_checklist, etc.), never through this router.
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, time
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin, UserContext
from app.dependencies.db import get_db
from app.dependencies.vertical_guard import require_vertical_enabled
from app.schemas.base import ApiResponse, ok
from app.engines.final_records.operations_service import (
    list_operations, compute_metrics_cached,
)

router = APIRouter(
    prefix="/v1/admin/home-services/operations",
    tags=["Home Services Operations"],
    dependencies=[Depends(require_vertical_enabled("home_services"))],
)

_RID = lambda r: getattr(r.state, "request_id", "—")


def _parse_date(v: str | None, *, end_of_day: bool = False) -> datetime | None:
    if not v:
        return None
    try:
        parsed = datetime.fromisoformat(v)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid ISO date: {v}") from exc
    if end_of_day and "T" not in v and " " not in v:
        parsed = datetime.combine(parsed.date(), time.max)
    return parsed


def _parse_date_range(date_from: str | None, date_to: str | None) -> tuple[datetime | None, datetime | None]:
    start = _parse_date(date_from)
    end = _parse_date(date_to, end_of_day=True)
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="date_from must be on or before date_to")
    return start, end


def _csv_safe(value):
    """Prevent spreadsheet formula execution in administrator exports."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


@router.get("", summary="Unified Bookings & Jobs operational feed (admin)", response_model=ApiResponse)
async def get_operations(
    r: Request,
    view: Literal["all", "requests", "active", "approval", "exceptions", "completed"] = Query("all"),
    search: str | None = Query(None, min_length=1, max_length=200),
    stage: Literal["REQUEST", "MATCHING", "UNASSIGNED", "ASSIGNED", "SCHEDULED", "ON_THE_WAY", "INSPECTION", "AWAITING_ESTIMATE", "AWAITING_APPROVAL", "READY_TO_START", "IN_PROGRESS", "WORK_DONE", "COMPLETED", "AT_RISK", "CLOSED", "UNKNOWN"] | None = Query(None),
    assignment: Literal["assigned", "unassigned"] | None = Query(None),
    tenant_id: uuid.UUID | None = Query(None),
    technician_id: uuid.UUID | None = Query(None),
    customer_id: uuid.UUID | None = Query(None),
    city: str | None = Query(None, max_length=100),
    state: str | None = Query(None, max_length=100),
    district: str | None = Query(None, max_length=100),
    zipcode: str | None = Query(None, max_length=20),
    amount_min: Decimal | None = Query(None, ge=0),
    amount_max: Decimal | None = Query(None, ge=0),
    sort_by: Literal["created_at", "updated_at", "scheduled_date", "amount"] = Query("created_at"),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
):
    parsed_from, parsed_to = _parse_date_range(date_from, date_to)
    if amount_min is not None and amount_max is not None and amount_min > amount_max:
        raise HTTPException(status_code=422, detail="amount_min must be less than or equal to amount_max")
    result = await list_operations(
        db, view=view, search=search, stage=stage, assignment=assignment,
        tenant_id=tenant_id, technician_id=technician_id, customer_id=customer_id,
        city=city, state=state, district=district, zipcode=zipcode,
        amount_min=amount_min, amount_max=amount_max,
        sort_by=sort_by, sort_dir=sort_dir,
        date_from=parsed_from, date_to=parsed_to,
        page=page, page_size=page_size,
    )
    return ok(result, _RID(r), "home_services_operations")


@router.get("/summary", summary="Unified operations KPI metrics (admin) — pagination-independent",
            response_model=ApiResponse)
async def get_operations_summary(
    r: Request,
    tenant_id: uuid.UUID | None = Query(None),
    refresh: bool = Query(False, description="Bypass the cache and recompute now."),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
):
    """Counting every job is a full table pass, so the result is cached for a
    minute and served stale-while-revalidating. The payload carries `freshness`
    and `computed_at`; pass refresh=true (the console's Refresh button) to force
    a recompute.
    """
    result = await compute_metrics_cached(db, tenant_id=tenant_id, refresh=refresh)
    return ok(result, _RID(r), "home_services_operations")


@router.get("/export", summary="Export the unified operational feed as CSV, same filters as the list (admin)")
async def export_operations(
    r: Request,
    view: Literal["all", "requests", "active", "approval", "exceptions", "completed"] = Query("all"),
    search: str | None = Query(None, min_length=1, max_length=200),
    stage: Literal["REQUEST", "MATCHING", "UNASSIGNED", "ASSIGNED", "SCHEDULED", "ON_THE_WAY", "INSPECTION", "AWAITING_ESTIMATE", "AWAITING_APPROVAL", "READY_TO_START", "IN_PROGRESS", "WORK_DONE", "COMPLETED", "AT_RISK", "CLOSED", "UNKNOWN"] | None = Query(None),
    assignment: Literal["assigned", "unassigned"] | None = Query(None),
    tenant_id: uuid.UUID | None = Query(None),
    technician_id: uuid.UUID | None = Query(None),
    customer_id: uuid.UUID | None = Query(None),
    city: str | None = Query(None, max_length=100),
    state: str | None = Query(None, max_length=100),
    district: str | None = Query(None, max_length=100),
    zipcode: str | None = Query(None, max_length=20),
    amount_min: Decimal | None = Query(None, ge=0),
    amount_max: Decimal | None = Query(None, ge=0),
    sort_by: Literal["created_at", "updated_at", "scheduled_date", "amount"] = Query("created_at"),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
):
    # Same filters as the list endpoint, bounded page_size sweep (not the
    # frontend's currently-loaded rows) -- caps at 5000 rows per export to
    # keep this bounded rather than unbounded-streaming the whole table.
    parsed_from, parsed_to = _parse_date_range(date_from, date_to)
    if amount_min is not None and amount_max is not None and amount_min > amount_max:
        raise HTTPException(status_code=422, detail="amount_min must be less than or equal to amount_max")
    result = await list_operations(
        db, view=view, search=search, stage=stage, assignment=assignment,
        tenant_id=tenant_id, technician_id=technician_id, customer_id=customer_id,
        city=city, state=state, district=district, zipcode=zipcode,
        amount_min=amount_min, amount_max=amount_max,
        sort_by=sort_by, sort_dir=sort_dir,
        date_from=parsed_from, date_to=parsed_to,
        page=1, page_size=5000,
    )
    buf = io.StringIO()
    fieldnames = ["work_id", "work_type", "draft_id", "booking_id", "job_id", "booking_number",
                  "customer_name", "master_service", "job_type", "tenant_name",
                  "technician_name", "current_stage", "canonical_status", "assignment_status",
                  "sla_state", "location_summary", "created_at", "updated_at"]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in result["records"]:
        writer.writerow({key: _csv_safe(value) for key, value in row.items()})
    buf.seek(0)
    exported = len(result["records"])
    total = result["pagination"]["total"]
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={
                                 "Content-Disposition": "attachment; filename=home_services_operations.csv",
                                 "Cache-Control": "no-store",
                                 "X-Export-Total": str(total),
                                 "X-Export-Truncated": "true" if exported < total else "false",
                             })
