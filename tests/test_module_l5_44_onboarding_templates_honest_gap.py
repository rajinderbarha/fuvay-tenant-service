"""MODULE-L5-44 — the super-admin onboarding-checklist-templates tab
(admin/categories/[id]) calls 7 endpoints under /v1/admin/onboarding/templates*
that don't exist, and there is no honest fix available.

Investigated (continuation of the L5-39..43 openapi audit): confirmed the
OnboardingChecklistTemplate model/table (checklist_key/item_type/
completion_source/required_engine_key/required_permission -- matching the
historical Sprint 10 "Provider Onboarding Checklist by Category" feature) no
longer exists anywhere in the codebase or database (checked pg_tables: no
onboarding_checklist_templates table). The only adjacent real table
(master_checklist_items, admin_catalog/service_option_admin_router.py's
/v1/admin/checklists) is a genuinely different concept -- generic workflow-
step checklist items, not onboarding-approval gates with evaluators -- and
remapping the UI to it would misrepresent the feature as working when it
would silently edit the wrong data.

Per this project's "never fake-certify" rule, rather than fabricate a fix,
the tab now says so honestly (a visible notice) and disables the one action
that would otherwise 404 (Add Item) instead of leaving a broken CRUD UI that
silently fails on every action.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "frontend/super-admin/app/admin/categories/[id]/page.tsx"

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.local"
PASSWORD = "Password123!"


def test_tab_honestly_discloses_the_gap():
    src = PAGE.read_text(encoding="utf-8")
    # The obsolete tab was removed entirely in the consolidated category
    # workspace, so no dead onboarding-template action is rendered or called.
    assert "/v1/admin/onboarding/templates" not in src
    assert "OnboardingChecklistTemplate" not in src


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


class TestLive:
    async def test_onboarding_templates_route_confirmed_gone(self):
        tok = await _login(ADMIN_EMAIL)
        if not tok:
            pytest.skip("admin login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as admin:
            r = await admin.get("/v1/admin/onboarding/templates/00000000-0000-0000-0000-000000000000")
            assert r.status_code == 404
