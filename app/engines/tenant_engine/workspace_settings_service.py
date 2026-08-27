"""Home Services Workspace Settings -- Phase 1: General tab composed read/write.

Reuses canonical sources instead of inventing a new settings store:
- Workspace identity: Tenant (tenant_engine/models.py)
- Regional prefs: TenantSettings (timezone/currency/language, real columns) +
  Tenant.meta JSONB for date_format/time_format/measurement_system (same
  additive-JSON pattern app.engines.profile already uses for
  website_url/description -- no migration needed for Phase 1).
- Business hours: read-only projection of provider_availability_rules
  (scope_type='provider', scope_id NULL) -- the SAME table and rows the
  existing /v1/provider/availability endpoints already own; editing stays
  on that canonical endpoint rather than being duplicated here.
- Controlled policy section: real, already-documented constants
  and honest
  static descriptions of scattered-but-real backend behavior (matching
  policy, workflow gate, direct-payment model) -- never fabricated numbers.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_platform_audit
from app.dependencies.auth import UserContext
from app.engines.tenant_engine.models import Tenant, TenantSettings
from app.exceptions import NotFoundException, ServiceOSException

DOW_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

# Tenant-editable regional fields kept in Tenant.meta (no schema migration
# needed for Phase 1 -- same pattern app.engines.profile uses for
# website_url/description).
_META_REGIONAL_FIELDS = ("date_format", "time_format", "measurement_system")
_META_DEFAULTS = {"date_format": "DD MMM YYYY", "time_format": "12-hour", "measurement_system": "Metric"}


def _field(key: str, label: str, value, *, ownership: str, editable: bool, source: str,
           help_text: str = "", version: str | None = None) -> dict:
    return {
        "key": key, "label": label, "value": value, "effective_value": value,
        "ownership": ownership, "editable": editable, "source": source,
        "help_text": help_text, "version": version,
    }


class WorkspaceSettingsService:
    def __init__(self, db: AsyncSession, actor: UserContext):
        self.db = db
        self.actor = actor

    async def _load_tenant(self) -> Tenant:
        if not self.actor.tenant_id:
            raise ServiceOSException("TENANT_ACCESS_DENIED", "No tenant context in token.")
        r = await self.db.execute(select(Tenant).where(Tenant.id == uuid.UUID(self.actor.tenant_id)))
        tenant = r.scalar_one_or_none()
        if not tenant:
            raise NotFoundException("Tenant", self.actor.tenant_id)
        return tenant

    async def _load_or_create_settings(self, tenant_id: uuid.UUID) -> TenantSettings:
        r = await self.db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant_id))
        row = r.scalar_one_or_none()
        if row:
            return row
        row = TenantSettings(tenant_id=tenant_id)
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_general(self) -> dict:
        tenant = await self._load_tenant()
        settings = await self._load_or_create_settings(tenant.id)
        meta = tenant.meta or {}

        business_hours_rows = (await self.db.execute(text(
            "SELECT day_of_week, start_time, end_time, is_active, updated_at "
            "FROM provider_availability_rules "
            "WHERE tenant_id=:tid AND scope_type='provider' AND scope_id IS NULL "
            "ORDER BY day_of_week"
        ), {"tid": str(tenant.id)})).fetchall()
        by_dow = {r.day_of_week: r for r in business_hours_rows}
        business_hours = []
        for dow in range(7):
            row = by_dow.get(dow)
            business_hours.append({
                "day": DOW_LABELS[dow], "day_of_week": dow,
                "is_open": bool(row and row.is_active),
                "start_time": str(row.start_time)[:5] if row and row.start_time else None,
                "end_time": str(row.end_time)[:5] if row and row.end_time else None,
            })

        technicians_count = (await self.db.execute(text(
            "SELECT COUNT(*) FROM provider_team_members WHERE tenant_id=:tid AND status='active' AND deleted_at IS NULL"
        ), {"tid": str(tenant.id)})).scalar_one()

        identity = [
            _field("workspace_name", "Workspace name", tenant.business_name,
                   ownership="TENANT_CONTROLLED", editable=True, source="Tenant.business_name",
                   help_text="Editing your verified business name is handled in Business Profile and may require a change request."),
            _field("workspace_code", "Workspace code", tenant.tenant_code,
                   ownership="SERVICEOS_CONTROLLED", editable=False, source="Tenant.tenant_code"),
            _field("default_vertical", "Default vertical", "Home Services" if tenant.vertical == "home_services" else tenant.vertical,
                   ownership="ADMIN_POLICY", editable=False, source="Tenant.vertical",
                   help_text="Set at enrollment. Changing verticals is an admin-reviewed process."),
            _field("workspace_status", "Workspace status", tenant.status,
                   ownership="DERIVED_READ_ONLY", editable=False, source="Tenant.status"),
        ]

        regional = [
            _field("timezone", "Time zone", settings.timezone,
                   ownership="TENANT_CONTROLLED", editable=True, source="TenantSettings.timezone"),
            _field("date_format", "Date format", meta.get("date_format", _META_DEFAULTS["date_format"]),
                   ownership="TENANT_CONTROLLED", editable=True, source="Tenant.meta.date_format"),
            _field("time_format", "Time format", meta.get("time_format", _META_DEFAULTS["time_format"]),
                   ownership="TENANT_CONTROLLED", editable=True, source="Tenant.meta.time_format"),
            _field("measurement_system", "Measurement system", meta.get("measurement_system", _META_DEFAULTS["measurement_system"]),
                   ownership="TENANT_CONTROLLED", editable=True, source="Tenant.meta.measurement_system"),
            _field("currency", "Currency", settings.currency,
                   ownership="ADMIN_POLICY", editable=False, source="TenantSettings.currency",
                   help_text="Locked by vertical policy."),
            _field("primary_language", "Primary language", "English",
                   ownership="TENANT_CONTROLLED", editable=False, source="TenantSettings.language",
                   help_text="Only English is currently supported for operational UI; customer-chat language is separate."),
        ]

        controlled_policy = [
            {
                "key": "provider_matching", "label": "Provider matching", "ownership": "SERVICEOS_CONTROLLED",
                "effective_value": "ServiceOS-matched",
                "explanation": "ServiceOS selects the eligible provider for each customer request. Customers do not manually choose providers.",
                "policy_version": None, "effective_date": None, "link": None,
            },
            {
                "key": "job_workflow", "label": "Job workflow", "ownership": "SERVICEOS_CONTROLLED",
                "effective_value": "Inspection + customer-approved estimate required",
                "explanation": "Repair jobs require inspection and a customer-approved estimate before work starts.",
                "policy_version": None, "effective_date": None, "link": None,
            },
            {
                "key": "payment_model", "label": "Payment model", "ownership": "SERVICEOS_CONTROLLED",
                "effective_value": "Customer pays provider directly",
                "explanation": "Customer pays the provider directly. ServiceOS records confirmations and exceptions only.",
                "policy_version": None, "effective_date": None, "link": "/finance",
            },
            {
                # Replaced the security deposit in migration 317: headcount is
                # bought as seats rather than collateralised.
                "key": "technician_seats", "label": "Technician seats", "ownership": "ADMIN_POLICY",
                "effective_value": "Purchased with a top-up plan",
                "explanation": "Each seat lets you add one technician, and one more job can be booked per slot.",
                "policy_version": "v1", "effective_date": None, "link": "/finance/topups",
            },
        ]

        return {
            "identity": identity,
            "regional": regional,
            "business_hours": business_hours,
            "business_hours_note": "These are default business hours. Technician availability and capacity are managed separately.",
            "controlled_policy": controlled_policy,
            "operational_summary": {"active_technicians": technicians_count},
            "workspace_status": tenant.status,
            "configuration_version": tenant.updated_at.isoformat() if tenant.updated_at else None,
            "last_updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None,
        }

    async def update_general(self, payload: dict, expected_version: str | None) -> dict:
        tenant = await self._load_tenant()

        if expected_version and tenant.updated_at and tenant.updated_at.isoformat() != expected_version:
            raise ServiceOSException(
                "SETTINGS_VERSION_STALE",
                "Workspace settings were changed by someone else since you loaded this page. Reload and try again.",
                status_code=409,
            )

        settings = await self._load_or_create_settings(tenant.id)
        changed: dict[str, object] = {}

        if "workspace_name" in payload and payload["workspace_name"] != tenant.business_name:
            tenant.business_name = payload["workspace_name"]
            changed["workspace_name"] = payload["workspace_name"]
        if "timezone" in payload and payload["timezone"] != settings.timezone:
            settings.timezone = payload["timezone"]
            changed["timezone"] = payload["timezone"]

        meta = dict(tenant.meta or {})
        for field in _META_REGIONAL_FIELDS:
            if field in payload and payload[field] != meta.get(field):
                meta[field] = payload[field]
                changed[field] = payload[field]
        if changed:
            tenant.meta = meta
            tenant.updated_at = datetime.now(timezone.utc)

        if changed:
            await record_platform_audit(
                self.db, operation="workspace_settings.updated", engine_id="tenant_engine",
                entity_id=str(tenant.id), entity_type="tenant",
                actor_id=uuid.UUID(self.actor.user_id), actor_role=self.actor.role,
                tenant_id=tenant.id, after={"changed_fields": changed},
            )

        return await self.get_general()

    # ── Team & Access (Phase 2) ──────────────────────────────────────────────
    async def get_team_access(self) -> dict:
        tenant = await self._load_tenant()

        owner_row = None
        if tenant.owner_user_id:
            owner_row = (await self.db.execute(text(
                "SELECT id, full_name, email FROM users WHERE id=:uid"
            ), {"uid": str(tenant.owner_user_id)})).fetchone()

        staff_rows = (await self.db.execute(text(
            "SELECT id, full_name, member_type, status, email, phone FROM provider_team_members "
            "WHERE tenant_id=:tid AND deleted_at IS NULL ORDER BY full_name"
        ), {"tid": str(tenant.id)})).fetchall()

        by_type: dict[str, list] = {"manager": [], "staff": [], "technician": []}
        for row in staff_rows:
            if row.status == "active" and row.member_type in by_type:
                by_type[row.member_type].append({"id": str(row.id), "full_name": row.full_name})

        return {
            "owner": {"id": str(owner_row.id), "full_name": owner_row.full_name, "email": owner_row.email} if owner_row else None,
            "active_managers": by_type["manager"],
            "active_staff": by_type["staff"],
            "active_technicians": by_type["technician"],
            "pending_invitations": [],
            "pending_invitations_note": "Pending-invitation tracking doesn't exist on the backend yet -- always empty, not fabricated.",
            "team_directory_link": "/provider/staff",
        }

    # ── Activity & Audit (Phase 2) -- real platform_audit_logs projection ────
    async def get_activity(self, limit: int = 30) -> dict:
        tenant = await self._load_tenant()

        rows = (await self.db.execute(text(
            "SELECT pal.id, pal.operation, pal.engine_id, pal.entity_type, pal.actor_id, pal.actor_role, "
            "pal.before_state, pal.after_state, pal.created_at, u.full_name AS actor_name "
            "FROM platform_audit_logs pal LEFT JOIN users u ON u.id = pal.actor_id "
            "WHERE pal.tenant_id=:tid AND pal.engine_id IN ('tenant_engine','profile') "
            "ORDER BY pal.created_at DESC LIMIT :lim"
        ), {"tid": str(tenant.id), "lim": limit})).fetchall()

        def _safe_summary(state: dict | None) -> dict | None:
            if not state:
                return None
            # Never surface secrets/raw documents in audit payloads.
            return {k: v for k, v in state.items() if k not in ("hashed_password", "raw_key", "secret")}

        items = [{
            "id": str(r.id),
            "operation": r.operation,
            "engine_id": r.engine_id,
            "entity_type": r.entity_type,
            "actor_name": r.actor_name or "System",
            "actor_role": r.actor_role,
            "before": _safe_summary(r.before_state),
            "after": _safe_summary(r.after_state),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in rows]

        return {"items": items}
