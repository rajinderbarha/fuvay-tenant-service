"""Retention for the photos a job produces.

Revision ID: 323
Revises: 322

TWO KINDS OF PHOTO, TWO DIFFERENT JOBS

A job accumulates images from both ends and they are not the same thing:

  what the CUSTOMER sent    `home_service_booking_drafts.photo_urls`,
                            `service_bookings.customer_photo_urls`
                            -- a picture of their broken tap. Once the work is
                            done this has served its purpose.

  the COMPLETION PROOF      `service_job_completion_proofs.before_photo_ids` /
                            `after_photo_ids`
                            -- the provider's evidence that the work was done
                            properly. This is what settles a warranty claim or
                            a complaint, and deleting it on the same schedule
                            would destroy the platform's defence in exactly the
                            cases it is needed.

So customer photos go shortly after completion, and completion proofs are kept
until the job's warranty has expired plus a margin.

RETENTION IS ADMIN POLICY, AND DRIVEN BY A DATE

Both periods sit on the monetization policy with everything else an operator
tunes. The sweep purges what is PAST ITS DATE rather than "everything, on
Sunday": a missed run then costs latency instead of silently skipping a week,
and re-running is harmless.

`media_purged_at` marks a record whose images have gone, so the sweep is
idempotent and a purge is visible rather than inferred from an empty column.
"""
from alembic import op

revision = "323"
down_revision = "322"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ADD COLUMN IF NOT EXISTS customer_photo_retention_days   INTEGER NULL,
        ADD COLUMN IF NOT EXISTS completion_proof_retention_days INTEGER NULL
    """)
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        DROP CONSTRAINT IF EXISTS ck_vmp_retention
    """)
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ADD CONSTRAINT ck_vmp_retention CHECK (
            (customer_photo_retention_days   IS NULL OR customer_photo_retention_days   >= 0) AND
            (completion_proof_retention_days IS NULL OR completion_proof_retention_days >= 0)
        )
    """)

    # Marks a job whose photos have already gone, so the sweep never revisits
    # it and a purge can be seen rather than inferred from an empty column.
    op.execute("""
        ALTER TABLE service_jobs
        ADD COLUMN IF NOT EXISTS customer_media_purged_at   TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS completion_media_purged_at TIMESTAMPTZ NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_service_jobs_customer_media_unpurged
        ON service_jobs (status, updated_at)
        WHERE customer_media_purged_at IS NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_service_jobs_completion_media_unpurged
        ON service_jobs (warranty_expires_at)
        WHERE completion_media_purged_at IS NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_service_jobs_completion_media_unpurged")
    op.execute("DROP INDEX IF EXISTS ix_service_jobs_customer_media_unpurged")
    op.execute("ALTER TABLE service_jobs DROP COLUMN IF EXISTS completion_media_purged_at")
    op.execute("ALTER TABLE service_jobs DROP COLUMN IF EXISTS customer_media_purged_at")
    op.execute("ALTER TABLE vertical_monetization_policies DROP CONSTRAINT IF EXISTS ck_vmp_retention")
    op.execute("ALTER TABLE vertical_monetization_policies DROP COLUMN IF EXISTS completion_proof_retention_days")
    op.execute("ALTER TABLE vertical_monetization_policies DROP COLUMN IF EXISTS customer_photo_retention_days")
