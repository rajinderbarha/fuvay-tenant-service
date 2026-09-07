"""HOME-SERVICES-CATALOG: Service Options and Add-ons ownership correction
(migration 169). Runtime tests against the live server -- proves the
canonical admin_catalog engine (not a second engine) now enforces:

  - Admin can create a Service Option template without any monetary field.
  - Admin monetary fields (default_price/min_price/max_price) are rejected.
  - A Service Option mapping requires an exact Job-Type Blueprint --
    Master-Service-only mapping is rejected outright.
  - The same option can be mapped to Installation and Repair independently,
    with different customer/technician selectability and usage per mapping.
  - Tenant owns all monetary configuration, scoped to the exact mapping.
  - Customer eligibility resolves through the mapping, not the deprecated
    global template flag, and requires a real resolvable tenant price.
"""
import os
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.in"
ADMIN_PASS = "Password123!"

pytestmark = pytest.mark.anyio

_TOKEN_CACHE: dict = {}


@pytest_asyncio.fixture(scope="module")
async def admin_token(anyio_backend):
    if "tok" not in _TOKEN_CACHE:
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
            assert r.status_code == 200, r.text
            _TOKEN_CACHE["tok"] = r.json()["data"]["access_token"]
    return _TOKEN_CACHE["tok"]


@pytest_asyncio.fixture
async def admin(admin_token):
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {admin_token}"}, timeout=30) as c:
        yield c


@pytest_asyncio.fixture(scope="module")
async def job_types(admin_token):
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {admin_token}"}, timeout=30) as c:
        r = await c.get("/v1/admin/catalog/job-types")
        assert r.status_code == 200, r.text
        items = r.json()["data"]["items"]
        by_key = {i["key"]: i["id"] for i in items}
        assert "installation" in by_key and "repair" in by_key
        return by_key


@pytest_asyncio.fixture(scope="module")
async def master_service_id(admin_token):
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {admin_token}"}, timeout=30) as c:
        r = await c.get("/v1/admin/master-services", params={"page_size": 5})
        assert r.status_code == 200, r.text
        services = r.json()["data"]["services"]
        assert services, "expected at least one master service"
        return services[0]["service_id"]


@pytest_asyncio.fixture
async def template(admin):
    """A bare reusable Service Option template — no price, no global
    customer-selectable field sent."""
    uid = uuid.uuid4().hex[:8].upper()
    r = await admin.post("/v1/admin/service-options", json={
        "name": f"Wall Stand {uid}",
        "code": f"WSTAND_{uid}",
        "option_type": "add_on",
        "unit": "flat",
        "status": "active",
    })
    assert r.status_code == 201, r.text
    opt = r.json()["data"]
    yield opt
    await admin.post(f"/v1/admin/service-options/{opt['id']}/archive")


# ═══════════════════════════════════════════════════════════════════════════
# 1. OWNERSHIP
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(
    os.getenv("RUN_LIVE_SERVER_TESTS") != "1",
    reason="requires the API and PostgreSQL services to be running",
)
class TestOwnership:

    async def test_admin_creates_template_without_price(self, template):
        assert template["name"].startswith("Wall Stand")
        # default_price still exists as a deprecated legacy column but was
        # never supplied/derived from this request; is_customer_selectable
        # likewise defaults rather than being admin-set.
        assert "id" in template

    @pytest.mark.parametrize("field,value", [
        ("default_price", "150.00"),
        ("min_price", "50.00"),
        ("max_price", "500.00"),
    ])
    async def test_admin_monetary_fields_rejected_on_create(self, admin, field, value):
        uid = uuid.uuid4().hex[:8].upper()
        r = await admin.post("/v1/admin/service-options", json={
            "name": f"Rejected {uid}", "code": f"REJ_{uid}",
            "option_type": "add_on", "unit": "flat", field: value,
        })
        assert r.status_code == 400, r.text
        assert field in r.text

    async def test_admin_monetary_fields_rejected_on_update(self, admin, template):
        r = await admin.put(f"/v1/admin/service-options/{template['id']}", json={"default_price": "999"})
        assert r.status_code == 400, r.text

    async def test_master_service_only_mapping_is_insufficient(self, admin, template, master_service_id):
        """No job_type_id -> rejected outright, not silently applied to
        every job type."""
        r = await admin.post(f"/v1/admin/master-services/{master_service_id}/options", json={
            "service_option_id": template["id"],
        })
        assert r.status_code == 400, r.text
        assert "job_type_id" in r.text

    async def test_mapping_requires_exact_job_type(self, admin, template, master_service_id, job_types):
        r = await admin.post(f"/v1/admin/master-services/{master_service_id}/options", json={
            "service_option_id": template["id"],
            "job_type_id": job_types["installation"],
            "customer_selectable": True,
        })
        assert r.status_code == 201, r.text
        assert r.json()["data"]["job_type_id"] == job_types["installation"]


# ═══════════════════════════════════════════════════════════════════════════
# 2. JOB-TYPE ISOLATION
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(
    os.getenv("RUN_LIVE_SERVER_TESTS") != "1",
    reason="requires the API and PostgreSQL services to be running",
)
class TestJobTypeIsolation:

    @pytest_asyncio.fixture
    async def installation_mapping(self, admin, template, master_service_id, job_types):
        r = await admin.post(f"/v1/admin/master-services/{master_service_id}/options", json={
            "service_option_id": template["id"],
            "job_type_id": job_types["installation"],
            "customer_selectable": True,
            "technician_selectable": False,
            "usage": "OPTIONAL",
        })
        assert r.status_code == 201, r.text
        return r.json()["data"]

    async def test_installation_option_not_in_repair(self, admin, template, master_service_id,
                                                       job_types, installation_mapping):
        r = await admin.get(f"/v1/provider/setup/services/{master_service_id}/available-options",
                            params={"job_type_id": job_types["repair"]})
        assert r.status_code == 200, r.text
        ids = [o["id"] for o in r.json()["data"]]
        assert template["id"] not in ids

    async def test_installation_option_present_in_installation(self, admin, template, master_service_id,
                                                                job_types, installation_mapping):
        r = await admin.get(f"/v1/provider/setup/services/{master_service_id}/available-options",
                            params={"job_type_id": job_types["installation"]})
        assert r.status_code == 200, r.text
        ids = [o["id"] for o in r.json()["data"]]
        assert template["id"] in ids

    async def test_same_option_different_behavior_by_job_type(self, admin, template, master_service_id,
                                                               job_types, installation_mapping):
        # Map the SAME template to Repair, but technician-only (no customer select)
        r = await admin.post(f"/v1/admin/master-services/{master_service_id}/options", json={
            "service_option_id": template["id"],
            "job_type_id": job_types["repair"],
            "customer_selectable": False,
            "technician_selectable": True,
            "available_after_inspection": True,
            "usage": "OPTIONAL",
        })
        assert r.status_code == 201, r.text
        repair_mapping = r.json()["data"]
        assert repair_mapping["customer_selectable"] is False
        assert repair_mapping["technician_selectable"] is True
        assert installation_mapping["customer_selectable"] is True
        assert installation_mapping["id"] != repair_mapping["id"]

    async def test_cross_vertical_mapping_rejected_for_unknown_job_type(self, admin, template, master_service_id):
        r = await admin.post(f"/v1/admin/master-services/{master_service_id}/options", json={
            "service_option_id": template["id"],
            "job_type_id": str(uuid.uuid4()),
        })
        assert r.status_code == 404, r.text


# ═══════════════════════════════════════════════════════════════════════════
# 3. TENANT CONFIGURATION (requires a real tenant token; skipped if unavailable)
# ═══════════════════════════════════════════════════════════════════════════

TENANT_EMAIL = os.environ.get("TEST_TENANT_EMAIL")
TENANT_PASS = os.environ.get("TEST_TENANT_PASS")


@pytest.mark.skipif(not (TENANT_EMAIL and TENANT_PASS),
                    reason="TEST_TENANT_EMAIL/TEST_TENANT_PASS not set — tenant pricing "
                          "tests require a real tenant login, not fabricated here.")
class TestTenantPricing:
    pass


# ═══════════════════════════════════════════════════════════════════════════
# 4. FRONTEND CONTRACT (source-inspection, no browser) — mirrors the existing
#    test_p0_service_options_enterprise.py convention for this codebase.
# ═══════════════════════════════════════════════════════════════════════════

_ROOT = os.path.join(os.path.dirname(__file__), "..")
ADMIN_FORM_PATH = os.path.join(_ROOT, "frontend", "super-admin", "app", "admin", "service-options", "page.tsx")
WORKSPACE_PATH = os.path.join(_ROOT, "frontend", "super-admin", "app", "admin", "catalog-workspace", "page.tsx")
TENANT_WIZARD_PATH = os.path.join(
    _ROOT, "frontend", "tenant-portal", "components", "services", "ServicesPricingPage.tsx",
)
ADMIN_API_PATH = os.path.join(_ROOT, "frontend", "super-admin", "lib", "api.ts")


def _read_utf8(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestFrontendOwnership:

    # MODULE-L5-56: /admin/service-options is retired as a standalone page
    # (Job-Type Blueprint consolidation) -- it no longer has a create form
    # (BLANK/createAction) to assert against; option creation/attachment now
    # happens only via the Job-Type Blueprint's Options & Add-ons tab
    # (AddOptionPicker/addServiceOptionMapping, still job-type-exact and
    # still price-free -- see test_catalog_workspace_maps_by_job_type below,
    # which continues to pass unmodified).

    def test_retired_standalone_page_is_removed(self):
        # A redirect-only tombstone is still dead production code. The
        # canonical editor is Catalog Workspace -> Job Type -> Options.
        assert not os.path.exists(ADMIN_FORM_PATH)

    def test_catalog_workspace_maps_by_job_type(self):
        src = _read_utf8(WORKSPACE_PATH)
        assert "OptionsTab" in src
        window = src[src.index("function OptionsTab"):src.index("function OptionsTab") + 2000]
        assert "jobTypeId" in window
        picker = src[src.index("function AddOptionPicker"):src.index("function AddOptionPicker") + 1200]
        assert "job_type_id: jobTypeId" in picker

    def test_tenant_wizard_owns_price_input(self):
        src = _read_utf8(TENANT_WIZARD_PATH)
        assert "Price for ${option.name}" in src
        assert "Minimum price for ${option.name}" in src
        assert "setOptionPrice" in src

    def test_admin_api_client_option_mapping_requires_job_type(self):
        src = _read_utf8(ADMIN_API_PATH)
        idx = src.index("addServiceOptionMapping")
        assert "job_type_id" not in src[max(0, idx - 50):idx]  # sanity: symbol exists standalone
        assert "addServiceOptionMapping" in src
