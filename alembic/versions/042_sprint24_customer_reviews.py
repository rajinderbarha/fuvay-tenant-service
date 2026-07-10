"""Sprint 24 — Customer Reviews + Rating Engine

Revision ID: 042
Revises: 041
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. customer_reviews ────────────────────────────────────────────────────
    op.create_table(
        "customer_reviews",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("review_number",       sa.String(40),  nullable=False),
        sa.Column("customer_id",         postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",           postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id",         postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("offering_id",         postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("record_type",         sa.String(40),  nullable=False),
        sa.Column("record_id",           postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id",          postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_id",              postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("appointment_id",      postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id",             postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("staff_member_id",     postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_id",            postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("overall_rating",      sa.Integer(),   nullable=False),
        sa.Column("provider_rating",     sa.Integer(),   nullable=True),
        sa.Column("staff_rating",        sa.Integer(),   nullable=True),
        sa.Column("communication_rating",sa.Integer(),   nullable=True),
        sa.Column("punctuality_rating",  sa.Integer(),   nullable=True),
        sa.Column("quality_rating",      sa.Integer(),   nullable=True),
        sa.Column("value_rating",        sa.Integer(),   nullable=True),
        sa.Column("review_title",        sa.String(200), nullable=True),
        sa.Column("review_text",         sa.Text(),      nullable=True),
        sa.Column("review_tags",         postgresql.JSONB(), nullable=True),
        sa.Column("media_urls",          postgresql.JSONB(), nullable=True),
        sa.Column("status",              sa.String(30),  nullable=False, server_default="pending"),
        sa.Column("visibility",          sa.String(40),  nullable=False, server_default="private_until_approved"),
        sa.Column("moderation_reason",   sa.Text(),      nullable=True),
        sa.Column("rejection_reason",    sa.Text(),      nullable=True),
        sa.Column("edited_at",           sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at",        sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at",         sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at",         sa.DateTime(timezone=True), nullable=True),
        sa.Column("hidden_at",           sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",          sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_cr_number", "customer_reviews", ["review_number"])
    op.create_unique_constraint("uq_cr_customer_record", "customer_reviews",
                                ["customer_id", "record_type", "record_id"])
    op.create_index("ix_cr_tenant_id",      "customer_reviews", ["tenant_id"])
    op.create_index("ix_cr_customer_id",    "customer_reviews", ["customer_id"])
    op.create_index("ix_cr_record_type_id", "customer_reviews", ["record_type", "record_id"])
    op.create_index("ix_cr_status",         "customer_reviews", ["status"])
    op.create_index("ix_cr_overall_rating", "customer_reviews", ["overall_rating"])

    # ── 2. review_replies ─────────────────────────────────────────────────────
    op.create_table(
        "review_replies",
        sa.Column("id",                postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("review_id",         postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",         postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("replied_by_user_id",postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reply_text",        sa.Text(),     nullable=False),
        sa.Column("status",            sa.String(20), nullable=False, server_default="pending"),
        sa.Column("moderation_reason", sa.Text(),     nullable=True),
        sa.Column("submitted_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",        sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",        sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_rr_review", "review_replies", ["review_id"])
    op.create_index("ix_rr_review_id", "review_replies", ["review_id"])
    op.create_index("ix_rr_status",    "review_replies", ["status"])

    # ── 3. review_flags ───────────────────────────────────────────────────────
    op.create_table(
        "review_flags",
        sa.Column("id",                postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("review_id",         postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",         postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("flagged_by_user_id",postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("flagged_by_type",   sa.String(20), nullable=False),
        sa.Column("reason_code",       sa.String(30), nullable=False),
        sa.Column("reason_text",       sa.Text(),     nullable=True),
        sa.Column("status",            sa.String(20), nullable=False, server_default="open"),
        sa.Column("created_at",        sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",        sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_rf_review_id", "review_flags", ["review_id"])
    op.create_index("ix_rf_status",    "review_flags", ["status"])

    # ── 4. review_events ─────────────────────────────────────────────────────
    op.create_table(
        "review_events",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("review_id",     postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",     postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type",    sa.String(20),  nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type",    sa.String(60),  nullable=False),
        sa.Column("old_value",     postgresql.JSONB(), nullable=True),
        sa.Column("new_value",     postgresql.JSONB(), nullable=True),
        sa.Column("reason",        sa.Text(),      nullable=True),
        sa.Column("request_id",    sa.String(100), nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_re_review_id",  "review_events", ["review_id"])
    op.create_index("ix_re_event_type", "review_events", ["event_type"])
    op.create_index("ix_re_tenant_id",  "review_events", ["tenant_id"])

    # ── 5. tenant_rating_summaries ────────────────────────────────────────────
    op.create_table(
        "tenant_rating_summaries",
        sa.Column("id",                         postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id",                  postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_reviews",              sa.Integer(), nullable=False, server_default="0"),
        sa.Column("average_rating",             sa.Numeric(4,2), nullable=False, server_default="0"),
        sa.Column("provider_average_rating",    sa.Numeric(4,2), nullable=False, server_default="0"),
        sa.Column("communication_average_rating",sa.Numeric(4,2), nullable=False, server_default="0"),
        sa.Column("punctuality_average_rating", sa.Numeric(4,2), nullable=False, server_default="0"),
        sa.Column("quality_average_rating",     sa.Numeric(4,2), nullable=False, server_default="0"),
        sa.Column("value_average_rating",       sa.Numeric(4,2), nullable=False, server_default="0"),
        sa.Column("five_star_count",            sa.Integer(), nullable=False, server_default="0"),
        sa.Column("four_star_count",            sa.Integer(), nullable=False, server_default="0"),
        sa.Column("three_star_count",           sa.Integer(), nullable=False, server_default="0"),
        sa.Column("two_star_count",             sa.Integer(), nullable=False, server_default="0"),
        sa.Column("one_star_count",             sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_review_at",             sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",                 sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_trs_tenant", "tenant_rating_summaries", ["tenant_id"])
    op.create_index("ix_trs_tenant_id", "tenant_rating_summaries", ["tenant_id"])

    # ── 6. staff_rating_summaries ─────────────────────────────────────────────
    op.create_table(
        "staff_rating_summaries",
        sa.Column("id",                          postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id",                   postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_member_id",             postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_reviews",               sa.Integer(), nullable=False, server_default="0"),
        sa.Column("average_rating",              sa.Numeric(4,2), nullable=False, server_default="0"),
        sa.Column("communication_average_rating",sa.Numeric(4,2), nullable=False, server_default="0"),
        sa.Column("punctuality_average_rating",  sa.Numeric(4,2), nullable=False, server_default="0"),
        sa.Column("quality_average_rating",      sa.Numeric(4,2), nullable=False, server_default="0"),
        sa.Column("last_review_at",              sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",                  sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_srs_staff", "staff_rating_summaries", ["tenant_id", "staff_member_id"])
    op.create_index("ix_srs_tenant_id",      "staff_rating_summaries", ["tenant_id"])
    op.create_index("ix_srs_staff_member_id","staff_rating_summaries", ["staff_member_id"])

    # ── 7. review_policies ────────────────────────────────────────────────────
    op.create_table(
        "review_policies",
        sa.Column("id",                       postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("category_id",              postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id",               postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("policy_key",              sa.String(80),  nullable=False),
        sa.Column("policy_name",             sa.String(200), nullable=False),
        sa.Column("auto_approve_enabled",    sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("require_admin_moderation",sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("allow_provider_reply",    sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("require_reply_moderation",sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("allow_review_edit",       sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("edit_window_hours",       sa.Integer(), nullable=False, server_default="48"),
        sa.Column("min_rating",              sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_rating",              sa.Integer(), nullable=False, server_default="5"),
        sa.Column("allow_media",             sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("max_media_count",         sa.Integer(), nullable=False, server_default="5"),
        sa.Column("eligible_statuses",       postgresql.JSONB(), nullable=True),
        sa.Column("is_active",              sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at",             sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",             sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_rp_category_id", "review_policies", ["category_id"])
    op.create_index("ix_rp_is_active",   "review_policies", ["is_active"])

    # Seed default policy
    op.execute("""
        INSERT INTO review_policies (
            id, policy_key, policy_name,
            auto_approve_enabled, require_admin_moderation,
            allow_provider_reply, require_reply_moderation,
            allow_review_edit, edit_window_hours,
            min_rating, max_rating, allow_media, max_media_count,
            eligible_statuses, is_active, created_at, updated_at
        ) VALUES (
            gen_random_uuid(), 'default', 'Default Review Policy',
            false, true, true, true, true, 48, 1, 5, true, 5,
            '["completed", "work_done", "payment_collected", "paid", "contacted", "follow_up", "site_visit_completed", "converted", "closed_lost"]'::jsonb,
            true, NOW(), NOW()
        )
    """)


def downgrade() -> None:
    op.drop_table("review_policies")
    op.drop_table("staff_rating_summaries")
    op.drop_table("tenant_rating_summaries")
    op.drop_table("review_events")
    op.drop_table("review_flags")
    op.drop_table("review_replies")
    op.drop_table("customer_reviews")
