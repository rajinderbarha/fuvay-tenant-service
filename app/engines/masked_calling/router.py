"""Masked calling — staff endpoints + telephony status webhook.

No endpoint here returns a real phone number, in any state, for any role. That
is the engine's whole purpose: a number handed over once becomes a permanent
private channel, and the next job goes off-platform.

The webhook is authenticated by a shared secret and fails CLOSED when none is
configured -- an open status endpoint would let anyone forge a 'connected'
call and tick off the technician's obligation to actually speak to the customer.
"""
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_staff_or_above_mutation
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.masked_calling import service as svc

staff_router = APIRouter(prefix="/v1/staff/service-jobs", tags=["staff-masked-calling"])
webhook_router = APIRouter(prefix="/v1/webhooks/masked-calling", tags=["masked-calling-webhooks"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@staff_router.get(
    "/{job_id}/contact",
    summary="How to reach this job's customer (never a phone number)",
    description=(
        "Returns a display alias, whether a call can be placed, and why not if it "
        "cannot. Deliberately carries no phone number in any state -- calls are "
        "bridged by the platform so neither side sees the other's number."
    ),
)
async def get_contact(
    job_id: uuid.UUID, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await svc.describe_contact(db, job_id, uuid.UUID(str(user.tenant_id)))
    return ok(data, _rid(r), "staff-masked-contact")


@staff_router.post(
    "/{job_id}/call",
    summary="Call this job's customer through the platform",
    description=(
        "Bridges the technician and the customer using the platform's caller id. "
        "Neither number is revealed or stored. The binding is scoped to this job and "
        "expires, so it is never a standing private line. A CONNECTED call satisfies "
        "the 'call the customer first' task; a ring-out does not."
    ),
)
async def call_customer(
    job_id: uuid.UUID, r: Request,
    user=Depends(require_staff_or_above_mutation), db: AsyncSession = Depends(get_db),
):
    session = await svc.place_call(
        db, job_id=job_id, tenant_id=uuid.UUID(str(user.tenant_id)),
        initiator_user_id=uuid.UUID(str(user.user_id)),
    )
    # Serialize BEFORE committing: commit expires the instance's attributes, and
    # touching them afterwards triggers a lazy refresh that raises
    # MissingGreenlet on an async session. The values are already flushed, so
    # this dict is the committed state.
    payload = session.to_dict()
    await db.commit()
    return ok(payload, _rid(r), "staff-masked-call")


@webhook_router.post(
    "/status",
    summary="Telephony provider call-status callback",
    description=(
        "Shared-secret authenticated (X-Webhook-Secret header or `secret` field). "
        "Matched on the reference WE handed the provider, never on a job id from the "
        "payload, so a forged callback cannot target an arbitrary job. Idempotent: a "
        "replayed terminal status is a no-op."
    ),
)
async def provider_status(
    body: dict, r: Request, db: AsyncSession = Depends(get_db),
):
    supplied = r.headers.get("X-Webhook-Secret") or body.get("secret")
    svc.assert_webhook_authorized(supplied)

    session = await svc.apply_provider_status(
        db,
        provider_call_id=(body.get("CallSid") or body.get("Sid") or body.get("call_id")),
        # Vendors echo our reference under various names; all are OUR value.
        session_reference=(body.get("CustomField") or body.get("reference")
                           or body.get("custom_field")),
        raw_status=(body.get("Status") or body.get("status") or body.get("CallStatus")),
        duration_seconds=(body.get("DialCallDuration") or body.get("duration")),
        recording_url=(body.get("RecordingUrl") or body.get("recording_url")),
    )
    # Same reason as above: serialize before the commit expires the instance.
    payload = {"matched": session is not None,
               "session": session.to_dict() if session else None}
    await db.commit()
    # 200 even when unmatched: a provider retrying forever on an unknown id
    # helps nobody, and the miss is visible in the response.
    return ok(payload, _rid(r), "masked-calling-webhook")
