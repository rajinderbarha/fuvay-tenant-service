"""Phase 2A Slice 2C — CHECK constraint restricting users.role to the 10
canonical RBAC roles enforced by app.core.permissions.ROLE_PERMISSIONS.

users.role was a plain VARCHAR(30) with no DB-level constraint at all (no
CHECK, no enum, no FK) — confirmed by direct information_schema/pg_constraint
inspection during this slice's investigation. Nothing else in the schema
legitimately stores a non-canonical value in this specific column: unlike
the several unrelated columns found to share role-sounding vocabulary
(NotificationTemplate.audience, ServiceChecklistItem.owner_role,
ComplianceRequest.subject_type, IntelligenceKnowledgeBase.allowed_roles_json
— all investigated in Slices 2B/2C and confirmed to be separate,
non-RBAC concepts with their own validation, or none), users.role IS the
literal RBAC-enforcement field the PermissionChecker keys off. A CHECK
constraint here is safe and does not affect those other columns.

This migration deliberately does NOT silently rewrite any existing invalid
row. It detects invalid values first and raises a clear, actionable error if
any exist, refusing to apply the constraint until they are resolved (per
Slice 2B/2C's confirmed finding: 2 accounts, manager@demo-ac-services.local
and readonly@demo-ac-services.local, currently hold 'tenant_manager' and
'tenant_readonly' respectively — see
docs/workflow-rearchitecture/phase-02a-slice-02c/invalid-role-remediation-recommendation.md
for the pending, evidence-based remediation decision required before this
migration can succeed).

Revision ID: 144
Revises: 143
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "144"
down_revision = "143"
branch_labels = None
depends_on = None

CANONICAL_ROLES = (
    "super_admin", "tenant_owner", "staff", "technician", "customer", "guest",
    "admin_operations", "admin_finance", "admin_security", "admin_readonly",
)

CONSTRAINT_NAME = "ck_users_role_canonical"


def upgrade() -> None:
    conn = op.get_bind()
    placeholders = ", ".join(f"'{r}'" for r in CANONICAL_ROLES)
    invalid = conn.exec_driver_sql(
        f"SELECT email, role FROM users WHERE role NOT IN ({placeholders})"
    ).fetchall()
    if invalid:
        details = ", ".join(f"{email!r}={role!r}" for email, role in invalid)
        raise RuntimeError(
            "Migration 144 aborted: users.role contains values outside the "
            f"10 canonical RBAC roles: {details}. Remediate these accounts "
            "first (see scripts/workflow_rearchitecture/remediate_invalid_roles.py "
            "and docs/workflow-rearchitecture/phase-02a-slice-02c/"
            "invalid-role-remediation-recommendation.md), then re-run this "
            "migration. This migration will never silently rewrite role data."
        )

    op.create_check_constraint(
        CONSTRAINT_NAME,
        "users",
        f"role IN ({placeholders})",
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "users", type_="check")
