"""MODULE-L5-37 — the staff-app mobile had no notification surface at all.

Final piece of the MODULE-L5-00-004 (staff_app_mobile least-certified
surface) investigation. Server-side job-assignment/booking notifications
(MODULE-L5-25 etc. raise InAppNotification rows with
notification_type="job_assigned", source_record_type="service_jobs") were
never fetched or shown anywhere in the app -- a technician only learned a job
was assigned to them by polling the Jobs tab. The real endpoints
(/v1/staff/notifications*) existed and worked but nothing called them.

Built: notificationsApi (list / unread-count / mark-read / mark-all-read),
NotificationsScreen (list + mark-all-read + deep-link into the real job
detail via source_record_type "service_jobs"), a bell + unread badge on
HomeScreen, and the Notifications route in AppNavigator. Verified live: seeded
a job_assigned notification, confirmed unread-count 1 -> list -> mark-read ->
count 0.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

API_TS = Path("mobile/staff-app/src/lib/api.ts")
SCREEN = Path("mobile/staff-app/src/screens/NotificationsScreen.tsx")
HOME = Path("mobile/staff-app/src/screens/HomeScreen.tsx")
NAV = Path("mobile/staff-app/src/navigation/AppNavigator.tsx")

BASE = "http://localhost:8000"
STAFF_EMAIL = "staff@serviceos.local"
PASSWORD = "Password123!"


def test_notifications_api_targets_the_real_staff_endpoints():
    src = API_TS.read_text(encoding="utf-8")
    block = src.split("export const notificationsApi")[1].split("\n};")[0]
    assert "/v1/staff/notifications" in block
    for fn in ("list:", "unreadCount:", "markRead:", "markAllRead:"):
        assert fn in block


def test_home_screen_shows_unread_bell_and_routes_to_notifications():
    src = HOME.read_text(encoding="utf-8")
    assert "notificationsApi.unreadCount" in src
    assert 'navigation.navigate("Notifications"' in src


def test_notifications_screen_deep_links_job_assignments():
    src = SCREEN.read_text(encoding="utf-8")
    # assignment notifications carry source_record_type "service_jobs"
    assert '"service_jobs"' in src
    assert 'navigation.navigate("JobDetail"' in src


def test_notifications_route_registered():
    src = NAV.read_text(encoding="utf-8")
    assert 'name="Notifications"' in src


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


class TestLive:
    async def test_staff_notification_endpoints_are_live(self):
        tok = await _login(STAFF_EMAIL)
        if not tok:
            pytest.skip("staff login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as staff:
            lst = await staff.get("/v1/staff/notifications?limit=5")
            assert lst.status_code == 200
            assert "items" in lst.json()["data"]

            cnt = await staff.get("/v1/staff/notifications/unread-count")
            assert cnt.status_code == 200
            assert "unread_count" in cnt.json()["data"]
