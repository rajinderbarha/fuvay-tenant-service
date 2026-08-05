"""TENANT-SERVICE-EMERGENCY-SURCHARGE: per-service extra charge for
emergency/priority bookings, set by the tenant during Services & Pricing.

Coverage & Availability already lets a tenant enable "emergency booking" at
the business level (bookingWindow.emergency_booking_allowed), but nowhere in
Services & Pricing could the tenant price that emergency service -- this
column closes that gap. Independent of tenant_visit_fee (inspection-based
Repair visit charge); a service can have both.

Revision ID: 195
Revises: 194
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "195"
down_revision = "194"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_services",
        sa.Column("tenant_emergency_surcharge", sa.Numeric(12, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenant_services", "tenant_emergency_surcharge")
