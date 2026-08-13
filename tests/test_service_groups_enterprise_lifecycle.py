"""Enterprise Service Groups control-plane contracts."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_directory_queries_are_database_aggregated_and_paged():
    src = read("app/engines/admin_catalog/service.py")
    section = src[src.index("async def _sg_linked_counts"):src.index("# MASTER SERVICES — Enterprise")]
    assert "func.count(func.distinct(TenantService.tenant_id))" in section
    assert "provider_counts: dict[str, set[str]]" not in section
    assert "func.count(ServiceGroup.id).filter" in section
    assert "sort_columns =" in section
    assert ".limit(limit).offset(offset)" in section


def test_lifecycle_is_audited_recoverable_and_reasoned():
    src = read("app/engines/admin_catalog/service.py")
    router = read("app/engines/admin_catalog/admin_router.py")
    assert "async def restore_service_group" in src
    assert '"service_group", g.id, "retire"' in src
    assert '"service_group", g.id, "restore"' in src
    assert "len(reason) < 10" in src
    assert '/service-groups/{group_id}/restore' in router
    assert '/service-groups/{group_id}/audit' in router
    assert '/service-groups/bulk-status' in router


def test_inner_and_retired_pages_are_real_routes_with_connected_links():
    detail = read("frontend/super-admin/app/admin/service-groups/[id]/page.tsx")
    retired = read("frontend/super-admin/app/admin/service-groups/retired/page.tsx")
    directory = read("frontend/super-admin/app/admin/service-groups/page.tsx")
    assert "getServiceGroupAudit" in detail
    assert "/admin/master-services?service_group_id=" in detail
    assert "/admin/categories/" in detail
    assert "restoreServiceGroup" in retired
    assert 'resourceKey="admin_service_groups"' in directory
    assert "/admin/service-groups/retired" in directory
    assert "bulkServiceGroupStatus" in directory


def test_service_group_export_and_database_indexes_are_enterprise_enabled():
    registry = read("app/engines/enterprise_grid/filter_registry.py")
    adapters = read("app/engines/enterprise_grid/resource_adapters.py")
    migration = read("alembic/versions/255_service_group_enterprise_indexes.py")
    assert '"admin_service_groups"' in registry
    assert '"admin_service_groups":  _adapter_admin_service_groups' in adapters
    assert "ix_sg_live_directory" in migration
    assert "ix_sg_name_trgm" in migration
    assert "ix_tenant_services_enabled_lookup" in migration
