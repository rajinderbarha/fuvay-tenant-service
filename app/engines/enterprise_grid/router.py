"""Sprint 26 — Enterprise Grid API Router.

Endpoints:
  Saved Views:
    GET    /v1/enterprise/saved-views
    POST   /v1/enterprise/saved-views
    GET    /v1/enterprise/saved-views/{view_id}
    PUT    /v1/enterprise/saved-views/{view_id}
    DELETE /v1/enterprise/saved-views/{view_id}
    POST   /v1/enterprise/saved-views/{view_id}/set-default

  Column Preferences:
    GET    /v1/enterprise/column-preferences
    PUT    /v1/enterprise/column-preferences
    POST   /v1/enterprise/column-preferences/reset

  Exports:
    POST   /v1/enterprise/exports
    GET    /v1/enterprise/exports
    GET    /v1/enterprise/exports/{export_id}
    POST   /v1/enterprise/exports/{export_id}/retry

  Registry:
    GET    /v1/enterprise/registry/{resource_key}
    GET    /v1/enterprise/registry
"""
from __future__ import annotations
import uuid
from typing import Optional, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.enterprise_grid.filter_registry import EnterpriseFilterRegistry
from app.engines.enterprise_grid.query_service import EnterpriseListQueryService
from app.engines.enterprise_grid.services import SavedViewService, ColumnPreferenceService, ExportService
from app.engines.enterprise_grid.constants import (
    ENTERPRISE_SYNC_EXPORT_ROW_LIMIT, SCOPE_PROVIDER,
    ERR_EXPORT_FIELD_NOT_ALLOWED, ERR_EXPORT_JOB_NOT_FOUND, ERR_EXPORT_JOB_ACCESS_DENIED,
    ERR_EXPORT_CONCURRENT_JOB_LIMIT, ERR_EXPORT_TENANT_CONCURRENT_LIMIT,
    ERR_EXPORT_IDEMPOTENCY_CONFLICT, ERR_EXPORT_FIELD_LIMIT,
    ERR_EXPORT_SELECTED_ID_LIMIT, ERR_EXPORT_DATE_RANGE_EXCEEDED,
    EXPORT_IDEMPOTENCY_KEY_MAX_LEN,
)
from app.core.permissions import permission_checker
from app.core.security import rate_limiter
from app.exceptions import ServiceOSException

enterprise_router = APIRouter(prefix="/enterprise", tags=["Enterprise Grid"])

_saved_view = SavedViewService()
_col_pref   = ColumnPreferenceService()
_export     = ExportService()
_query_svc  = EnterpriseListQueryService()


def _rid(r: Request | None) -> str:
    return getattr(r.state, "request_id", "—") if r else "—"


# FINAL-L5-05R Part 31: the export service raises plain ValueError for
# domain errors (a pre-existing, pervasive pattern across this whole
# router, shared with saved-views/column-preferences -- not something
# introduced this sprint). Left uncaught, these produced an unhandled 500
# instead of a controlled 422/404/403, discovered live while verifying the
# newly-completed resource mapping. Scoped narrowly to the 3 export
# endpoints (list/get/retry/create) -- saved-views and column-preferences
# error handling is unrelated to this sprint's Export Authorization scope
# and is not touched.
_EXPORT_ERROR_STATUS = {
    ERR_EXPORT_FIELD_NOT_ALLOWED: 422,
    ERR_EXPORT_JOB_NOT_FOUND:     404,
    ERR_EXPORT_JOB_ACCESS_DENIED: 403,
    # FINAL-L5-05AA — export abuse-protection error codes (mission Part 8):
    # 429 for concurrency/quota limits, 422 for payload-bound violations,
    # 409 for idempotency-key conflicts.
    ERR_EXPORT_CONCURRENT_JOB_LIMIT:    429,
    ERR_EXPORT_TENANT_CONCURRENT_LIMIT: 429,
    ERR_EXPORT_IDEMPOTENCY_CONFLICT:    409,
    ERR_EXPORT_FIELD_LIMIT:             422,
    ERR_EXPORT_SELECTED_ID_LIMIT:       422,
    ERR_EXPORT_DATE_RANGE_EXCEEDED:     422,
}


def _raise_controlled_export_error(e: ValueError) -> None:
    msg = str(e)
    code = msg.split(":", 1)[0]
    status = _EXPORT_ERROR_STATUS.get(code, 422)
    raise ServiceOSException(
        error_code=code if code in _EXPORT_ERROR_STATUS else "EXPORT_FILTER_INVALID",
        detail=msg,
        status_code=status,
    ) from e


# ── Request bodies ─────────────────────────────────────────────────────────────

class CreateSavedViewIn(BaseModel):
    """Create a new saved view for a grid resource."""
    resource_key: str = Field(..., description="Registry resource key (e.g. admin_service_jobs)")
    view_name:    str = Field(..., min_length=1, max_length=128)
    scope:        str = Field("admin", description="admin | provider")
    filters:      dict = Field({}, description="Filter key-value pairs (validated against registry)")
    sort:         dict = Field({}, description="e.g. {sort_by: created_at, sort_direction: desc}")
    columns:      list = Field([], description="List of column keys to show")
    page_size:    int  = Field(25, ge=10, le=100)
    visibility:   str  = Field("private", description="private | tenant_shared | admin_shared")


class UpdateSavedViewIn(BaseModel):
    """Partial update for a saved view."""
    view_name:    Optional[str]  = None
    filters:      Optional[dict] = None
    sort:         Optional[dict] = None
    columns:      Optional[list] = None
    page_size:    Optional[int]  = None
    visibility:   Optional[str]  = None


class SaveColumnPrefsIn(BaseModel):
    """Save column visibility/order preferences for a resource."""
    resource_key: str  = Field(..., description="Registry resource key")
    columns:      list = Field(..., description="List of column configs [{key, visible, order}]")
    density:      str  = Field("comfortable", description="compact | comfortable | spacious")


class ResetColumnPrefsIn(BaseModel):
    """Reset column preferences to registry defaults."""
    resource_key: str


class CreateExportIn(BaseModel):
    """Request a CSV/XLSX export for a grid resource.

    If estimated_row_count > 5000 the job is created with status=failed
    and failure_reason includes EXPORT_ASYNC_REQUIRED. Async worker support
    is a carry-forward TODO.
    """
    resource_key:         str      = Field(..., description="Registry resource key")
    filters:              dict     = Field({}, description="Filters to apply (same as grid)")
    columns:              list[str]= Field([], description="Columns to include in export")
    export_format:        str      = Field("csv", description="csv | xlsx")
    estimated_row_count:  Optional[int] = Field(
        None, ge=0,
        description=(
            f"Caller-estimated row count. Exports above "
            f"{ENTERPRISE_SYNC_EXPORT_ROW_LIMIT} rows receive "
            f"status=failed with EXPORT_ASYNC_REQUIRED."
        ),
    )


# ── Registry ──────────────────────────────────────────────────────────────────

@enterprise_router.get(
    "/registry",
    tags=["Enterprise Grid"],
    summary="List all registered grid resource keys",
    description=(
        "Returns all registered resource keys available for use with saved views, "
        "column preferences, and exports. Each key maps to a resource config with "
        "allowed filters, sort fields, and column definitions."
    ),
)
async def list_resources(
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    keys = EnterpriseFilterRegistry.all_resource_keys()
    return ok({"resource_keys": keys}, _rid(r), "enterprise.registry.list")


@enterprise_router.get(
    "/registry/{resource_key}",
    tags=["Enterprise Grid"],
    summary="Get filter/sort/column config for a resource",
    description=(
        "Returns the full resource config including allowed_filters, allowed_sort_fields, "
        "default_sort, available_columns, and sensitive_fields for the given resource key."
    ),
)
async def get_resource_config(
    resource_key: str,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cfg = EnterpriseFilterRegistry.get_config(resource_key)
    return ok(cfg, _rid(r), "enterprise.registry.get")


# ── Saved Views ───────────────────────────────────────────────────────────────

@enterprise_router.get(
    "/saved-views",
    tags=["Enterprise Saved Views"],
    summary="List saved views for a resource",
    description=(
        "Returns saved views visible to the current user: "
        "own private views + tenant_shared within same tenant + admin_shared for admins. "
        "Filter by resource_key and scope."
    ),
)
async def list_saved_views(
    resource_key: str,
    scope:        str = "admin",
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    views = await _saved_view.list_views(db, u.user_id, u.tenant_id, resource_key, scope)
    return ok([v.to_dict() for v in views], _rid(r), "enterprise.saved_views.list")


@enterprise_router.post(
    "/saved-views",
    tags=["Enterprise Saved Views"],
    summary="Create a saved view",
    description=(
        "Creates a named saved view that stores filter state, sort, visible columns, "
        "and page_size. Filters are validated against the registry before save. "
        "Visibility: private (own only) | tenant_shared | admin_shared."
    ),
    status_code=201,
)
async def create_saved_view(
    body: CreateSavedViewIn,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    view = await _saved_view.create_view(
        db, u.user_id, u.tenant_id,
        scope        = body.scope,
        resource_key = body.resource_key,
        view_name    = body.view_name,
        filters      = body.filters,
        sort         = body.sort,
        columns      = body.columns,
        page_size    = body.page_size,
        visibility   = body.visibility,
    )
    return ok(view.to_dict(), _rid(r), "enterprise.saved_view.created")


@enterprise_router.get(
    "/saved-views/{view_id}",
    tags=["Enterprise Saved Views"],
    summary="Get a saved view by ID",
    description="Returns the saved view if the current user has read access. Raises SAVED_VIEW_ACCESS_DENIED otherwise.",
)
async def get_saved_view(
    view_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    view = await _saved_view.get_view(db, view_id, u.user_id, u.tenant_id)
    return ok(view.to_dict(), _rid(r), "enterprise.saved_view.get")


@enterprise_router.put(
    "/saved-views/{view_id}",
    tags=["Enterprise Saved Views"],
    summary="Update a saved view",
    description="Partial update (PATCH-style). Only the owner may update. Raises SAVED_VIEW_ACCESS_DENIED for others.",
)
async def update_saved_view(
    view_id: uuid.UUID,
    body: UpdateSavedViewIn,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updates = body.model_dump(exclude_none=True)
    view    = await _saved_view.update_view(db, view_id, u.user_id, u.tenant_id, updates)
    return ok(view.to_dict(), _rid(r), "enterprise.saved_view.updated")


@enterprise_router.delete(
    "/saved-views/{view_id}",
    tags=["Enterprise Saved Views"],
    summary="Delete a saved view",
    description="Permanently deletes the saved view. Only the owner may delete.",
)
async def delete_saved_view(
    view_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _saved_view.delete_view(db, view_id, u.user_id, u.tenant_id)
    return ok({"deleted": str(view_id)}, _rid(r), "enterprise.saved_view.deleted")


@enterprise_router.post(
    "/saved-views/{view_id}/set-default",
    tags=["Enterprise Saved Views"],
    summary="Set a view as the user's default for its resource",
    description=(
        "Marks this view as the default for the current user on the resource. "
        "Clears is_default from all other views the user owns for the same resource."
    ),
)
async def set_default_view(
    view_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    view = await _saved_view.set_default(db, view_id, u.user_id, u.tenant_id)
    return ok(view.to_dict(), _rid(r), "enterprise.saved_view.set_default")


# ── Column Preferences ────────────────────────────────────────────────────────

@enterprise_router.get(
    "/column-preferences",
    tags=["Enterprise Column Preferences"],
    summary="Get column preferences for a resource",
    description=(
        "Returns the current user's column visibility, order, and density preferences "
        "for the given resource. Falls back to registry defaults if not yet saved."
    ),
)
async def get_column_preferences(
    resource_key: str,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await _col_pref.get_preferences(db, u.user_id, resource_key)
    return ok(prefs.to_dict() if hasattr(prefs, "to_dict") else {"columns": prefs.columns, "density": prefs.density},
              _rid(r), "enterprise.col_prefs.get")


@enterprise_router.put(
    "/column-preferences",
    tags=["Enterprise Column Preferences"],
    summary="Save column preferences for a resource",
    description=(
        "Saves the user's column visibility/order/density preferences for a resource. "
        "Sensitive columns are rejected with COLUMN_PREFERENCE_INVALID."
    ),
)
async def save_column_preferences(
    body: SaveColumnPrefsIn,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await _col_pref.save_preferences(
        db, u.user_id, u.tenant_id,
        body.resource_key, body.columns, body.density,
    )
    return ok(prefs.to_dict(), _rid(r), "enterprise.col_prefs.saved")


@enterprise_router.post(
    "/column-preferences/reset",
    tags=["Enterprise Column Preferences"],
    summary="Reset column preferences to registry defaults",
    description="Deletes the saved preferences record and returns the registry default column list.",
)
async def reset_column_preferences(
    body: ResetColumnPrefsIn,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    defaults = await _col_pref.reset_preferences(db, u.user_id, body.resource_key)
    return ok({"columns": defaults, "density": "comfortable"}, _rid(r), "enterprise.col_prefs.reset")


# ── Exports ───────────────────────────────────────────────────────────────────

_EXPORT_STANDARD_RESPONSE = """
Standard list response envelope:
```json
{
  "success": true,
  "data": {
    "items": [],
    "pagination": {
      "page": 1, "page_size": 25, "total_items": 250,
      "total_pages": 10, "has_next": true, "has_previous": false
    },
    "sort": { "sort_by": "created_at", "sort_direction": "desc" },
    "filters_applied": {},
    "available_filters": [],
    "available_columns": [],
    "saved_view_id": null
  },
  "request_id": "req_xxx"
}
```

Standard query parameters accepted by all enterprise list endpoints:
`page`, `page_size`, `sort_by`, `sort_direction`, `search`,
`status`, `category_id`, `tenant_id`, `offering_id`, `customer_id`,
`staff_member_id`, `date_from`, `date_to`, `created_from`, `created_to`,
`updated_from`, `updated_to`, `record_type`, `type`, `priority`,
`payment_status`, `commission_status`, `assignment_status`,
`review_status`, `complaint_status`.

**Error codes:**
`GRID_RESOURCE_NOT_FOUND`, `GRID_FILTER_NOT_ALLOWED`, `GRID_SORT_NOT_ALLOWED`,
`GRID_INVALID_PAGE`, `GRID_INVALID_PAGE_SIZE`, `GRID_INVALID_DATE_RANGE`,
`GRID_SEARCH_TOO_LONG`, `GRID_ACCESS_DENIED`,
`SAVED_VIEW_NOT_FOUND`, `SAVED_VIEW_ACCESS_DENIED`, `SAVED_VIEW_INVALID_FILTER`,
`SAVED_VIEW_INVALID_COLUMNS`, `SAVED_VIEW_DUPLICATE_NAME`,
`COLUMN_PREFERENCE_INVALID`, `COLUMN_PREFERENCE_ACCESS_DENIED`,
`EXPORT_NOT_ALLOWED`, `EXPORT_FIELD_NOT_ALLOWED`, `EXPORT_TOO_LARGE`,
`EXPORT_ASYNC_REQUIRED`, `EXPORT_JOB_NOT_FOUND`, `EXPORT_JOB_ACCESS_DENIED`,
`EXPORT_GENERATION_FAILED`.
"""


@enterprise_router.post(
    "/exports",
    tags=["Enterprise Exports"],
    summary="Request a CSV/XLSX export job",
    description=(
        "Creates an export job for the given resource with applied filters and columns. "
        "If `estimated_row_count` is provided and exceeds 5000, the job is created with "
        "status=failed and EXPORT_ASYNC_REQUIRED in the failure_reason "
        "(async worker is a carry-forward TODO). "
        "Provider exports are always tenant-scoped; admin tenant_id filter is optional.\n\n"
        + _EXPORT_STANDARD_RESPONSE
    ),
    status_code=201,
)
async def create_export(
    body: CreateExportIn,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # FINAL-L5-05O/05R: create_export_job previously had zero domain-
    # permission gating -- any authenticated role could export any of the
    # 39 registered resources. Every registered resource now has an
    # explicit export-shaped permission (never a read permission alone),
    # and an unknown/unregistered resource_key fails closed with a
    # controlled error rather than silently skipping the permission check
    # (dict.get on an unknown key would otherwise return None, which is
    # falsy and would have bypassed authorization entirely).
    if not EnterpriseFilterRegistry.resource_exists(body.resource_key):
        raise ServiceOSException(
            error_code="EXPORT_RESOURCE_UNSUPPORTED",
            detail=f"Export resource '{body.resource_key}' is not a recognized export resource.",
            status_code=422,
            context={"resource_key": body.resource_key},
        )
    required = EnterpriseFilterRegistry.required_export_permission(body.resource_key)
    if required and not permission_checker.has(
        role=u.role, permission=required, overrides=getattr(u, "permission_overrides", None),
    ):
        raise ServiceOSException(
            error_code="PERMISSION_DENIED",
            detail=f"Permission '{required}' required. Your role '{u.role}' does not have this permission.",
            blocking_rule=f"required_permission: {required}",
            resolution="Contact your administrator to grant this permission.",
            context={"required": required, "role": u.role},
        )
    # FINAL-L5-05R Part 10/11/23: SCOPE_PROVIDER resources must always be
    # exported using the caller's own tenant_id -- a payload filter cannot
    # override authorized scope. This mirrors EnterpriseListQueryService.
    # validate_scope() (used by the list/query path) but was never wired
    # into export creation, so a provider/tenant-side caller could
    # previously request an export with a filters.tenant_id belonging to a
    # different tenant with no rejection at job-creation time.
    scope_type = EnterpriseFilterRegistry.get_scope_type(body.resource_key)
    if scope_type == SCOPE_PROVIDER and u.role != "super_admin":
        # super_admin is platform-wide and legitimately exports any
        # tenant's provider-scoped data (matches the established pattern
        # elsewhere in this codebase, e.g. ServiceabilityService.
        # _assert_owns_tenant(), which exempts super_admin identically).
        requested_tenant_id = body.filters.get("tenant_id") if body.filters else None
        if requested_tenant_id and str(requested_tenant_id) != str(u.tenant_id):
            raise ServiceOSException(
                error_code="EXPORT_CROSS_TENANT_FORBIDDEN",
                detail="Cannot export another tenant's data.",
                status_code=403,
                context={"resource_key": body.resource_key},
            )
    # FINAL-L5-05AA Part 7: lightweight abuse control BEFORE any DB write --
    # a denied-authorization or invalid-resource request never reaches this
    # line (both raise above), so an unauthorized caller never consumes a
    # Redis round-trip or a database write either way. Reuses the platform's
    # existing atomic Redis sliding-window limiter (app.core.security,
    # already proven in app.engines.platform_commerce.service.initiate_deposit)
    # rather than building a second one -- the "api:export" policy (5/hour)
    # already existed in RATE_LIMITS but was never actually wired into this
    # endpoint until now (confirmed via grep: 0 prior callers).
    await rate_limiter.check_and_raise(
        limit_key="export", limit_type="api:export", identifier=str(u.user_id),
    )

    idempotency_key = r.headers.get("X-Idempotency-Key") if r else None
    if idempotency_key and len(idempotency_key) > EXPORT_IDEMPOTENCY_KEY_MAX_LEN:
        idempotency_key = idempotency_key[:EXPORT_IDEMPOTENCY_KEY_MAX_LEN]

    try:
        job, is_replay = await _export.create_export_job(
            db, u.user_id, u.tenant_id,
            resource_key         = body.resource_key,
            filters              = body.filters,
            columns              = body.columns,
            export_format        = body.export_format,
            estimated_row_count  = body.estimated_row_count,
            idempotency_key      = idempotency_key,
        )
    except ValueError as e:
        _raise_controlled_export_error(e)
    return ok(job.to_dict(), _rid(r), "enterprise.export.created", idempotent=is_replay)


@enterprise_router.get(
    "/exports",
    tags=["Enterprise Exports"],
    summary="List export jobs for the current user",
    description="Returns all export jobs requested by the current user, newest first.",
)
async def list_exports(
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    jobs = await _export.list_export_jobs(db, u.user_id)
    return ok([j.to_dict() for j in jobs], _rid(r), "enterprise.exports.list")


@enterprise_router.get(
    "/exports/{export_id}",
    tags=["Enterprise Exports"],
    summary="Get export job status and download URL",
    description=(
        "Returns the current status of an export job. "
        "When status=completed, file_url is populated. "
        "When status=failed, failure_reason explains why (e.g. EXPORT_ASYNC_REQUIRED)."
    ),
)
async def get_export(
    export_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        job = await _export.get_export_job(db, export_id, u.user_id)
    except ValueError as e:
        _raise_controlled_export_error(e)
    return ok(job.to_dict(), _rid(r), "enterprise.export.get")


@enterprise_router.post(
    "/exports/{export_id}/retry",
    tags=["Enterprise Exports"],
    summary="Retry a failed export job",
    description=(
        "Resets a failed or expired export job back to pending status. "
        "Note: if the job failed with EXPORT_ASYNC_REQUIRED, it will fail again "
        "until an async worker is implemented."
    ),
)
async def retry_export(
    export_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        job = await _export.get_export_job(db, export_id, u.user_id)
    except ValueError as e:
        _raise_controlled_export_error(e)
    from app.engines.enterprise_grid.constants import EXPORT_PENDING
    if job.status not in ("failed", "expired"):
        raise ServiceOSException(
            error_code="EXPORT_JOB_NOT_READY",
            detail=f"Only failed or expired jobs can be retried (current status: {job.status}).",
            status_code=409,
        )
    job.status         = EXPORT_PENDING
    job.failure_reason = None
    job.error_code      = None
    job.error_message   = None
    job.worker_id        = None
    job.claimed_at       = None
    job.started_at        = None
    job.storage_key       = None
    job.progress           = 0
    await db.commit()
    return ok(job.to_dict(), _rid(r), "enterprise.export.retry")


@enterprise_router.post(
    "/exports/{export_id}/cancel",
    tags=["Enterprise Exports"],
    summary="Cancel a queued or in-progress export job",
    description=(
        "Cancels a pending or processing export job. Cancelled jobs are "
        "never downloadable, and any partial storage object is cleaned up "
        "by the cleanup worker. Completed/failed/expired jobs cannot be "
        "cancelled (409)."
    ),
)
async def cancel_export(
    export_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        job = await _export.get_export_job(db, export_id, u.user_id)
    except ValueError as e:
        _raise_controlled_export_error(e)
    if job.status not in ("pending", "processing"):
        raise ServiceOSException(
            error_code="EXPORT_JOB_NOT_READY",
            detail=f"Only pending or processing jobs can be cancelled (current status: {job.status}).",
            status_code=409,
        )
    from datetime import datetime, timezone
    job.status = "cancelled"
    job.cancelled_at = datetime.now(timezone.utc)
    await db.commit()
    return ok(job.to_dict(), _rid(r), "enterprise.export.cancel")


@enterprise_router.get(
    "/exports/{export_id}/download",
    tags=["Enterprise Exports"],
    summary="Download a completed export file",
    description=(
        "Independently re-authorizes (resource export permission + own-job "
        "ownership + COMPLETED status + not-expired + file-exists) before "
        "streaming the private file. Knowing the job ID alone is never "
        "sufficient (rule 15)."
    ),
)
async def download_export(
    export_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        job = await _export.get_export_job(db, export_id, u.user_id)
    except ValueError as e:
        _raise_controlled_export_error(e)

    # Re-check the resource export permission at download time, not just at
    # creation time -- a permission revoked between job creation and
    # download must take effect (rule: "Permission removal takes effect
    # according to session policy").
    required = EnterpriseFilterRegistry.required_export_permission(job.resource_key)
    if required and not permission_checker.has(
        role=u.role, permission=required, overrides=getattr(u, "permission_overrides", None),
    ):
        raise ServiceOSException(
            error_code="EXPORT_DOWNLOAD_FORBIDDEN",
            detail="You no longer have permission to download this export.",
            status_code=403,
        )

    if job.status != "completed":
        raise ServiceOSException(
            error_code="EXPORT_JOB_NOT_READY",
            detail=f"Export is not ready for download (status: {job.status}).",
            status_code=409,
        )
    from datetime import datetime, timezone
    if job.expires_at and job.expires_at < datetime.now(timezone.utc):
        raise ServiceOSException(
            error_code="EXPORT_JOB_EXPIRED",
            detail="This export has expired. Please retry to generate a new one.",
            status_code=410,
        )
    if not job.storage_key:
        raise ServiceOSException(
            error_code="EXPORT_JOB_NOT_FOUND",
            detail="Export file is missing.",
            status_code=404,
        )

    from app.engines.enterprise_grid.export_storage import ExportStorageService
    storage = ExportStorageService()
    if not storage.exists(job.storage_key):
        raise ServiceOSException(
            error_code="EXPORT_JOB_NOT_FOUND",
            detail="Export file is missing.",
            status_code=404,
        )
    content = storage.read_bytes(job.storage_key)

    from app.core.audit import record_platform_audit
    await record_platform_audit(
        db, operation="export.downloaded", engine_id="enterprise_grid",
        tenant_id=job.tenant_id, entity_type="export_job", entity_id=str(job.id),
        actor_id=uuid.UUID(u.user_id) if getattr(u, "user_id", None) else None, actor_role=u.role,
        request_id=_rid(r),
    )
    await db.commit()

    safe_filename = job.filename or f"export-{job.id}.csv"
    return Response(
        content=content,
        media_type=job.content_type or "text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
