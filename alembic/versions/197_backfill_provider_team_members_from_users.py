"""TEAM-DIRECTORY: backfill provider_team_members from real technician/staff Users.

Audit finding (FINAL-L5-05C/05V, confirmed live): every real technician is an
auth.users row (role IN ('technician','staff')) with tenant_id set --
provider_team_members has 0 rows in production/demo. Every eligibility path
already prefers ProviderTeamMember and only falls back to User when it finds
none (home_service_assignment/service.py, dispatch_service.py), and the
readiness/coverage engine (team_readiness_service.py) reads ONLY
ProviderTeamMember. Backfilling one ProviderTeamMember row per existing
technician/staff User (linked via user_id) makes ProviderTeamMember the real,
populated primary record going forward -- no code path needs to change,
since the fallback logic was written to prefer it the moment rows exist.

Idempotent: skips any User that already has a linked, non-deleted
ProviderTeamMember row (matched on user_id).

Revision ID: 197
Revises: 196
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "197"
down_revision = "196"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    already_linked = {
        row[0] for row in conn.execute(sa.text(
            "SELECT user_id FROM provider_team_members "
            "WHERE user_id IS NOT NULL AND deleted_at IS NULL"
        )).fetchall()
    }

    users = conn.execute(sa.text(
        "SELECT id, tenant_id, full_name, phone, email, role, is_active "
        "FROM users WHERE tenant_id IS NOT NULL AND role IN ('technician', 'staff') "
        "AND deleted_at IS NULL"
    )).fetchall()

    for u in users:
        if u.id in already_linked:
            continue
        tenant_row = conn.execute(
            sa.text("SELECT category_id FROM tenants WHERE id=:tid"), {"tid": str(u.tenant_id)}
        ).fetchone()
        cat_id = str(tenant_row.category_id) if tenant_row and tenant_row.category_id else None
        conn.execute(sa.text("""
            INSERT INTO provider_team_members
                (id, tenant_id, category_id, user_id, member_type, full_name, phone, email,
                 designation, status, can_receive_assignment, skills, supported_offering_ids,
                 supported_type_ids, supported_brand_ids, service_area_ids,
                 username, password_generated, created_at, updated_at)
            VALUES
                (:id, :tid, :cat_id, :uid, :member_type, :full_name, :phone, :email,
                 :designation, :status, true, '[]'::jsonb, '[]'::jsonb,
                 '[]'::jsonb, '[]'::jsonb, '[]'::jsonb,
                 :username, false, now(), now())
        """), {
            "id": str(uuid.uuid4()), "tid": str(u.tenant_id), "cat_id": cat_id, "uid": str(u.id),
            "member_type": u.role, "full_name": u.full_name or "", "phone": u.phone, "email": u.email,
            "designation": u.role, "status": "active" if u.is_active else "inactive",
            "username": u.email or u.phone,
        })


def downgrade() -> None:
    # Data backfill only -- removing these rows would destroy any capability/
    # availability configuration a tenant has since added on top of them, so
    # downgrade is intentionally a no-op rather than deleting live data.
    pass
