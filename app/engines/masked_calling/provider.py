"""Masked calling — telephony provider seam.

The platform bridges both legs of the call, so the concrete provider only ever
needs one operation: "connect these two numbers using our caller id, and tell
me your call id". Everything else (who may call whom, what it means for the
job, what the customer sees) is platform logic and stays out of here.

WHY AN INTERFACE RATHER THAN A HARDCODED VENDOR
Exotel, Knowlarity and Twilio all differ in how they express a two-leg bridge
and in what their status callbacks send. Committing to one vendor's request
shape inside the service layer would make swapping them a rewrite. The service
layer therefore depends only on `TelephonyProvider`.

NOT-CONFIGURED IS AN EXPLICIT STATE, NOT A FALLBACK
`NullTelephonyProvider` is selected when no vendor is configured, and it
REFUSES to place a call. It deliberately does not degrade to handing back a
real phone number: doing so would silently defeat the only thing this engine
exists to prevent. The API surfaces MASKED_CALLING_NOT_CONFIGURED so the app
can say "calling unavailable" honestly.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config import get_settings
from app.engines.masked_calling import constants as c


@dataclass(frozen=True)
class BridgeResult:
    """Outcome of asking the provider to bridge two legs."""
    provider_call_id: str | None
    accepted: bool
    failure_reason: str | None = None


class TelephonyProvider(Protocol):
    name: str

    @property
    def configured(self) -> bool: ...

    async def bridge(
        self, *, from_number: str, to_number: str, caller_id: str, reference: str,
    ) -> BridgeResult:
        """Dial `from_number`, then join `to_number`, both showing `caller_id`.

        `reference` is our session id, echoed back on status callbacks so a
        webhook can be matched without trusting caller-supplied job ids.
        """
        ...


class NullTelephonyProvider:
    """Selected when no vendor is configured. Refuses, never leaks."""

    name = "none"

    @property
    def configured(self) -> bool:
        return False

    async def bridge(self, **_kwargs) -> BridgeResult:
        return BridgeResult(
            provider_call_id=None, accepted=False,
            failure_reason=c.ERR_CALLING_NOT_CONFIGURED,
        )


class HttpTelephonyProvider:
    """Generic HTTP bridge for providers that accept a simple form/JSON POST.

    Exotel's connect-two-numbers API is of exactly this shape (POST with
    From/To/CallerId under basic auth), so `MASKED_CALLING_PROVIDER=exotel`
    uses this adapter with Exotel's field names. Any vendor whose bridge
    endpoint takes the same three fields works by pointing
    MASKED_CALLING_API_BASE at it.

    IMPORTANT for whoever wires the live account: the exact response field
    carrying the call id differs between vendors. `_extract_call_id` checks the
    common shapes and returns None if it cannot find one -- in which case the
    call may still connect, but status callbacks cannot be matched to this
    session. That is logged as a real failure to attribute rather than
    silently ignored.
    """

    def __init__(self, kind: str) -> None:
        s = get_settings()
        self.name = kind
        self._base = (s.MASKED_CALLING_API_BASE or "").rstrip("/")
        self._key = s.MASKED_CALLING_API_KEY
        self._secret = s.MASKED_CALLING_API_SECRET

    @property
    def configured(self) -> bool:
        return bool(self._base and self._key and self._secret)

    def _auth_header(self) -> dict[str, str]:
        token = base64.b64encode(f"{self._key}:{self._secret}".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    @staticmethod
    def _extract_call_id(payload: object) -> str | None:
        if not isinstance(payload, dict):
            return None
        for key in ("Sid", "sid", "call_id", "CallSid", "id", "uuid"):
            value = payload.get(key)
            if isinstance(value, (str, int)) and str(value):
                return str(value)
        for nest in ("Call", "call", "data", "result"):
            inner = payload.get(nest)
            if isinstance(inner, dict):
                found = HttpTelephonyProvider._extract_call_id(inner)
                if found:
                    return found
        return None

    async def bridge(
        self, *, from_number: str, to_number: str, caller_id: str, reference: str,
    ) -> BridgeResult:
        if not self.configured:
            return BridgeResult(None, False, c.ERR_CALLING_NOT_CONFIGURED)
        body = {
            "From": from_number,
            "To": to_number,
            "CallerId": caller_id,
            "CustomField": reference,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(self._base, data=body, headers=self._auth_header())
        except Exception as exc:  # noqa: BLE001 -- a telephony outage must not 500 the job screen
            return BridgeResult(None, False, f"provider_unreachable: {type(exc).__name__}")

        if resp.status_code >= 400:
            # Body may contain vendor error detail; truncated so a huge HTML
            # error page cannot bloat the row.
            return BridgeResult(None, False, f"provider_http_{resp.status_code}: {resp.text[:150]}")

        try:
            payload = resp.json()
        except Exception:  # noqa: BLE001
            payload = None
        return BridgeResult(self._extract_call_id(payload), True, None)


def get_provider() -> TelephonyProvider:
    """The configured provider, or the refusing Null one.

    Resolved per call rather than cached at import so settings changes take
    effect without a restart, and so tests can point it at a fake.
    """
    kind = (get_settings().MASKED_CALLING_PROVIDER or "").strip().lower()
    if kind in ("exotel", "http"):
        provider = HttpTelephonyProvider(kind)
        return provider if provider.configured else NullTelephonyProvider()
    return NullTelephonyProvider()
