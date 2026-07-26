"""Conditional Question Engine -- the single largest remaining gap from the
Admin Catalog page's preflight audit. The mockup's "Problems & Questions"
tab has a full question-builder side (conditional questions with input types,
answer sources, DeepSeek flags, and show-when rules) that had NO backing
tables. Problems/intents already exist (MasterIssueType/ServiceIssueMapping,
untouched here); this adds the QUESTION half:

  - catalog_questions: a question DEFINITION scoped to (master_service,
    job_type). input_type + answer_source + customer/tenant visibility +
    deepseek_enabled + structural validation (JSONB, never monetary).
  - catalog_question_options: static allowed answers for a question whose
    answer_source is "static" (dimension-sourced questions read their
    options from the dimension instead).
  - catalog_question_rules: the show-when conditions (job_type / problem /
    dimension_enabled / answer_equals), ALL ANDed. This is the rule builder
    that lets admin express "Ask 'Is an error code visible?' when Job Type =
    Repair AND Problem = Not cooling" WITHOUT exposing raw JSON.

This is the authoritative source for what DeepSeek may ask -- DeepSeek asks
only questions configured here, never invents parameters.

Purely additive. No monetary columns anywhere.

Revision ID: 155
Revises: 154
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "155"
down_revision = "154"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_questions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("master_service_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_type_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("question_key", sa.String(60), nullable=False),
        sa.Column("label", sa.String(300), nullable=False),
        # single_select / multi_select / boolean / number / text / photo /
        # date / time / address
        sa.Column("input_type", sa.String(20), nullable=False, server_default="single_select"),
        # static / dimension / problem / free
        sa.Column("answer_source", sa.String(20), nullable=False, server_default="static"),
        sa.Column("dimension_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("customer_visible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("tenant_setup_visible", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deepseek_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("validation", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("help_text", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("master_service_id", "job_type_id", "question_key", name="uq_cq_service_job_key"),
    )
    op.create_index("ix_cq_master_service", "catalog_questions", ["master_service_id"])
    op.create_index("ix_cq_job_type", "catalog_questions", ["job_type_id"])

    op.create_table(
        "catalog_question_options",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("question_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("question_id", "code", name="uq_cqo_question_code"),
    )
    op.create_index("ix_cqo_question", "catalog_question_options", ["question_id"])

    op.create_table(
        "catalog_question_rules",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("question_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        # job_type / problem / dimension_enabled / answer_equals
        sa.Column("condition_type", sa.String(30), nullable=False),
        # The referenced entity id (job_type_id / issue_type_id / dimension_id)
        # OR another question id for answer_equals.
        sa.Column("ref_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        # Expected value (e.g. an option code for answer_equals). Structural
        # only -- never a monetary amount.
        sa.Column("expected_value", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_cqr_question", "catalog_question_rules", ["question_id"])


def downgrade() -> None:
    op.drop_index("ix_cqr_question", table_name="catalog_question_rules")
    op.drop_table("catalog_question_rules")
    op.drop_index("ix_cqo_question", table_name="catalog_question_options")
    op.drop_table("catalog_question_options")
    op.drop_index("ix_cq_job_type", table_name="catalog_questions")
    op.drop_index("ix_cq_master_service", table_name="catalog_questions")
    op.drop_table("catalog_questions")
