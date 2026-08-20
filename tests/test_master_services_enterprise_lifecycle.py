"""Enterprise Master Services control-plane contracts."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_directory_queries_are_database_aggregated_joined_and_paged():
    src = read("app/engines/admin_catalog/service.py")
    section = src[src.index("# MASTER SERVICES — Enterprise"):]
    assert "func.count().filter(live)" in section
    assert "select(MasterService, ServiceCategory.name" in section
    assert "provider_exists = exists().where" in section
    assert "sort_columns =" in section
    assert ".limit(limit).offset(offset)" in section
    assert "select(MasterService).where(MasterService.deleted_at.is_(None))\n        result" not in section


def test_canonical_mappings_and_blueprints_drive_counts_and_readiness():
    src = read("app/engines/admin_catalog/service.py")
    section = src[src.index("async def _ms_linked_counts"):src.index("async def get_master_services_summary")]
    assert "ServiceOptionMapping.master_service_id" in section
    assert "ServiceIssueMapping.master_service_id" in section
    assert "MasterServiceJobType.master_service_id" in section
    assert "ServiceJobWorkflow.master_service_id" in section
    assert 'return "missing_job_types"' in section
    assert 'return "missing_workflows"' in section


def test_hierarchy_is_validated_for_create_update_and_activation():
    src = read("app/engines/admin_catalog/service.py")
    assert src.count("SERVICE_GROUP_CATEGORY_MISMATCH") >= 2
    activate = src[src.index("async def activate_master_service"):src.index("async def deactivate_master_service")]
    assert "SERVICE_CATEGORY_INACTIVE" in activate
    assert "SERVICE_GROUP_INACTIVE" in activate
    assert "SERVICE_GROUP_REQUIRED" in activate


def test_lifecycle_is_audited_recoverable_and_safe_for_provider_history():
    src = read("app/engines/admin_catalog/service.py")
    router = read("app/engines/admin_catalog/admin_router.py")
    assert "async def restore_master_service" in src
    assert '"master_service", svc.id, "retire"' in src
    assert '"master_service", svc.id, "restore"' in src
    assert "MASTER_SERVICE_IN_USE" in src
    assert "len((reason or \"\").strip()) < 10" in src
    assert '/master-services/{service_id}/restore' in router
    assert '/master-services/{service_id}/audit' in router
    assert '/master-services/bulk-status' in router
    assert "PERMANENT_DELETE_DISABLED" in router


def test_inner_and_integrated_lifecycle_directory_are_durable_connected_routes():
    detail = read("frontend/super-admin/app/admin/master-services/[id]/page.tsx")
    directory = read("frontend/super-admin/app/admin/master-services/page.tsx")
    assert "getMasterServiceAudit" in detail
    assert "/admin/catalog-workspace?service_id=" in detail
    assert "/admin/service-groups/" in detail
    assert "/admin/categories/" in detail
    assert 'resourceKey="admin_master_services"' in directory
    assert 'lifecycleFilter' in directory
    assert 'retired: lifecycleFilter === "retired"' in directory
    assert "View / restore" in directory
    assert "/admin/master-services/retired" not in directory
    assert not (ROOT / "frontend/super-admin/app/admin/master-services/retired/page.tsx").exists()
    assert "bulkMasterServiceStatus" in directory


def test_export_registry_and_postgres_indexes_cover_large_directories():
    registry = read("app/engines/enterprise_grid/filter_registry.py")
    adapters = read("app/engines/enterprise_grid/resource_adapters.py")
    controls = read("frontend/super-admin/components/enterprise/OperationsDirectoryControls.tsx")
    migration = read("alembic/versions/256_master_service_enterprise_indexes.py")
    assert '"admin_master_services"' in registry
    assert '"admin_master_services": _adapter_admin_master_services' in adapters
    assert "admin_master_services" in controls
    assert "ix_ms_live_directory" in migration
    assert "ix_ms_retired_directory" in migration
    assert "ix_ms_name_trgm" in migration
    assert "CREATE INDEX CONCURRENTLY" in migration
