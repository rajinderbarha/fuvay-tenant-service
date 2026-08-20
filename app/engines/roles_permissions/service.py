"""Phase 1B — Roles & Permissions read service.

ServiceOS's RBAC is code-based (app/core/permissions.py::ROLE_PERMISSIONS,
class P), not a DB-table CRUD system. This service does NOT introduce a
parallel roles/permissions table — it exposes the real, authoritative
code-defined roles/permissions as read data, enriched with live counts
(assigned users) from the `users` table, so the admin UI has something real
to render instead of nothing.

The ticket names 10 roles; only 6 actually exist in ROLE_PERMISSIONS
(super_admin, tenant_owner, staff, technician, customer, guest). The other
4 named roles (platform_admin, finance_admin, operations_admin,
support_admin, compliance_officer) plus tenant_manager are surfaced with
is_implemented=false rather than fabricated — this is intentionally honest,
not a bug.
"""
from __future__ import annotations
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, ROLE_PERMISSIONS

# Ticket's 10 required roles, in order. Roles present in ROLE_PERMISSIONS are
# "implemented"; the rest are documented gaps (see PHASE_1B_ROLES_UI_REPORT.md).
REQUIRED_ROLE_ORDER = [
    "super_admin", "admin_operations", "admin_finance", "admin_security",
    "admin_readonly", "tenant_owner", "staff", "technician", "customer", "guest",
]
ROLE_LABELS = {
    "super_admin": "Platform Super Admin",
    "admin_operations": "Operations Admin",
    "admin_finance": "Finance Admin",
    "admin_security": "Security Admin",
    "admin_readonly": "Admin Read Only",
    "tenant_owner": "Tenant Owner",
    "staff": "Staff",
    "technician": "Technician",
    "customer": "Customer",
    "guest": "Guest",
}
ROLE_SCOPE = {
    "super_admin": "platform",
    "admin_operations": "platform",
    "admin_finance": "platform",
    "admin_security": "platform",
    "admin_readonly": "platform",
    "tenant_owner": "tenant",
    "staff": "tenant",
    "technician": "tenant",
    "customer": "customer",
    "guest": "public",
}
SYSTEM_ROLES = set(ROLE_PERMISSIONS.keys())


def _permission_count(role: str) -> int:
    perms = ROLE_PERMISSIONS.get(role, [])
    if P.ALL in perms:
        return len([n for n in dir(P) if not n.startswith("_") and n != "ALL"])
    return len(perms)


async def list_roles(db: AsyncSession) -> dict:
    # Real user counts per role, all in one query
    rows = (await db.execute(text(
        "SELECT role, count(*) FROM users WHERE deleted_at IS NULL GROUP BY role"))).all()
    user_counts = {r: c for r, c in rows}

    items = []
    all_role_keys = list(dict.fromkeys(REQUIRED_ROLE_ORDER + list(ROLE_PERMISSIONS.keys())))
    for role in all_role_keys:
        implemented = role in ROLE_PERMISSIONS
        items.append({
            "role_id": role,
            "role_key": role,
            "label": ROLE_LABELS.get(role, role.replace("_", " ").title()),
            "type": "system" if role in SYSTEM_ROLES else "custom",
            "scope": ROLE_SCOPE.get(role, "unknown"),
            "is_implemented": implemented,
            "is_active": implemented,
            "user_count": user_counts.get(role, 0),
            "permission_count": _permission_count(role) if implemented else 0,
            "updated_at": None,
        })

    total = len(items)
    system_count = sum(1 for i in items if i["type"] == "system")
    custom_count = total - system_count
    active_count = sum(1 for i in items if i["is_active"])
    total_users_assigned = sum(i["user_count"] for i in items)
    permission_gaps = sum(1 for i in items if not i["is_implemented"])

    return {
        "items": items,
        "summary": {
            "total_roles": total, "system_roles": system_count,
            "custom_roles": custom_count, "active_roles": active_count,
            "users_assigned": total_users_assigned, "permission_gaps": permission_gaps,
        },
    }


async def get_role_detail(db: AsyncSession, role_key: str) -> dict:
    implemented = role_key in ROLE_PERMISSIONS
    perms = ROLE_PERMISSIONS.get(role_key, [])
    if P.ALL in perms:
        perm_list = ["* (all permissions — super_admin wildcard)"]
    else:
        perm_list = sorted(perms)

    rows = (await db.execute(text(
        "SELECT id, email, full_name, is_active, created_at FROM users "
        "WHERE role = :role AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 100"),
        {"role": role_key})).mappings().all()
    assigned_users = [{
        "id": str(r["id"]), "email": r["email"], "full_name": r["full_name"],
        "is_active": r["is_active"],
        "created_at": r["created_at"].isoformat() if r["created_at"] else None,
    } for r in rows]

    return {
        "role_id": role_key, "role_key": role_key,
        "label": ROLE_LABELS.get(role_key, role_key.replace("_", " ").title()),
        "type": "system" if role_key in SYSTEM_ROLES else "custom",
        "scope": ROLE_SCOPE.get(role_key, "unknown"),
        "is_implemented": implemented,
        "permissions": perm_list,
        "permission_count": _permission_count(role_key) if implemented else 0,
        "assigned_users": assigned_users,
        "assigned_user_count": len(assigned_users),
    }


# ── Permissions ──────────────────────────────────────────────────────────────

MODULE_KEYWORDS = [
    ("AUTH", "Auth / IAM"), ("SETTINGS", "Platform Settings"),
    ("DASHBOARD", "Dashboard"), ("NAVIGATION", "Navigation"),
    ("ENGINES", "Engines"), ("VERTICALS", "Verticals"),
    ("USERS", "Users & Roles"), ("CATALOG", "Catalog"),
    ("PRICING", "Pricing"), ("TENANT", "Tenant"),
    ("BOOKING", "Booking"), ("PAYMENT", "Finance"),
    ("FINANCE", "Finance"), ("AUDIT", "Audit"),
    ("COMPLIANCE", "Compliance"), ("FIELD_OPS", "Field Ops"),
    ("STAFF", "Users & Roles"), ("CUSTOMER", "Tenant"),
    ("REVIEW", "Catalog"), ("CHAT", "Catalog"),
    ("NOTIFICATION", "Platform Settings"), ("ANALYTICS", "Dashboard"),
    ("RAG", "Catalog"), ("INVENTORY", "Catalog"),
    ("SERVICEABILITY", "Catalog"),
]


def _classify_module(const_name: str) -> str:
    for kw, label in MODULE_KEYWORDS:
        if const_name.startswith(kw):
            return label
    return "Other"


def _classify_risk(const_name: str) -> str:
    high_risk_markers = ("DELETE", "SUSPEND", "TERMINATE", "REVOKE", "ERASURE",
                          "SECURITY", "LOCK", "DEACTIVATE", "EXPORT")
    if any(m in const_name for m in high_risk_markers):
        return "high"
    if "UPDATE" in const_name or "WRITE" in const_name or "MANAGE" in const_name or "CREATE" in const_name:
        return "medium"
    return "low"


def _app_scope(const_name: str) -> str:
    if const_name.startswith(("TENANT", "STAFF", "FIELD_OPS")):
        return "tenant"
    if const_name.startswith("CUSTOMER"):
        return "customer"
    return "admin"


def list_permissions(module: str | None = None, app_scope: str | None = None,
                      risk_level: str | None = None, search: str | None = None,
                      page: int = 1, limit: int = 50,
                      paginate: bool = True) -> dict:
    items = []
    for name in sorted(dir(P)):
        if name.startswith("_"):
            continue
        value = getattr(P, name)
        if not isinstance(value, str):
            continue
        mod = _classify_module(name)
        scope = _app_scope(name)
        risk = _classify_risk(name)
        if module and mod != module:
            continue
        if app_scope and scope != app_scope:
            continue
        if risk_level and risk != risk_level:
            continue
        if search and search.lower() not in name.lower() and search.lower() not in value.lower():
            continue
        # A role is "assigned" this permission if it's explicitly listed, or the
        # role has the P.ALL wildcard (super_admin implicitly has everything).
        assigned_roles = sorted(
            role for role, perms in ROLE_PERMISSIONS.items()
            if value in perms or P.ALL in perms
        )
        items.append({
            "permission_key": value, "constant_name": name,
            "module": mod, "app_scope": scope, "risk_level": risk,
            "description": name.replace("_", " ").title(),
            "assigned_roles": assigned_roles,
            "assigned_role_count": len(assigned_roles),
            "status": "active",
        })

    total = len(items)
    admin_count = sum(1 for i in items if i["app_scope"] == "admin")
    tenant_count = sum(1 for i in items if i["app_scope"] == "tenant")
    customer_count = sum(1 for i in items if i["app_scope"] == "customer")
    high_risk_count = sum(1 for i in items if i["risk_level"] == "high")
    unassigned_count = sum(1 for i in items if i["assigned_role_count"] == 0)

    safe_page = max(1, page)
    safe_limit = min(200, max(1, limit))
    start = (safe_page - 1) * safe_limit
    page_items = items[start:start + safe_limit] if paginate else items

    return {
        "items": page_items,
        "summary": {
            "total_permissions": total, "admin_permissions": admin_count,
            "tenant_permissions": tenant_count, "customer_permissions": customer_count,
            "high_risk_permissions": high_risk_count, "unassigned_permissions": unassigned_count,
        },
        "meta": {
            "total": total,
            "page": safe_page,
            "limit": safe_limit,
            "total_pages": max(1, (total + safe_limit - 1) // safe_limit),
        },
    }


def list_permissions_grouped(**filters) -> dict:
    result = list_permissions(**filters, paginate=False)
    grouped: dict[str, list[dict]] = {}
    for item in result["items"]:
        grouped.setdefault(item["module"], []).append(item)
    return {"groups": [{"module": k, "items": v, "count": len(v)} for k, v in sorted(grouped.items())],
            "summary": result["summary"]}
