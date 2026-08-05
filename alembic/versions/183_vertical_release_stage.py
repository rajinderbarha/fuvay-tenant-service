"""BUSINESS-VERTICALS-CONTROL-CENTER: separate Release Stage from Runtime
Status.

Audit finding: `verticals.is_enabled` (runtime) and `verticals.is_beta`
(release maturity) are already two independent booleans -- not conflated
in the schema. The gap is that `is_beta` only expresses one release stage
("beta" vs not), with no way to represent Draft/Upcoming/Deprecated/
Retired. This migration adds an explicit `release_stage` column with the
full canonical set, backfilled from the existing `is_beta` flag so no
vertical's displayed state changes:

  is_beta = true  -> release_stage = 'beta'
  is_beta = false -> release_stage = 'production'

`is_beta` is left in place (not dropped) -- other code may still read it,
and this migration doesn't audit every caller. `release_stage` is
additive and forward-compatible: a future slice can migrate remaining
`is_beta` reads to `release_stage` and then retire the boolean once all
callers are confirmed migrated.

Revision ID: 183
Revises: 182
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "183"
down_revision = "182"
branch_labels = None
depends_on = None

RELEASE_STAGES = ("draft", "upcoming", "beta", "production", "deprecated", "retired")


def upgrade() -> None:
    op.add_column(
        "verticals",
        sa.Column("release_stage", sa.String(length=20), nullable=False, server_default="production"),
    )
    op.execute("UPDATE verticals SET release_stage = 'beta' WHERE is_beta = true")
    op.create_index("ix_verticals_release_stage", "verticals", ["release_stage"])
    op.create_check_constraint(
        "ck_verticals_release_stage_valid",
        "verticals",
        sa.text(f"release_stage IN {RELEASE_STAGES}"),
    )


def downgrade() -> None:
    op.drop_constraint("ck_verticals_release_stage_valid", "verticals", type_="check")
    op.drop_index("ix_verticals_release_stage", table_name="verticals")
    op.drop_column("verticals", "release_stage")
