"""Customer Users Enterprise Upgrade — CustomerAdminService.

Composes existing engines rather than duplicating tables:
  - Sessions/login hist. -> app.engines.security.admin_service.SecurityAdminService
                            (queries auth.UserSession/auth.LoginEvent generically)
  - Block/suspend        -> app.engines.auth.service.AuthService.lock_user/unlock_user/
                            suspend_user/unsuspend_user (Phase 0E infra, reused as-is)
  - DPDP/privacy         -> app.engines.compliance.enterprise_service.ComplianceEnterpriseService
  - Addresses            -> app.engines.serviceability.models.CustomerAddress (direct query)
  - Audit trail          -> app.core.audit.record_platform_audit (PlatformAuditLog)
"""
from __future__ import annotations
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_platform_audit
from app.dependencies.auth import UserContext
from app.engines.auth.models import User
from app.engines.auth.service import AuthService
from app.engines.compliance.enterprise_service import ComplianceEnterpriseService
from app.engines.security.admin_service import SecurityAdminService
from app.engines.serviceability.models import CustomerAddress
from app.exceptions import NotFoundException


class CustomerAdminService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None,
                 actor_role: str | None = None,
                 actor_ip: str | None = None):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.actor_ip = actor_ip

    async def _get_customer(self, customer_id: uuid.UUID) -> User:
        r = await self.db.execute(select(User).where(
            User.id == customer_id, User.role == "customer"))
        u = r.scalar_one_or_none()
        if not u:
            raise NotFoundException("Customer", str(customer_id))
        return u

    async def _audit(self, operation: str, customer_id: uuid.UUID,
                      before: dict | None = None, after: dict | None = None) -> None:
        await record_platform_audit(
            self.db, operation=operation, engine_id="customers",
            entity_id=str(customer_id), entity_type="customer",
            actor_id=self.actor_id, actor_role=self.actor_role, actor_ip=self.actor_ip,
            request_id=self.request_id, before=before, after=after,
        )

    # ─────────────────────────────────────────────────────────────────────
    # ADDRESSES
    # ─────────────────────────────────────────────────────────────────────

    async def list_addresses(self, customer_id: uuid.UUID) -> dict:
        await self._get_customer(customer_id)
        r = await self.db.execute(select(CustomerAddress).where(
            CustomerAddress.customer_id == customer_id
        ).order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc()))
        rows = r.scalars().all()
        await self._audit("customer.address_viewed", customer_id)
        return {"addresses": [{
            "id": str(a.id), "name": a.name, "phone": a.phone,
            "address_line_1": a.address_line_1, "address_line_2": a.address_line_2,
            "landmark": a.landmark, "city": a.city, "district": a.district,
            "state": a.state, "country": a.country, "zipcode": a.zipcode,
            "is_default": a.is_default, "is_active": a.is_active,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        } for a in rows], "total": len(rows)}

    # ─────────────────────────────────────────────────────────────────────
    # SESSIONS / LOGIN HISTORY
    # ─────────────────────────────────────────────────────────────────────

    async def list_sessions(self, customer_id: uuid.UUID) -> dict:
        await self._get_customer(customer_id)
        sec = SecurityAdminService(self.db, self.request_id, self.actor_id,
                                    self.actor_role, self.actor_ip)
        return await sec.list_sessions(tenant_id=None, role="customer", active_only=False,
                                        search=None, limit=100, cursor=None)

    async def list_login_history(self, customer_id: uuid.UUID) -> dict:
        customer = await self._get_customer(customer_id)
        sec = SecurityAdminService(self.db, self.request_id, self.actor_id,
                                    self.actor_role, self.actor_ip)
        from app.engines.auth.models import LoginEvent
        r = await self.db.execute(select(LoginEvent).where(
            LoginEvent.user_id == customer.id
        ).order_by(LoginEvent.created_at.desc()).limit(50))
        events = r.scalars().all()
        return {"login_history": [{
            "event_type": e.event_type, "ip_address": e.ip_address,
            "failure_reason": e.failure_reason, "device_id": e.device_id,
            "request_id": e.request_id, "created_at": e.created_at.isoformat(),
        } for e in events]}

    async def revoke_all_sessions(self, customer_id: uuid.UUID, reason: str) -> dict:
        await self._get_customer(customer_id)
        sec = SecurityAdminService(self.db, self.request_id, self.actor_id,
                                    self.actor_role, self.actor_ip)
        result = await sec.revoke_all_user_sessions(customer_id, reason)
        await self._audit("customer.sessions_revoked", customer_id, after={"reason": reason})
        return result

    # ─────────────────────────────────────────────────────────────────────
    # PRIVACY / DPDP
    # ─────────────────────────────────────────────────────────────────────

    async def list_privacy_requests(self, customer_id: uuid.UUID) -> dict:
        await self._get_customer(customer_id)
        svc = ComplianceEnterpriseService(self.db, self.request_id, self.actor_id, self.actor_role)
        return await svc.list_requests(subject_id=customer_id, page=1, limit=50)

    # ─────────────────────────────────────────────────────────────────────
    # AUDIT LOGS
    # ─────────────────────────────────────────────────────────────────────

    async def list_audit_logs(self, customer_id: uuid.UUID) -> dict:
        await self._get_customer(customer_id)
        from app.engines.security.models import PlatformAuditLog
        r = await self.db.execute(select(PlatformAuditLog).where(
            PlatformAuditLog.entity_id == str(customer_id),
            PlatformAuditLog.engine_id == "customers",
        ).order_by(PlatformAuditLog.created_at.desc()).limit(50))
        rows = r.scalars().all()
        return {"audit_logs": [{
            "log_id": str(a.id), "operation": a.operation, "actor_role": a.actor_role,
            "actor_ip": a.actor_ip, "is_high_risk": a.is_high_risk,
            "before_state": a.before_state, "after_state": a.after_state,
            "created_at": a.created_at.isoformat(),
        } for a in rows]}

    # ─────────────────────────────────────────────────────────────────────
    # ACCOUNT ACTIONS — reuse AuthService's Phase 0E lock/deactivate infra
    # ─────────────────────────────────────────────────────────────────────

    def _admin_ctx(self) -> UserContext:
        return UserContext(
            user_id=str(self.actor_id), email="", role=self.actor_role or "super_admin",
            tenant_id=None, full_name="", is_verified=True,
        )

    async def block_customer(self, customer_id: uuid.UUID, reason: str) -> dict:
        await self._get_customer(customer_id)
        auth = AuthService(self.db, self.request_id)
        result = await auth.lock_user(self._admin_ctx(), customer_id, reason, None, revoke_sessions=True)
        await self._audit("customer.blocked", customer_id, after={"reason": reason})
        return result

    async def unblock_customer(self, customer_id: uuid.UUID, reason: str) -> dict:
        await self._get_customer(customer_id)
        auth = AuthService(self.db, self.request_id)
        result = await auth.unlock_user(self._admin_ctx(), customer_id, reason)
        await self._audit("customer.unblocked", customer_id, after={"reason": reason})
        return result

    async def suspend_customer(self, customer_id: uuid.UUID, reason: str) -> dict:
        await self._get_customer(customer_id)
        auth = AuthService(self.db, self.request_id)
        result = await auth.suspend_user(self._admin_ctx(), customer_id, reason, revoke_sessions=True)
        await self._audit("customer.suspended", customer_id, after={"reason": reason})
        return result

    async def reactivate_customer(self, customer_id: uuid.UUID, reason: str) -> dict:
        await self._get_customer(customer_id)
        auth = AuthService(self.db, self.request_id)
        result = await auth.unsuspend_user(self._admin_ctx(), customer_id, reason)
        await self._audit("customer.reactivated", customer_id, after={"reason": reason})
        return result
