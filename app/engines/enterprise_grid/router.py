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
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.enterprise_grid.filter_registry import EnterpriseFilterRegistry
from app.engines.enterprise_grid.query_service import EnterpriseListQueryService
from app.engines.enterprise_grid.services import SavedViewService, ColumnPreferenceService, ExportService
from app.engines.enterprise_grid.constants import ENTERPRISE_SYNC_EXPORT_ROW_LIMIT
from app.core.permissions import permission_checker
from app.exceptions import ServiceOSException

enterprise_router = APIRouter(prefix="/enterprise", tags=["Enterprise Grid"])

_saved_view = SavedViewService()
_col_pref   = ColumnPreferenceService()
_export     = ExportService()
_query_svc  = EnterpriseListQueryService()


def _rid(r: Request | None) -> str:
    return getattr(r.state, "request_id", "—") if r else "—"


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
    # FINAL-L5-05O: create_export_job previously had zero domain-permission
    # gating -- any authenticated role could export any of the 33 registered
    # resources. Finance/Security/Operations-sensitive resources now require
    # an explicit export-shaped permission (never a read permission alone).
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
    job = await _export.create_export_job(
        db, u.user_id, u.tenant_id,
        resource_key         = body.resource_key,
        filters              = body.filters,
        columns              = body.columns,
        export_format        = body.export_format,
        estimated_row_count  = body.estimated_row_count,
    )
    return ok(job.to_dict(), _rid(r), "enterprise.export.created")


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
    job = await _export.get_export_job(db, export_id, u.user_id)
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
    job = await _export.get_export_job(db, export_id, u.user_id)
    from app.engines.enterprise_grid.constants import EXPORT_PENDING
    job.status         = EXPORT_PENDING
    job.failure_reason = None
    await db.commit()
    return ok(job.to_dict(), _rid(r), "enterprise.export.retry")
