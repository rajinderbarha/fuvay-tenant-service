"""ICON-EVERYWHERE (2026-08-05) -- additive icon_url columns on the 3
catalog entities that had no icon field at all: master_issue_types
("Problem"), checklist_templates ("Checklist"), catalog_questions
("Q&A"). Companion to the icon-picker feature already wired onto
Category/Subcategory/Master Service/Type/Brand -- those 5 already had
icon_url/logo_url columns; these 3 did not.

Revision ID: 226
Revises: 225
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "226"
down_revision = "225"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "master_issue_types",
        sa.Column("icon_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "checklist_templates",
        sa.Column("icon_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "catalog_questions",
        sa.Column("icon_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("catalog_questions", "icon_url")
    op.drop_column("checklist_templates", "icon_url")
    op.drop_column("master_issue_types", "icon_url")
