"""P0 Enterprise Notification Template Center.

Extends the existing `notification_templates` table (previously just
tenant_id/notif_type/channel/title/body/variables/is_active/vertical) with
full enterprise fields: event_type, audience, app_scope, scope_type, language,
status, subject/html_body/plain_text_body, action fields, priority,
is_platform_default, fallback_template_id, created_by/updated_by, archived_at.

Adds: notification_template_versions, notification_test_sends,
notification_template_audit_logs. Adds template_id FK on notification_records
so delivery analytics can be grouped per-template.

Revision ID: 102
Revises: 101
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "102"
down_revision = "101"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    def _col_exists(table: str, col: str) -> bool:
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.columns WHERE table_name=:t AND column_name=:c"),
            {"t": table, "c": col})
        return bool(r.fetchone())

    new_cols = [
        ("event_type", sa.String(80)),
        ("audience", sa.String(30)),
        ("app_scope", sa.String(30)),
        ("scope_type", sa.String(30)),
        ("category_id", UUID(as_uuid=True)),
        ("language", sa.String(10)),
        ("status", sa.String(30)),
        ("subject", sa.String(255)),
        ("html_body", sa.Text),
        ("plain_text_body", sa.Text),
        ("action_label", sa.String(100)),
        ("action_url", sa.String(500)),
        ("priority", sa.String(20)),
        ("is_platform_default", sa.Boolean),
        ("is_system", sa.Boolean),
        ("fallback_template_id", UUID(as_uuid=True)),
        ("created_by_user_id", UUID(as_uuid=True)),
        ("updated_by_user_id", UUID(as_uuid=True)),
        ("archived_at", sa.DateTime(timezone=True)),
    ]
    for col, coltype in new_cols:
        if not _col_exists("notification_templates", col):
            op.add_column("notification_templates", sa.Column(col, coltype, nullable=True))

    # Backfill new required-ish fields from existing data so old rows behave sanely.
    op.execute("UPDATE notification_templates SET event_type = notif_type WHERE event_type IS NULL")
    op.execute("UPDATE notification_templates SET language = 'en' WHERE language IS NULL")
    op.execute("UPDATE notification_templates SET audience = 'customer' WHERE audience IS NULL")
    op.execute("UPDATE notification_templates SET app_scope = 'customer_app' WHERE app_scope IS NULL")
    op.execute("UPDATE notification_templates SET priority = 'normal' WHERE priority IS NULL")
    op.execute("""
        UPDATE notification_templates
        SET scope_type = CASE WHEN tenant_id IS NOT NULL THEN 'tenant'
                               WHEN vertical IS NOT NULL THEN 'vertical'
                               ELSE 'platform_default' END
        WHERE scope_type IS NULL
    """)
    op.execute("UPDATE notification_templates SET is_platform_default = (tenant_id IS NULL) WHERE is_platform_default IS NULL")
    op.execute("UPDATE notification_templates SET is_system = false WHERE is_system IS NULL")
    op.execute("UPDATE notification_templates SET status = CASE WHEN is_active THEN 'active' ELSE 'inactive' END WHERE status IS NULL")

    if not _col_exists("notification_records", "template_id"):
        op.add_column("notification_records", sa.Column("template_id", UUID(as_uuid=True), nullable=True))
        op.create_index("ix_nr_template", "notification_records", ["template_id"])

    op.create_table(
        "notification_template_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("snapshot_json", JSONB, nullable=False),
        sa.Column("changed_by_user_id", UUID(as_uuid=True)),
        sa.Column("change_reason", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ntv_template", "notification_template_versions", ["template_id"])

    op.create_table(
        "notification_test_sends",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", UUID(as_uuid=True), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("sample_payload_json", JSONB),
        sa.Column("rendered_title", sa.Text),
        sa.Column("rendered_body", sa.Text),
        sa.Column("sent_by_user_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_nts_template", "notification_test_sends", ["template_id"])

    op.create_table(
        "notification_template_audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("action_type", sa.String(80), nullable=False),
        sa.Column("template_id", UUID(as_uuid=True)),
        sa.Column("actor_user_id", UUID(as_uuid=True)),
        sa.Column("actor_role", sa.String(40)),
        sa.Column("old_value_json", JSONB),
        sa.Column("new_value_json", JSONB),
        sa.Column("reason", sa.Text),
        sa.Column("request_id", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ntal_action", "notification_template_audit_logs", ["action_type"])
    op.create_index("ix_ntal_template", "notification_template_audit_logs", ["template_id"])


def downgrade() -> None:
    op.drop_table("notification_template_audit_logs")
    op.drop_table("notification_test_sends")
    op.drop_table("notification_template_versions")
    op.drop_index("ix_nr_template", table_name="notification_records")
    op.drop_column("notification_records", "template_id")
    for col in [
        "event_type", "audience", "app_scope", "scope_type", "category_id", "language",
        "status", "subject", "html_body", "plain_text_body", "action_label", "action_url",
        "priority", "is_platform_default", "is_system", "fallback_template_id",
        "created_by_user_id", "updated_by_user_id", "archived_at",
    ]:
        op.drop_column("notification_templates", col)
