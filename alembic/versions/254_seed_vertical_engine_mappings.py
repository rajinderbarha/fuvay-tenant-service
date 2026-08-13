"""Seed canonical direct engine dependencies for every vertical.

Revision ID: 254
Revises: 253
"""
from alembic import op
import sqlalchemy as sa


revision = "254"
down_revision = "253"
branch_labels = None
depends_on = None


# Direct dependencies only; transitive engine-to-engine dependencies remain
# owned by engine_dependencies and are intentionally not duplicated here.
MAPPINGS = {
    "home_services": [
        ("service_catalog", True), ("booking", True), ("field_ops", True),
        ("job_dispatch", True), ("finance", True), ("payment", True),
        ("notification", True), ("media_vault", False),
        ("review_rating", False), ("chat", False),
        ("complaint_dispute", False), ("commission", False),
    ],
    "coaching": [
        ("service_catalog", True), ("appointment", True), ("leads_crm", True),
        ("payment", True), ("notification", True), ("media_vault", False),
    ],
    "real_estate": [
        ("service_catalog", True), ("real_estate", True), ("leads_crm", True),
        ("appointment", True), ("notification", True), ("media_vault", False),
    ],
    "beauty": [
        ("service_catalog", True), ("appointment", True), ("booking", True),
        ("payment", True), ("notification", True),
    ],
    "restaurant": [
        ("service_catalog", True), ("food_menu", True), ("inventory", True),
        ("payment", True), ("notification", True),
    ],
    "product_marketplace": [
        ("service_catalog", True), ("inventory", True), ("payment", True),
        ("notification", True),
    ],
    "professional_services": [
        ("service_catalog", True), ("appointment", True), ("leads_crm", True),
        ("payment", True), ("notification", True), ("media_vault", False),
    ],
}


def upgrade() -> None:
    connection = op.get_bind()
    for vertical_key, mappings in MAPPINGS.items():
        for sort_order, (engine_key, required) in enumerate(mappings):
            connection.execute(sa.text("""
                INSERT INTO vertical_engine_mappings
                    (vertical_id, engine_key, is_required, sort_order)
                SELECT v.id, :engine_key, :required, :sort_order
                  FROM verticals v
                 WHERE v.key = :vertical_key
                ON CONFLICT (vertical_id, engine_key) DO UPDATE SET
                    is_required = EXCLUDED.is_required,
                    sort_order = EXCLUDED.sort_order
            """), {
                "vertical_key": vertical_key, "engine_key": engine_key,
                "required": required, "sort_order": sort_order,
            })


def downgrade() -> None:
    connection = op.get_bind()
    for vertical_key, mappings in MAPPINGS.items():
        connection.execute(sa.text("""
            DELETE FROM vertical_engine_mappings
             WHERE vertical_id IN (SELECT id FROM verticals WHERE key = :vertical_key)
               AND engine_key = ANY(:engine_keys)
        """), {
            "vertical_key": vertical_key,
            "engine_keys": [engine_key for engine_key, _ in mappings],
        })
