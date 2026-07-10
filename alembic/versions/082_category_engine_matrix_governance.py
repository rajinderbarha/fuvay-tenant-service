"""Category Engine Matrix Governance — recommendation/dependency/runtime-risk fields + audit ownership.

Revision ID: 082
Revises: 081
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "082"
down_revision = "081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("category_engine_matrix",
        sa.Column("recommendation_status", sa.String(30), nullable=False,
                  server_default="not_applicable"))
    op.add_column("category_engine_matrix",
        sa.Column("dependency_status", sa.String(20), nullable=False,
                  server_default="not_checked"))
    op.add_column("category_engine_matrix",
        sa.Column("runtime_risk", sa.String(20), nullable=False,
                  server_default="low"))
    op.add_column("category_engine_matrix",
        sa.Column("status", sa.String(20), nullable=False,
                  server_default="active"))
    op.add_column("category_engine_matrix",
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True))
    op.add_column("category_engine_matrix",
        sa.Column("updated_by_user_id", UUID(as_uuid=True), nullable=True))

    op.create_index("ix_cem_recommendation", "category_engine_matrix", ["recommendation_status"])
    op.create_index("ix_cem_status", "category_engine_matrix", ["status"])


def downgrade() -> None:
    op.drop_index("ix_cem_status", table_name="category_engine_matrix")
    op.drop_index("ix_cem_recommendation", table_name="category_engine_matrix")
    op.drop_column("category_engine_matrix", "updated_by_user_id")
    op.drop_column("category_engine_matrix", "created_by_user_id")
    op.drop_column("category_engine_matrix", "status")
    op.drop_column("category_engine_matrix", "runtime_risk")
    op.drop_column("category_engine_matrix", "dependency_status")
    op.drop_column("category_engine_matrix", "recommendation_status")
