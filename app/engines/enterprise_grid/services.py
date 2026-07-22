"""Sprint 26 — Saved Views, Column Preferences, Export Services."""
from __future__ import annotations
import csv
import hashlib
import io
import json
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.enterprise_grid.constants import (
    VIS_PRIVATE, VIS_TENANT_SHARED, VIS_ADMIN_SHARED,
    EXPORT_PENDING, EXPORT_COMPLETED, EXPORT_FAILED,
    EXPORT_EXPIRY_HOURS, MAX_EXPORT_ROWS,
    ERR_SAVED_VIEW_NOT_FOUND, ERR_SAVED_VIEW_ACCESS_DENIED,
    ERR_SAVED_VIEW_INVALID_FILTER, ERR_SAVED_VIEW_INVALID_COLUMNS,
    ERR_SAVED_VIEW_DUPLICATE_NAME,
    ERR_COLUMN_PREFERENCE_INVALID,
    ERR_EXPORT_NOT_ALLOWED, ERR_EXPORT_FIELD_NOT_ALLOWED,
    ERR_EXPORT_JOB_NOT_FOUND,
    ERR_EXPORT_JOB_ACCESS_DENIED, ERR_EXPORT_GENERATION_FAILED,
    ERR_EXPORT_CONCURRENT_JOB_LIMIT, ERR_EXPORT_TENANT_CONCURRENT_LIMIT,
    ERR_EXPORT_IDEMPOTENCY_CONFLICT, ERR_EXPORT_FIELD_LIMIT,
    ERR_EXPORT_SELECTED_ID_LIMIT, ERR_EXPORT_DATE_RANGE_EXCEEDED,
    EXPORT_MAX_CONCURRENT_JOBS_PER_ACTOR, EXPORT_MAX_CONCURRENT_JOBS_PER_TENANT,
    EXPORT_MAX_COLUMNS, EXPORT_MAX_SELECTED_IDS, EXPORT_MAX_DATE_RANGE_DAYS,
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
        if str(view.owner_user_id) != str(user_id):
            raise ValueError(ERR_SAVED_VIEW_ACCESS_DENIED)
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

    # ── FINAL-L5-05AA: payload-bound validation helpers ─────────────────────
    # Each raises ValueError with a controlled error-code prefix, matching
    # this file's established convention (router._raise_controlled_export_error
    # maps the prefix to the right HTTP status).

    _DATE_FILTER_PAIRS = (
        ("date_from", "date_to"), ("created_from", "created_to"),
        ("updated_from", "updated_to"), ("start_date", "end_date"),
    )
    _ID_LIST_FILTER_KEYS = ("ids", "selected_ids", "id_in", "record_ids")

    def _validate_payload_bounds(self, columns: list[str], filters: dict) -> None:
        if len(columns) > EXPORT_MAX_COLUMNS:
            raise ValueError(
                f"{ERR_EXPORT_FIELD_LIMIT}: {len(columns)} columns requested, "
                f"maximum is {EXPORT_MAX_COLUMNS}"
            )
        for key in self._ID_LIST_FILTER_KEYS:
            val = filters.get(key)
            if isinstance(val, (list, tuple)) and len(val) > EXPORT_MAX_SELECTED_IDS:
                raise ValueError(
                    f"{ERR_EXPORT_SELECTED_ID_LIMIT}: {len(val)} IDs selected via "
                    f"'{key}', maximum is {EXPORT_MAX_SELECTED_IDS}"
                )
        for from_key, to_key in self._DATE_FILTER_PAIRS:
            f, t = filters.get(from_key), filters.get(to_key)
            if not (f and t):
                continue
            try:
                d_from = datetime.fromisoformat(str(f).replace("Z", "+00:00"))
                d_to = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue  # malformed dates are the filter-validation layer's concern, not this bound check
            if (d_to - d_from).days > EXPORT_MAX_DATE_RANGE_DAYS:
                raise ValueError(
                    f"{ERR_EXPORT_DATE_RANGE_EXCEEDED}: {(d_to - d_from).days} day range "
                    f"requested via '{from_key}'/'{to_key}', maximum is {EXPORT_MAX_DATE_RANGE_DAYS} days"
                )

    @staticmethod
    def _fingerprint(resource_key: str, filters: dict, columns: list[str], export_format: str) -> str:
        """Deterministic payload fingerprint -- field/filter key ORDER never
        changes the fingerprint (mission Part 10: 'field order does not
        change fingerprint... filter order does not change fingerprint')."""
        normalized = {
            "resource_key": resource_key,
            "filters": {k: filters[k] for k in sorted(filters.keys())},
            "columns": sorted(columns),
            "export_format": export_format,
        }
        blob = json.dumps(normalized, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode()).hexdigest()

    async def _count_active_jobs(self, db: AsyncSession, *, user_id: uuid.UUID | None = None,
                                  tenant_id: uuid.UUID | None = None) -> int:
        from app.engines.enterprise_grid.constants import EXPORT_PROCESSING
        conditions = [EnterpriseExportJob.status.in_((EXPORT_PENDING, EXPORT_PROCESSING))]
        if user_id is not None:
            conditions.append(EnterpriseExportJob.requested_by_user_id == user_id)
        if tenant_id is not None:
            conditions.append(EnterpriseExportJob.tenant_id == tenant_id)
        result = await db.execute(
            select(func.count()).select_from(EnterpriseExportJob).where(*conditions)
        )
        return result.scalar_one()

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
        idempotency_key: str | None = None,
    ) -> tuple[EnterpriseExportJob, bool]:
        """Returns (job, is_idempotent_replay)."""
        # validate export fields
        allowed_export = EnterpriseFilterRegistry.get_allowed_export_fields(resource_key)
        blocked        = [c for c in columns if c not in allowed_export]
        if blocked:
            raise ValueError(f"{ERR_EXPORT_FIELD_NOT_ALLOWED}: {blocked}")

        # validate filters — silently drop unknown keys
        invalid_filters = [k for k in filters if not EnterpriseFilterRegistry.validate_filter(resource_key, k)]
        safe_filters    = {k: v for k, v in filters.items() if k not in invalid_filters}

        # FINAL-L5-05AA Part 6/20/22/23: bounded payload -- rejected BEFORE
        # any rate-limit/idempotency/DB work, matching the mission's
        # required decision order ("validate payload" precedes "apply
        # lightweight abuse controls").
        self._validate_payload_bounds(columns, safe_filters)

        fingerprint = self._fingerprint(resource_key, safe_filters, columns, export_format)

        # FINAL-L5-05AA Part 9/10/12: a single per-actor Postgres advisory
        # lock guards BOTH the idempotency check-then-insert AND the
        # concurrent-job count-then-insert sequences. Taking the lock
        # before the idempotency lookup (not just before the concurrency
        # count) is required: two simultaneous requests carrying the SAME
        # idempotency key would otherwise both observe "no existing job"
        # and both attempt an INSERT, racing on the migration-136 partial
        # unique index and surfacing a raw IntegrityError instead of a
        # graceful replay. This mirrors the Service Area advisory-lock
        # pattern (FINAL-L5-05Q) used to close an equivalent TOCTOU race
        # for duplicate coverage creation.
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": f"export_concurrent:{user_id}"},
        )

        # Idempotent replay / conflict resolution. Scoped per-actor (never
        # cross-actor, never cross-tenant) via the migration-136 partial
        # unique index on (requested_by_user_id, idempotency_key).
        if idempotency_key:
            existing = (await db.execute(
                select(EnterpriseExportJob).where(
                    EnterpriseExportJob.requested_by_user_id == user_id,
                    EnterpriseExportJob.idempotency_key == idempotency_key,
                )
            )).scalars().first()
            if existing is not None:
                existing_fp = self._fingerprint(
                    existing.resource_key, existing.filters, existing.columns, existing.export_format,
                )
                if existing_fp != fingerprint:
                    raise ValueError(
                        f"{ERR_EXPORT_IDEMPOTENCY_CONFLICT}: idempotency key '{idempotency_key}' "
                        f"was already used with a different export request"
                    )
                return existing, True

        # Atomic concurrent-job limit (still under the same actor-scoped
        # lock acquired above). Tenant-level counting is a plain read (not
        # lock-protected) since the actor-level lock already prevents that
        # actor's own race, and a tenant limit is a soft-fairness control,
        # not a hard security boundary requiring cross-actor locking here.
        actor_active = await self._count_active_jobs(db, user_id=user_id)
        if actor_active >= EXPORT_MAX_CONCURRENT_JOBS_PER_ACTOR:
            raise ValueError(
                f"{ERR_EXPORT_CONCURRENT_JOB_LIMIT}: {actor_active} active export jobs, "
                f"maximum concurrent is {EXPORT_MAX_CONCURRENT_JOBS_PER_ACTOR}"
            )
        if tenant_id is not None:
            tenant_active = await self._count_active_jobs(db, tenant_id=tenant_id)
            if tenant_active >= EXPORT_MAX_CONCURRENT_JOBS_PER_TENANT:
                raise ValueError(
                    f"{ERR_EXPORT_TENANT_CONCURRENT_LIMIT}: {tenant_active} active export jobs "
                    f"for this tenant, maximum concurrent is {EXPORT_MAX_CONCURRENT_JOBS_PER_TENANT}"
                )

        # MODULE-L5-31: this used to fail the job closed with
        # EXPORT_ASYNC_REQUIRED whenever estimated_row_count exceeded
        # ENTERPRISE_SYNC_EXPORT_ROW_LIMIT (5000), on the assumption that no
        # async worker existed yet to process it. A real async worker
        # (app/jobs/export_worker.py, started in main.py's lifespan) was
        # built afterward and every adapter query is itself capped at
        # MAX_EXPORT_ROWS=5000 (resource_adapters.py), so there is no longer
        # any size an estimated_row_count could name that the worker can't
        # safely handle -- the old gate just permanently failed large,
        # perfectly processable requests before they ever reached the
        # worker's pending-job queue. Every job now queues as pending.
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
            idempotency_key      = idempotency_key,
        )
        db.add(job)
        await db.commit()
        return job, False

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
