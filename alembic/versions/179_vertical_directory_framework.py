"""VERTICAL-DIRECTORY-FRAMEWORK: canonical Staff<->Vertical and
Customer<->Vertical relationship tables, plus vertical ownership on
complaints.

Audited before adding tables (see engine docstrings for evidence):
  - Tenant<->Vertical already has a real relationship: TenantVerticalEnrollment
    (migration 148, vertical_catalog engine) -- NOT duplicated here. Provider
    directory scoping reuses it directly, falling back to Tenant.vertical
    (a flat, always-set string) only for tenants that predate the enrollment
    table (unambiguous single-vertical legacy case).
  - Staff (ProviderTeamMember) has ZERO vertical relationship today -- only
    tenant_id + category_id. New table required.
  - Customer (auth.User) has ZERO vertical relationship today -- only
    inferable via bookings. New table required.
  - CustomerComplaint has NO vertical_id -- only category_id/tenant_id.
    Column added; backfilled ONLY where category.slug matches a real
    vertical.key exactly (the same slug==key convention already relied on
    elsewhere in this codebase, e.g. entitlement/vertical_catalog). Anything
    else is left NULL (fail closed) and reported, never guessed/defaulted.

Purely additive. No existing column dropped or renamed.

Revision ID: 179
Revises: 178
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "179"
down_revision = "178"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Staff <-> Vertical explicit assignment ───────────────────────────────
    op.create_table(
        "staff_business_verticals",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("staff_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vertical_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("designation", sa.String(60), nullable=True),
        sa.Column("job_type_capabilities", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("service_capabilities", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("verification_status", sa.String(30), nullable=False, server_default="not_started"),
        sa.Column("assignment_status", sa.String(30), nullable=False, server_default="assigned"),
        sa.Column("availability_status", sa.String(30), nullable=False, server_default="unavailable"),
        sa.Column("assigned_by_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_sbv_staff", "staff_business_verticals", ["staff_id"])
    op.create_index("ix_sbv_tenant", "staff_business_verticals", ["tenant_id"])
    op.create_index("ix_sbv_vertical", "staff_business_verticals", ["vertical_id"])
    op.create_index("uq_sbv_staff_vertical", "staff_business_verticals",
                    ["staff_id", "vertical_id"], unique=True)

    # ── Customer <-> Vertical derived/explicit relationship ──────────────────
    op.create_table(
        "customer_business_verticals",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vertical_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("booking_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("relationship_status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("source_relationship", sa.String(30), nullable=False),  # booking | job | payment | subscription | complaint
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cbv_customer", "customer_business_verticals", ["customer_id"])
    op.create_index("ix_cbv_vertical", "customer_business_verticals", ["vertical_id"])
    op.create_index("uq_cbv_customer_vertical", "customer_business_verticals",
                    ["customer_id", "vertical_id"], unique=True)

    # ── Complaint -> Vertical snapshot ────────────────────────────────────────
    op.add_column("customer_complaints",
                  sa.Column("vertical_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_cc_vertical", "customer_complaints", ["vertical_id"])

    conn = op.get_bind()

    # Backfill complaints.vertical_id ONLY where category.slug == a real
    # vertical.key exactly (fail closed otherwise -- no guessing, no
    # defaulting to home_services).
    result = conn.execute(sa.text("""
        UPDATE customer_complaints cc
        SET vertical_id = v.id
        FROM service_categories sc, verticals v
        WHERE cc.category_id = sc.id AND sc.slug = v.key AND cc.vertical_id IS NULL
    """))
    backfilled = result.rowcount
    total = conn.execute(sa.text("SELECT count(*) FROM customer_complaints")).scalar()
    unresolved = conn.execute(sa.text(
        "SELECT count(*) FROM customer_complaints WHERE vertical_id IS NULL")).scalar()
    print(f"[179] customer_complaints: total={total} backfilled={backfilled} "
          f"unresolved_left_null={unresolved} (excluded from vertical directories, "
          f"visible only in an authorized global remediation queue)")

    # Backfill staff_business_verticals from Tenant.vertical (the one
    # unambiguous, always-set flat field) -- NOT from every
    # TenantVerticalEnrollment a multi-vertical tenant might hold, since the
    # spec explicitly forbids assuming a multi-vertical tenant's staff are
    # available in every one of its verticals. Multi-vertical tenants'
    # additional verticals are left for explicit admin assignment.
    conn.execute(sa.text("""
        INSERT INTO staff_business_verticals
            (id, staff_id, tenant_id, vertical_id, is_active, verification_status,
             assignment_status, availability_status, created_at, updated_at)
        SELECT gen_random_uuid(), ptm.id, ptm.tenant_id, v.id,
               (ptm.status = 'active'), 'not_started', 'assigned', 'unavailable', now(), now()
        FROM provider_team_members ptm
        JOIN tenants t ON t.id = ptm.tenant_id
        JOIN verticals v ON v.key = t.vertical
        WHERE ptm.deleted_at IS NULL
        ON CONFLICT (staff_id, vertical_id) DO NOTHING
    """))
    staff_backfilled = conn.execute(sa.text("SELECT count(*) FROM staff_business_verticals")).scalar()
    total_staff = conn.execute(sa.text("SELECT count(*) FROM provider_team_members WHERE deleted_at IS NULL")).scalar()
    print(f"[179] staff_business_verticals: backfilled={staff_backfilled} of total_active_staff={total_staff} "
          f"(one row per staff member's tenant's PRIMARY vertical only -- multi-vertical "
          f"tenants' additional verticals require explicit admin assignment, not guessed)")

    # customer_business_verticals: derive from real Home Services activity
    # only (service_bookings is the one canonical transactional table with a
    # direct customer_id + tenant_id -> vertical path proven this session).
    # Other verticals have no equivalent canonical transactional table yet
    # confirmed in this codebase -- not backfilled, reported as a gap rather
    # than guessed.
    conn.execute(sa.text("""
        INSERT INTO customer_business_verticals
            (id, customer_id, vertical_id, first_activity_at, last_activity_at,
             booking_count, relationship_status, source_relationship, created_at, updated_at)
        SELECT gen_random_uuid(), sb.customer_id, v.id,
               MIN(sb.created_at), MAX(sb.created_at), COUNT(*), 'active', 'booking', now(), now()
        FROM service_bookings sb
        JOIN verticals v ON v.key = 'home_services'
        WHERE sb.customer_id IS NOT NULL
        GROUP BY sb.customer_id, v.id
        ON CONFLICT (customer_id, vertical_id) DO NOTHING
    """))
    cust_backfilled = conn.execute(sa.text("SELECT count(*) FROM customer_business_verticals")).scalar()
    print(f"[179] customer_business_verticals: backfilled={cust_backfilled} rows from service_bookings "
          f"(home_services only -- no other vertical has a confirmed canonical transactional "
          f"table in this codebase yet; not guessed)")


def downgrade() -> None:
    op.drop_index("ix_cc_vertical", table_name="customer_complaints")
    op.drop_column("customer_complaints", "vertical_id")

    op.drop_index("uq_cbv_customer_vertical", table_name="customer_business_verticals")
    op.drop_index("ix_cbv_vertical", table_name="customer_business_verticals")
    op.drop_index("ix_cbv_customer", table_name="customer_business_verticals")
    op.drop_table("customer_business_verticals")

    op.drop_index("uq_sbv_staff_vertical", table_name="staff_business_verticals")
    op.drop_index("ix_sbv_vertical", table_name="staff_business_verticals")
    op.drop_index("ix_sbv_tenant", table_name="staff_business_verticals")
    op.drop_index("ix_sbv_staff", table_name="staff_business_verticals")
    op.drop_table("staff_business_verticals")
