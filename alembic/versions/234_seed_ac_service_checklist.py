"""Seed a real, published AC checklist so checklists actually populate.

The checklist engine was complete but had NO CONTENT: 0 sections, 0 items, 0
job-type mappings. `get_applicable_mappings` therefore returned nothing for
every job, no `job_checklist_instances` were ever created, and the technician's
checklist was permanently empty -- indistinguishable from the feature being
broken.

This seeds a STARTER checklist the admin owns and can edit: it is authored
through the same tables the admin UI writes
(template -> version -> sections -> items -> PUBLISHED -> job-type mapping),
so nothing here is a special case the real authoring flow cannot manage.

Deliberately conservative content: only steps a technician genuinely performs
on an AC visit, phrased as verifiable checks. `usage='OPTIONAL'` and
`completion_gate='NONE'` so an incomplete checklist cannot BLOCK a live job --
turning it into a hard gate is an explicit admin decision, not something a seed
should impose on running work.

Mapped to every job type of AC Service, because a mapping is scoped per
(job_type, phase) and a customer's draft can resolve to any of them.

Idempotent by template code: re-running does not duplicate.

Revision ID: 234
Revises: 233
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "234"
down_revision = "233"
branch_labels = None
depends_on = None

TEMPLATE_CODE = "ac-service-standard-v1"

# (section title, [(label, item_type, is_required, evidence_required, help_text)])
SECTIONS = [
    ("Before starting", [
        ("Confirmed the reported problem with the customer", "YES_NO", True, False,
         "Check what the customer told us still matches what you find."),
        ("Checked power supply and stabiliser", "YES_NO", True, False, None),
        ("Photographed the unit before any work", "PHOTO", True, True,
         "One clear photo of the indoor unit before you begin."),
    ]),
    ("Inspection", [
        ("Measured cooling temperature at the vent", "NUMBER", True, False,
         "Record the temperature in degrees Celsius."),
        ("Checked gas pressure", "YES_NO", True, False, None),
        ("Inspected and cleaned air filters", "YES_NO", True, False, None),
        ("Checked drainage for blockage or leaks", "YES_NO", True, False, None),
        ("Inspected electrical connections and wiring", "YES_NO", True, False, None),
    ]),
    ("Before leaving", [
        ("Tested the unit with the customer present", "YES_NO", True, False, None),
        ("Photographed the completed work", "PHOTO", True, True,
         "One photo showing the unit working after service."),
        ("Explained what was done and any follow-up needed", "YES_NO", True, False, None),
        ("Left the work area clean", "YES_NO", True, False, None),
    ]),
]


def upgrade() -> None:
    conn = op.get_bind()

    service_id = conn.execute(sa.text(
        "SELECT id FROM master_services WHERE service_name = 'AC Service' AND is_active"
    )).scalar()
    if not service_id:
        return

    existing = conn.execute(sa.text(
        "SELECT id FROM checklist_templates WHERE code = :code"
    ), {"code": TEMPLATE_CODE}).scalar()
    if existing:
        return   # already seeded

    template_id = conn.execute(sa.text(
        """
        INSERT INTO checklist_templates (
            id, name, code, description, purpose, status, owner_scope,
            tenant_id, created_by_user_id, created_at, updated_at
        ) VALUES (
            gen_random_uuid(), 'AC Service — Standard Visit', :code,
            'Standard field checks for an AC service visit. Providers choose which of these their technicians must complete.',
            'INSPECTION', 'active', 'PLATFORM', NULL, NULL, NOW(), NOW()
        ) RETURNING id
        """
    ), {"code": TEMPLATE_CODE}).scalar()

    # Published immediately: a DRAFT version is invisible to tenants by design
    # (they must never select from an admin's unfinished edit), so a draft-only
    # seed would leave the feature exactly as empty as before.
    version_id = conn.execute(sa.text(
        """
        INSERT INTO checklist_template_versions (
            id, checklist_template_id, version_number, status, change_summary,
            published_by, published_at, created_at, updated_at
        ) VALUES (
            gen_random_uuid(), :tid, 1, 'PUBLISHED', 'Initial seeded standard checklist.',
            NULL, NOW(), NOW(), NOW()
        ) RETURNING id
        """
    ), {"tid": template_id}).scalar()

    for section_order, (title, items) in enumerate(SECTIONS):
        section_id = conn.execute(sa.text(
            """
            INSERT INTO checklist_sections (
                id, checklist_template_version_id, title, display_order, created_at, updated_at
            ) VALUES (gen_random_uuid(), :vid, :title, :ord, NOW(), NOW())
            RETURNING id
            """
        ), {"vid": version_id, "title": title, "ord": section_order}).scalar()

        for item_order, (label, item_type, required, evidence, help_text) in enumerate(items):
            conn.execute(sa.text(
                """
                INSERT INTO checklist_items (
                    id, checklist_section_id, item_type, label, help_text,
                    is_required, evidence_required, min_evidence_count, max_evidence_count,
                    display_order, customer_visible, created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), :sid, :itype, :label, :help,
                    :req, :ev, :minev, 3,
                    :ord, true, NOW(), NOW()
                )
                """
            ), {
                "sid": section_id, "itype": item_type, "label": label, "help": help_text,
                "req": required, "ev": evidence, "minev": 1 if evidence else 0,
                "ord": item_order,
            })

    # Map to EVERY job type of AC Service: a mapping is scoped per
    # (job_type, phase) and a draft can resolve to any of them.
    job_types = conn.execute(sa.text(
        "SELECT DISTINCT id FROM master_service_job_types WHERE master_service_id = :sid"
    ), {"sid": service_id}).scalars().all()

    for order, msjt_id in enumerate(job_types):
        conn.execute(sa.text(
            """
            INSERT INTO job_type_checklist_mappings (
                id, master_service_job_type_id, service_job_workflow_id,
                checklist_template_version_id, phase, usage, actor, completion_gate,
                condition_rules, display_order, status, created_by, updated_by,
                created_at, updated_at
            ) VALUES (
                gen_random_uuid(), :msjt, NULL, :vid, 'INSPECTION',
                'OPTIONAL', 'TECHNICIAN', 'NONE',
                NULL, :ord, 'active', NULL, NULL, NOW(), NOW()
            )
            ON CONFLICT (master_service_job_type_id, checklist_template_version_id, phase)
            DO NOTHING
            """
        ), {"msjt": msjt_id, "vid": version_id, "ord": order})

    total = sum(len(items) for _, items in SECTIONS)
    print(f"[234] seeded AC checklist: {len(SECTIONS)} sections, {total} points, "
          f"mapped to {len(job_types)} job type(s)")


def downgrade() -> None:
    conn = op.get_bind()
    version_ids = conn.execute(sa.text(
        "SELECT v.id FROM checklist_template_versions v "
        "JOIN checklist_templates t ON t.id = v.checklist_template_id "
        "WHERE t.code = :code"
    ), {"code": TEMPLATE_CODE}).scalars().all()
    for vid in version_ids:
        conn.execute(sa.text(
            "DELETE FROM tenant_service_checklist_items WHERE checklist_template_version_id = :v"
        ), {"v": vid})
        conn.execute(sa.text(
            "DELETE FROM job_type_checklist_mappings WHERE checklist_template_version_id = :v"
        ), {"v": vid})
        conn.execute(sa.text(
            "DELETE FROM checklist_items WHERE checklist_section_id IN "
            "(SELECT id FROM checklist_sections WHERE checklist_template_version_id = :v)"
        ), {"v": vid})
        conn.execute(sa.text(
            "DELETE FROM checklist_sections WHERE checklist_template_version_id = :v"
        ), {"v": vid})
    conn.execute(sa.text(
        "DELETE FROM checklist_template_versions WHERE checklist_template_id IN "
        "(SELECT id FROM checklist_templates WHERE code = :code)"
    ), {"code": TEMPLATE_CODE})
    conn.execute(sa.text("DELETE FROM checklist_templates WHERE code = :code"),
                 {"code": TEMPLATE_CODE})
