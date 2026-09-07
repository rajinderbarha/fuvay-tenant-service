"""Enterprise contracts for the consolidated admin Catalog Workspace."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_workspace_queries_are_bounded_debounced_and_context_scoped():
    page = read("frontend/super-admin/app/admin/catalog-workspace/page.tsx")
    add_job_type = read("frontend/super-admin/components/catalog/AddServiceJobType.tsx")
    api = read("frontend/super-admin/lib/api.ts")
    router = read("app/engines/checklist_catalog/admin_router.py")
    assert "debouncedServiceQuery" in page
    assert "servicePageSize" in page and "Services per page" in page
    # Attaching a job type is now a bounded pick from the curated,
    # runtime-supported set (job_type_blueprint_service.py rejects anything
    # else) -- not a searchable, debounced, ad-hoc-creatable picker.
    assert "pageSize: 100" in add_job_type and "runtime_supported" in add_job_type
    mapping_form = read("frontend/super-admin/components/catalog/AddChecklistMappingForm.tsx")
    assert "listPublishedTemplateOptions" in mapping_form
    assert "listMappingsDirectory" in page
    assert "master_service_job_type_id: masterServiceJobTypeId" in page
    assert "master_service_job_type_id: uuid.UUID | None" in router
    assert "master_service_job_type_id?: string" in api
    assert "checklistCatalogApi.listMappings()" not in page


def test_catalog_console_aggregates_only_current_page():
    source = read("app/engines/admin_catalog/service.py")
    section = source[source.index("async def list_home_services_catalog_console"):source.index("async def get_home_services_service_console_detail")]
    assert "service_ids = [service.id for service in svcs]" in section
    assert "MasterServiceType.master_service_id.in_(service_ids)" in section
    assert "MasterServiceBrand.master_service_id.in_(service_ids)" in section


def test_job_type_directory_is_server_paginated_and_searchable():
    service = read("app/engines/admin_catalog/job_type_service.py")
    router = read("app/engines/admin_catalog/job_type_router.py")
    assert "search: str | None" in service
    assert ".offset((page - 1) * page_size)" in service
    assert ".limit(page_size)" in service
    assert "page_size: int = Query(50, ge=1, le=100)" in router


def test_dimension_readiness_batches_value_counts():
    service = read("app/engines/admin_catalog/dimension_service.py")
    section = service[service.index("async def get_service_job_dimensions"):service.index("async def set_service_job_dimension")]
    assert "generic_counts" in section
    assert ".group_by(CatalogDimensionValue.dimension_id)" in section
    assert "await self._value_count" not in section


def test_retired_catalog_notice_routes_are_removed():
    removed = [
        "frontend/super-admin/app/admin/service-options/page.tsx",
        "frontend/super-admin/app/admin/service-options/[id]/page.tsx",
        "frontend/super-admin/app/admin/issue-types/page.tsx",
        "frontend/super-admin/app/admin/pricing-tiers/page.tsx",
        "frontend/super-admin/app/admin/pricing/tiers/[tier_id]/page.tsx",
        "frontend/super-admin/app/admin/location-mapping/page.tsx",
        "frontend/super-admin/app/admin/home-services/pricing-rules/page.tsx",
        "frontend/super-admin/app/admin/catalog/[vertical]/page.tsx",
        "frontend/super-admin/app/admin/catalog-module/[key]/page.tsx",
    ]
    assert all(not (ROOT / path).exists() for path in removed)
