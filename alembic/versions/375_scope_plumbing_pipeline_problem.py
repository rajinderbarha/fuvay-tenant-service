"""Scope Plumbing fixture questions and model appliance pipeline exactly.

Revision ID: 375
Revises: 374
"""
from alembic import op
import sqlalchemy as sa


revision = "375"
down_revision = "374"
branch_labels = None
depends_on = None


PIPELINE_SLUG = "plumbing-appliance-pipeline-installation"


def upgrade() -> None:
    conn = op.get_bind()

    # Pipeline installation is an exact catalog leaf, not a fixture subtype.
    # Its provider-entered price remains independent from Tap/Basin/Commode.
    conn.execute(sa.text("""
        INSERT INTO service_types
            (category_id, name, slug, code, type_family, customer_visible,
             status, display_order, is_active)
        SELECT ms.category_id, 'New pipeline for appliance', :slug,
               'PLUMBING_APPLIANCE_PIPELINE_INSTALLATION', 'Appliance Type',
               true, 'active', 50, true
        FROM master_services ms
        WHERE lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
        ORDER BY ms.created_at LIMIT 1
        ON CONFLICT (slug) DO UPDATE SET
            name=EXCLUDED.name, code=EXCLUDED.code,
            customer_visible=true, status='active', is_active=true,
            deleted_at=NULL, display_order=EXCLUDED.display_order,
            parent_type_id=NULL
    """), {"slug": PIPELINE_SLUG})
    conn.execute(sa.text("""
        INSERT INTO master_service_types
            (master_service_id, service_type_id, is_required, is_default, is_active)
        SELECT ms.id, st.id, true, false, true
        FROM master_services ms CROSS JOIN service_types st
        WHERE lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND st.slug=:slug
        ON CONFLICT (master_service_id, service_type_id) DO UPDATE SET
            is_required=true, is_active=true
    """), {"slug": PIPELINE_SLUG})
    conn.execute(sa.text("""
        INSERT INTO service_type_mappings
            (type_id, category_id, service_group_id, service_id,
             customer_visible, provider_visible, status, display_order)
        SELECT st.id, ms.category_id, ms.service_group_id, ms.id,
               true, true, 'active', st.display_order
        FROM master_services ms CROSS JOIN service_types st
        WHERE lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND st.slug=:slug
        ON CONFLICT (type_id, category_id, service_group_id, service_id)
        DO UPDATE SET customer_visible=true, provider_visible=true,
                      status='active', display_order=EXCLUDED.display_order
    """), {"slug": PIPELINE_SLUG})

    # The pipeline Problem itself selects the exact catalog leaf. The booking
    # service validates this slug against both service/type mappings before it
    # can enter a draft.
    conn.execute(sa.text("""
        UPDATE service_issue_mappings sim SET
            metadata_json=(CASE WHEN jsonb_typeof(sim.metadata_json)='object'
                           THEN sim.metadata_json ELSE '{}'::jsonb END)
                || jsonb_build_object(
                    'default_service_type_slug', CAST(:slug AS text)
                ),
            updated_at=now()
        FROM master_services ms, master_issue_types mit
        WHERE sim.master_service_id=ms.id AND sim.issue_type_id=mit.id
          AND lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND lower(mit.name)='new pipeline for appliance'
          AND sim.deleted_at IS NULL
    """), {"slug": PIPELINE_SLUG})

    # Keep the fixture carousel limited to its four roots even after the new
    # pipeline Type becomes mapped to Plumbing.
    # Assign the canonical allowlist as JSONB so every supported PostgreSQL
    # driver receives the same value.
    conn.execute(sa.text("""
        UPDATE catalog_questions cq SET
            validation=(CASE WHEN jsonb_typeof(cq.validation)='object'
                         THEN cq.validation ELSE '{}'::jsonb END)
                || '{"type_tree_level":"root"}'::jsonb
                || '{"allowed_type_slugs":["plumbing-tap-change","plumbing-wash-basin-installation","plumbing-commode-installation","plumbing-other-fixture-installation"]}'::jsonb,
            updated_at=now()
        FROM master_services ms, job_types jt
        WHERE cq.master_service_id=ms.id AND cq.job_type_id=jt.id
          AND lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND jt.key='installation' AND cq.question_key='fixture_type'
    """))

    # Only the fixture Problem may open fixture/commode questions. This is
    # enforced by the same runtime rule engine used by Instagram and the app.
    conn.execute(sa.text("""
        INSERT INTO catalog_question_rules
            (question_id, condition_type, ref_id, expected_value)
        SELECT cq.id, 'problem', tap_issue.id, NULL
        FROM catalog_questions cq
        JOIN master_services ms ON ms.id=cq.master_service_id
        JOIN job_types jt ON jt.id=cq.job_type_id
        JOIN service_issue_mappings sim
          ON sim.master_service_id=ms.id AND sim.job_type_id=jt.id
         AND sim.deleted_at IS NULL AND sim.status='active'
        JOIN master_issue_types tap_issue ON tap_issue.id=sim.issue_type_id
        WHERE lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND jt.key='installation'
          AND cq.question_key IN ('fixture_type', 'commode_type')
          AND lower(tap_issue.name)='new tap / fixture installation'
          AND NOT EXISTS (
              SELECT 1 FROM catalog_question_rules r
              WHERE r.question_id=cq.id AND r.condition_type='problem'
                AND r.ref_id=tap_issue.id
          )
    """))

    conn.execute(sa.text("""
        UPDATE master_service_job_types msjt SET
            setup_rules_revision=msjt.setup_rules_revision + 1, updated_at=now()
        FROM master_services ms, job_types jt
        WHERE msjt.master_service_id=ms.id AND msjt.job_type_id=jt.id
          AND lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND jt.key='installation'
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        DELETE FROM catalog_question_rules r USING catalog_questions cq,
            master_services ms, master_issue_types mit
        WHERE r.question_id=cq.id AND cq.master_service_id=ms.id
          AND r.ref_id=mit.id AND r.condition_type='problem'
          AND lower(ms.service_name)='plumbing'
          AND lower(mit.name)='new tap / fixture installation'
          AND cq.question_key IN ('fixture_type', 'commode_type')
    """))
    conn.execute(sa.text("""
        UPDATE catalog_questions cq SET
            validation=NULLIF(COALESCE(cq.validation, '{}'::jsonb)
                              - 'allowed_type_slugs', '{}'::jsonb),
            updated_at=now()
        FROM master_services ms
        WHERE cq.master_service_id=ms.id
          AND lower(ms.service_name)='plumbing'
          AND cq.question_key='fixture_type'
    """))
    conn.execute(sa.text("""
        UPDATE service_issue_mappings sim SET
            metadata_json=NULLIF(COALESCE(sim.metadata_json, '{}'::jsonb)
                                 - 'default_service_type_slug', '{}'::jsonb),
            updated_at=now()
        FROM master_services ms, master_issue_types mit
        WHERE sim.master_service_id=ms.id AND sim.issue_type_id=mit.id
          AND lower(ms.service_name)='plumbing'
          AND lower(mit.name)='new pipeline for appliance'
    """))
    conn.execute(sa.text("""
        UPDATE service_type_mappings stm SET status='inactive', updated_at=now()
        FROM service_types st
        WHERE stm.type_id=st.id AND st.slug=:slug
    """), {"slug": PIPELINE_SLUG})
    conn.execute(sa.text("""
        UPDATE master_service_types mst SET is_active=false, updated_at=now()
        FROM service_types st
        WHERE mst.service_type_id=st.id AND st.slug=:slug
    """), {"slug": PIPELINE_SLUG})
    conn.execute(sa.text("""
        UPDATE service_types SET status='archived', is_active=false,
            deleted_at=now(), updated_at=now()
        WHERE slug=:slug
    """), {"slug": PIPELINE_SLUG})
