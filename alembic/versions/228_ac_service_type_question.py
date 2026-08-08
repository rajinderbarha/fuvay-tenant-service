"""AC Service was unbookable: it is flagged `is_type_required` but had no
question that could ever set `offering_type_id`, so EVERY AC Service
booking failed at confirmation with "Missing required fields:
offering_type_id".

`_compute_missing_fields` requires `offering_type_id` whenever the
offering is `is_type_required`, and the ONLY thing that writes that column
is QuestionFlowService._bridge_to_draft_columns, which maps a question
whose key is ac_type / service_type / offering_type onto a ServiceType.
AC Service's questions were brand / capacity_ton / issue_detail -- none of
them a type -- so the requirement was structurally unsatisfiable and the
customer hit a dead end with a raw field name.

AC Installation already carries exactly this question, so this adds the
matching one to AC Service rather than inventing a new shape: same key,
same input type, same two option codes (split_ac / window_ac), which are
real `service_types` rows. Keeping the requirement (rather than clearing
the flag) is deliberate -- tenant price overrides resolve by
service_type_id, so the type genuinely affects what an AC Service costs.

Idempotent: inserts only if AC Service has no type question yet, so it is
safe on an environment where an admin already added one by hand.

Alembic here runs on asyncpg (see alembic/env.py), so every statement uses
SQLAlchemy `text()` bindparams -- driver-native `%(name)s` placeholders do
not work -- and each execute carries exactly ONE statement (asyncpg
rejects multi-statement strings).

Revision ID: 228
Revises: 227
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "228"
down_revision = "227"
branch_labels = None
depends_on = None

# Codes must match ServiceType.slug -- that is what the draft-column bridge
# lower-cases and matches on to resolve offering_type_id.
OPTIONS = (("split_ac", "Split AC"), ("window_ac", "Window AC"))


def upgrade() -> None:
    conn = op.get_bind()

    service_id = conn.execute(sa.text(
        "SELECT id FROM master_services "
        "WHERE service_name = 'AC Service' AND is_active"
    )).scalar()
    if not service_id:
        return  # nothing to fix in this environment

    already = conn.execute(sa.text(
        "SELECT id FROM catalog_questions "
        "WHERE master_service_id = :sid "
        "AND question_key IN ('ac_type', 'service_type', 'offering_type')"
    ), {"sid": service_id}).scalar()
    if already:
        return

    # display_order 0 so the type is asked before brand/capacity/detail --
    # it is the most defining answer and it gates price resolution.
    question_id = conn.execute(sa.text(
        """
        INSERT INTO catalog_questions (
            id, master_service_id, question_key, label, input_type, answer_source,
            required, customer_visible, tenant_setup_visible, deepseek_enabled,
            display_order, is_active, created_at, updated_at
        ) VALUES (
            gen_random_uuid(), :sid, 'ac_type', 'Split AC or Window AC?',
            'single_select', 'static',
            true, true, false, true,
            0, true, NOW(), NOW()
        ) RETURNING id
        """
    ), {"sid": service_id}).scalar()

    for order, (code, label) in enumerate(OPTIONS):
        conn.execute(sa.text(
            """
            INSERT INTO catalog_question_options (
                id, question_id, code, label, display_order, is_active, created_at, updated_at
            ) VALUES (gen_random_uuid(), :qid, :code, :label, :ord, true, NOW(), NOW())
            """
        ), {"qid": question_id, "code": code, "label": label, "ord": order})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        """
        DELETE FROM catalog_question_options WHERE question_id IN (
            SELECT q.id FROM catalog_questions q
            JOIN master_services ms ON ms.id = q.master_service_id
            WHERE ms.service_name = 'AC Service' AND q.question_key = 'ac_type'
        )
        """
    ))
    conn.execute(sa.text(
        """
        DELETE FROM catalog_questions WHERE id IN (
            SELECT q.id FROM catalog_questions q
            JOIN master_services ms ON ms.id = q.master_service_id
            WHERE ms.service_name = 'AC Service' AND q.question_key = 'ac_type'
        )
        """
    ))
