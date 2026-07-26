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
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok
from app.engines.final_records.operations_service import list_operations, compute_metrics

router = APIRouter(prefix="/v1/admin/home-services/operations", tags=["Home Services Operations"])

_RID = lambda r: getattr(r.state, "request_id", "—")


def _parse_date(v: str | None) -> datetime | None:
    if not v:
        return None
    return datetime.fromisoformat(v)


@router.get("", summary="Unified Bookings & Jobs operational feed (admin)", response_model=ApiResponse)
async def get_operations(
    r: Request,
    view: str = Query("all"),
    search: str | None = Query(None),
    stage: str | None = Query(None),
    assignment: str | None = Query(None),
    tenant_id: uuid.UUID | None = Query(None),
    technician_id: uuid.UUID | None = Query(None),
    customer_id: uuid.UUID | None = Query(None),
    city: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
):
    result = await list_operations(
        db, view=view, search=search, stage=stage, assignment=assignment,
        tenant_id=tenant_id, technician_id=technician_id, customer_id=customer_id,
        city=city, date_from=_parse_date(date_from), date_to=_parse_date(date_to),
        page=page, page_size=page_size,
    )
    return ok(result, _RID(r), "home_services_operations")


@router.get("/summary", summary="Unified operations KPI metrics (admin) — pagination-independent",
            response_model=ApiResponse)
async def get_operations_summary(
    r: Request,
    tenant_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
):
    result = await compute_metrics(db, tenant_id=tenant_id)
    return ok(result, _RID(r), "home_services_operations")


@router.get("/export", summary="Export the unified operational feed as CSV, same filters as the list (admin)")
async def export_operations(
    r: Request,
    view: str = Query("all"),
    search: str | None = Query(None),
    stage: str | None = Query(None),
    assignment: str | None = Query(None),
    tenant_id: uuid.UUID | None = Query(None),
    city: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
):
    # Same filters as the list endpoint, bounded page_size sweep (not the
    # frontend's currently-loaded rows) -- caps at 5000 rows per export to
    # keep this bounded rather than unbounded-streaming the whole table.
    result = await list_operations(
        db, view=view, search=search, stage=stage, assignment=assignment,
        tenant_id=tenant_id, city=city, date_from=_parse_date(date_from), date_to=_parse_date(date_to),
        page=1, page_size=5000,
    )
    buf = io.StringIO()
    fieldnames = ["work_id", "work_type", "booking_id", "job_id", "booking_number",
                  "customer_name", "master_service", "job_type", "tenant_name",
                  "technician_name", "current_stage", "canonical_status", "assignment_status",
                  "sla_state", "location_summary", "created_at", "updated_at"]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in result["records"]:
        writer.writerow(row)
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=home_services_operations.csv"})
