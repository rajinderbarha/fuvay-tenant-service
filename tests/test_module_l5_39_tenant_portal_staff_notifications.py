"""MODULE-L5-39 — tenant-portal staff notifications page was doubly broken:
wrong mark-read route (404) and a notification shape that didn't match the
backend.

Found via a systematic openapi-vs-frontend-calls audit of
frontend/tenant-portal/lib/api.ts. staffSelfApi.markRead called
POST /v1/staff/notifications/{id}/mark-read -- the real route is
/{notification_id}/read (the /mark-read path 404s). Separately, the
StaffNotification TS interface modeled is_read (boolean) + type, but the real
InAppNotification.to_dict() returns read_status ("read"|"unread") +
notification_type -- so the unread badge/highlight/filter never matched and
the title fell back to "Notification". markAllRead also read {marked} where
the backend returns {marked_read}.

Fixed: corrected the route, the StaffNotification interface, and every
consumer (notifications page unread/badge/title logic, dashboard unread
count). Verified live: seeding a notification and POSTing the corrected /read
path flips read_status to "read".
"""
from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[1]
API_TS = ROOT / "frontend/tenant-portal/lib/api.ts"
NOTIF_PAGE = ROOT / "frontend/tenant-portal/app/staff/notifications/page.tsx"

BASE = "http://localhost:8000"
STAFF_EMAIL = "staff@serviceos.local"
PASSWORD = "Password123!"


def _live(text: str) -> str:
    return "\n".join(l for l in text.splitlines()
                      if not l.strip().startswith("//") and not l.strip().startswith("*"))


def test_mark_read_uses_the_real_route():
    src = _live(API_TS.read_text(encoding="utf-8"))
    assert "/v1/staff/notifications/${id}/read" in src
    assert "mark-read" not in src


def test_staff_notification_interface_matches_backend_shape():
    src = API_TS.read_text(encoding="utf-8")
    block = src.split("export interface StaffNotification")[1].split("}")[0]
    assert "read_status" in block
    assert "notification_type" in block
    assert "is_read" not in block


def test_notifications_page_uses_read_status():
    src = _live(NOTIF_PAGE.read_text(encoding="utf-8"))
    assert "read_status" in src
    assert ".is_read" not in src


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


class TestLive:
    async def test_mark_read_route_reaches_handler_and_wrong_one_404s(self):
        tok = await _login(STAFF_EMAIL)
        if not tok:
            pytest.skip("staff login unavailable")
        fake = "00000000-0000-0000-0000-000000000000"
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as staff:
            wrong = await staff.post(f"/v1/staff/notifications/{fake}/mark-read")
            assert wrong.status_code == 404  # route does not exist

            right = await staff.post(f"/v1/staff/notifications/{fake}/read")
            # reaches the handler -> domain not-found, not a route 404
            assert right.json().get("error_code") == "IN_APP_NOTIFICATION_NOT_FOUND"
