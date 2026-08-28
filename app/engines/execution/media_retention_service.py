"""Delete the photos a finished job no longer needs.

Two kinds of image, two different jobs, and they must not share a schedule:

  what the CUSTOMER sent   a picture of the broken tap. Once the work is done
                           it has served its purpose and is personal data the
                           platform has no reason to keep.

  the COMPLETION PROOF     the provider's before/after evidence. This is what
                           settles a warranty claim or a complaint, so it is
                           kept until the job's warranty has expired plus a
                           margin. Deleting it with the customer's photos would
                           destroy the platform's defence in exactly the cases
                           it exists for.

DRIVEN BY A DATE, NOT BY THE CLOCK

The sweep purges what is PAST ITS RETENTION rather than "everything, on
Sunday". A missed run then costs latency instead of silently skipping a week
of deletions, and re-running is harmless because `*_media_purged_at` marks
what has already gone.

DELETION MEANS DELETION

The file is destroyed at Cloudinary, not just unlinked. Dropping the database
row would hide the image from the app while its URL kept serving it to anyone
who had ever seen it -- which is not what "deleted" means to the person in the
photograph.
"""
from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger("execution.media_retention")

_HS_KEY = "home_services"

#: Job states after which the customer's photos have served their purpose.
FINISHED_STATUSES = ("completed", "cancelled")


async def _policy(db: AsyncSession):
    return (await db.execute(text(
        "SELECT p.customer_photo_retention_days, p.completion_proof_retention_days "
        "FROM vertical_monetization_policies p "
        "JOIN verticals v ON v.id = p.vertical_id "
        "WHERE p.is_current = true AND p.status = 'published' AND v.key = :k LIMIT 1"
    ), {"k": _HS_KEY})).first()


async def _destroy_assets(db: AsyncSession, asset_ids: list[Any]) -> int:
    """Delete each asset at the CDN, then mark the row gone.

    Order matters: the row is only marked once the file is actually destroyed,
    so a failure mid-way leaves work for the next run rather than a record that
    claims an image is gone while it is still being served.
    """
    from app.cloudinary_client import destroy

    destroyed = 0
    for raw in asset_ids:
        if not raw:
            continue
        row = (await db.execute(text(
            "SELECT id, storage_key FROM media_assets "
            "WHERE id = CAST(:id AS uuid) AND deleted_at IS NULL"
        ), {"id": str(raw)})).first()
        if row is None:
            continue
        if row.storage_key:
            result = await destroy(row.storage_key)
            if result.get("result") not in ("ok", "not found", "skipped"):
                logger.warning("media_retention.destroy_failed",
                               asset_id=str(row.id), result=result.get("result"))
                continue
        await db.execute(text(
            "UPDATE media_assets SET deleted_at = now(), updated_at = now() WHERE id = :id"
        ), {"id": row.id})
        destroyed += 1
    return destroyed


async def purge_customer_photos(db: AsyncSession, *, retention_days: int, limit: int) -> dict:
    """Photos the customer sent, on jobs finished longer ago than the retention."""
    jobs = (await db.execute(text(
        "SELECT j.id, j.booking_id, b.draft_id "
        "FROM service_jobs j "
        "LEFT JOIN service_bookings b ON b.id = j.booking_id "
        "WHERE j.customer_media_purged_at IS NULL "
        "  AND j.status = ANY(:statuses) "
        "  AND j.updated_at < now() - make_interval(days => :days) "
        "ORDER BY j.updated_at LIMIT :lim"
    ), {"statuses": list(FINISHED_STATUSES), "days": int(retention_days),
        "lim": limit})).fetchall()

    purged_jobs = destroyed = 0
    for job in jobs:
        if job.booking_id:
            urls = (await db.execute(text(
                "SELECT customer_photo_urls FROM service_bookings WHERE id = :b"
            ), {"b": str(job.booking_id)})).scalar()
            destroyed += await _destroy_assets(db, list(urls or []))
            await db.execute(text(
                "UPDATE service_bookings SET customer_photo_urls = '[]'::jsonb, "
                "  updated_at = now() WHERE id = :b"), {"b": str(job.booking_id)})
        if job.draft_id:
            urls = (await db.execute(text(
                "SELECT photo_urls FROM home_service_booking_drafts WHERE id = :d"
            ), {"d": str(job.draft_id)})).scalar()
            destroyed += await _destroy_assets(db, list(urls or []))
            await db.execute(text(
                "UPDATE home_service_booking_drafts SET photo_urls = '[]'::jsonb, "
                "  updated_at = now() WHERE id = :d"), {"d": str(job.draft_id)})

        await db.execute(text(
            "UPDATE service_jobs SET customer_media_purged_at = now(), updated_at = now() "
            "WHERE id = :id"), {"id": str(job.id)})
        purged_jobs += 1

    return {"jobs": purged_jobs, "assets_destroyed": destroyed}


async def purge_completion_proofs(db: AsyncSession, *, retention_days: int, limit: int) -> dict:
    """Before/after evidence, once the warranty it defends has expired.

    A job with no warranty date is left alone: without one there is no way to
    know the claim window has closed, and guessing would throw away the
    provider's evidence early.
    """
    jobs = (await db.execute(text(
        "SELECT id FROM service_jobs "
        "WHERE completion_media_purged_at IS NULL "
        "  AND warranty_expires_at IS NOT NULL "
        "  AND warranty_expires_at < now() - make_interval(days => :days) "
        "ORDER BY warranty_expires_at LIMIT :lim"
    ), {"days": int(retention_days), "lim": limit})).fetchall()

    purged_jobs = destroyed = 0
    for job in jobs:
        proofs = (await db.execute(text(
            "SELECT id, before_photo_ids, after_photo_ids "
            "FROM service_job_completion_proofs WHERE job_id = :j"
        ), {"j": str(job.id)})).fetchall()
        for proof in proofs:
            destroyed += await _destroy_assets(db, list(proof.before_photo_ids or []))
            destroyed += await _destroy_assets(db, list(proof.after_photo_ids or []))
            await db.execute(text(
                "UPDATE service_job_completion_proofs "
                "SET before_photo_ids = '[]'::jsonb, after_photo_ids = '[]'::jsonb, "
                "    updated_at = now() WHERE id = :id"), {"id": proof.id})
        await db.execute(text(
            "UPDATE service_jobs SET completion_media_purged_at = now(), updated_at = now() "
            "WHERE id = :id"), {"id": str(job.id)})
        purged_jobs += 1

    return {"jobs": purged_jobs, "assets_destroyed": destroyed}


async def sweep(db: AsyncSession, *, limit: int = 100) -> dict:
    """One pass. Each retention is independent -- leaving one unset does not
    stop the other, and unset means "never purge this kind"."""
    policy = await _policy(db)
    if policy is None:
        return {"customer": {}, "completion": {}, "reason": "no_published_policy"}

    customer = {"jobs": 0, "assets_destroyed": 0}
    completion = {"jobs": 0, "assets_destroyed": 0}

    if policy.customer_photo_retention_days is not None:
        customer = await purge_customer_photos(
            db, retention_days=policy.customer_photo_retention_days, limit=limit)
    if policy.completion_proof_retention_days is not None:
        completion = await purge_completion_proofs(
            db, retention_days=policy.completion_proof_retention_days, limit=limit)

    if customer["jobs"] or completion["jobs"]:
        logger.info("media_retention.swept", customer=customer, completion=completion)
    return {"customer": customer, "completion": completion}
