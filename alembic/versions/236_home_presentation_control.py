"""Backend control over how Home presents itself.

Two things the customer app could not be told by the backend:

1. HOW a banner should look and WHERE it belongs. `customer_campaigns` carried
   copy, artwork, targeting and a date window, but every banner rendered in the
   one carousel at the top -- so a festival promotion, a small reminder strip and
   a full hero could not be distinguished, and admin had no way to place one
   lower down the screen. `display_style` and `placement` say both, with
   `accent_color`/`badge_text` for the festival treatment.

2. WHICH sections appear at all, and in what order. That was hardcoded in the
   app, so re-ordering Home or hiding a section needed an app release.
   `home_section_settings` holds one row per section the app knows how to
   render; the customer payload returns the enabled ones in order.

The section rows are SEEDED, not created on demand: a key the app does not know
how to render is useless, so admin picks from a fixed vocabulary rather than
inventing keys. Adding a section is deliberately a code + migration change.

Revision ID: 236
Revises: 235
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "236"
down_revision = "235"
branch_labels = None
depends_on = None

# (key, order, default_enabled) -- order in tens so a later insert between two
# existing sections does not need every row renumbered.
SECTIONS = [
    ("active_booking",   10, True),
    ("campaign_top",     20, True),
    ("quick_problems",   30, True),
    ("service_grid",     40, True),
    ("campaign_mid",     50, True),
    ("assistant_entry",  60, True),
    ("global_services",  70, True),
    ("how_it_works",     80, True),
    ("trust_benefits",   90, True),
    ("campaign_bottom", 100, True),
]


def upgrade() -> None:
    op.add_column("customer_campaigns", sa.Column(
        "display_style", sa.String(30), nullable=False, server_default="hero"))
    op.add_column("customer_campaigns", sa.Column(
        "placement", sa.String(30), nullable=False, server_default="campaign_top"))
    op.add_column("customer_campaigns", sa.Column("accent_color", sa.String(9), nullable=True))
    op.add_column("customer_campaigns", sa.Column("badge_text", sa.String(40), nullable=True))
    op.create_index(
        "ix_cc_placement_style", "customer_campaigns", ["placement", "display_style"])

    op.create_table(
        "home_section_settings",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("section_key", sa.String(50), nullable=False, unique=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="100"),
        # Null means "use the wording the app ships with"; an override is for
        # renaming a section, never for inventing one.
        sa.Column("title_override", sa.String(120), nullable=True),
        sa.Column("updated_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_hss_order", "home_section_settings", ["display_order"])

    for key, order, enabled in SECTIONS:
        op.execute(
            sa.text(
                "INSERT INTO home_section_settings (section_key, is_enabled, display_order) "
                "VALUES (:k, :e, :o) ON CONFLICT (section_key) DO NOTHING"
            ).bindparams(k=key, e=enabled, o=order)
        )


def downgrade() -> None:
    op.drop_index("ix_hss_order", table_name="home_section_settings")
    op.drop_table("home_section_settings")
    op.drop_index("ix_cc_placement_style", table_name="customer_campaigns")
    for column in ("badge_text", "accent_color", "placement", "display_style"):
        op.drop_column("customer_campaigns", column)
