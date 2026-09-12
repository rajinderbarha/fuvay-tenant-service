"""Deliver the saved provider warranty as a PDF after the Instagram rating ask."""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlsplit

import structlog

from app.engines.final_records.warranty_certificate import (
    issue_warranty_certificate, render_certificate_pdf,
)
from app.engines.media.storage import MediaStorageService
from app.engines.messaging_gateway import meta_client
from app.engines.messaging_gateway.constants import CHANNEL_INSTAGRAM

logger = structlog.get_logger(__name__)
DELIVERY_KEY = "instagram_warranty_pdf"


def _https_url(value: str | None) -> bool:
    try:
        parsed = urlsplit(value or "")
        return bool(parsed.scheme == "https" and parsed.hostname and not parsed.username
                    and not parsed.password)
    except ValueError:
        return False


async def send_warranty_certificate(db, job, thread, *, config: dict) -> bool:
    """Best-effort delivery, isolated from the already successful rating ask.

    Completion has already issued the immutable warranty snapshot. Store its
    PDF through the configured document driver, which uses a random file name;
    keep the storage reference and successful-send marker on the completed job
    so a retry reuses the document and does not resend a successful delivery.
    """
    job_id = str(job.id)
    if (thread.channel != CHANNEL_INSTAGRAM or job.status != "completed"
            or not job.customer_id or job.customer_id != thread.customer_id):
        return False
    try:
        snapshot = await issue_warranty_certificate(db, job)
        # A storage configuration query can fail at the database level. A
        # savepoint keeps that failure from rolling back the rating question.
        async with db.begin_nested():
            return await _send(db, job, thread, snapshot, config)
    except Exception as exc:  # the staff completion and rating must still succeed
        logger.warning("messaging_gateway.warranty.failed", job_id=job_id,
                       error_type=type(exc).__name__)
        return False


async def _send(db, job, thread, snapshot: dict, config: dict) -> bool:
    delivery = dict((job.completion_data or {}).get(DELIVERY_KEY) or {})
    if delivery.get("sent_at"):
        return True

    document_url = delivery.get("document_url")
    if not _https_url(document_url):
        pdf = render_certificate_pdf(snapshot)
        stored = await MediaStorageService(db=db).store_file(
            file_bytes=pdf,
            original_filename=f"warranty-{job.warranty_certificate_number}.pdf",
            mime_type="application/pdf",
            media_context="warranty_certificate",
            owner_id=str(job.customer_id),
        )
        document_url = stored.public_url
        if not _https_url(document_url):
            logger.warning("messaging_gateway.warranty.no_public_https_url",
                           job_id=str(job.id), storage_driver=stored.storage_driver)
            return False
        delivery = {
            "document_url": document_url,
            "storage_driver": stored.storage_driver,
            "storage_key": stored.storage_key,
            "storage_bucket": stored.storage_bucket,
            "certificate_number": snapshot.get("certificate_number"),
        }
        job.completion_data = {**(job.completion_data or {}), DELIVERY_KEY: delivery}
        await db.flush()

    result = await meta_client.send_document(
        thread.channel_user_id, document_url, channel=thread.channel, config=config,
    )
    if not result.get("sent"):
        logger.warning("messaging_gateway.warranty.send_failed", job_id=str(job.id),
                       reason=result.get("reason"), status=result.get("status"))
        return False

    now = datetime.now(timezone.utc)
    job.completion_data = {
        **(job.completion_data or {}),
        DELIVERY_KEY: {**delivery, "sent_at": now.isoformat(), "thread_id": str(thread.id)},
    }
    thread.last_outbound_at = now
    await db.flush()
    logger.info("messaging_gateway.warranty.sent", job_id=str(job.id), thread_id=str(thread.id))
    return True
