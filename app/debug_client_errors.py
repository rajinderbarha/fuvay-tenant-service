"""TEMPORARY client-error sink — safe to delete.

A server capture proves what the API returned; it says nothing about a crash
that happens AFTER a successful response. This gives the app somewhere to
post its own uncaught errors so the stack trace lands in the same capture
log as the request that preceded it.

Only mounted when `SERVICEOS_CAPTURE_FILE` is set (see app/main.py), so it
does not exist in a normal run.

The posted error is echoed back in the RESPONSE body on purpose: the capture
middleware records responses, not request bodies, so echoing is what gets the
trace into the log without teaching that middleware to buffer request bodies.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/_debug", tags=["Debug (temporary)"])


@router.post("/client-error", response_model=ApiResponse[dict])
async def record_client_error(r: Request):
    try:
        body = await r.json()
    except Exception:
        body = {"raw": (await r.body()).decode("utf-8", "replace")[:8000]}

    # Echoed so the capture middleware records it.
    return ok({"client_error": body}, getattr(r.state, "request_id", "—"), "debug")
