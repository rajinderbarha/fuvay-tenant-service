"""Sprint 26 — Saved Views, Column Preferences, Export Services."""
from __future__ import annotations
import csv
import io
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.enterprise_grid.constants import (
    VIS_PRIVATE, VIS_TENANT_SHARED, VIS_ADMIN_SHARED,
    EXPORT_PENDING, EXPORT_COMPLETED, EXPORT_FAILED,
    EXPORT_EXPIRY_HOURS, MAX_EXPORT_ROWS, ENTERPRISE_SYNC_EXPORT_ROW_LIMIT,
    ERR_SAVED_VIEW_NOT_FOUND, ERR_SAVED_VIEW_ACCESS_DENIED,
    ERR_SAVED_VIEW_INVALID_FILTER, ERR_SAVED_VIEW_INVALID_COLUMNS,
    ERR_SAVED_VIEW_DUPLICATE_NAME,
    ERR_COLUMN_PREFERENCE_INVALID,
    ERR_EXPORT_NOT_ALLOWED, ERR_EXPORT_FIELD_NOT_ALLOWED,
    ERR_EXPORT_TOO_LARGE, ERR_EXPORT_ASYNC_REQUIRED,
    ERR_EXPORT_JOB_NOT_FOUND,
    ERR_EXPORT_JOB_ACCESS_DENIED, ERR_EXPORT_GENERATION_FAILED,
)
from app.engines.enterprise_grid.filter_registry import EnterpriseFilterRegistry
from app.engines.enterprise_grid.models import (
    EnterpriseSavedView, EnterpriseColumnPreference, EnterpriseExportJob,
)


# ── Saved View Service ────────────────────────────────────────────────────────

class SavedViewService:

    async def list_views(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
        resource_key: str,
        scope: str,
    ) -> list[EnterpriseSavedView]:
        conditions = [
            EnterpriseSavedView.resource_key == resource_key,
            EnterpriseSavedView.scope        == scope,
        ]
        # user sees: own private + tenant_shared within same tenant + admin_shared for admins
        from sqlalchemy import or_
        visibility_clauses = [
            and_(EnterpriseSavedView.owner_user_id == user_id,
                 EnterpriseSavedView.visibility == VIS_PRIVATE),
        ]
        if tenant_id:
            visibility_clauses.append(
                and_(EnterpriseSavedView.tenant_id == tenant_id,
                     EnterpriseSavedView.visibility == VIS_TENANT_SHARED)
            )
        if scope == "admin":
            visibility_clauses.append(
                EnterpriseSavedView.visibility == VIS_ADMIN_SHARED
            )
        conditions.append(or_(*visibility_clauses))
        r = await db.execute(
            select(EnterpriseSavedView).where(*conditions).order_by(EnterpriseSavedView.created_at.desc())
        )
        return r.scalars().all()

    async def create_view(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
        scope: str,
        resource_key: str,
        view_name: str,
        filters: dict,
        sort: dict,
        columns: list,
        page_size: int = 25,
        visibility: str = VIS_PRIVATE,
    ) -> EnterpriseSavedView:
        # validate filter keys
        invalid_filters = [k for k in filters if not EnterpriseFilterRegistry.validate_filter(resource_key, k)]
        if invalid_filters:
            raise ValueError(f"{ERR_SAVED_VIEW_INVALID_FILTER}: {invalid_filters}")

        # validate columns
        invalid_cols = EnterpriseFilterRegistry.validate_columns(resource_key, [c if isinstance(c, str) else c.get("key", "") for c in columns])
        if invalid_cols:
            raise ValueError(f"{ERR_SAVED_VIEW_INVALID_COLUMNS}: {invalid_cols}")

        # check duplicate name for this user + resource
        dup = await db.execute(
            select(EnterpriseSavedView).where(
                EnterpriseSavedView.owner_user_id == user_id,
                EnterpriseSavedView.resource_key  == resource_key,
                EnterpriseSavedView.view_name     == view_name,
            )
        )
        if dup.scalars().first():
            raise ValueError(ERR_SAVED_VIEW_DUPLICATE_NAME)

        view = EnterpriseSavedView(
            owner_user_id = user_id,
            tenant_id     = tenant_id,
            scope         = scope,
            resource_key  = resource_key,
            view_name     = view_name,
            filters       = filters,
            sort          = sort,
            columns       = columns,
            page_size     = page_size,
            visibility    = visibility,
        )
        db.add(view)
        await db.commit()
        return view

    async def get_view(
        self,
        db: AsyncSession,
        view_id: uuid.UUID,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
    ) -> EnterpriseSavedView:
        r = await db.execute(select(EnterpriseSavedView).where(EnterpriseSavedView.id == view_id))
        view = r.scalars().first()
        if not view:
            raise ValueError(ERR_SAVED_VIEW_NOT_FOUND)
        self._check_access(view, user_id, tenant_id)
        return view

    async def update_view(
        self,
        db: AsyncSession,
        view_id: uuid.UUID,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
        updates: dict,
    ) -> EnterpriseSavedView:
        view = await self.get_view(db, view_id, user_id, tenant_id)
        if str(view.owner_user_id) != str(user_id):
            raise ValueError(ERR_SAVED_VIEW_ACCESS_DENIED)
        for k, v in updates.items():
            if hasattr(view, k) and k not in ("id", "owner_user_id", "created_at"):
                setattr(view, k, v)
        await db.commit()
        return view

    async def delete_view(
        self,
        db: AsyncSession,
        view_id: uuid.UUID,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
    ) -> None:
        view = await self.get_view(db, view_id, user_id, tenant_id)
        if str(view.owner_user_id) != str(user_id):
            raise ValueError(ERR_SAVED_VIEW_ACCESS_DENIED)
        await db.delete(view)
        await db.commit()

    async def set_default(
        self,
        db: AsyncSession,
        view_id: uuid.UUID,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
    ) -> EnterpriseSavedView:
        view = await self.get_view(db, view_id, user_id, tenant_id)
        # unset other defaults for this user+resource
        others = await db.execute(
            select(EnterpriseSavedView).where(
                EnterpriseSavedView.owner_user_id == user_id,
                EnterpriseSavedView.resource_key  == view.resource_key,
                EnterpriseSavedView.is_default    == True,
                EnterpriseSavedView.id            != view_id,
            )
        )
        for other in others.scalars().all():
            other.is_default = False
        view.is_default = True
        await db.commit()
        return view

    def _check_access(self, view: EnterpriseSavedView, user_id: uuid.UUID, tenant_id: uuid.UUID | None) -> None:
        if view.visibility == VIS_PRIVATE:
            if str(view.owner_user_id) != str(user_id):
                raise ValueError(ERR_SAVED_VIEW_ACCESS_DENIED)
        elif view.visibility == VIS_TENANT_SHARED:
            if not tenant_id or str(view.tenant_id) != str(tenant_id):
                raise ValueError(ERR_SAVED_VIEW_ACCESS_DENIED)


# ── Column Preference Service ─────────────────────────────────────────────────

class ColumnPreferenceService:

    async def get_preferences(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        resource_key: str,
    ) -> EnterpriseColumnPreference | None:
        r = await db.execute(
            select(EnterpriseColumnPreference).where(
                EnterpriseColumnPreference.user_id      == user_id,
                EnterpriseColumnPreference.resource_key == resource_key,
            )
        )
        prefs = r.scalars().first()
        if not prefs:
            # return default from registry
            available = EnterpriseFilterRegistry.get_available_columns(resource_key)
            return EnterpriseColumnPreference(
                user_id=user_id, resource_key=resource_key,
                columns=available, density="comfortable",
            )
        return prefs

    async def save_preferences(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
        resource_key: str,
        columns: list,
        density: str = "comfortable",
    ) -> EnterpriseColumnPreference:
        # validate no sensitive cols
        col_keys = [c.get("key", c) if isinstance(c, dict) else c for c in columns]
        invalid  = EnterpriseFilterRegistry.validate_columns(resource_key, col_keys)
        if invalid:
            raise ValueError(f"{ERR_COLUMN_PREFERENCE_INVALID}: {invalid}")

        r = await db.execute(
            select(EnterpriseColumnPreference).where(
                EnterpriseColumnPreference.user_id      == user_id,
                EnterpriseColumnPreference.resource_key == resource_key,
            )
        )
        prefs = r.scalars().first()
        if prefs:
            prefs.columns = columns
            prefs.density = density
        else:
            prefs = EnterpriseColumnPreference(
                user_id=user_id, tenant_id=tenant_id,
                resource_key=resource_key, columns=columns, density=density,
            )
            db.add(prefs)
        await db.commit()
        return prefs

    async def reset_preferences(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        resource_key: str,
    ) -> list:
        r = await db.execute(
            select(EnterpriseColumnPreference).where(
                EnterpriseColumnPreference.user_id      == user_id,
                EnterpriseColumnPreference.resource_key == resource_key,
            )
        )
        prefs = r.scalars().first()
        if prefs:
            await db.delete(prefs)
            await db.commit()
        return EnterpriseFilterRegistry.get_available_columns(resource_key)


# ── Export Service ────────────────────────────────────────────────────────────

class ExportService:

    async def create_export_job(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
        resource_key: str,
        filters: dict,
        columns: list[str],
        export_format: str = "csv",
        scope: str = "admin",
        estimated_row_count: int | None = None,
    ) -> EnterpriseExportJob:
        # validate export fields
        allowed_export = EnterpriseFilterRegistry.get_allowed_export_fields(resource_key)
        blocked        = [c for c in columns if c not in allowed_export]
        if blocked:
            raise ValueError(f"{ERR_EXPORT_FIELD_NOT_ALLOWED}: {blocked}")

        # validate filters — silently drop unknown keys
        invalid_filters = [k for k in filters if not EnterpriseFilterRegistry.validate_filter(resource_key, k)]
        safe_filters    = {k: v for k, v in filters.items() if k not in invalid_filters}

        # enforce sync export row limit
        too_large       = (
            estimated_row_count is not None
            and estimated_row_count > ENTERPRISE_SYNC_EXPORT_ROW_LIMIT
        )
        if too_large:
            status         = EXPORT_FAILED
            failure_reason = (
                f"Async export worker required for exports larger than "
                f"{ENTERPRISE_SYNC_EXPORT_ROW_LIMIT} rows "
                f"(estimated: {estimated_row_count}). "
                f"Error: {ERR_EXPORT_ASYNC_REQUIRED}"
            )
        else:
            status         = EXPORT_PENDING
            failure_reason = None

        job = EnterpriseExportJob(
            requested_by_user_id = user_id,
            tenant_id            = tenant_id,
            resource_key         = resource_key,
            status               = status,
            export_format        = export_format,
            filters              = safe_filters,
            columns              = columns,
            failure_reason       = failure_reason,
            expires_at           = datetime.now(timezone.utc) + timedelta(hours=EXPORT_EXPIRY_HOURS),
        )
        db.add(job)
        await db.commit()
        return job

    # FINAL-L5-05R Part 14: CSV formula injection mitigation. A cell value
    # beginning with =, +, -, @, tab, or CR opens a formula context in
    # Excel/Sheets when the file is opened -- prefixing with a single quote
    # neutralizes it (standard OWASP CSV-injection mitigation) without
    # altering the visible value for any legitimate data.
    _FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

    def _sanitize_csv_cell(self, value: object) -> object:
        if isinstance(value, str) and value.startswith(self._FORMULA_PREFIXES):
            return "'" + value
        return value

    def generate_csv(
        self,
        resource_key: str,
        columns: list[str],
        rows: list[dict],
    ) -> str:
        allowed_export = EnterpriseFilterRegistry.get_allowed_export_fields(resource_key)
        safe_cols      = [c for c in columns if c in allowed_export]
        buf            = io.StringIO()
        writer         = csv.DictWriter(buf, fieldnames=safe_cols, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: self._sanitize_csv_cell(row.get(k, "")) for k in safe_cols})
        return buf.getvalue()

    async def mark_completed(
        self,
        db: AsyncSession,
        job: EnterpriseExportJob,
        row_count: int,
        file_url: str,
    ) -> EnterpriseExportJob:
        job.status    = EXPORT_COMPLETED
        job.row_count = row_count
        job.file_url  = file_url
        await db.commit()
        return job

    async def mark_failed(
        self,
        db: AsyncSession,
        job: EnterpriseExportJob,
        reason: str,
    ) -> EnterpriseExportJob:
        job.status         = EXPORT_FAILED
        job.failure_reason = reason
        await db.commit()
        return job

    async def get_export_job(
        self,
        db: AsyncSession,
        job_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> EnterpriseExportJob:
        r = await db.execute(select(EnterpriseExportJob).where(EnterpriseExportJob.id == job_id))
        job = r.scalars().first()
        if not job:
            raise ValueError(ERR_EXPORT_JOB_NOT_FOUND)
        if str(job.requested_by_user_id) != str(user_id):
            raise ValueError(ERR_EXPORT_JOB_ACCESS_DENIED)
        return job

    async def list_export_jobs(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[EnterpriseExportJob]:
        r = await db.execute(
            select(EnterpriseExportJob)
            .where(EnterpriseExportJob.requested_by_user_id == user_id)
            .order_by(EnterpriseExportJob.created_at.desc())
            .limit(50)
        )
        return r.scalars().all()
