"""Live Admin -> Tenant Home Services catalog lifecycle certification.

Uses unique temporary records through the public HTTP APIs, proves that the
tenant sees and can configure the admin-authored service, then removes every
temporary database row.  This complements source-contract tests with a real
running-backend/Postgres integration check.
"""
from __future__ import annotations

import uuid

import asyncpg
import pytest
from httpx import AsyncClient


BASE = "http://localhost:8000"
DB_URL = "postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos"
PASSWORD = "Password123!"

pytestmark = pytest.mark.anyio


async def _login(email: str) -> tuple[str, str | None]:
    async with AsyncClient(base_url=BASE, timeout=30) as client:
        response = await client.post(
            "/v1/auth/login", json={"email": email, "password": PASSWORD}
        )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    return data["access_token"], data["user"].get("tenant_id")


def _id(data: dict, *keys: str) -> str:
    for key in keys:
        if data.get(key):
            return str(data[key])
    raise AssertionError(f"No identifier in response. Expected one of {keys}: {data}")


async def test_admin_master_service_lifecycle_propagates_to_tenant_catalog():
    admin_token, _ = await _login("admin@serviceos.in")
    tenant_token, tenant_id = await _login("provider@serviceos.in")
    assert tenant_id

    suffix = uuid.uuid4().hex[:10]
    created: dict[str, str] = {}

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    tenant_headers = {"Authorization": f"Bearer {tenant_token}"}

    try:
        async with AsyncClient(base_url=BASE, timeout=30, headers=admin_headers) as admin:
            # Independent category + service-group CRUD/lifecycle certification.
            category_response = await admin.post(
                "/v1/admin/business-verticals",
                json={
                    "name": f"Catalog Audit Vertical {suffix}",
                    "description": "Temporary operation-level integration audit",
                    "vertical_type": "other",
                    "finance_model": "free_listing",
                    "customer_flow_type": "service_booking",
                    "provider_business_model": "service_provider",
                    "tenant_selectable": True,
                    "is_customer_visible": False,
                    "registration_available": False,
                },
            )
            assert category_response.status_code == 201, category_response.text
            category = category_response.json()["data"]
            created["category"] = _id(category, "category_id", "id")

            category_update = await admin.put(
                f"/v1/admin/service-categories/{created['category']}",
                json={"description": "Updated by operation-level integration audit"},
            )
            assert category_update.status_code == 200, category_update.text
            assert category_update.json()["data"]["description"].startswith("Updated")

            group_response = await admin.post(
                "/v1/admin/service-groups",
                json={
                    "name": f"Catalog Audit Group {suffix}",
                    "code": f"catalog_audit_{suffix}",
                    "category_id": created["category"],
                    "description": "Temporary operation-level integration audit",
                },
            )
            assert group_response.status_code == 201, group_response.text
            group = group_response.json()["data"]
            created["group"] = _id(group, "group_id", "id")

            group_update = await admin.put(
                f"/v1/admin/service-groups/{created['group']}",
                json={"description": "Updated group integration audit"},
            )
            assert group_update.status_code == 200, group_update.text
            assert group_update.json()["data"]["description"].startswith("Updated")

            for action in ("deactivate", "activate"):
                response = await admin.post(
                    f"/v1/admin/service-groups/{created['group']}/{action}"
                )
                assert response.status_code == 200, response.text
            archived = await admin.post(
                f"/v1/admin/service-groups/{created['group']}/archive",
                json={"reason": "Temporary operation-level lifecycle audit"},
            )
            assert archived.status_code == 200, archived.text
            restored = await admin.post(
                f"/v1/admin/service-groups/{created['group']}/restore",
                json={"reason": "Temporary operation-level lifecycle audit"},
            )
            assert restored.status_code == 200, restored.text

            group_audit = await admin.get(
                f"/v1/admin/service-groups/{created['group']}/audit"
            )
            assert group_audit.status_code == 200, group_audit.text
            assert group_audit.json()["data"]["total"] >= 4

            # Pick a real entitled Home Services group/job type from the
            # tenant-visible admin catalog, then author a new master service in
            # that hierarchy so propagation is tested without bypassing policy.
            async with AsyncClient(base_url=BASE, timeout=30, headers=tenant_headers) as tenant:
                available_before = await tenant.get(
                    f"/v1/tenant/catalog/available-services?tenant_id={tenant_id}"
                )
                assert available_before.status_code == 200, available_before.text
                baseline = next(
                    row for row in available_before.json()["data"]["services"]
                    if row.get("admin_ready") and row.get("service_group_id") and row.get("job_type_id")
                )

            master_response = await admin.post(
                "/v1/admin/master-services-v2",
                json={
                    "service_name": f"Catalog Integration Service {suffix}",
                    "category_id": baseline["category_id"],
                    "service_group_id": baseline["service_group_id"],
                    "description": "Temporary Admin to Tenant propagation audit",
                    "tenant_override_allowed": True,
                },
            )
            assert master_response.status_code == 201, master_response.text
            master = master_response.json()["data"]
            created["master"] = _id(master, "service_id", "id", "master_service_id")

            master_update = await admin.put(
                f"/v1/admin/master-services/{created['master']}",
                json={"description": "Updated Admin to Tenant propagation audit"},
            )
            assert master_update.status_code == 200, master_update.text

            for action in ("deactivate", "activate"):
                response = await admin.post(
                    f"/v1/admin/master-services/{created['master']}/{action}"
                )
                assert response.status_code == 200, response.text
            archived = await admin.post(
                f"/v1/admin/master-services/{created['master']}/archive",
                json={"reason": "Temporary operation-level lifecycle audit"},
            )
            assert archived.status_code == 200, archived.text
            restored = await admin.post(
                f"/v1/admin/master-services/{created['master']}/restore",
                json={"reason": "Temporary operation-level lifecycle audit"},
            )
            assert restored.status_code == 200, restored.text
            activated = await admin.post(
                f"/v1/admin/master-services/{created['master']}/activate"
            )
            assert activated.status_code == 200, activated.text

            link_response = await admin.post(
                f"/v1/admin/master-services/{created['master']}/job-types",
                json={"job_type_id": baseline["job_type_id"], "display_order": 1},
            )
            assert link_response.status_code == 201, link_response.text
            created["job_type_link"] = _id(link_response.json()["data"], "id", "link_id")

            workflow_response = await admin.put(
                f"/v1/admin/master-services/{created['master']}/job-types/"
                f"{baseline['job_type_id']}/workflow",
                json={
                    "inspection_required": False,
                    "quote_approval_required": False,
                    "checklist_required": False,
                    "schedule_required": False,
                    "address_required": False,
                    "technician_required": False,
                    "service_area_required": False,
                    "availability_required": False,
                    "pricing_behavior": "fixed",
                },
            )
            assert workflow_response.status_code == 200, workflow_response.text
            created["workflow"] = _id(workflow_response.json()["data"], "id", "workflow_id")

            master_get = await admin.get(f"/v1/admin/master-services/{created['master']}")
            master_list = await admin.get(
                "/v1/admin/master-services",
                params={"q": suffix, "service_group_id": baseline["service_group_id"]},
            )
            master_audit = await admin.get(
                f"/v1/admin/master-services/{created['master']}/audit"
            )
            assert master_get.status_code == master_list.status_code == master_audit.status_code == 200
            assert any(
                row["service_id"] == created["master"]
                for row in master_list.json()["data"]["services"]
            )
            assert master_audit.json()["data"]["total"] >= 4

        async with AsyncClient(base_url=BASE, timeout=30, headers=tenant_headers) as tenant:
            available = await tenant.get(
                f"/v1/tenant/catalog/available-services?tenant_id={tenant_id}"
            )
            assert available.status_code == 200, available.text
            propagated = next(
                row for row in available.json()["data"]["services"]
                if row["service_id"] == created["master"]
            )
            assert propagated["admin_ready"] is True
            assert propagated["service_group_id"] == baseline["service_group_id"]
            assert propagated["job_type_id"] == baseline["job_type_id"]

            enabled = await tenant.post(
                f"/v1/tenant/catalog/enable-service?tenant_id={tenant_id}",
                json={
                    "master_service_id": created["master"],
                    "job_type_id": baseline["job_type_id"],
                    "tenant_display_name": f"Tenant Catalog Service {suffix}",
                    "tenant_base_price": 999,
                    "warranty_days": 7,
                },
            )
            assert enabled.status_code == 201, enabled.text
            created["tenant_service"] = _id(
                enabled.json()["data"], "tenant_service_id", "id"
            )

            updated = await tenant.put(
                f"/v1/tenant/catalog/enabled-services/{created['tenant_service']}",
                json={
                    "tenant_display_name": f"Tenant Catalog Service Updated {suffix}",
                    "tenant_description": "Provider-owned service description",
                    "tenant_base_price": 1099,
                    "warranty_days": 9,
                },
            )
            assert updated.status_code == 200, updated.text
            assert updated.json()["data"]["warranty_days"] == 9

            detail = await tenant.get(
                f"/v1/tenant/catalog/enabled-services/{created['tenant_service']}"
            )
            requirements = await tenant.get(
                f"/v1/tenant/catalog/services/{created['master']}/requirements",
                params={"tenant_id": tenant_id, "job_type_id": baseline["job_type_id"]},
            )
            assert detail.status_code == requirements.status_code == 200
            assert requirements.json()["data"]["tenant_editable"] is False

            draft = await tenant.post(
                f"/v1/tenant/catalog/enabled-services/{created['tenant_service']}/save-draft"
            )
            validation = await tenant.get(
                f"/v1/tenant/catalog/enabled-services/{created['tenant_service']}/validate-for-publish"
            )
            assert draft.status_code == validation.status_code == 200
            assert validation.json()["data"]["valid"] is True, validation.text

            published = await tenant.post(
                f"/v1/tenant/catalog/enabled-services/{created['tenant_service']}/publish"
            )
            assert published.status_code == 200, published.text
            assert published.json()["data"]["setup_status"] == "published"

            price = await tenant.get(
                f"/v1/tenant/catalog/enabled-services/{created['tenant_service']}/resolve-price"
            )
            workspace = await tenant.get("/v1/tenant/home-services/services")
            enabled_list = await tenant.get(
                f"/v1/tenant/catalog/enabled-services?tenant_id={tenant_id}"
            )
            assert price.status_code == workspace.status_code == enabled_list.status_code == 200
            assert price.json()["data"]["resolved"] is True
            assert float(price.json()["data"]["minimum_price"]) == 1099
            assert any(
                row["tenant_service_id"] == created["tenant_service"]
                for row in enabled_list.json()["data"]["services"]
            )

            disabled = await tenant.post(
                f"/v1/tenant/catalog/disable-service?tenant_id={tenant_id}",
                json={
                    "master_service_id": created["master"],
                    "job_type_id": baseline["job_type_id"],
                },
            )
            assert disabled.status_code == 200, disabled.text

    finally:
        conn = await asyncpg.connect(DB_URL)
        try:
            if created.get("tenant_service"):
                tenant_service_id = uuid.UUID(created["tenant_service"])
                for table in ("tenant_service_brands", "tenant_service_types"):
                    await conn.execute(
                        f"DELETE FROM {table} WHERE tenant_service_id=$1", tenant_service_id
                    )
                await conn.execute(
                    "DELETE FROM tenant_services WHERE id=$1", tenant_service_id
                )
            if created.get("master"):
                master_id = uuid.UUID(created["master"])
                for table in (
                    "service_job_workflow", "master_service_job_types",
                    "service_blueprint_versions", "master_service_brands",
                    "master_service_types", "master_data_audit_log",
                ):
                    column = "entity_id" if table == "master_data_audit_log" else "master_service_id"
                    await conn.execute(f"DELETE FROM {table} WHERE {column}=$1", master_id)
                await conn.execute("DELETE FROM master_services WHERE id=$1", master_id)
            if created.get("group"):
                group_id = uuid.UUID(created["group"])
                await conn.execute(
                    "DELETE FROM master_data_audit_log WHERE entity_id=$1", group_id
                )
                await conn.execute("DELETE FROM service_groups WHERE id=$1", group_id)
            if created.get("category"):
                category_id = uuid.UUID(created["category"])
                await conn.execute(
                    "DELETE FROM master_data_audit_log WHERE entity_id=$1", category_id
                )
                await conn.execute("DELETE FROM service_categories WHERE id=$1", category_id)
        finally:
            await conn.close()
