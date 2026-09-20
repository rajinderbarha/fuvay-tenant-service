"""Add one-level Service Type variants and split Commode pricing leaves.

Revision ID: 374
Revises: 373
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "374"
down_revision = "373"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_types",
        sa.Column(
            "parent_type_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "service_types.id",
                name="fk_service_types_parent_type",
                ondelete="RESTRICT",
            ),
            nullable=True,
        ),
    )
    op.create_index("ix_service_types_parent", "service_types", ["parent_type_id"])
    conn = op.get_bind()

    children = (
        ("plumbing-western-commode-installation", "Western / English commode", "PLUMBING_WESTERN_COMMODE_INSTALLATION", 31),
        ("plumbing-indian-commode-installation", "Indian-style commode", "PLUMBING_INDIAN_COMMODE_INSTALLATION", 32),
    )
    for slug, name, code, order in children:
        conn.execute(sa.text("""
            INSERT INTO service_types
                (category_id, name, slug, code, type_family, customer_visible,
                 status, display_order, is_active, parent_type_id)
            SELECT parent.category_id, :name, :slug, :code, parent.type_family,
                   true, 'active', :display_order, true, parent.id
            FROM service_types parent
            WHERE parent.slug='plumbing-commode-installation'
              AND parent.deleted_at IS NULL
            ON CONFLICT (slug) DO UPDATE SET
                name=EXCLUDED.name, code=EXCLUDED.code,
                customer_visible=true, status='active', is_active=true,
                deleted_at=NULL, display_order=EXCLUDED.display_order,
                parent_type_id=EXCLUDED.parent_type_id
        """), {"slug": slug, "name": name, "code": code, "display_order": order})

    child_slugs = tuple(row[0] for row in children)
    conn.execute(sa.text("""
        INSERT INTO master_service_types
            (master_service_id, service_type_id, is_required, is_default, is_active)
        SELECT ms.id, child.id, true, false, true
        FROM master_services ms CROSS JOIN service_types child
        WHERE lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND child.slug IN :slugs
        ON CONFLICT (master_service_id, service_type_id) DO UPDATE SET
            is_required=true, is_active=true
    """).bindparams(sa.bindparam("slugs", expanding=True)), {"slugs": child_slugs})
    conn.execute(sa.text("""
        INSERT INTO service_type_mappings
            (type_id, category_id, service_group_id, service_id,
             customer_visible, provider_visible, status, display_order)
        SELECT child.id, ms.category_id, ms.service_group_id, ms.id,
               true, true, 'active', child.display_order
        FROM master_services ms CROSS JOIN service_types child
        WHERE lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND child.slug IN :slugs
        ON CONFLICT (type_id, category_id, service_group_id, service_id)
        DO UPDATE SET customer_visible=true, provider_visible=true,
                      status='active', display_order=EXCLUDED.display_order
    """).bindparams(sa.bindparam("slugs", expanding=True)), {"slugs": child_slugs})

    # The former Commode leaf is now navigation-only. Never copy its one old
    # amount into two variants whose labour may differ.
    conn.execute(sa.text("""
        UPDATE tenant_service_types tst SET
            is_enabled=false, tenant_min_price=NULL, tenant_max_price=NULL,
            tenant_price_adjustment=NULL, updated_at=now()
        FROM service_types st
        WHERE tst.service_type_id=st.id
          AND st.slug='plumbing-commode-installation'
    """))
    conn.execute(sa.text("""
        UPDATE tenant_service_brands tsb SET
            is_enabled=false, tenant_min_price=NULL, tenant_max_price=NULL,
            updated_at=now()
        FROM service_types st
        WHERE tsb.service_type_id=st.id
          AND st.slug='plumbing-commode-installation'
    """))
    conn.execute(sa.text("""
        UPDATE tenant_services ts SET setup_status='draft', published_at=NULL,
            last_active_step='services-pricing', updated_at=now()
        FROM master_services ms, job_types jt
        WHERE ts.master_service_id=ms.id AND ts.job_type_id=jt.id
          AND lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND jt.key='installation' AND ts.deleted_at IS NULL
    """))

    # Root question shows Tap, Basin, Commode and Other. The conditional
    # second question shows only children of the Commode node.
    conn.execute(sa.text("""
        UPDATE catalog_questions cq SET
            validation=(CASE WHEN jsonb_typeof(cq.validation)='object'
                         THEN cq.validation ELSE '{}'::jsonb END)
                || '{"type_tree_level":"root"}'::jsonb,
            updated_at=now()
        FROM master_services ms, job_types jt
        WHERE cq.master_service_id=ms.id AND cq.job_type_id=jt.id
          AND lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND jt.key='installation' AND cq.question_key='fixture_type'
    """))
    conn.execute(sa.text("""
        INSERT INTO catalog_questions
            (master_service_id, job_type_id, question_key, label, input_type,
             answer_source, dimension_id, required, customer_visible,
             tenant_setup_visible, deepseek_enabled, validation,
             display_order, is_active)
        SELECT ms.id, jt.id, 'commode_type', 'Which commode type?',
               'single_select', 'dimension', cd.id, true, true, false, true,
               '{"type_parent_slug":"plumbing-commode-installation"}'::jsonb,
               20, true
        FROM master_services ms CROSS JOIN job_types jt CROSS JOIN catalog_dimensions cd
        WHERE lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND jt.key='installation' AND cd.key='type'
        ON CONFLICT (master_service_id, job_type_id, question_key) DO UPDATE SET
            label=EXCLUDED.label, input_type=EXCLUDED.input_type,
            answer_source=EXCLUDED.answer_source,
            dimension_id=EXCLUDED.dimension_id, required=true,
            customer_visible=true, validation=EXCLUDED.validation,
            display_order=EXCLUDED.display_order, is_active=true
    """))
    conn.execute(sa.text("""
        INSERT INTO catalog_question_rules
            (question_id, condition_type, ref_id, expected_value)
        SELECT child.id, 'answer_equals', parent.id,
               'plumbing-commode-installation'
        FROM catalog_questions child
        JOIN catalog_questions parent
          ON parent.master_service_id=child.master_service_id
         AND parent.job_type_id=child.job_type_id
         AND parent.question_key='fixture_type'
        JOIN master_services ms ON ms.id=child.master_service_id
        WHERE child.question_key='commode_type'
          AND lower(ms.service_name)='plumbing'
          AND NOT EXISTS (
              SELECT 1 FROM catalog_question_rules r
              WHERE r.question_id=child.id
                AND r.condition_type='answer_equals'
                AND r.expected_value='plumbing-commode-installation'
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
        DELETE FROM catalog_question_rules r USING catalog_questions q,
            master_services ms
        WHERE r.question_id=q.id AND q.master_service_id=ms.id
          AND lower(ms.service_name)='plumbing' AND q.question_key='commode_type'
    """))
    conn.execute(sa.text("""
        DELETE FROM catalog_questions q USING master_services ms
        WHERE q.master_service_id=ms.id AND lower(ms.service_name)='plumbing'
          AND q.question_key='commode_type'
    """))
    conn.execute(sa.text("""
        UPDATE catalog_questions q SET
            validation=NULLIF(COALESCE(q.validation, '{}'::jsonb) - 'type_tree_level', '{}'::jsonb),
            updated_at=now()
        FROM master_services ms
        WHERE q.master_service_id=ms.id AND lower(ms.service_name)='plumbing'
          AND q.question_key='fixture_type'
    """))
    conn.execute(sa.text("""
        UPDATE service_type_mappings stm SET status='inactive', updated_at=now()
        FROM service_types st
        WHERE stm.type_id=st.id
          AND st.slug IN ('plumbing-western-commode-installation',
                          'plumbing-indian-commode-installation')
    """))
    conn.execute(sa.text("""
        UPDATE master_service_types mst SET is_active=false, updated_at=now()
        FROM service_types st
        WHERE mst.service_type_id=st.id
          AND st.slug IN ('plumbing-western-commode-installation',
                          'plumbing-indian-commode-installation')
    """))
    conn.execute(sa.text("""
        UPDATE service_types SET status='archived', is_active=false,
            deleted_at=now(), updated_at=now()
        WHERE slug IN ('plumbing-western-commode-installation',
                       'plumbing-indian-commode-installation')
    """))
    op.drop_index("ix_service_types_parent", table_name="service_types")
    op.drop_column("service_types", "parent_type_id")
