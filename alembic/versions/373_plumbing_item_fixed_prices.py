"""Model Plumbing Installation as individually priced catalog items.

Revision ID: 373
Revises: 372
"""
from alembic import op
import sqlalchemy as sa


revision = "373"
down_revision = "372"
branch_labels = None
depends_on = None


ITEMS = (
    ("plumbing-tap-change", "Tap change", "PLUMBING_TAP_CHANGE", 10),
    ("plumbing-wash-basin-installation", "Wash basin installation", "PLUMBING_WASH_BASIN_INSTALLATION", 20),
    ("plumbing-commode-installation", "Commode installation", "PLUMBING_COMMODE_INSTALLATION", 30),
    ("plumbing-other-fixture-installation", "Other fixture installation", "PLUMBING_OTHER_FIXTURE_INSTALLATION", 40),
)


def upgrade() -> None:
    conn = op.get_bind()

    # Reuse the global Type catalog and its media fields.  The slugs are
    # service-qualified so they cannot collide with similarly named types.
    for slug, name, code, order in ITEMS:
        conn.execute(sa.text("""
            INSERT INTO service_types
                (category_id, name, slug, code, type_family, customer_visible,
                 status, display_order, is_active)
            SELECT ms.category_id, :name, :slug, :code, 'Appliance Type',
                   true, 'active', :display_order, true
            FROM master_services ms
            WHERE lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
            ORDER BY ms.created_at LIMIT 1
            ON CONFLICT (slug) DO UPDATE SET
                name=EXCLUDED.name, code=EXCLUDED.code,
                customer_visible=true, status='active', is_active=true,
                deleted_at=NULL, display_order=EXCLUDED.display_order
        """), {"slug": slug, "name": name, "code": code, "display_order": order})

    slugs = tuple(row[0] for row in ITEMS)
    conn.execute(sa.text("""
        UPDATE master_service_types mst SET is_active=false, updated_at=now()
        FROM master_services ms, service_types st
        WHERE mst.master_service_id=ms.id AND mst.service_type_id=st.id
          AND lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND st.slug NOT IN :slugs
    """).bindparams(sa.bindparam("slugs", expanding=True)), {"slugs": slugs})
    conn.execute(sa.text("""
        INSERT INTO master_service_types
            (master_service_id, service_type_id, is_required, is_default, is_active)
        SELECT ms.id, st.id, true, false, true
        FROM master_services ms CROSS JOIN service_types st
        WHERE lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND st.slug IN :slugs
        ON CONFLICT (master_service_id, service_type_id) DO UPDATE SET
            is_required=true, is_active=true
    """).bindparams(sa.bindparam("slugs", expanding=True)), {"slugs": slugs})

    conn.execute(sa.text("""
        UPDATE service_type_mappings stm SET status='inactive', updated_at=now()
        FROM master_services ms, service_types st
        WHERE stm.service_id=ms.id AND stm.type_id=st.id
          AND lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND st.slug NOT IN :slugs
    """).bindparams(sa.bindparam("slugs", expanding=True)), {"slugs": slugs})
    conn.execute(sa.text("""
        INSERT INTO service_type_mappings
            (type_id, category_id, service_group_id, service_id,
             customer_visible, provider_visible, status, display_order)
        SELECT st.id, ms.category_id, ms.service_group_id, ms.id,
               true, true, 'active', st.display_order
        FROM master_services ms CROSS JOIN service_types st
        WHERE lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND st.slug IN :slugs
        ON CONFLICT (type_id, category_id, service_group_id, service_id)
        DO UPDATE SET customer_visible=true, provider_visible=true,
                      status='active', display_order=EXCLUDED.display_order
    """).bindparams(sa.bindparam("slugs", expanding=True)), {"slugs": slugs})

    # Plumbing Installation is a fixed menu: Type is required for matching
    # and is the price-bearing dimension.  Explicit selection prevents an
    # unpriced catalog item from being exposed through an "all" mode.
    conn.execute(sa.text("""
        UPDATE service_job_dimensions sjd SET
            enabled=true, required=true, ask_customer=true,
            show_during_tenant_setup=true, use_for_matching=true,
            affects_price=true, allow_tenant_override=true,
            allow_all_coverage=false, allow_selected_coverage=true,
            allow_exclusion_coverage=false, updated_at=now()
        FROM master_services ms, job_types jt, catalog_dimensions cd
        WHERE sjd.master_service_id=ms.id AND sjd.job_type_id=jt.id
          AND sjd.dimension_id=cd.id AND lower(ms.service_name)='plumbing'
          AND ms.deleted_at IS NULL AND jt.key='installation' AND cd.key='type'
    """))
    conn.execute(sa.text("""
        INSERT INTO service_job_dimensions
            (master_service_id, job_type_id, dimension_id, enabled, required,
             ask_customer, show_during_tenant_setup, use_for_matching,
             affects_price, allow_tenant_override, allow_all_coverage,
             allow_selected_coverage, allow_exclusion_coverage, display_order)
        SELECT ms.id, jt.id, cd.id, true, true, true, true, true, true,
               true, false, true, false, 10
        FROM master_services ms CROSS JOIN job_types jt CROSS JOIN catalog_dimensions cd
        WHERE lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND jt.key='installation' AND cd.key='type'
        ON CONFLICT (master_service_id, job_type_id, dimension_id) DO NOTHING
    """))

    # Append, do not mutate, the workflow version old bookings reference.
    conn.execute(sa.text("""
        WITH old AS (
            UPDATE service_job_workflow sjw SET
                is_current=false, superseded_at=now(), effective_to=now(), updated_at=now()
            FROM master_services ms, job_types jt
            WHERE sjw.master_service_id=ms.id AND sjw.job_type_id=jt.id
              AND sjw.is_current=true AND lower(ms.service_name)='plumbing'
              AND ms.deleted_at IS NULL AND jt.key='installation'
              AND sjw.pricing_behavior <> 'fixed'
            RETURNING sjw.*
        )
        INSERT INTO service_job_workflow
            (master_service_id, job_type_id, inspection_required,
             quote_approval_required, checklist_required, schedule_required,
             address_required, technician_required, service_area_required,
             availability_required, pricing_behavior, version_number,
             is_current, status, supersedes_workflow_id, effective_from,
             created_by, approved_by, published_by, change_reason,
             published_at, allows_cancellation, allows_reschedule,
             requires_direct_payment_record, steps_json, transitions_json)
        SELECT master_service_id, job_type_id, inspection_required,
               quote_approval_required, checklist_required, schedule_required,
               address_required, technician_required, service_area_required,
               availability_required, 'fixed', version_number + 1,
               true, 'published', id, now(), created_by, approved_by,
               published_by, 'Exact fixed price per Plumbing installation item',
               now(), allows_cancellation, allows_reschedule,
               requires_direct_payment_record, steps_json, transitions_json
        FROM old
    """))

    # The customer question now reads directly from the mapped Type library;
    # its answer therefore writes offering_type_id without label heuristics.
    conn.execute(sa.text("""
        UPDATE catalog_questions cq SET
            answer_source='dimension', dimension_id=cd.id,
            input_type='single_select', required=true, customer_visible=true,
            label='What needs to be installed?', updated_at=now()
        FROM master_services ms, job_types jt, catalog_dimensions cd
        WHERE cq.master_service_id=ms.id AND cq.job_type_id=jt.id
          AND lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND jt.key='installation' AND cd.key='type'
          AND cq.question_key='fixture_type'
    """))
    conn.execute(sa.text("""
        UPDATE catalog_question_options cqo SET is_active=false, updated_at=now()
        FROM catalog_questions cq, master_services ms, job_types jt
        WHERE cqo.question_id=cq.id AND cq.master_service_id=ms.id
          AND cq.job_type_id=jt.id AND lower(ms.service_name)='plumbing'
          AND ms.deleted_at IS NULL AND jt.key='installation'
          AND cq.question_key='fixture_type'
    """))

    # Never fabricate four item prices from the old service-level range.
    # Existing jobs retain their immutable booking/price snapshots.
    conn.execute(sa.text("""
        UPDATE tenant_services ts SET
            tenant_base_price=NULL, tenant_min_price=NULL, tenant_max_price=NULL,
            requires_type=true, type_coverage_mode='selected',
            setup_status='draft', published_at=NULL,
            last_active_step='services-pricing', updated_at=now()
        FROM master_services ms, job_types jt
        WHERE ts.master_service_id=ms.id AND ts.job_type_id=jt.id
          AND lower(ms.service_name)='plumbing' AND ms.deleted_at IS NULL
          AND jt.key='installation' AND ts.deleted_at IS NULL
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
        UPDATE service_job_dimensions sjd SET
            required=false, affects_price=false, allow_all_coverage=true,
            allow_exclusion_coverage=true, updated_at=now()
        FROM master_services ms, job_types jt, catalog_dimensions cd
        WHERE sjd.master_service_id=ms.id AND sjd.job_type_id=jt.id
          AND sjd.dimension_id=cd.id AND lower(ms.service_name)='plumbing'
          AND jt.key='installation' AND cd.key='type'
    """))
    conn.execute(sa.text("""
        UPDATE service_type_mappings stm SET status='inactive'
        FROM service_types st, master_services ms
        WHERE stm.type_id=st.id AND stm.service_id=ms.id
          AND lower(ms.service_name)='plumbing' AND st.slug IN :slugs
    """).bindparams(sa.bindparam("slugs", expanding=True)), {"slugs": tuple(row[0] for row in ITEMS)})
