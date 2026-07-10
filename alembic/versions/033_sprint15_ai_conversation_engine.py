"""Sprint 15 — AI Conversation Engine + DeepSeek Orchestrator.

Creates 7 tables for persistent AI conversations, workflow states,
prompt template management, and full LLM/tool call audit logging.

Revision ID: 033
Revises: 032
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. ai_conversation_sessions ──────────────────────────────────────────
    op.create_table(
        "ai_conversation_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_key", sa.String(128), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=True),
        sa.Column("category_id", UUID(as_uuid=True), nullable=True),
        sa.Column("current_intent", sa.String(100), nullable=True),
        sa.Column("workflow_status", sa.String(50), nullable=False,
                  server_default=sa.text("'active'")),
        sa.Column("collected_fields", JSONB, nullable=True),
        sa.Column("context_data", JSONB, nullable=True),
        sa.Column("turn_count", sa.Integer(), nullable=False,
                  server_default=sa.text("0")),
        sa.Column("last_activity_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False,
                  server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("session_key", name="uq_acs_session_key"),
    )
    op.create_index("ix_acs_customer_id", "ai_conversation_sessions", ["customer_id"])
    op.create_index("ix_acs_session_key", "ai_conversation_sessions", ["session_key"])
    op.create_index("ix_acs_workflow_status", "ai_conversation_sessions", ["workflow_status"])
    op.create_index("ix_acs_is_active", "ai_conversation_sessions", ["is_active"])
    op.create_index("ix_acs_last_activity", "ai_conversation_sessions", ["last_activity_at"])

    # ── 2. ai_conversation_messages ───────────────────────────────────────────
    op.create_table(
        "ai_conversation_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("intent_at_time", sa.String(100), nullable=True),
        sa.Column("tool_calls_made", JSONB, nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["ai_conversation_sessions.id"],
                                ondelete="CASCADE"),
    )
    op.create_index("ix_acm_session_id", "ai_conversation_messages", ["session_id"])
    op.create_index("ix_acm_role", "ai_conversation_messages", ["role"])
    op.create_index("ix_acm_created_at", "ai_conversation_messages", ["created_at"])

    # ── 3. ai_workflow_states ─────────────────────────────────────────────────
    op.create_table(
        "ai_workflow_states",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_name", sa.String(100), nullable=False),
        sa.Column("current_step", sa.String(100), nullable=True),
        sa.Column("steps_completed", JSONB, nullable=True),
        sa.Column("steps_pending", JSONB, nullable=True),
        sa.Column("extracted_data", JSONB, nullable=True),
        sa.Column("validation_errors", JSONB, nullable=True),
        sa.Column("is_complete", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["ai_conversation_sessions.id"],
                                ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", "workflow_name", name="uq_aws_session_workflow"),
    )
    op.create_index("ix_aws_session_id", "ai_workflow_states", ["session_id"])
    op.create_index("ix_aws_workflow_name", "ai_workflow_states", ["workflow_name"])

    # ── 4. ai_prompt_templates ────────────────────────────────────────────────
    op.create_table(
        "ai_prompt_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_key", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False,
                  server_default=sa.text("'system'")),
        sa.Column("template_content", sa.Text(), nullable=False),
        sa.Column("variables", JSONB, nullable=True),
        sa.Column("version", sa.Integer(), nullable=False,
                  server_default=sa.text("1")),
        sa.Column("is_active", sa.Boolean(), nullable=False,
                  server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("template_key", name="uq_apt_template_key"),
    )
    op.create_index("ix_apt_template_key", "ai_prompt_templates", ["template_key"])
    op.create_index("ix_apt_category", "ai_prompt_templates", ["category"])
    op.create_index("ix_apt_is_active", "ai_prompt_templates", ["is_active"])

    # ── 5. ai_llm_call_logs ───────────────────────────────────────────────────
    op.create_table(
        "ai_llm_call_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), nullable=True),
        sa.Column("call_type", sa.String(50), nullable=False,
                  server_default=sa.text("'chat'")),
        sa.Column("model_used", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("had_tool_calls", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("tool_names", JSONB, nullable=True),
        sa.Column("response_status", sa.String(30), nullable=False,
                  server_default=sa.text("'success'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("request_payload_size", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["ai_conversation_sessions.id"],
                                ondelete="SET NULL"),
    )
    op.create_index("ix_allcl_session_id", "ai_llm_call_logs", ["session_id"])
    op.create_index("ix_allcl_created_at", "ai_llm_call_logs", ["created_at"])
    op.create_index("ix_allcl_response_status", "ai_llm_call_logs", ["response_status"])

    # ── 6. ai_tool_call_logs ──────────────────────────────────────────────────
    op.create_table(
        "ai_tool_call_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("llm_call_id", UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", UUID(as_uuid=True), nullable=True),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("input_params", JSONB, nullable=True),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False,
                  server_default=sa.text("true")),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["llm_call_id"], ["ai_llm_call_logs.id"],
                                ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["ai_conversation_sessions.id"],
                                ondelete="SET NULL"),
    )
    op.create_index("ix_atcl_llm_call_id", "ai_tool_call_logs", ["llm_call_id"])
    op.create_index("ix_atcl_session_id", "ai_tool_call_logs", ["session_id"])
    op.create_index("ix_atcl_tool_name", "ai_tool_call_logs", ["tool_name"])
    op.create_index("ix_atcl_created_at", "ai_tool_call_logs", ["created_at"])

    # ── 7. ai_conversation_audit_logs ─────────────────────────────────────────
    op.create_table(
        "ai_conversation_audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("event_data", JSONB, nullable=True),
        sa.Column("severity", sa.String(20), nullable=False,
                  server_default=sa.text("'info'")),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["ai_conversation_sessions.id"],
                                ondelete="SET NULL"),
    )
    op.create_index("ix_acal_session_id", "ai_conversation_audit_logs", ["session_id"])
    op.create_index("ix_acal_event_type", "ai_conversation_audit_logs", ["event_type"])
    op.create_index("ix_acal_severity", "ai_conversation_audit_logs", ["severity"])
    op.create_index("ix_acal_created_at", "ai_conversation_audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("ai_conversation_audit_logs")
    op.drop_table("ai_tool_call_logs")
    op.drop_table("ai_llm_call_logs")
    op.drop_table("ai_prompt_templates")
    op.drop_table("ai_workflow_states")
    op.drop_table("ai_conversation_messages")
    op.drop_table("ai_conversation_sessions")
