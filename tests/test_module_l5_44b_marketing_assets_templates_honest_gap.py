"""MODULE-L5-44 (part 2) — super-admin's marketing assets + templates pages
call endpoints that don't exist, and (like onboarding templates) the concept
they assume was genuinely superseded, not renamed.

adminMarketingApi.listAssets/approveAsset/etc. call /v1/admin/marketing/
assets* -- MarketingAsset's fields (campaign_id, admin_notes,
rejection_reason, publish_url) don't match any real table:
marketing_post_assets (the only "asset" table) is a child-of-post AI
generation record with no campaign_id or admin-approval fields. The real
admin marketing system is entirely posts-based (/v1/admin/marketing/posts,
approve/reject/schedule/publish-now).

adminMarketingApi.listTemplates/createTemplate/etc. call /v1/admin/marketing/
templates* -- MarketingTemplate's fields (template_key, channel,
title_template, body_template, variables, is_ai_enabled,
requires_admin_approval) don't match marketing_content_templates
(vertical_key, post_type, prompt_template, caption_structure,
hashtag_set_json, cta) at the real /v1/admin/marketing/content-templates.

Per this project's "never fake-certify" rule, both pages now disclose the gap
honestly instead of offering a CRUD UI where every action 404s.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[1]
ASSETS_PAGE = ROOT / "frontend/super-admin/app/admin/marketing/assets/page.tsx"
TEMPLATES_PAGE = ROOT / "frontend/super-admin/app/admin/marketing/templates/page.tsx"

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.local"
PASSWORD = "Password123!"


def test_assets_page_discloses_the_gap():
    src = ASSETS_PAGE.read_text(encoding="utf-8")
    assert "legacy asset-approval workspace has been retired" in src
    assert 'window.location.href = "/admin/marketing"' in src
    assert "adminMarketingApi" not in src


def test_templates_page_discloses_the_gap():
    src = TEMPLATES_PAGE.read_text(encoding="utf-8")
    assert "legacy template workspace has been retired" in src
    assert 'window.location.href = "/admin/marketing"' in src
    assert "adminMarketingApi" not in src


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


class TestLive:
    async def test_dead_routes_confirmed_and_real_posts_system_exists(self):
        tok = await _login(ADMIN_EMAIL)
        if not tok:
            pytest.skip("admin login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as admin:
            dead_assets = await admin.get("/v1/admin/marketing/assets")
            assert dead_assets.status_code == 404

            dead_templates = await admin.get("/v1/admin/marketing/templates")
            assert dead_templates.status_code == 404

            real_posts = await admin.get("/v1/admin/marketing/posts")
            assert real_posts.status_code == 200

            real_content_templates = await admin.get("/v1/admin/marketing/content-templates")
            assert real_content_templates.status_code == 200
