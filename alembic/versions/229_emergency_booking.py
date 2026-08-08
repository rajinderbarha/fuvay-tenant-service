"""Record emergency bookings end-to-end.

Until now "emergency" existed only as four config flags
(tenant_booking_window_settings.emergency_booking_allowed,
provider_availability_rules.emergency_available,
provider_enabled_offerings.supports_emergency,
tenant_services.tenant_emergency_surcharge) plus a transient query
parameter on the slot endpoints. Nothing was ever STORED: a customer could
request an emergency visit, get a slot inside the waived notice period, and
the provider would receive an ordinary-looking booking with no indication it
was urgent -- and no surcharge, despite tenant_services carrying a rate for
exactly that.

Adds the three columns needed to carry it from draft -> booking -> job:

  is_emergency          the customer really did request an emergency visit
  emergency_surcharge   the amount actually charged for it, frozen at
                        confirmation (never recomputed later from a rate the
                        tenant may since have changed)

`service_jobs` gets `is_emergency` only -- money lives on the booking, the
job just needs to sort urgent work first in the provider's dashboard.

Revision ID: 229
Revises: 228
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "229"
down_revision = "228"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("home_service_booking_drafts",
                  sa.Column("is_emergency", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("service_bookings",
                  sa.Column("is_emergency", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("service_bookings",
                  sa.Column("emergency_surcharge", sa.Numeric(12, 2), nullable=True))
    op.add_column("service_jobs",
                  sa.Column("is_emergency", sa.Boolean(), nullable=False, server_default=sa.false()))
    # Urgent work must be cheap to find in the provider's dashboard, which
    # filters by tenant and sorts urgent-first.
    op.create_index("ix_service_jobs_tenant_emergency", "service_jobs",
                    ["tenant_id", "is_emergency"])


def downgrade() -> None:
    op.drop_index("ix_service_jobs_tenant_emergency", table_name="service_jobs")
    op.drop_column("service_jobs", "is_emergency")
    op.drop_column("service_bookings", "emergency_surcharge")
    op.drop_column("service_bookings", "is_emergency")
    op.drop_column("home_service_booking_drafts", "is_emergency")
