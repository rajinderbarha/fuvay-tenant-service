"""Remove badge assignments whose holder no longer exists.

Revision ID: 283
Revises: 282
"""

from alembic import op


revision = "283"
down_revision = "282"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM badge_assignments assignment
         WHERE assignment.target_type = 'tenant'
           AND NOT EXISTS (
               SELECT 1 FROM tenants tenant WHERE tenant.id = assignment.target_id
           )
        """
    )
    op.execute(
        """
        DELETE FROM badge_assignments assignment
         WHERE assignment.target_type IN ('staff', 'technician')
           AND NOT EXISTS (
               SELECT 1 FROM users member
                WHERE member.id = assignment.target_id
                  AND member.role = 'staff'
                  AND member.deleted_at IS NULL
           )
        """
    )


def downgrade() -> None:
    # Orphan rows have no valid holder to reconstruct.
    pass
