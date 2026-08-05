"""
Dependency: vertical_guard
Enforces business-vertical status at the API boundary. Never trusts a
client-supplied vertical_id -- every check resolves the vertical from the
caller's own trusted JWT-derived tenant_id (UserContext.tenant_id via
get_current_user), the same real auth mechanism every other router in this
codebase uses. (app.dependencies.tenant.get_tenant/TenantContext is a stale,
never-finished Phase-1 stub -- its own docstring says "Phase 2: replace with
JWT extraction" -- and was NOT used here for that reason, confirmed via live
testing where it resolved a hardcoded dummy tenant_id instead of the caller's
real one.)

require_vertical_enabled(vertical_key)      -> platform switch is on
require_tenant_vertical_active(vertical_key) -> AND this tenant's enrollment in
                                                  that vertical is status="active"
require_vertical_capability(vertical_key, capability) -> AND the vertical
                                                  declares that capability
require_vertical_not_active(vertical_key)   -> the INVERSE: this tenant has
                                                  NOT finished activating yet
"""
from typing import Callable

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.vertical_catalog.models import Vertical, TenantVerticalEnrollment
from app.exceptions import (
    VerticalDisabledException, TenantVerticalNotActiveException,
    VerticalCapabilityUnavailableException, VerticalAlreadyActiveException,
)


async def _load_vertical(db: AsyncSession, vertical_key: str) -> Vertical | None:
    return (await db.execute(select(Vertical).where(Vertical.key == vertical_key))).scalar_one_or_none()


def require_vertical_enabled(vertical_key: str) -> Callable:
    async def _guard(
        user: UserContext = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> UserContext:
        v = await _load_vertical(db, vertical_key)
        if not v or not v.is_enabled:
            raise VerticalDisabledException(vertical_key)
        return user

    _guard.__name__ = f"vertical_guard_{vertical_key}"
    return _guard


def require_tenant_vertical_active(vertical_key: str) -> Callable:
    """Platform vertical must be enabled AND this tenant's own enrollment in it
    must be 'active' -- resolved server-side from tenant_vertical_enrollments,
    keyed off the caller's own JWT tenant_id, never a client-supplied one."""
    async def _guard(
        user: UserContext = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> UserContext:
        if not user.tenant_id:
            raise TenantVerticalNotActiveException(vertical_key, "—", None)
        v = await _load_vertical(db, vertical_key)
        if not v or not v.is_enabled:
            raise VerticalDisabledException(vertical_key)
        enrollment = (await db.execute(
            select(TenantVerticalEnrollment).where(
                TenantVerticalEnrollment.tenant_id == user.tenant_id,
                TenantVerticalEnrollment.vertical_id == v.id,
            )
        )).scalar_one_or_none()
        if not enrollment or enrollment.status != "active":
            raise TenantVerticalNotActiveException(
                vertical_key, user.tenant_id,
                enrollment.status if enrollment else None,
            )
        return user

    _guard.__name__ = f"tenant_vertical_active_{vertical_key}"
    return _guard


def require_vertical_not_active(vertical_key: str) -> Callable:
    """The inverse of `require_tenant_vertical_active`: the caller must NOT be
    activated in this vertical yet.

    Real bug fixed here: this guard was imported by
    vertical_catalog/tenant_documents_router.py but never existed, so that
    module raised ImportError on import -- which is why the whole onboarding
    documents router could never be mounted and all of its routes 404'd.

    It guards ONBOARDING-only surfaces (submitting setup paperwork). Once a
    tenant is live, those endpoints must close: re-submitting onboarding
    documents against an active vertical is not an edit path, it is a way to
    put a live tenant back into a half-configured state.

    A missing enrollment counts as "not active" -- a tenant who has not
    enrolled yet is exactly who this surface is for.
    """
    async def _guard(
        user: UserContext = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> UserContext:
        if not user.tenant_id:
            # No tenant context at all -- nothing is active, so this
            # onboarding-only surface stays open.
            return user
        v = await _load_vertical(db, vertical_key)
        if not v or not v.is_enabled:
            raise VerticalDisabledException(vertical_key)
        enrollment = (await db.execute(
            select(TenantVerticalEnrollment).where(
                TenantVerticalEnrollment.tenant_id == user.tenant_id,
                TenantVerticalEnrollment.vertical_id == v.id,
            )
        )).scalar_one_or_none()
        if enrollment and enrollment.status == "active":
            raise VerticalAlreadyActiveException(vertical_key, user.tenant_id)
        return user

    _guard.__name__ = f"vertical_not_active_{vertical_key}"
    return _guard


def require_vertical_capability(vertical_key: str, capability: str) -> Callable:
    """All of: platform vertical enabled, tenant enrollment active, vertical
    declares the capability. Permission checks (require_permission) compose
    alongside this as a separate dependency -- this guard only resolves
    vertical/capability availability, not user role."""
    async def _guard(
        user: UserContext = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> UserContext:
        if not user.tenant_id:
            raise TenantVerticalNotActiveException(vertical_key, "—", None)
        v = await _load_vertical(db, vertical_key)
        if not v or not v.is_enabled:
            raise VerticalDisabledException(vertical_key)
        enrollment = (await db.execute(
            select(TenantVerticalEnrollment).where(
                TenantVerticalEnrollment.tenant_id == user.tenant_id,
                TenantVerticalEnrollment.vertical_id == v.id,
            )
        )).scalar_one_or_none()
        if not enrollment or enrollment.status != "active":
            raise TenantVerticalNotActiveException(
                vertical_key, user.tenant_id,
                enrollment.status if enrollment else None,
            )
        if capability not in (v.capabilities or []):
            raise VerticalCapabilityUnavailableException(vertical_key, capability)
        return user

    _guard.__name__ = f"vertical_capability_{vertical_key}_{capability}"
    return _guard
