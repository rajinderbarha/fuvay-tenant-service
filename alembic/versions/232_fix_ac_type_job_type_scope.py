"""Fix migration 228: the ac_type question it added to AC Service was never
asked, so AC Service bookings STILL failed with
"Missing required fields: offering_type_id".

228 inserted the question with `job_type_id = NULL`, but
CatalogQuestionService.resolve_applicable_questions filters on an EXACT match:

    CatalogQuestion.job_type_id == job_type_id
    if job_type_id else CatalogQuestion.job_type_id.is_(None)

An AC Service draft resolves a real job_type_id, so the NULL-scoped row was
excluded from every question flow. The customer was never asked the type,
`_bridge_to_draft_columns` therefore never set `draft.offering_type_id`, and
confirmation failed exactly as it did before 228 -- the fix looked applied but
changed nothing at runtime. Confirmed live over HTTP (confirm -> 422).

Every other AC Service question (brand, capacity_ton, issue_detail) is scoped
to the same job type, so this aligns ac_type with its siblings rather than
inventing a scope: the job_type_id is READ from those sibling rows instead of
being hardcoded, so it stays correct in any environment whose ids differ.

Idempotent, and only ever narrows a NULL scope -- it will not overwrite a
job_type_id an admin has deliberately set.

Revision ID: 232
Revises: 231
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "232"
down_revision = "231"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    service_id = conn.execute(sa.text(
        "SELECT id FROM master_services WHERE service_name = 'AC Service' AND is_active"
    )).scalar()
    if not service_id:
        return

    # The scope the offering's OTHER customer-visible questions already use.
    # Most common wins, so one stray row cannot mis-scope the fix.
    sibling_job_type = conn.execute(sa.text(
        """
        SELECT job_type_id FROM catalog_questions
        WHERE master_service_id = :sid
          AND question_key <> 'ac_type'
          AND job_type_id IS NOT NULL
          AND is_active
        GROUP BY job_type_id
        ORDER BY count(*) DESC
        LIMIT 1
        """
    ), {"sid": service_id}).scalar()
    if not sibling_job_type:
        return   # nothing to align to; leaving NULL is no worse than guessing

    conn.execute(sa.text(
        "UPDATE catalog_questions SET job_type_id = :jt, updated_at = NOW() "
        "WHERE master_service_id = :sid AND question_key = 'ac_type' "
        "AND job_type_id IS NULL"
    ), {"jt": sibling_job_type, "sid": service_id})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        """
        UPDATE catalog_questions SET job_type_id = NULL, updated_at = NOW()
        WHERE question_key = 'ac_type'
          AND master_service_id = (
            SELECT id FROM master_services WHERE service_name = 'AC Service'
          )
        """
    ))
