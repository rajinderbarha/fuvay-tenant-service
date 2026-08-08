"""Every job type of a type/brand-required offering needs the question that
fills it -- otherwise that job type is permanently unbookable.

The structural mismatch: `is_type_required` / `is_brand_required` are flags on
the OFFERING (master_services), but catalog questions are scoped per
(master_service_id, job_type_id) and
CatalogQuestionService.resolve_applicable_questions matches job_type_id
EXACTLY. So an offering can be type-required while only SOME of its job types
have a type question -- and a customer whose draft resolves to one of the
others is never asked, `offering_type_id` stays NULL, and confirmation fails
with "Missing required fields".

Found live: AC Service has two job types, "Service" and "Installation". Only
"Service" had ac_type/brand questions; 14 real drafts had already resolved to
"Installation", every one of which would fail at confirm on BOTH
offering_type_id and brand_id.

This backfills the gap generally rather than patching the one offering: for
each active offering that requires a type and/or brand, every one of its job
types that lacks the corresponding question gets a copy of a SIBLING job
type's question -- same key, label, input type, and options. Copying rather
than inventing means the customer is asked exactly what an admin already
authored for that offering, with the same option codes the draft-column bridge
matches on.

Offerings with no sibling question to copy are left alone: there is nothing to
copy from, and fabricating a question (with what options?) would be inventing
catalog content. Those remain visible as the same "Missing required fields"
error, which is the honest outcome for an offering an admin has not finished
authoring.

Idempotent: only inserts where the question is absent.

Revision ID: 233
Revises: 232
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "233"
down_revision = "232"
branch_labels = None
depends_on = None

# question_key values the draft-column bridge understands, per requirement.
# (see QuestionFlowService._bridge_to_draft_columns)
TYPE_KEYS = ("ac_type", "service_type", "offering_type")
BRAND_KEYS = ("brand",)


def _backfill(conn, requirement_column: str, keys: tuple[str, ...]) -> int:
    """Copy the requirement's question to every job type of every offering that
    needs it and does not have it. Returns rows inserted."""
    inserted = 0

    offerings = conn.execute(sa.text(
        f"SELECT id FROM master_services WHERE is_active AND {requirement_column}"
    )).scalars().all()

    for service_id in offerings:
        job_types = conn.execute(sa.text(
            "SELECT DISTINCT job_type_id FROM master_service_job_types "
            "WHERE master_service_id = :sid AND job_type_id IS NOT NULL"
        ), {"sid": service_id}).scalars().all()
        if len(job_types) < 2:
            continue   # nothing to spread across

        # A source question for this requirement, on ANY of its job types.
        source = conn.execute(sa.text(
            "SELECT id, question_key, label, input_type, answer_source, dimension_id, "
            "       required, customer_visible, tenant_setup_visible, deepseek_enabled, "
            "       validation, help_text, display_order, icon_url "
            "FROM catalog_questions "
            "WHERE master_service_id = :sid AND question_key = ANY(:keys) "
            "  AND is_active AND job_type_id IS NOT NULL "
            "ORDER BY display_order LIMIT 1"
        ), {"sid": service_id, "keys": list(keys)}).mappings().first()
        if not source:
            continue   # nothing authored to copy -- see module docstring

        for job_type_id in job_types:
            exists = conn.execute(sa.text(
                "SELECT 1 FROM catalog_questions "
                "WHERE master_service_id = :sid AND job_type_id = :jt "
                "  AND question_key = ANY(:keys) AND is_active LIMIT 1"
            ), {"sid": service_id, "jt": job_type_id, "keys": list(keys)}).first()
            if exists:
                continue

            new_id = conn.execute(sa.text(
                """
                INSERT INTO catalog_questions (
                    id, master_service_id, job_type_id, question_key, label, input_type,
                    answer_source, dimension_id, required, customer_visible,
                    tenant_setup_visible, deepseek_enabled, validation, help_text,
                    display_order, icon_url, is_active, created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), :sid, :jt, :qkey, :label, :itype,
                    :asrc, :dim, :req, :cvis,
                    :tvis, :ds, :val, :help,
                    :ord, :icon, true, NOW(), NOW()
                ) RETURNING id
                """
            ), {
                "sid": service_id, "jt": job_type_id,
                "qkey": source["question_key"], "label": source["label"],
                "itype": source["input_type"], "asrc": source["answer_source"],
                "dim": source["dimension_id"], "req": source["required"],
                "cvis": source["customer_visible"], "tvis": source["tenant_setup_visible"],
                "ds": source["deepseek_enabled"], "val": source["validation"],
                "help": source["help_text"], "ord": source["display_order"],
                "icon": source["icon_url"],
            }).scalar()
            inserted += 1

            # Options must come across too -- the codes are what the bridge
            # matches against ServiceType.slug / Brand.slug.
            conn.execute(sa.text(
                """
                INSERT INTO catalog_question_options (
                    id, question_id, code, label, display_order, is_active, created_at, updated_at
                )
                SELECT gen_random_uuid(), :new_id, o.code, o.label, o.display_order,
                       o.is_active, NOW(), NOW()
                FROM catalog_question_options o
                WHERE o.question_id = :src_id
                """
            ), {"new_id": new_id, "src_id": source["id"]})

    return inserted


def upgrade() -> None:
    conn = op.get_bind()
    n_type = _backfill(conn, "is_type_required", TYPE_KEYS)
    n_brand = _backfill(conn, "is_brand_required", BRAND_KEYS)
    print(f"[233] backfilled {n_type} type question(s), {n_brand} brand question(s)")


def downgrade() -> None:
    # Not reversible in a targeted way: the copies are indistinguishable from
    # admin-authored questions once created, and deleting by key would remove
    # legitimate originals. Left in place deliberately.
    pass
