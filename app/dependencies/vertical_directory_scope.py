"""VERTICAL-DIRECTORY-FRAMEWORK: the one central service-layer vertical
scope object every directory service must require. Router-level checks
alone are insufficient (mission spec) -- this is resolved once per request
and passed into every directory service call so internal callers cannot
accidentally bypass vertical scoping.

Permission model: colon-delimited, matching this codebase's existing
wildcard convention (`app/core/permissions.py::PermissionChecker.has` --
"field_ops:*" style engine wildcards), NOT a second permission syntax.
`f"{vertical_key}:{domain}:{action}"` (e.g. "home_services:providers:view")
resolves for free against any role holding "home_services:*" or
"home_services:providers:*" -- no new permission constant needs to be
registered per vertical, satisfying "apply to every future Business
Vertical without hardcoding vertical names."
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import permission_checker
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.vertical_catalog.models import Vertical
from app.exceptions import ServiceOSException, VerticalDisabledException


@dataclass
class VerticalScope:
    vertical: Vertical
    vertical_key: str
    domain: str
    actor: UserContext
    tenant_restriction: uuid.UUID | None = None


def _url_slug_to_key(slug: str) -> str:
    """URL segments use hyphens ("home-services"); vertical.key uses
    underscores ("home_services") -- the one place this translation
    happens, never re-derived ad hoc elsewhere."""
    return slug.replace("-", "_")


async def _resolve_vertical(db: AsyncSession, vertical_slug: str) -> Vertical:
    key = _url_slug_to_key(vertical_slug)
    v = (await db.execute(select(Vertical).where(Vertical.key == key))).scalar_one_or_none()
    if not v:
        raise ServiceOSException("NOT_FOUND", f"Business Vertical '{vertical_slug}' not found", status_code=404)
    return v


def require_vertical_domain_scope(domain: str, action: str = "view"):
    """FastAPI dependency factory. `domain` is one of
    providers|staff|customers|complaints. Resolves and validates, in order:
    1. The exact Business Vertical (server-side, from the route path only --
       never a client-supplied vertical id in the body/query).
    2. Vertical enabled status (fails closed with VERTICAL_DISABLED).
    3. User permission for {vertical_key}:{domain}:{action}.
    Returns a VerticalScope every directory service call must be given."""

    async def _dep(
        vertical: str = Path(...),
        db: AsyncSession = Depends(get_db),
        user: UserContext = Depends(get_current_user),
    ) -> VerticalScope:
        v = await _resolve_vertical(db, vertical)
        if not v.is_enabled:
            raise VerticalDisabledException(v.key)
        permission = f"{v.key}:{domain}:{action}"
        if not permission_checker.has(role=user.role, permission=permission,
                                      overrides=getattr(user, "permission_overrides", None)):
            raise ServiceOSException("PERMISSION_DENIED",
                                     f"Missing permission '{permission}'.", status_code=403)
        return VerticalScope(vertical=v, vertical_key=v.key, domain=domain, actor=user)

    return _dep
