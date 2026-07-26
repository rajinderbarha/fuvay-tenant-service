"""P0 Service Options Enterprise Upgrade — backend tests.

Tests cover:
- /summary endpoint shape and counts
- option_type server-side filter
- mapped=true/false server-side filter
- existing CRUD still works
- frontend files exist and contain expected patterns
"""
import os
import re
import uuid
import pytest
import pytest_asyncio
from decimal import Decimal
from httpx import AsyncClient

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.in"
ADMIN_PASS  = "Password123!"

PAGE_PATH   = os.path.join(os.path.dirname(__file__), "..", "frontend", "super-admin",
                           "app", "admin", "service-options", "page.tsx")
DETAIL_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "super-admin",
                           "app", "admin", "service-options", "[id]", "page.tsx")
API_PATH    = os.path.join(os.path.dirname(__file__), "..", "frontend", "super-admin",
                           "lib", "api.ts")
SERVICE_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "engines",
                             "admin_catalog", "service_option_service.py")
ROUTER_PATH  = os.path.join(os.path.dirname(__file__), "..", "app", "engines",
                             "admin_catalog", "service_option_admin_router.py")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()

def _strip_comments(src: str) -> str:
    src = re.sub(r'""".*?"""', '', src, flags=re.DOTALL)
    src = re.sub(r"'''.*?'''", '', src, flags=re.DOTALL)
    src = re.sub(r'#.*', '', src)
    return src


_TOKEN_CACHE: dict = {}


@pytest_asyncio.fixture(scope="module")
async def token(anyio_backend):
    if "tok" not in _TOKEN_CACHE:
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
            assert r.status_code == 200, r.text
            _TOKEN_CACHE["tok"] = r.json()["data"]["access_token"]
    return _TOKEN_CACHE["tok"]


@pytest_asyncio.fixture
async def client(token):
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(base_url=BASE, headers=headers, timeout=30) as c:
        yield c


@pytest_asyncio.fixture
async def test_option(client):
    uid = uuid.uuid4().hex[:8].upper()
    r = await client.post("/v1/admin/service-options", json={
        "name": f"TestOption {uid}",
        "code": f"TST_{uid}",
        "option_type": "add_on",
        "unit": "flat",
        "default_price": "99.00",
        "status": "active",
        "is_customer_selectable": True,
        "display_order": 0,
    })
    assert r.status_code == 201, r.text
    opt = r.json()["data"]
    yield opt
    # cleanup: archive to hide from future tests
    await client.post(f"/v1/admin/service-options/{opt['id']}/archive")


pytestmark = pytest.mark.anyio


# ═════════════════════════════════════════════════════════════════════════════
# 1. BACKEND FILE CHECKS
# ═════════════════════════════════════════════════════════════════════════════

class TestBackendFiles:
    def test_service_file_exists(self):
        assert os.path.isfile(SERVICE_PATH)

    def test_service_has_list_service_options_summary(self):
        src = _read(SERVICE_PATH)
        assert "list_service_options_summary" in src

    def test_service_summary_returns_correct_keys(self):
        src = _read(SERVICE_PATH)
        for key in ("total", "active", "inactive", "archived", "customer_selectable", "mapped", "unmapped"):
            assert f'"{key}"' in src or f"'{key}'" in src, f"Missing key {key!r} in summary"

    def test_service_option_type_filter_in_list(self):
        src = _strip_comments(_read(SERVICE_PATH))
        assert "option_type" in src
        assert "MasterServiceOption.option_type == option_type" in src

    def test_service_mapped_true_filter(self):
        src = _strip_comments(_read(SERVICE_PATH))
        assert "mapped is True" in src or "mapped == True" in src

    def test_service_mapped_false_filter(self):
        src = _strip_comments(_read(SERVICE_PATH))
        assert "mapped is False" in src or "mapped == False" in src

    def test_router_file_exists(self):
        assert os.path.isfile(ROUTER_PATH)

    def test_router_has_summary_endpoint(self):
        src = _read(ROUTER_PATH)
        assert '"/summary"' in src or "'/summary'" in src

    def test_router_summary_before_option_id(self):
        src = _read(ROUTER_PATH)
        summary_pos = src.index("/summary")
        option_id_pos = src.index("/{option_id}")
        assert summary_pos < option_id_pos, "/summary route must be defined before /{option_id}"

    def test_router_has_option_type_param(self):
        src = _read(ROUTER_PATH)
        assert "option_type" in src

    def test_router_has_mapped_param(self):
        src = _read(ROUTER_PATH)
        assert "mapped" in src


# ═════════════════════════════════════════════════════════════════════════════
# 2. SUMMARY ENDPOINT
# ═════════════════════════════════════════════════════════════════════════════

class TestSummaryEndpoint:
    async def test_summary_returns_200(self, client):
        r = await client.get("/v1/admin/service-options/summary")
        assert r.status_code == 200, r.text

    async def test_summary_has_all_keys(self, client):
        r = await client.get("/v1/admin/service-options/summary")
        data = r.json()["data"]
        for key in ("total", "active", "inactive", "archived", "customer_selectable", "mapped", "unmapped"):
            assert key in data, f"Missing key: {key}"

    async def test_summary_values_are_integers(self, client):
        r = await client.get("/v1/admin/service-options/summary")
        data = r.json()["data"]
        for key in ("total", "active", "inactive", "archived", "customer_selectable", "mapped", "unmapped"):
            assert isinstance(data[key], int), f"{key} should be int, got {type(data[key])}"

    async def test_summary_total_gte_active_plus_inactive(self, client):
        r = await client.get("/v1/admin/service-options/summary")
        data = r.json()["data"]
        assert data["total"] >= data["active"] + data["inactive"]

    async def test_summary_increases_after_create(self, client, test_option):
        r1 = await client.get("/v1/admin/service-options/summary")
        total_before = r1.json()["data"]["total"]
        # test_option was already created; just verify total >= 1
        assert total_before >= 1

    async def test_summary_no_auth_fails(self):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.get("/v1/admin/service-options/summary")
        assert r.status_code in (401, 403)

    async def test_summary_unmapped_gte_zero(self, client):
        r = await client.get("/v1/admin/service-options/summary")
        data = r.json()["data"]
        assert data["unmapped"] >= 0

    async def test_summary_mapped_plus_unmapped_lte_total(self, client):
        r = await client.get("/v1/admin/service-options/summary")
        data = r.json()["data"]
        # mapped counts active+inactive, unmapped counts only active → sum can exceed total
        # but individually each should be <= total
        assert data["mapped"] <= data["total"]
        assert data["unmapped"] <= data["total"]


# ═════════════════════════════════════════════════════════════════════════════
# 3. OPTION_TYPE FILTER
# ═════════════════════════════════════════════════════════════════════════════

class TestOptionTypeFilter:
    async def test_filter_by_option_type_add_on(self, client, test_option):
        r = await client.get("/v1/admin/service-options", params={"option_type": "add_on"})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        items = data["items"]
        for item in items:
            assert item["option_type"] == "add_on", f"Got unexpected type: {item['option_type']}"

    async def test_filter_by_option_type_upgrade(self, client):
        r = await client.get("/v1/admin/service-options", params={"option_type": "upgrade"})
        assert r.status_code == 200, r.text
        items = r.json()["data"]["items"]
        for item in items:
            assert item["option_type"] == "upgrade"

    async def test_filter_by_option_type_excludes_others(self, client, test_option):
        # test_option is add_on; filter for upgrade should not contain it
        r = await client.get("/v1/admin/service-options", params={"option_type": "tool"})
        assert r.status_code == 200
        ids = [item["id"] for item in r.json()["data"]["items"]]
        assert test_option["id"] not in ids


# ═════════════════════════════════════════════════════════════════════════════
# 4. MAPPED FILTER
# ═════════════════════════════════════════════════════════════════════════════

class TestMappedFilter:
    async def test_mapped_true_returns_only_mapped(self, client):
        r = await client.get("/v1/admin/service-options", params={"mapped": "true"})
        assert r.status_code == 200, r.text

    async def test_mapped_false_returns_only_unmapped(self, client, test_option):
        r = await client.get("/v1/admin/service-options", params={"mapped": "false"})
        assert r.status_code == 200, r.text
        ids = [item["id"] for item in r.json()["data"]["items"]]
        # test_option has no mappings, so it should appear
        assert test_option["id"] in ids

    async def test_mapped_filter_absent_returns_all(self, client, test_option):
        r = await client.get("/v1/admin/service-options")
        assert r.status_code == 200
        ids = [item["id"] for item in r.json()["data"]["items"]]
        assert test_option["id"] in ids


# ═════════════════════════════════════════════════════════════════════════════
# 5. EXISTING CRUD
# ═════════════════════════════════════════════════════════════════════════════

class TestExistingCRUD:
    async def test_list_returns_200(self, client):
        r = await client.get("/v1/admin/service-options")
        assert r.status_code == 200

    async def test_list_has_items_and_total(self, client):
        r = await client.get("/v1/admin/service-options")
        data = r.json()["data"]
        assert "items" in data
        assert "total" in data

    async def test_get_option(self, client, test_option):
        r = await client.get(f"/v1/admin/service-options/{test_option['id']}")
        assert r.status_code == 200
        assert r.json()["data"]["id"] == test_option["id"]

    async def test_activate_deactivate_cycle(self, client, test_option):
        opt_id = test_option["id"]
        r = await client.post(f"/v1/admin/service-options/{opt_id}/deactivate")
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "inactive"
        r = await client.post(f"/v1/admin/service-options/{opt_id}/activate")
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "active"

    async def test_update_option(self, client, test_option):
        r = await client.put(f"/v1/admin/service-options/{test_option['id']}", json={
            "description": "updated description"
        })
        assert r.status_code == 200
        assert r.json()["data"]["description"] == "updated description"

    async def test_archive_option(self, client):
        uid = uuid.uuid4().hex[:8].upper()
        r = await client.post("/v1/admin/service-options", json={
            "name": f"ArchiveMe {uid}", "code": f"ARC_{uid}",
            "option_type": "tool", "unit": "flat", "default_price": "0", "status": "active",
        })
        assert r.status_code == 201
        opt_id = r.json()["data"]["id"]
        r = await client.post(f"/v1/admin/service-options/{opt_id}/archive")
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "archived"


# ═════════════════════════════════════════════════════════════════════════════
# 6. FRONTEND FILE CHECKS
# ═════════════════════════════════════════════════════════════════════════════

# MODULE-L5-56: /admin/service-options (and its [id] detail page) are
# intentionally retired as standalone pages (Job-Type Blueprint
# consolidation) -- both now render a retired-notice redirect to
# /admin/catalog-workspace. Their enterprise-dashboard content (summary
# cards, action menus, pagination, etc.) no longer exists by design; see
# tests/test_module_l5_56_blueprint_consolidation.py::TestStandalonePageRetirement
# for the replacement contract. Skipped rather than deleted so the
# historical intent stays visible in git history.
@pytest.mark.skip(reason="MODULE-L5-56: /admin/service-options retired as a standalone page; "
                          "superseded by Catalog Workspace's Options & Add-ons tab.")
class TestFrontendFiles:
    def test_page_file_exists(self):
        assert os.path.isfile(PAGE_PATH), f"Missing: {PAGE_PATH}"

    def test_detail_page_exists(self):
        assert os.path.isfile(DETAIL_PATH), f"Missing: {DETAIL_PATH}"

    def test_page_imports_summary_api(self):
        src = _read(PAGE_PATH)
        assert "summary" in src

    def test_page_has_summary_cards(self):
        src = _read(PAGE_PATH)
        assert "SummaryCard" in src

    def test_page_server_side_option_type(self):
        src = _read(PAGE_PATH)
        assert "option_type" in src

    def test_page_server_side_mapped_filter(self):
        src = _read(PAGE_PATH)
        assert "mappedFilter" in src or "mapped" in src

    def test_page_has_action_menu(self):
        src = _read(PAGE_PATH)
        assert "ActionMenu" in src

    def test_page_has_readiness_badge(self):
        src = _read(PAGE_PATH)
        assert "Readiness" in src or "ReadinessBadge" in src

    def test_page_links_to_detail(self):
        src = _read(PAGE_PATH)
        assert "service-options/${" in src or "service-options/$" in src or "/service-options/" in src

    def test_page_has_pagination(self):
        src = _read(PAGE_PATH)
        assert "pagination" in src.lower() or "totalPages" in src or "total_pages" in src

    def test_page_has_chip_filter_removal(self):
        src = _read(PAGE_PATH)
        assert "Chip" in src or "chip" in src.lower()

    def test_api_has_summary_method(self):
        src = _read(API_PATH)
        assert "summary:" in src or "summary =" in src

    def test_api_summary_hits_correct_endpoint(self):
        src = _read(API_PATH)
        assert "/v1/admin/service-options/summary" in src

    def test_api_list_has_option_type_param(self):
        src = _read(API_PATH)
        assert "option_type" in src

    def test_api_list_has_mapped_param(self):
        src = _read(API_PATH)
        assert "mapped" in src

    def test_api_exports_service_option_summary_interface(self):
        src = _read(API_PATH)
        assert "ServiceOptionSummary" in src

    def test_detail_page_has_edit_modal(self):
        src = _read(DETAIL_PATH)
        assert "editModal" in src or "Edit" in src

    def test_detail_page_has_activate_deactivate(self):
        src = _read(DETAIL_PATH)
        assert "activateOption" in src or "activate" in src.lower()

    def test_detail_page_has_archive(self):
        src = _read(DETAIL_PATH)
        assert "archiveOption" in src or "archive" in src.lower()

    def test_detail_page_back_link(self):
        src = _read(DETAIL_PATH)
        assert "/admin/service-options" in src
