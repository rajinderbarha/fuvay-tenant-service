"""Workflow Templates Enterprise Engine — new standalone tables.

Revision ID: 106
Revises: 105
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "106"
down_revision = "105"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── workflow_templates ─────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS workflow_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workflow_key TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            vertical_key TEXT NOT NULL DEFAULT 'universal',
            workflow_type TEXT NOT NULL DEFAULT 'repair',
            status TEXT NOT NULL DEFAULT 'draft',
            current_version INTEGER NOT NULL DEFAULT 1,
            readiness_status TEXT NOT NULL DEFAULT 'draft',
            runtime_health TEXT NOT NULL DEFAULT 'not_used',
            steps_json JSONB NOT NULL DEFAULT '[]',
            transitions_json JSONB NOT NULL DEFAULT '[]',
            sla_rules_json JSONB NOT NULL DEFAULT '[]',
            approval_gates_json JSONB NOT NULL DEFAULT '[]',
            automation_rules_json JSONB NOT NULL DEFAULT '[]',
            service_mappings_json JSONB NOT NULL DEFAULT '[]',
            validation_result_json JSONB NOT NULL DEFAULT '{}',
            simulator_scenarios_json JSONB NOT NULL DEFAULT '[]',
            created_by_user_id UUID,
            updated_by_user_id UUID,
            published_at TIMESTAMPTZ,
            archived_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_wt_status ON workflow_templates (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_wt_vertical ON workflow_templates (vertical_key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_wt_readiness ON workflow_templates (readiness_status)")

    # ── workflow_template_versions ─────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS workflow_template_versions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workflow_template_id UUID NOT NULL,
            version_number INTEGER NOT NULL,
            snapshot_json JSONB NOT NULL DEFAULT '{}',
            change_summary TEXT,
            published_by_user_id UUID,
            published_at TIMESTAMPTZ,
            is_rollback BOOLEAN NOT NULL DEFAULT false,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_wtv_template ON workflow_template_versions (workflow_template_id)")

    # ── workflow_runtime_events ────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS workflow_runtime_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workflow_template_id UUID NOT NULL,
            workflow_version INTEGER NOT NULL DEFAULT 1,
            booking_id UUID,
            job_id UUID,
            tenant_id UUID,
            from_step_key TEXT,
            to_step_key TEXT NOT NULL,
            action_by_user_id UUID,
            action_role TEXT,
            transition_status TEXT NOT NULL DEFAULT 'success',
            error_code TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_wre_template ON workflow_runtime_events (workflow_template_id)")

    # ── workflow_audit_logs ────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS workflow_audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workflow_template_id UUID NOT NULL,
            action_type TEXT NOT NULL,
            actor_user_id UUID,
            old_value_json JSONB,
            new_value_json JSONB,
            reason TEXT,
            request_id TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_wal_template ON workflow_audit_logs (workflow_template_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS workflow_audit_logs")
    op.execute("DROP TABLE IF EXISTS workflow_runtime_events")
    op.execute("DROP TABLE IF EXISTS workflow_template_versions")
    op.execute("DROP TABLE IF EXISTS workflow_templates")
