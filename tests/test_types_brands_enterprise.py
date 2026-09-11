"""Enterprise Type/Brand directory regression guards."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_type_and_brand_lists_are_server_paginated_without_n_plus_one():
    type_source = (ROOT / "app/engines/admin_catalog/types_service.py").read_text(encoding="utf-8")
    brand_source = (ROOT / "app/engines/admin_catalog/brand_service.py").read_text(encoding="utf-8")
    type_list = type_source.split("async def list_types", 1)[1].split("async def get_type", 1)[0]
    brand_list = brand_source.split("async def list_brands", 1)[1].split("async def get_brand", 1)[0]
    assert ".limit(page_size).offset(" in type_list
    assert ".limit(page_size).offset(" in brand_list
    assert "_mapping_counts(" not in type_list
    assert "for b in page_rows" not in brand_list


def test_mapping_directories_join_names_and_sync_runtime_tables():
    source = (ROOT / "app/engines/admin_catalog/types_service.py").read_text(encoding="utf-8")
    assert "outerjoin(ServiceGroup" in source
    assert "outerjoin(MasterService" in source
    assert "_sync_type_mapping" in source and "MasterServiceType(" in source
    assert "_sync_brand_mapping" in source and "MasterServiceBrand(" in source
    service = (ROOT / "app/engines/admin_catalog/service.py").read_text(encoding="utf-8")
    assert "_inherit_directory_mappings" in service


def test_retirement_is_soft_audited_guarded_and_restorable():
    types = (ROOT / "app/engines/admin_catalog/types_service.py").read_text(encoding="utf-8")
    brands = (ROOT / "app/engines/admin_catalog/brand_service.py").read_text(encoding="utf-8")
    archive_type = types.split("async def archive_type", 1)[1].split("async def restore_type", 1)[0]
    assert 't.deleted_at = now' in archive_type
    assert "SERVICE_TYPE_IN_USE" not in archive_type
    assert "provider_usages_disabled" in archive_type
    assert "TenantServiceBrand.service_type_id == type_id" in archive_type
    assert 'mapping.status = "archived"' in archive_type
    assert "row.is_active = False" in archive_type
    assert 'b.deleted_at = utcnow()' in brands and "BRAND_IN_USE" in brands
    assert "restore_type" in types and "restore_brand" in brands
    page = (ROOT / "frontend/super-admin/app/admin/types-brands/page.tsx").read_text(encoding="utf-8")
    assert 'retired: lifecycle === "retired"' in page
    assert "restoreAction" in page and "Restore as inactive" in page
    assert not (ROOT / "frontend/super-admin/app/admin/types-brands/retired/page.tsx").exists()


def test_enterprise_personalization_and_export_resources_registered():
    registry = (ROOT / "app/engines/enterprise_grid/filter_registry.py").read_text(encoding="utf-8")
    adapters = (ROOT / "app/engines/enterprise_grid/resource_adapters.py").read_text(encoding="utf-8")
    controls = (ROOT / "frontend/super-admin/components/enterprise/OperationsDirectoryControls.tsx").read_text(encoding="utf-8")
    for key in ("admin_service_types", "admin_brands"):
        assert key in registry and key in adapters and key in controls


def test_brand_mapping_counts_use_list_contract_fields():
    page = (ROOT / "frontend/super-admin/app/admin/types-brands/page.tsx").read_text(encoding="utf-8")
    assert "row.category_mapping_count" in page
    assert "row.service_mapping_count" in page
    assert "row.category_mappings?.length" not in page
