"""Stop matching technician arrival against the customer's map location.

Revision ID: 363
Revises: 362

Verified arrival refused "Reached Site" whenever the customer address had no
geocoded location, and the technician app never submits per-job GPS, so the
geofence could not be satisfied at all. The Home Services policy now records
arrival without a map match. Administrators can still re-enable verification
by publishing a new policy version.
"""
from alembic import op


revision = "363"
down_revision = "362"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ALTER COLUMN arrival_verification_enabled SET DEFAULT false
    """)
    # The live policy and any unpublished draft cloned from it. Archived
    # versions are left untouched as the historical record.
    op.execute("""
        UPDATE vertical_monetization_policies p
        SET arrival_verification_enabled = false
        FROM verticals v
        WHERE p.vertical_id = v.id AND v.key = 'home_services'
          AND (p.is_current = true OR p.status = 'draft')
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ALTER COLUMN arrival_verification_enabled SET DEFAULT true
    """)
