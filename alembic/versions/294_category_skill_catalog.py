"""Category-scoped technician skill catalog and normalized assignments.

Revision ID: 294
Revises: 293
"""
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "294"
down_revision = "293"
branch_labels = None
depends_on = None


DEFAULT_HOME_SERVICE_SKILLS = (
    ("ac_diagnostics", "AC Diagnostics", "Diagnose cooling, electrical and airflow faults.", 10, True),
    ("ac_repair", "AC Repair", "Repair approved AC components after diagnosis.", 20, True),
    ("ac_installation", "AC Installation", "Install and commission supported AC systems.", 30, True),
    ("ac_uninstallation", "AC Uninstallation", "Safely disconnect and remove AC systems.", 40, True),
    ("ac_maintenance", "AC Maintenance / Servicing", "Perform preventive maintenance and routine servicing.", 50, False),
    ("ac_gas_refill", "AC Gas Refill", "Inspect, recover and recharge refrigerant.", 60, True),
    ("refrigerant_handling", "Refrigerant Handling", "Handle refrigerants using approved safety practices.", 70, True),
    ("electrical_safety", "Electrical Safety", "Apply electrical isolation and safe-work procedures.", 80, True),
)


def upgrade() -> None:
    op.create_table(
        "category_skills",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("category_id", UUID(as_uuid=True), nullable=False),
        sa.Column("service_group_id", UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("requires_verification", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["category_id"], ["service_categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_group_id"], ["service_groups.id"], ondelete="SET NULL"),
        sa.CheckConstraint("status IN ('active','retired')", name="ck_category_skills_status"),
        sa.UniqueConstraint("category_id", "code", name="uq_category_skills_category_code"),
    )
    op.create_index("ix_category_skills_category_status_order", "category_skills", ["category_id", "status", "display_order", "id"])
    op.create_index("ix_category_skills_group_status", "category_skills", ["service_group_id", "status"])
    op.execute("CREATE INDEX ix_category_skills_name_lower ON category_skills (category_id, lower(name))")

    op.create_table(
        "provider_team_member_skills",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("staff_member_id", UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", UUID(as_uuid=True), nullable=False),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="not_required"),
        sa.Column("assigned_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staff_member_id"], ["provider_team_members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["category_skills.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("verification_status IN ('not_required','pending','verified','rejected')", name="ck_ptms_verification_status"),
        sa.UniqueConstraint("staff_member_id", "skill_id", name="uq_ptms_member_skill"),
    )
    op.create_index("ix_ptms_tenant_skill_member", "provider_team_member_skills", ["tenant_id", "skill_id", "staff_member_id"])
    op.create_index("ix_ptms_member_status", "provider_team_member_skills", ["staff_member_id", "verification_status"])

    bind = op.get_bind()
    category_id = bind.execute(sa.text(
        "SELECT id FROM service_categories WHERE vertical_type='home_services' AND is_active=true ORDER BY created_at LIMIT 1"
    )).scalar()
    if category_id:
        group_id = bind.execute(sa.text(
            "SELECT id FROM service_groups WHERE category_id=:cid AND status='active' "
            "AND (lower(name) LIKE '%ac%' OR lower(name) LIKE '%air conditioning%') "
            "ORDER BY display_order, created_at LIMIT 1"
        ), {"cid": category_id}).scalar()
        for code, name, description, order, verify in DEFAULT_HOME_SERVICE_SKILLS:
            bind.execute(sa.text(
                "INSERT INTO category_skills (id, category_id, service_group_id, code, name, description, status, requires_verification, display_order) "
                "VALUES (:id,:cid,:gid,:code,:name,:description,'active',:verify,:display_order) "
                "ON CONFLICT (category_id, code) DO NOTHING"
            ), {"id": uuid.uuid4(), "cid": category_id, "gid": group_id, "code": code,
                "name": name, "description": description, "verify": verify, "display_order": order})


def downgrade() -> None:
    op.drop_table("provider_team_member_skills")
    op.drop_index("ix_category_skills_name_lower", table_name="category_skills")
    op.drop_table("category_skills")
