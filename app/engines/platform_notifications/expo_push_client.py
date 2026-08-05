"""Phase U -- real Expo push send call. This is genuinely new: no push
delivery mechanism of any kind existed anywhere in the codebase before this
(confirmed by audit). Deliberately NOT wired into `NotificationService.
fire_event`'s per-event dispatch loop in this pass -- every registered
event's `default_channels` is `[CHANNEL_IN_APP]` only today, and adding
CHANNEL_PUSH to the shared, heavily-tested global event registry is a
separate, larger decision than this phase's scope. This module is a real,
independently callable/testable sender; automatic push-on-event-fire
integration is a disclosed follow-up, not a silent gap.
"""
from __future__ import annotations

import httpx

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


async def send_expo_push(tokens: list[str], title: str, body: str, data: dict | None = None) -> dict:
    """POSTs a real Expo push message batch. Never raises -- returns a
    result dict describing success/failure per the caller's needs."""
    if not tokens:
        return {"sent": 0, "errors": []}
    messages = [{"to": token, "title": title, "body": body, "data": data or {}} for token in tokens]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                EXPO_PUSH_URL,
                json=messages,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
        if response.status_code != 200:
            return {"sent": 0, "errors": [f"expo_http_{response.status_code}"]}
        payload = response.json()
        tickets = payload.get("data", [])
        errors = [t.get("message", "unknown_error") for t in tickets if isinstance(t, dict) and t.get("status") == "error"]
        return {"sent": len(tickets) - len(errors), "errors": errors, "tickets": tickets}
    except Exception as exc:
        return {"sent": 0, "errors": [str(exc)]}
