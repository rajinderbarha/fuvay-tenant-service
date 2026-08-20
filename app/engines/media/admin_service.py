"""MediaLibraryAdminService — enterprise admin operations on media_assets.

Migration 085 adds: media_links, media_signed_links, media_audit_logs +
new columns on media_assets (is_flagged, moderation_status, visibility,
archived_at, description, tags_json, linked_module, linked_record_id, etc.)

Security rules (must stay in effect):
  - Private media requires authorization — no URL guessing.
  - Every admin preview / download is audit-logged.
  - Deleted media uses soft delete first; hard delete allowed only when no
    active links exist (bookings, complaints, jobs, compliance, invoices).
  - Signed tokens expire; they are single-use-flagged on first use.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import String, and_, cast, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext
from app.engines.media.models import MediaAsset
from app.exceptions import NotFoundException, ServiceOSException
from app.schemas.base import decode_cursor, encode_cursor

logger = structlog.get_logger("media.admin_service")
utcnow = lambda: datetime.now(timezone.utc)

# These module-types block hard delete while they have active records.
PROTECTED_MODULES = {"booking", "job", "complaint", "dispute", "invoice", "compliance_export"}

SIGNED_LINK_TTL_PREVIEW = timedelta(minutes=15)
SIGNED_LINK_TTL_DOWNLOAD = timedelta(minutes=60)


class MediaLibraryAdminService:

    def __init__(self, db: AsyncSession, actor: UserContext) -> None:
        self.db = db
        self.actor = actor

    # ── Summary cards ────────────────────────────────────────────────────────

    async def get_summary(self) -> dict:
        seven_days_ago = utcnow() - timedelta(days=7)
        live = MediaAsset.deleted_at.is_(None)
        aggregate = await self.db.execute(
            select(
                func.count(MediaAsset.id).label("total"),
                func.count(MediaAsset.id).filter(MediaAsset.status == "active").label("active"),
                func.count(MediaAsset.id).filter(MediaAsset.status == "archived").label("archived"),
                func.count(MediaAsset.id).filter(MediaAsset.is_flagged.is_(True)).label("flagged"),
                func.count(MediaAsset.id).filter(MediaAsset.status == "quarantined").label("quarantined"),
                func.count(MediaAsset.id).filter(MediaAsset.is_public.is_(True)).label("public_count"),
                func.count(MediaAsset.id).filter(MediaAsset.is_public.is_(False)).label("private_count"),
                func.count(MediaAsset.id).filter(MediaAsset.mime_type.ilike("image/%")).label("images_count"),
                func.count(MediaAsset.id).filter(MediaAsset.mime_type.ilike("video/%")).label("videos_count"),
                func.count(MediaAsset.id).filter(
                    and_(
                        ~MediaAsset.mime_type.ilike("image/%"),
                        ~MediaAsset.mime_type.ilike("video/%"),
                    )
                ).label("documents_count"),
                func.count(MediaAsset.id).filter(MediaAsset.created_at >= seven_days_ago).label("recent_count"),
                func.coalesce(func.sum(MediaAsset.file_size_bytes), 0).label("total_size_bytes"),
                func.coalesce(func.sum(MediaAsset.file_size_bytes).filter(MediaAsset.status == "active"), 0).label("active_size_bytes"),
            ).where(live)
        )
        stats = aggregate.one()

        ctx_r = await self.db.execute(
            select(MediaAsset.media_context, func.count())
            .where(MediaAsset.status == "active")
            .group_by(MediaAsset.media_context)
            .order_by(func.count().desc())
            .limit(10)
        )
        by_context = {row[0]: row[1] for row in ctx_r.fetchall()}

        return {
            "total": stats.total,
            "active": stats.active,
            "archived": stats.archived,
            "flagged": stats.flagged,
            "quarantined": stats.quarantined,
            "public_count": stats.public_count,
            "private_count": stats.private_count,
            "images_count": stats.images_count,
            "videos_count": stats.videos_count,
            "documents_count": stats.documents_count,
            "recent_count": stats.recent_count,
            "total_size_bytes": stats.total_size_bytes,
            "total_size_mb": round(stats.total_size_bytes / (1024 * 1024), 2),
            "active_size_bytes": stats.active_size_bytes,
            "active_size_mb": round(stats.active_size_bytes / (1024 * 1024), 2),
            "by_context": by_context,
        }

    # ── Enterprise list ──────────────────────────────────────────────────────

    async def list_assets_admin(
        self,
        q: str | None = None,
        context: str | None = None,
        owner_type: str | None = None,
        visibility: str | None = None,
        status: str | None = None,
        moderation_status: str | None = None,
        is_flagged: bool | None = None,
        tenant_id: str | None = None,
        customer_id: str | None = None,
        file_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        sort: str = "newest",
        cursor: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        page_size = min(page_size, 200)
        allowed_sorts = {"newest", "oldest", "largest", "smallest"}
        if sort not in allowed_sorts:
            raise ServiceOSException("SORT_FIELD_NOT_ALLOWED", f"Unsupported media sort: {sort}.")

        base = select(MediaAsset).where(MediaAsset.deleted_at == None)  # noqa: E711

        if status:
            base = base.where(MediaAsset.status == status)
        if context:
            base = base.where(MediaAsset.media_context == context)
        if owner_type:
            base = base.where(MediaAsset.owner_type == owner_type)
        if tenant_id:
            base = base.where(MediaAsset.tenant_id == uuid.UUID(tenant_id))
        if customer_id:
            base = base.where(MediaAsset.customer_id == uuid.UUID(customer_id))
        if is_flagged is not None:
            base = base.where(MediaAsset.is_flagged.is_(is_flagged))
        if moderation_status:
            base = base.where(MediaAsset.moderation_status == moderation_status)
        if file_type:
            base = base.where(MediaAsset.mime_type.ilike(f"{file_type}/%"))
        if visibility == "public":
            base = base.where(MediaAsset.is_public == True)
        elif visibility == "private":
            base = base.where(MediaAsset.is_public == False)
        if q:
            term = f"%{q.strip()}%"
            base = base.where(or_(
                MediaAsset.file_name_original.ilike(term),
                MediaAsset.description.ilike(term),
                MediaAsset.media_number.ilike(term),
                MediaAsset.media_context.ilike(term),
                MediaAsset.owner_type.ilike(term),
                cast(MediaAsset.owner_id, String).ilike(term),
                cast(MediaAsset.tags_json, String).ilike(term),
            ))
        if date_from:
            try:
                base = base.where(MediaAsset.created_at >= datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc))
            except ValueError as exc:
                raise ServiceOSException("INVALID_PAYLOAD", "date_from must use ISO format.") from exc
        if date_to:
            try:
                end = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc) + timedelta(days=1)
                base = base.where(MediaAsset.created_at < end)
            except ValueError as exc:
                raise ServiceOSException("INVALID_PAYLOAD", "date_to must use ISO format.") from exc

        total_r = await self.db.execute(select(func.count()).select_from(base.subquery()))
        total = total_r.scalar_one()

        sort_by_size = sort in {"largest", "smallest"}
        sort_column = MediaAsset.file_size_bytes if sort_by_size else MediaAsset.created_at
        descending = sort in {"newest", "largest"}
        if cursor:
            decoded = decode_cursor(cursor)
            if decoded.get("sort") != sort:
                raise ServiceOSException("INVALID_PAYLOAD", "Pagination cursor does not match the active sort.")
            cursor_id = uuid.UUID(decoded["id"])
            raw_value = decoded["value"]
            cursor_value = int(raw_value) if sort_by_size else datetime.fromisoformat(raw_value)
            comparator = sort_column < cursor_value if descending else sort_column > cursor_value
            tie_breaker = MediaAsset.id < cursor_id if descending else MediaAsset.id > cursor_id
            base = base.where(or_(comparator, and_(sort_column == cursor_value, tie_breaker)))

        order = (sort_column.desc(), MediaAsset.id.desc()) if descending else (sort_column.asc(), MediaAsset.id.asc())
        # Offset is retained only for older API clients. The admin UI uses cursor paging.
        offset = 0 if cursor or page == 1 else (page - 1) * page_size
        rows_r = await self.db.execute(base.order_by(*order).offset(offset).limit(page_size + 1))
        assets = list(rows_r.scalars().all())
        has_next = len(assets) > page_size
        assets = assets[:page_size]
        next_cursor = None
        if has_next and assets:
            last = assets[-1]
            value = str(last.file_size_bytes) if sort_by_size else last.created_at.isoformat()
            next_cursor = encode_cursor({"sort": sort, "value": value, "id": str(last.id)})

        return {
            "items": [self._to_admin_dict(a) for a in assets],
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": has_next,
            "next_cursor": next_cursor,
        }

    # ── Detail ───────────────────────────────────────────────────────────────

    async def get_detail(self, media_id: uuid.UUID) -> dict:
        asset = await self._load(media_id)
        data = self._to_admin_dict(asset)
        await self._log_audit(media_id, "admin_preview", {"file_name": asset.file_name_original})
        return data

    # ── Linked records ───────────────────────────────────────────────────────

    async def get_linked_records(self, media_id: uuid.UUID) -> list[dict]:
        """Return media_links rows for this asset; fall back to inline columns."""
        asset = await self._load(media_id)
        try:
            async with self.db.begin_nested():
                r = await self.db.execute(
                    text("""
                        SELECT id, module_name, record_type, record_id, display_name, status, created_at
                        FROM media_links WHERE media_id = :mid ORDER BY created_at DESC
                    """),
                    {"mid": str(media_id)},
                )
            rows = r.fetchall()
            linked = [
                {
                    "id": str(row[0]),
                    "module_name": row[1],
                    "record_type": row[2],
                    "record_id": str(row[3]),
                    "display_name": row[4],
                    "status": row[5],
                    "created_at": row[6].isoformat() if row[6] else None,
                }
                for row in rows
            ]
            if linked:
                return linked
        except Exception:
            logger.exception("media.linked_records_query_failed", media_id=str(media_id))
        if asset.linked_module and asset.linked_record_id:
            return [{
                "id": f"inline-{asset.id}",
                "module_name": asset.linked_module,
                "record_type": asset.linked_module,
                "record_id": asset.linked_record_id,
                "display_name": None,
                "status": "active",
                "created_at": asset.created_at.isoformat() if asset.created_at else None,
            }]
        return []

    # ── Audit logs ───────────────────────────────────────────────────────────

    async def get_audit_logs(self, media_id: uuid.UUID, limit: int = 50) -> list[dict]:
        await self._load(media_id)
        try:
            async with self.db.begin_nested():
                r = await self.db.execute(
                    text("""
                        SELECT id, actor_user_id, actor_role, action_type, request_id,
                               metadata_json, created_at
                        FROM media_audit_logs WHERE media_id = :mid
                        ORDER BY created_at DESC LIMIT :lim
                    """),
                    {"mid": str(media_id), "lim": limit},
                )
            rows = r.fetchall()
            return [
                {
                    "id": str(row[0]),
                    "actor_user_id": str(row[1]) if row[1] else None,
                    "actor_role": row[2],
                    "action_type": row[3],
                    "request_id": row[4],
                    "metadata_json": row[5] or {},
                    "created_at": row[6].isoformat() if row[6] else None,
                }
                for row in rows
            ]
        except Exception:
            logger.exception("media.audit_logs_query_failed", media_id=str(media_id))
            return []

    # ── Signed URLs ──────────────────────────────────────────────────────────

    async def create_signed_preview_url(self, media_id: uuid.UUID) -> dict:
        asset = await self._load(media_id)
        token = secrets.token_urlsafe(48)
        expires = utcnow() + SIGNED_LINK_TTL_PREVIEW
        await self._insert_signed_link(media_id, token, expires, "preview")
        await self._log_audit(media_id, "admin_signed_preview_created",
                              {"file_name": asset.file_name_original})
        return {
            "token": token,
            "url": f"/v1/media/signed/{token}",
            "expires_at": expires.isoformat(),
            "purpose": "preview",
        }

    async def create_signed_download_url(self, media_id: uuid.UUID) -> dict:
        asset = await self._load(media_id)
        token = secrets.token_urlsafe(48)
        expires = utcnow() + SIGNED_LINK_TTL_DOWNLOAD
        await self._insert_signed_link(media_id, token, expires, "download")
        await self._log_audit(media_id, "admin_signed_download_created",
                              {"file_name": asset.file_name_original})
        return {
            "token": token,
            "url": f"/v1/media/signed/{token}",
            "expires_at": expires.isoformat(),
            "purpose": "download",
        }

    async def resolve_signed_token(self, token: str) -> dict:
        """Validate a signed token and return the media asset id + purpose.
        Marks token as used (single-use per spec).
        """
        try:
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            r = await self.db.execute(text("""
                UPDATE media_signed_links
                   SET status='used', used_at=now()
                 WHERE token = :token_hash
                   AND status = 'active'
                   AND expires_at > now()
                RETURNING media_id, purpose
            """), {"token_hash": token_hash})
            row = r.fetchone()
        except Exception:
            raise ServiceOSException("SIGNED_TOKEN_INVALID", "Invalid or expired token.")

        if not row:
            raise ServiceOSException("SIGNED_TOKEN_INVALID", "Invalid or expired token.")

        media_id, purpose = row
        return {"media_id": str(media_id), "purpose": purpose}

    # ── Archive / Restore ────────────────────────────────────────────────────

    async def archive_asset(self, media_id: uuid.UUID, reason: str | None = None) -> dict:
        asset = await self._load(media_id)
        if asset.status == "archived":
            return {"id": str(media_id), "status": "archived", "already_archived": True}

        asset.status = "archived"
        asset.archived_at = utcnow()
        asset.updated_at = utcnow()

        await self._log_audit(media_id, "admin_archived",
                              {"reason": reason, "file_name": asset.file_name_original})
        return {"id": str(media_id), "status": "archived"}

    async def restore_asset(self, media_id: uuid.UUID) -> dict:
        asset = await self._load_any(media_id)
        if asset.status not in ("archived", "quarantined"):
            raise ServiceOSException("MEDIA_INVALID_STATE",
                                     "Only archived or quarantined assets can be restored.")

        asset.status = "active"
        asset.archived_at = None
        asset.updated_at = utcnow()

        await self._log_audit(media_id, "admin_restored",
                              {"file_name": asset.file_name_original})
        return {"id": str(media_id), "status": "active"}

    # ── Delete ───────────────────────────────────────────────────────────────

    async def delete_asset(self, media_id: uuid.UUID, force: bool = False) -> dict:
        """Soft delete. Hard deletes are blocked if linked to protected modules."""
        asset = await self._load_any(media_id)
        if not force:
            links = await self.get_linked_records(media_id)
            active_protected = [
                l for l in links
                if l.get("status") == "active" and l.get("module_name") in PROTECTED_MODULES
            ]
            if active_protected:
                raise ServiceOSException(
                    "MEDIA_DELETE_BLOCKED",
                    f"File is linked to {len(active_protected)} active record(s). Archive first or use force=true.",
                )

        asset.status = "deleted"
        asset.deleted_at = utcnow()
        asset.updated_at = utcnow()

        await self._log_audit(media_id, "admin_deleted",
                              {"file_name": asset.file_name_original, "force": force})
        return {"id": str(media_id), "deleted": True}

    # ── Visibility ───────────────────────────────────────────────────────────

    async def change_visibility(self, media_id: uuid.UUID, is_public: bool) -> dict:
        asset = await self._load(media_id)
        old = asset.is_public
        asset.is_public = is_public
        asset.access_level = "public" if is_public else "tenant"
        asset.visibility = "public" if is_public else "private"
        asset.updated_at = utcnow()

        await self._log_audit(media_id, "admin_visibility_changed",
                              {"from": old, "to": is_public})
        return {"id": str(media_id), "is_public": is_public}

    # ── Flag / Quarantine / Clean ────────────────────────────────────────────

    async def flag_asset(self, media_id: uuid.UUID, reason: str) -> dict:
        asset = await self._load(media_id)
        asset.is_flagged = True
        asset.flag_reason = reason[:80]
        asset.flagged_at = utcnow()
        asset.moderation_status = "flagged"
        asset.updated_at = utcnow()

        await self._log_audit(media_id, "admin_flagged",
                              {"reason": reason, "file_name": asset.file_name_original})
        return {"id": str(media_id), "is_flagged": True, "flag_reason": reason}

    async def mark_clean(self, media_id: uuid.UUID) -> dict:
        asset = await self._load(media_id)
        asset.is_flagged = False
        asset.flag_reason = None
        asset.flagged_at = None
        asset.moderation_status = "clean"
        asset.updated_at = utcnow()

        await self._log_audit(media_id, "admin_marked_clean",
                              {"file_name": asset.file_name_original})
        return {"id": str(media_id), "is_flagged": False, "moderation_status": "clean"}

    async def quarantine_asset(self, media_id: uuid.UUID, reason: str) -> dict:
        asset = await self._load(media_id)
        asset.status = "quarantined"
        asset.is_flagged = True
        asset.flag_reason = reason[:80]
        asset.flagged_at = asset.flagged_at or utcnow()
        asset.moderation_status = "quarantined"
        asset.updated_at = utcnow()

        await self._log_audit(media_id, "admin_quarantined",
                              {"reason": reason, "file_name": asset.file_name_original})
        return {"id": str(media_id), "status": "quarantined", "reason": reason}

    # ── Bulk actions ─────────────────────────────────────────────────────────

    async def bulk_archive(self, media_ids: list[str]) -> dict:
        done, failed = [], []
        for mid_str in media_ids[:100]:
            try:
                mid = uuid.UUID(mid_str)
                await self.archive_asset(mid)
                done.append(mid_str)
            except Exception as e:
                failed.append({"id": mid_str, "error": str(e)})
        return {"archived": done, "failed": failed}

    async def bulk_delete(self, media_ids: list[str], force: bool = False) -> dict:
        done, failed = [], []
        for mid_str in media_ids[:100]:
            try:
                mid = uuid.UUID(mid_str)
                await self.delete_asset(mid, force=force)
                done.append(mid_str)
            except Exception as e:
                failed.append({"id": mid_str, "error": str(e)})
        return {"deleted": done, "failed": failed}

    # ── Export ───────────────────────────────────────────────────────────────

    async def export_csv(self, **filters) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "file_name", "context", "owner_type", "tenant_id", "status", "is_public", "is_flagged", "size_bytes", "created_at"])
        cursor = None
        exported = 0
        while exported < 50_000:
            result = await self.list_assets_admin(**filters, cursor=cursor, page=1, page_size=200)
            for item in result["items"]:
                writer.writerow([
                    item.get("id", ""), item.get("file_name_original", ""), item.get("media_context", ""),
                    item.get("owner_type", ""), item.get("tenant_id", "") or "", item.get("status", ""),
                    item.get("is_public", ""), item.get("is_flagged", ""), item.get("file_size_bytes", ""),
                    item.get("created_at", ""),
                ])
                exported += 1
            cursor = result.get("next_cursor")
            if not cursor:
                break
        return output.getvalue()

    # ── Storage summary ──────────────────────────────────────────────────────

    async def get_storage_summary(self) -> dict:
        r = await self.db.execute(
            select(
                MediaAsset.media_context,
                func.count().label("count"),
                func.sum(MediaAsset.file_size_bytes).label("total_bytes"),
            )
            .where(MediaAsset.status == "active")
            .group_by(MediaAsset.media_context)
            .order_by(func.sum(MediaAsset.file_size_bytes).desc())
        )
        rows = r.fetchall()
        breakdown = [
            {
                "context": row[0],
                "count": row[1],
                "total_bytes": row[2] or 0,
                "total_mb": round((row[2] or 0) / (1024 * 1024), 2),
            }
            for row in rows
        ]
        total_bytes = sum(b["total_bytes"] for b in breakdown)
        return {
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / (1024 * 1024), 2),
            "by_context": breakdown,
        }

    # ── Filter options ───────────────────────────────────────────────────────

    async def get_filter_options(self) -> dict:
        from app.engines.media.validation import CONTEXT_RULES
        ctx_r = await self.db.execute(
            select(MediaAsset.media_context, func.count())
            .where(MediaAsset.status != "deleted")
            .group_by(MediaAsset.media_context)
            .order_by(func.count().desc())
        )
        owner_r = await self.db.execute(
            select(MediaAsset.owner_type, func.count())
            .where(MediaAsset.status != "deleted")
            .group_by(MediaAsset.owner_type)
        )
        return {
            "contexts": [{"value": r[0], "count": r[1]} for r in ctx_r.fetchall()],
            "owner_types": [{"value": r[0], "count": r[1]} for r in owner_r.fetchall()],
            "statuses": ["active", "archived", "quarantined", "replaced", "deleted"],
            "file_types": ["image", "video", "application", "text"],
            "visibilities": ["public", "private"],
            "upload_contexts": [
                {
                    "value": context,
                    "max_mb": rules["max_mb"],
                    "allowed_types": sorted(rules["allowed_types"]),
                }
                for context, rules in sorted(CONTEXT_RULES.items())
            ],
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _load(self, media_id: uuid.UUID) -> MediaAsset:
        r = await self.db.execute(
            select(MediaAsset).where(
                MediaAsset.id == media_id,
                MediaAsset.deleted_at == None,  # noqa: E711
            )
        )
        asset = r.scalar_one_or_none()
        if not asset:
            raise NotFoundException("MediaAsset", str(media_id))
        return asset

    async def _load_any(self, media_id: uuid.UUID) -> MediaAsset:
        """Load including deleted (for restore operations)."""
        r = await self.db.execute(select(MediaAsset).where(MediaAsset.id == media_id))
        asset = r.scalar_one_or_none()
        if not asset:
            raise NotFoundException("MediaAsset", str(media_id))
        return asset

    async def _log_audit(self, media_id: uuid.UUID, action: str, meta: dict | None = None) -> None:
        try:
            async with self.db.begin_nested():
                await self.db.execute(
                    text("""
                        INSERT INTO media_audit_logs
                        (media_id, actor_user_id, actor_role, action_type, metadata_json)
                        VALUES (:mid, :uid, :role, :action, CAST(:meta AS jsonb))
                    """),
                    {
                        "mid":    str(media_id),
                        "uid":    self.actor.user_id,
                        "role":   self.actor.role,
                        "action": action,
                        "meta":   json.dumps(meta or {}, default=str),
                    },
                )
        except Exception:
            logger.exception("media.audit_log_failed", media_id=str(media_id), action=action)

    async def _insert_signed_link(
        self, media_id: uuid.UUID, token: str, expires_at: datetime, purpose: str
    ) -> None:
        try:
            async with self.db.begin_nested():
                await self.db.execute(
                    text("""
                        INSERT INTO media_signed_links
                        (media_id, created_by_user_id, purpose, token, expires_at, status)
                        VALUES (:mid, :uid, :purpose, :token, :expires, 'active')
                    """),
                    {
                        "mid":     str(media_id),
                        "uid":     self.actor.user_id,
                        "purpose": purpose,
                        "token":   hashlib.sha256(token.encode("utf-8")).hexdigest(),
                        "expires": expires_at,
                    },
                )
        except Exception as exc:
            logger.exception("media.signed_link_create_failed", media_id=str(media_id), purpose=purpose)
            raise ServiceOSException("SERVICE_UNAVAILABLE", "Secure media link could not be created.") from exc

    def _to_admin_dict(self, asset: MediaAsset) -> dict:
        d = asset.to_dict(view_url=f"/v1/media/{asset.id}/view")
        # Add enterprise fields (new columns from migration 085; safe getattr)
        d["is_flagged"]        = getattr(asset, "is_flagged", False) or False
        d["flag_reason"]       = getattr(asset, "flag_reason", None)
        d["moderation_status"] = getattr(asset, "moderation_status", "clean") or "clean"
        d["scan_status"]       = getattr(asset, "scan_status", "not_scanned") or "not_scanned"
        d["visibility"]        = "public" if asset.is_public else "private"
        d["description"]       = getattr(asset, "description", None)
        d["tags_json"]         = getattr(asset, "tags_json", []) or []
        d["linked_module"]     = getattr(asset, "linked_module", None)
        d["linked_record_id"]  = getattr(asset, "linked_record_id", None)
        archived_at            = getattr(asset, "archived_at", None)
        d["archived_at"]       = archived_at.isoformat() if archived_at else None
        d["flagged_at"]        = getattr(asset, "flagged_at", None)
        d["flagged_at"]        = d["flagged_at"].isoformat() if d["flagged_at"] else None
        d["upload_from_app"]   = getattr(asset, "uploaded_from_app", None)
        return d
