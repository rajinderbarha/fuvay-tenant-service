"""Preserve customer booking photos and note after draft finalization.

Revision ID: 312
Revises: 311

Booking drafts already stored Cloudinary-backed ``photo_urls`` and a
versioned answer snapshot, but finalization discarded the photos and exposed
no canonical customer note. Booking detail therefore always rendered "No
photos" even when the customer had attached evidence.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "312"
down_revision = "311"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_bookings",
        sa.Column(
            "customer_photo_urls",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("service_bookings", sa.Column("customer_note", sa.Text(), nullable=True))

    # Existing finalized records can be repaired from their immutable draft.
    # Only the customer-owned draft linked by the booking's unique draft_id is
    # consulted; job/staff media is deliberately not mixed into this field.
    op.execute(
        """
        UPDATE service_bookings AS booking
           SET customer_photo_urls = COALESCE(draft.photo_urls, '[]'::jsonb)
          FROM home_service_booking_drafts AS draft
         WHERE draft.id = booking.draft_id
        """
    )
    op.execute(
        """
        UPDATE service_bookings AS booking
           SET customer_note = (
               SELECT NULLIF(BTRIM(answer->>'answer_label'), '')
                 FROM jsonb_array_elements(
                      COALESCE(booking.answer_snapshot->'answers', '[]'::jsonb)
                 ) AS answer
                WHERE LOWER(COALESCE(answer->>'question_type', ''))
                      IN ('text', 'textarea', 'long_text')
                  AND NULLIF(BTRIM(answer->>'answer_label'), '') IS NOT NULL
                ORDER BY COALESCE((answer->>'sequence')::integer, 0) DESC
                LIMIT 1
           )
         WHERE booking.customer_note IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("service_bookings", "customer_note")
    op.drop_column("service_bookings", "customer_photo_urls")
