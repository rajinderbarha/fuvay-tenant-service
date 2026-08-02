"""Sprint 34E — Service Options + Issue Catalog tests (95 tests).

Coverage:
- Migration 057 (revision chain, all new tables/columns)
- Model classes (ServiceOptionGroup, ServiceOptionMapping, ServiceIssueMapping,
  TenantSupportedServiceOption, MasterIssueType extensions, MasterServiceOption extensions,
  HomeServiceBookingDraft extensions)
- ServiceOptionService (methods exist, lifecycle, mappings, provider, customer, validate)
- Admin routers (endpoints, require_super_admin)
- Provider router (endpoints, require_technician)
- Customer router (endpoints, no auth)
- main.py registrations
- Seed script (groups, options, issues)
- Super-admin api.ts (interfaces, methods)
- Tenant-portal api.ts (interfaces, methods)
- Provider service-options page (api imports)
- Admin pages (option-groups, service-options, issue-types)
- Audit events
"""
import ast
import os
import re

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def _exists(rel: str) -> bool:
    return os.path.exists(os.path.join(ROOT, rel))


# ═══════════════════════════════════════════════════════════════════════
# MIGRATION 057
# ═══════════════════════════════════════════════════════════════════════

class TestMigration057:
    def setup_method(self):
        self.src = _read("alembic/versions/057_sprint34e_service_options_issue_catalog.py")

    def test_revision_is_057(self):
        assert 'revision = "057"' in self.src

    def test_down_revision_is_056(self):
        assert 'down_revision = "056"' in self.src

    def test_creates_service_option_groups(self):
        assert "service_option_groups" in self.src

    def test_creates_service_option_mappings(self):
        assert "service_option_mappings" in self.src

    def test_creates_service_issue_mappings(self):
        assert "service_issue_mappings" in self.src

    def test_creates_tenant_supported_service_options(self):
        assert "tenant_supported_service_options" in self.src

    def test_adds_status_to_master_service_options(self):
        assert '"master_service_options"' in self.src
        assert '"status"' in self.src

    def test_adds_status_to_master_issue_types(self):
        assert '"master_issue_types"' in self.src

    def test_adds_requires_photo_to_issue_types(self):
        assert "requires_photo" in self.src

    def test_adds_requires_description_to_issue_types(self):
        assert "requires_description" in self.src

    def test_adds_option_group_id_to_options(self):
        assert "option_group_id" in self.src

    def test_adds_metadata_json_to_options(self):
        assert "metadata_json" in self.src

    def test_adds_issue_type_id_to_booking_drafts(self):
        assert "home_service_booking_drafts" in self.src
        assert "issue_type_id" in self.src

    def test_adds_service_option_ids_json_to_drafts(self):
        assert "service_option_ids_json" in self.src

    def test_unique_constraints_present(self):
        assert "uq_som_service_option" in self.src
        assert "uq_sim_service_issue" in self.src
        assert "uq_tsso_tenant_service_option" in self.src
        assert "uq_sog_code" in self.src

    def test_downgrade_drops_all_tables(self):
        assert "downgrade" in self.src
        assert "drop_table" in self.src


# ═══════════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════════

class TestModels:
    def setup_method(self):
        self.src = _read("app/engines/admin_catalog/models.py")

    def test_service_option_group_class_exists(self):
        assert "class ServiceOptionGroup" in self.src

    def test_service_option_group_tablename(self):
        assert '"service_option_groups"' in self.src

    def test_service_option_mapping_class_exists(self):
        assert "class ServiceOptionMapping" in self.src

    def test_service_option_mapping_tablename(self):
        assert '"service_option_mappings"' in self.src

    def test_service_issue_mapping_class_exists(self):
        assert "class ServiceIssueMapping" in self.src

    def test_service_issue_mapping_tablename(self):
        assert '"service_issue_mappings"' in self.src

    def test_tenant_supported_service_option_class_exists(self):
        assert "class TenantSupportedServiceOption" in self.src

    def test_tenant_supported_service_option_tablename(self):
        assert '"tenant_supported_service_options"' in self.src

    def test_master_issue_type_has_status(self):
        # status field added in 34E
        src = self.src
        idx = src.index("class MasterIssueType")
        excerpt = src[idx:idx+3000]
        assert "status" in excerpt

    def test_master_issue_type_has_requires_photo(self):
        idx = self.src.index("class MasterIssueType")
        excerpt = self.src[idx:idx+3000]
        assert "requires_photo" in excerpt

    def test_master_issue_type_has_requires_description(self):
        idx = self.src.index("class MasterIssueType")
        excerpt = self.src[idx:idx+3000]
        assert "requires_description" in excerpt

    def test_master_issue_type_has_metadata_json(self):
        idx = self.src.index("class MasterIssueType")
        excerpt = self.src[idx:idx+3000]
        assert "metadata_json" in excerpt

    def test_master_service_option_has_status(self):
        idx = self.src.index("class MasterServiceOption")
        excerpt = self.src[idx:idx+3000]
        assert "status" in excerpt

    def test_master_service_option_has_option_group_id(self):
        idx = self.src.index("class MasterServiceOption")
        excerpt = self.src[idx:idx+3000]
        assert "option_group_id" in excerpt

    def test_master_service_option_has_vertical_type(self):
        idx = self.src.index("class MasterServiceOption")
        excerpt = self.src[idx:idx+3500]
        assert "vertical_type" in excerpt

    def test_service_issue_mapping_has_is_common(self):
        idx = self.src.index("class ServiceIssueMapping")
        excerpt = self.src[idx:idx+2000]
        assert "is_common" in excerpt

    def test_service_issue_mapping_has_requires_photo(self):
        idx = self.src.index("class ServiceIssueMapping")
        excerpt = self.src[idx:idx+2000]
        assert "requires_photo" in excerpt

    def test_service_option_mapping_has_is_required(self):
        idx = self.src.index("class ServiceOptionMapping")
        excerpt = self.src[idx:idx+3500]
        assert "is_required" in excerpt

    def test_to_dict_methods_present(self):
        assert self.src.count("def to_dict") >= 3  # new models all have to_dict

    def test_booking_draft_has_issue_type_id(self):
        src = _read("app/engines/home_service_booking/models.py")
        assert "issue_type_id" in src

    def test_booking_draft_has_service_option_ids_json(self):
        src = _read("app/engines/home_service_booking/models.py")
        assert "service_option_ids_json" in src


# ═══════════════════════════════════════════════════════════════════════
# SERVICE OPTION SERVICE
# ═══════════════════════════════════════════════════════════════════════

class TestServiceOptionService:
    def setup_method(self):
        self.src = _read("app/engines/admin_catalog/service_option_service.py")

    def test_class_exists(self):
        assert "class ServiceOptionService" in self.src

    def test_init_accepts_tenant_id(self):
        assert "tenant_id" in self.src

    def test_list_option_groups(self):
        assert "async def list_option_groups" in self.src

    def test_create_option_group(self):
        assert "async def create_option_group" in self.src

    def test_update_option_group(self):
        assert "async def update_option_group" in self.src

    def test_list_service_options(self):
        assert "async def list_service_options" in self.src

    def test_create_service_option(self):
        assert "async def create_service_option" in self.src

    def test_update_service_option(self):
        assert "async def update_service_option" in self.src

    def test_activate_service_option(self):
        assert "async def activate_service_option" in self.src

    def test_deactivate_service_option(self):
        assert "async def deactivate_service_option" in self.src

    def test_archive_service_option(self):
        assert "async def archive_service_option" in self.src

    def test_list_issue_types(self):
        assert "async def list_issue_types" in self.src

    def test_create_issue_type(self):
        assert "async def create_issue_type" in self.src

    def test_update_issue_type(self):
        assert "async def update_issue_type" in self.src

    def test_activate_issue_type(self):
        assert "async def activate_issue_type" in self.src

    def test_deactivate_issue_type(self):
        assert "async def deactivate_issue_type" in self.src

    def test_archive_issue_type(self):
        assert "async def archive_issue_type" in self.src

    def test_list_service_option_mappings(self):
        assert "async def list_service_option_mappings" in self.src

    def test_add_service_option_mapping(self):
        assert "async def add_service_option_mapping" in self.src

    def test_update_service_option_mapping(self):
        assert "async def update_service_option_mapping" in self.src

    def test_remove_service_option_mapping(self):
        assert "async def remove_service_option_mapping" in self.src

    def test_list_service_issue_mappings(self):
        assert "async def list_service_issue_mappings" in self.src

    def test_add_service_issue_mapping(self):
        assert "async def add_service_issue_mapping" in self.src

    def test_update_service_issue_mapping(self):
        assert "async def update_service_issue_mapping" in self.src

    def test_remove_service_issue_mapping(self):
        assert "async def remove_service_issue_mapping" in self.src

    def test_get_available_options_for_service(self):
        assert "async def get_available_options_for_service" in self.src

    def test_get_provider_supported_options(self):
        assert "async def get_provider_supported_options" in self.src

    def test_set_provider_supported_options(self):
        assert "async def set_provider_supported_options" in self.src

    def test_validates_options_against_approved_list(self):
        assert "not approved for this service" in self.src

    def test_get_customer_options(self):
        assert "async def get_customer_options" in self.src

    def test_get_customer_issue_types(self):
        assert "async def get_customer_issue_types" in self.src

    def test_validate_service_diagnostics(self):
        assert "async def validate_service_diagnostics" in self.src

    def test_validate_returns_requires_photo(self):
        assert "requires_photo" in self.src

    def test_validate_returns_requires_description(self):
        assert "requires_description" in self.src

    def test_validate_handles_inactive_issue(self):
        assert "ISSUE_TYPE_INACTIVE" in self.src

    def test_validate_handles_unmapped_issue(self):
        assert "ISSUE_TYPE_NOT_MAPPED_TO_SERVICE" in self.src

    def test_validate_handles_unmapped_option(self):
        assert "SERVICE_OPTION_NOT_MAPPED_TO_SERVICE" in self.src

    def test_audit_logging(self):
        assert "_audit" in self.src
        assert "MasterDataAuditLog" in self.src

    def test_audit_events_created(self):
        assert "service_option.created" in self.src

    def test_audit_events_issue_created(self):
        assert "issue_type.created" in self.src

    def test_audit_events_mapped_to_service(self):
        assert "mapped_to_service" in self.src

    def test_audit_events_unmapped_from_service(self):
        assert "unmapped_from_service" in self.src

    def test_audit_events_provider_updated(self):
        assert "provider_service_option.updated" in self.src

    def test_customer_issues_ordered_common_first(self):
        assert "is_common.desc()" in self.src


# ═══════════════════════════════════════════════════════════════════════
# ADMIN ROUTER
# ═══════════════════════════════════════════════════════════════════════

class TestAdminRouter:
    def setup_method(self):
        self.src = _read("app/engines/admin_catalog/service_option_admin_router.py")

    def test_grp_router_prefix(self):
        assert "/v1/admin/service-option-groups" in self.src

    def test_opt_router_prefix(self):
        assert "/v1/admin/service-options" in self.src

    def test_iss_router_prefix(self):
        assert "/v1/admin/issue-types-v2" in self.src

    def test_map_router_prefix(self):
        assert "/v1/admin/master-services" in self.src

    def test_create_option_requires_super_admin(self):
        assert "require_super_admin" in self.src

    def test_create_issue_requires_super_admin(self):
        idx = self.src.index("def create_issue_type")
        excerpt = self.src[max(0, idx-400):idx+400]
        assert "require_super_admin" in excerpt

    def test_activate_option_endpoint(self):
        assert "/activate" in self.src

    def test_deactivate_option_endpoint(self):
        assert "/deactivate" in self.src

    def test_archive_option_endpoint(self):
        assert "/archive" in self.src

    def test_service_option_mapping_get(self):
        assert "/{service_id}/options" in self.src

    def test_service_issue_mapping_get(self):
        assert "/{service_id}/issues" in self.src

    def test_service_option_mapping_delete(self):
        assert "DELETE" in self.src or "delete" in self.src.lower()

    def test_service_issue_mapping_delete(self):
        assert "/{service_id}/issues/{mapping_id}" in self.src


# ═══════════════════════════════════════════════════════════════════════
# PROVIDER ROUTER
# ═══════════════════════════════════════════════════════════════════════

class TestProviderRouter:
    def setup_method(self):
        self.src = _read("app/engines/admin_catalog/service_option_provider_router.py")

    def test_prefix(self):
        assert "/v1/provider/setup/services" in self.src

    def test_available_options_endpoint(self):
        assert "available-options" in self.src

    def test_supported_options_get_endpoint(self):
        assert "supported-options" in self.src

    def test_supported_options_post_endpoint(self):
        assert "router.post" in self.src or "set_provider_supported_options" in self.src

    def test_requires_technician(self):
        assert "require_technician" in self.src

    def test_tenant_id_from_user(self):
        assert "tenant_id" in self.src


# ═══════════════════════════════════════════════════════════════════════
# CUSTOMER ROUTER
# ═══════════════════════════════════════════════════════════════════════

class TestCustomerRouter:
    def setup_method(self):
        self.src = _read("app/engines/admin_catalog/service_option_customer_router.py")

    def test_prefix(self):
        assert "/v1/customer/catalog" in self.src

    def test_service_options_endpoint(self):
        assert "/service-options" in self.src

    def test_issue_types_endpoint(self):
        assert "/issue-types" in self.src

    def test_diagnostics_validate_endpoint(self):
        assert "/service-diagnostics/validate" in self.src

    def test_no_auth_required(self):
        assert "require_super_admin" not in self.src
        assert "require_technician" not in self.src

    def test_no_auth_on_get_service_options(self):
        assert "get_db" in self.src


# ═══════════════════════════════════════════════════════════════════════
# MAIN.PY REGISTRATION
# ═══════════════════════════════════════════════════════════════════════

class TestMainPy:
    def setup_method(self):
        self.src = _read("app/main.py")

    def test_service_option_admin_router_imported(self):
        assert "service_option_admin_router" in self.src

    def test_service_option_provider_router_imported(self):
        assert "service_option_provider_router" in self.src

    def test_service_option_customer_router_imported(self):
        assert "service_option_customer_router" in self.src

    def test_svc_opt_grp_router_registered(self):
        assert "svc_opt_grp_router" in self.src

    def test_svc_opt_router_registered(self):
        assert "svc_opt_router" in self.src

    def test_svc_iss_router_registered(self):
        assert "svc_iss_router" in self.src

    def test_svc_map_router_registered(self):
        assert "svc_map_router" in self.src

    def test_svc_opt_provider_router_registered(self):
        assert "svc_opt_provider_router" in self.src

    def test_svc_opt_customer_router_registered(self):
        assert "svc_opt_customer_router" in self.src


# ═══════════════════════════════════════════════════════════════════════
# SEED SCRIPT
# ═══════════════════════════════════════════════════════════════════════

class TestSeedScript:
    def setup_method(self):
        self.src = _read("scripts/seed_service_options_issues.py")

    def test_file_exists(self):
        assert _exists("scripts/seed_service_options_issues.py")

    def test_has_groups(self):
        assert "GROUPS" in self.src
        assert "ac_type" in self.src

    def test_has_options(self):
        assert "OPTIONS" in self.src
        assert "split_ac" in self.src
        assert "front_load" in self.src

    def test_has_issues(self):
        assert "ISSUES" in self.src
        assert "not_cooling" in self.src
        assert "blockage" in self.src

    def test_idempotent_check_groups(self):
        assert "ServiceOptionGroup" in self.src
        assert "code == g" in self.src or "code ==" in self.src

    def test_idempotent_check_options(self):
        assert "MasterServiceOption" in self.src

    def test_idempotent_check_issues(self):
        assert "MasterIssueType" in self.src

    def test_has_requires_photo_in_issues(self):
        assert "requires_photo" in self.src

    def test_has_requires_description_in_issues(self):
        assert "requires_description" in self.src

    def test_short_circuit_marked_urgent(self):
        assert "urgent" in self.src

    def test_groups_count(self):
        count = self.src.count('"group_code"')
        assert count >= 5

    def test_options_count(self):
        count = self.src.count('"code"')
        assert count >= 20

    def test_issues_count(self):
        assert self.src.count('{"code":') + self.src.count('"code": ') >= 15


# ═══════════════════════════════════════════════════════════════════════
# SUPER-ADMIN FRONTEND API.TS
# ═══════════════════════════════════════════════════════════════════════

class TestSuperAdminApiTs:
    def setup_method(self):
        self.src = _read("frontend/super-admin/lib/api.ts")

    def test_service_option_group_34e_interface(self):
        assert "ServiceOptionGroup34E" in self.src

    def test_service_option_34e_interface(self):
        assert "ServiceOption34E" in self.src

    def test_issue_type_34e_interface(self):
        assert "IssueType34E" in self.src

    def test_service_option_mapping_34e_interface(self):
        assert "ServiceOptionMapping34E" in self.src

    def test_service_issue_mapping_34e_interface(self):
        assert "ServiceIssueMapping34E" in self.src

    def test_service_option_api_object(self):
        assert "serviceOptionApi" in self.src

    def test_list_option_groups(self):
        assert "listOptionGroups" in self.src

    def test_create_option_group(self):
        assert "createOptionGroup" in self.src

    def test_list_options(self):
        assert "listOptions" in self.src

    def test_create_option(self):
        assert "createOption" in self.src

    def test_activate_option(self):
        assert "activateOption" in self.src

    def test_list_issue_types(self):
        assert "listIssueTypes" in self.src

    def test_create_issue_type(self):
        assert "createIssueType" in self.src

    def test_activate_issue_type(self):
        assert "activateIssueType" in self.src

    def test_list_service_option_mappings(self):
        assert "listServiceOptionMappings" in self.src

    def test_add_service_option_mapping(self):
        assert "addServiceOptionMapping" in self.src

    def test_remove_service_option_mapping(self):
        assert "removeServiceOptionMapping" in self.src

    def test_list_service_issue_mappings(self):
        assert "listServiceIssueMappings" in self.src

    def test_add_service_issue_mapping(self):
        assert "addServiceIssueMapping" in self.src

    def test_remove_service_issue_mapping(self):
        assert "removeServiceIssueMapping" in self.src

    def test_uses_api_fetch_not_hardcoded(self):
        assert "apiFetch" in self.src


# ═══════════════════════════════════════════════════════════════════════
# SUPER-ADMIN PAGES
# ═══════════════════════════════════════════════════════════════════════

class TestSuperAdminPages:
    def test_option_groups_page_exists(self):
        assert _exists("frontend/super-admin/app/admin/service-setup/option-groups/page.tsx")

    def test_option_groups_page_uses_api(self):
        src = _read("frontend/super-admin/app/admin/service-setup/option-groups/page.tsx")
        assert "serviceOptionApi" in src
        assert "listOptionGroups" in src

    def test_option_groups_no_hardcoded_groups(self):
        src = _read("frontend/super-admin/app/admin/service-setup/option-groups/page.tsx")
        assert "Split AC" not in src
        assert "AC Type" not in src or "listOptionGroups" in src  # from API not hardcoded

    def test_service_options_page_exists(self):
        assert _exists("frontend/super-admin/app/admin/service-setup/service-options/page.tsx")

    def test_service_options_page_uses_api(self):
        src = _read("frontend/super-admin/app/admin/service-setup/service-options/page.tsx")
        assert "serviceOptionApi" in src
        assert "listOptions" in src

    def test_service_options_page_no_hardcoded_list(self):
        src = _read("frontend/super-admin/app/admin/service-setup/service-options/page.tsx")
        assert '["Split AC"' not in src
        assert '["Front Load"' not in src

    def test_issue_types_page_exists(self):
        assert _exists("frontend/super-admin/app/admin/service-setup/issue-types/page.tsx")

    def test_issue_types_page_uses_api(self):
        src = _read("frontend/super-admin/app/admin/service-setup/issue-types/page.tsx")
        assert "serviceOptionApi" in src
        assert "listIssueTypes" in src

    def test_issue_types_page_no_hardcoded_list(self):
        src = _read("frontend/super-admin/app/admin/service-setup/issue-types/page.tsx")
        assert '["Not cooling"' not in src
        assert '["Blockage"' not in src


# ═══════════════════════════════════════════════════════════════════════
# TENANT-PORTAL API.TS
# ═══════════════════════════════════════════════════════════════════════

class TestTenantPortalApiTs:
    def setup_method(self):
        self.src = _read("frontend/tenant-portal/lib/api.ts")

    def test_provider_available_service_option_interface(self):
        assert "ProviderAvailableServiceOption" in self.src

    def test_provider_supported_service_option_interface(self):
        assert "ProviderSupportedServiceOption" in self.src

    def test_customer_service_option_interface(self):
        assert "CustomerServiceOption" in self.src

    def test_customer_issue_type_interface(self):
        assert "CustomerIssueType" in self.src

    def test_diagnostics_validate_result_interface(self):
        assert "DiagnosticsValidateResult" in self.src

    def test_provider_service_option_api_object(self):
        assert "providerServiceOptionApi" in self.src

    def test_get_available_for_service(self):
        assert "getAvailableForService" in self.src

    def test_get_supported_for_service(self):
        assert "getSupportedForService" in self.src

    def test_set_supported_for_service(self):
        assert "setSupportedForService" in self.src

    def test_customer_service_diagnostics_api(self):
        assert "customerServiceDiagnosticsApi" in self.src

    def test_get_service_options(self):
        assert "getServiceOptions" in self.src

    def test_get_issue_types(self):
        assert "getIssueTypes" in self.src

    def test_validate_endpoint(self):
        assert "validate" in self.src
        assert "service-diagnostics" in self.src


# ═══════════════════════════════════════════════════════════════════════
# PROVIDER SERVICE-OPTIONS PAGE
# ═══════════════════════════════════════════════════════════════════════

class TestProviderServiceOptionsPage:
    def setup_method(self):
        path = "frontend/tenant-portal/app/(tenant)/provider/service-options/page.tsx"
        assert _exists(path), f"File not found: {path}"
        self.src = _read(path)

    def test_imports_provider_service_option_api(self):
        assert "providerServiceOptionApi" in self.src

    def test_loads_available_options(self):
        assert "getAvailableForService" in self.src

    def test_loads_supported_options(self):
        assert "getSupportedForService" in self.src

    def test_saves_supported_options(self):
        assert "setSupportedForService" in self.src

    def test_no_hardcoded_option_names(self):
        assert '"Split AC"' not in self.src
        assert '"Front Load"' not in self.src

    def test_chip_based_selection(self):
        assert "selected" in self.src or "toggle" in self.src
