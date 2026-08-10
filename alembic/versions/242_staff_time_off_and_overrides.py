"""staff time off + per-technician date overrides

The availability board has always had cells for both and nothing to read: date exceptions
existed only at TENANT level (`tenant_availability_exceptions`, "the whole business is
shut on Diwali"), and time off had no table at all -- the "Add time off" button had
nowhere to write. Both were disclosed on the page as missing rather than faked, which is
why they are being added now instead of being quietly derived from something else.

These are per-STAFF, and deliberately separate from each other:

* An override CHANGES a technician's hours for one date ("Wed 29 Jul, 10:00-16:00", or
  closed). It is a schedule edit.
* Time off REMOVES them for a period, possibly several days, and carries a reason and an
  approval state. It is a request about a person, not a schedule.

Folding the two together would force one of them to lie about the other: a half-day
override is not leave, and a week of leave is not a set of daily hour edits.

Revision ID: 242
Revises: 241
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "242"
down_revision = "241"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "staff_availability_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        # The provider's own team member, not a user id: availability belongs to the
        # roster row, which is what the board and the resolver both read.
        sa.Column("staff_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("override_date", sa.Date(), nullable=False),
        # Null start/end with full_day_closed = the technician is simply not working that
        # day. Times present = they work those hours instead of their weekly pattern.
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("full_day_closed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reason", sa.String(300), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    # One override per person per day. Two rows for one date would leave the resolver
    # picking between contradictory answers, which is worse than refusing the second write.
    op.create_index("uq_staff_override_day", "staff_availability_overrides",
                    ["staff_member_id", "override_date"], unique=True)
    op.create_index("ix_staff_override_tenant_date", "staff_availability_overrides",
                    ["tenant_id", "override_date"])

    op.create_table(
        "staff_time_off",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Inclusive range: a single day is start == end, which keeps "Tue 4 Aug, all day"
        # and "Mon-Fri next week" the same shape.
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        # A part-day absence still blocks the hours it covers; all_day blocks the date.
        sa.Column("all_day", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("reason", sa.String(300), nullable=True),
        # Approved on creation by the owner today; the column exists so a request flow can
        # be added without a second migration and without back-filling meaning.
        sa.Column("status", sa.String(20), nullable=False, server_default="approved"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_staff_time_off_lookup", "staff_time_off",
                    ["tenant_id", "staff_member_id", "start_date", "end_date"])
    # Deliberately NOT unique: overlapping leave is a real thing (a half day inside a
    # longer booking, a correction), and refusing it at the schema level would push
    # providers into deleting and re-entering rather than recording what happened.


def downgrade() -> None:
    op.drop_index("ix_staff_time_off_lookup", table_name="staff_time_off")
    op.drop_table("staff_time_off")
    op.drop_index("ix_staff_override_tenant_date", table_name="staff_availability_overrides")
    op.drop_index("uq_staff_override_day", table_name="staff_availability_overrides")
    op.drop_table("staff_availability_overrides")
