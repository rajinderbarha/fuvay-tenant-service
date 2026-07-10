"""Sprint 34H — Admin Bulk Setup Wizard test suite.

Tests: migration 059, models, services, router, main.py, frontend api.ts, frontend pages.
"""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


# ── Migration 059 ─────────────────────────────────────────────────────────────

class TestMigration059(unittest.TestCase):
    def setUp(self):
        self.src = _read("alembic/versions/059_sprint34h_bulk_setup_wizard.py")

    def test_revision_is_059(self):
        self.assertIn('revision = "059"', self.src)

    def test_down_revision_is_058(self):
        self.assertIn('down_revision = "058"', self.src)

    def test_creates_admin_bulk_setup_drafts(self):
        self.assertIn('"admin_bulk_setup_drafts"', self.src)

    def test_creates_admin_bulk_setup_runs(self):
        self.assertIn('"admin_bulk_setup_runs"', self.src)

    def test_creates_admin_bulk_setup_run_items(self):
        self.assertIn('"admin_bulk_setup_run_items"', self.src)

    def test_draft_status_field(self):
        self.assertIn('"status"', self.src)
        self.assertIn('"draft"', self.src)

    def test_draft_current_step_field(self):
        self.assertIn('"current_step"', self.src)

    def test_draft_target_vertical_type(self):
        self.assertIn('"target_vertical_type"', self.src)

    def test_draft_target_category_id(self):
        self.assertIn('"target_category_id"', self.src)

    def test_draft_selected_service_ids_json(self):
        self.assertIn('"selected_service_ids_json"', self.src)

    def test_draft_new_services_payload_json(self):
        self.assertIn('"new_services_payload_json"', self.src)

    def test_draft_selected_template_ids_json(self):
        self.assertIn('"selected_template_ids_json"', self.src)

    def test_draft_bulk_setup_payload_json(self):
        self.assertIn('"bulk_setup_payload_json"', self.src)

    def test_draft_preview_summary_json(self):
        self.assertIn('"preview_summary_json"', self.src)

    def test_draft_blocking_items_json(self):
        self.assertIn('"blocking_items_json"', self.src)

    def test_draft_applied_at(self):
        self.assertIn('"applied_at"', self.src)

    def test_run_draft_id(self):
        self.assertIn('"draft_id"', self.src)

    def test_run_status_default_running(self):
        self.assertIn('"running"', self.src)

    def test_run_summary_json(self):
        self.assertIn('"summary_json"', self.src)

    def test_run_item_entity_type(self):
        self.assertIn('"entity_type"', self.src)

    def test_run_item_action(self):
        self.assertIn('"action"', self.src)

    def test_run_item_entity_code(self):
        self.assertIn('"entity_code"', self.src)

    def test_index_draft_status(self):
        self.assertIn('"ix_abs_draft_status"', self.src)

    def test_index_run_draft(self):
        self.assertIn('"ix_abs_run_draft"', self.src)

    def test_index_run_item_run(self):
        self.assertIn('"ix_abs_run_item_run"', self.src)

    def test_downgrade_drops_tables(self):
        self.assertIn("downgrade", self.src)
        self.assertIn("drop_table", self.src)


# ── Models ────────────────────────────────────────────────────────────────────

class TestModels34H(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/engines/admin_catalog/models.py")

    def _cls(self, name: str, size: int = 2000) -> str:
        idx = self.src.find(f"class {name}(")
        self.assertGreater(idx, -1, f"{name} not found in models.py")
        return self.src[idx: idx + size]

    def test_admin_bulk_setup_draft_class_exists(self):
        self.assertIn("class AdminBulkSetupDraft(", self.src)

    def test_admin_bulk_setup_run_class_exists(self):
        self.assertIn("class AdminBulkSetupRun(", self.src)

    def test_admin_bulk_setup_run_item_class_exists(self):
        self.assertIn("class AdminBulkSetupRunItem(", self.src)

    def test_draft_tablename(self):
        w = self._cls("AdminBulkSetupDraft")
        self.assertIn("admin_bulk_setup_drafts", w)

    def test_draft_has_status(self):
        w = self._cls("AdminBulkSetupDraft")
        self.assertIn("status", w)

    def test_draft_has_current_step(self):
        w = self._cls("AdminBulkSetupDraft")
        self.assertIn("current_step", w)

    def test_draft_has_bulk_setup_payload_json(self):
        w = self._cls("AdminBulkSetupDraft")
        self.assertIn("bulk_setup_payload_json", w)

    def test_draft_has_preview_summary_json(self):
        w = self._cls("AdminBulkSetupDraft")
        self.assertIn("preview_summary_json", w)

    def test_draft_has_blocking_items_json(self):
        w = self._cls("AdminBulkSetupDraft")
        self.assertIn("blocking_items_json", w)

    def test_draft_has_applied_at(self):
        w = self._cls("AdminBulkSetupDraft")
        self.assertIn("applied_at", w)

    def test_draft_has_to_dict(self):
        w = self._cls("AdminBulkSetupDraft")
        self.assertIn("to_dict", w)

    def test_run_has_draft_id(self):
        w = self._cls("AdminBulkSetupRun")
        self.assertIn("draft_id", w)

    def test_run_has_summary_json(self):
        w = self._cls("AdminBulkSetupRun")
        self.assertIn("summary_json", w)

    def test_run_has_completed_at(self):
        w = self._cls("AdminBulkSetupRun")
        self.assertIn("completed_at", w)

    def test_run_item_has_entity_type(self):
        w = self._cls("AdminBulkSetupRunItem")
        self.assertIn("entity_type", w)

    def test_run_item_has_action(self):
        w = self._cls("AdminBulkSetupRunItem")
        self.assertIn("action", w)

    def test_run_item_has_entity_code(self):
        w = self._cls("AdminBulkSetupRunItem")
        self.assertIn("entity_code", w)

    def test_models_before_customer_flow_config(self):
        idx_draft = self.src.find("class AdminBulkSetupDraft(")
        idx_cfc = self.src.find("class CustomerFlowConfig(")
        self.assertGreater(idx_cfc, idx_draft)


# ── Bulk Setup Service ────────────────────────────────────────────────────────

class TestBulkSetupService(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/engines/admin_catalog/bulk_setup_service.py")

    def test_file_exists(self):
        self.assertIn("AdminBulkSetupDraftService", self.src)

    def test_has_create_draft(self):
        self.assertIn("async def create_draft", self.src)

    def test_has_list_drafts(self):
        self.assertIn("async def list_drafts", self.src)

    def test_has_get_draft(self):
        self.assertIn("async def get_draft", self.src)

    def test_has_update_draft(self):
        self.assertIn("async def update_draft", self.src)

    def test_has_delete_draft(self):
        self.assertIn("async def delete_draft", self.src)

    def test_has_set_category(self):
        self.assertIn("async def set_category", self.src)

    def test_has_set_services(self):
        self.assertIn("async def set_services", self.src)

    def test_has_set_templates(self):
        self.assertIn("async def set_templates", self.src)

    def test_has_set_brand_mappings(self):
        self.assertIn("async def set_brand_mappings", self.src)

    def test_has_set_option_mappings(self):
        self.assertIn("async def set_option_mappings", self.src)

    def test_has_set_issue_mappings(self):
        self.assertIn("async def set_issue_mappings", self.src)

    def test_has_set_document_mappings(self):
        self.assertIn("async def set_document_mappings", self.src)

    def test_has_set_checklist_mappings(self):
        self.assertIn("async def set_checklist_mappings", self.src)

    def test_has_set_pricing_mappings(self):
        self.assertIn("async def set_pricing_mappings", self.src)

    def test_has_set_commission_mappings(self):
        self.assertIn("async def set_commission_mappings", self.src)

    def test_has_set_workflow_mappings(self):
        self.assertIn("async def set_workflow_mappings", self.src)

    def test_has_get_available_categories(self):
        self.assertIn("async def get_available_categories", self.src)

    def test_has_get_available_services(self):
        self.assertIn("async def get_available_services", self.src)

    def test_has_get_available_templates(self):
        self.assertIn("async def get_available_templates", self.src)

    def test_has_get_available_brands(self):
        self.assertIn("async def get_available_brands", self.src)

    def test_has_get_available_brand_templates(self):
        self.assertIn("async def get_available_brand_templates", self.src)

    def test_has_get_available_option_groups(self):
        self.assertIn("async def get_available_option_groups", self.src)

    def test_has_get_available_service_options(self):
        self.assertIn("async def get_available_service_options", self.src)

    def test_has_get_available_issue_types(self):
        self.assertIn("async def get_available_issue_types", self.src)

    def test_has_get_available_workflow_templates(self):
        self.assertIn("async def get_available_workflow_templates", self.src)

    def test_has_get_available_pricing_templates(self):
        self.assertIn("async def get_available_pricing_templates", self.src)

    def test_has_get_available_commission_templates(self):
        self.assertIn("async def get_available_commission_templates", self.src)

    def test_commission_deferred_note(self):
        self.assertIn("deferred", self.src)

    def test_audit_events_logged(self):
        self.assertIn("admin_bulk_setup.draft_created", self.src)
        self.assertIn("admin_bulk_setup.category_selected", self.src)
        self.assertIn("admin_bulk_setup.brand_mappings_updated", self.src)


# ── Validation Service ────────────────────────────────────────────────────────

class TestValidationService(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/engines/admin_catalog/bulk_setup_service.py")

    def test_validation_service_exists(self):
        self.assertIn("AdminBulkSetupValidationService", self.src)

    def test_has_validate_draft(self):
        self.assertIn("async def validate_draft", self.src)

    def test_has_get_blocking_items(self):
        self.assertIn("async def get_blocking_items", self.src)

    def test_category_required_blocker(self):
        self.assertIn("CATEGORY_REQUIRED", self.src)

    def test_service_slug_duplicate_blocker(self):
        self.assertIn("SERVICE_SLUG_DUPLICATE", self.src)

    def test_template_inactive_blocker(self):
        self.assertIn("TEMPLATE_INACTIVE", self.src)

    def test_brand_inactive_blocker(self):
        self.assertIn("BRAND_INACTIVE", self.src)

    def test_option_inactive_blocker(self):
        self.assertIn("OPTION_INACTIVE", self.src)

    def test_issue_inactive_blocker(self):
        self.assertIn("ISSUE_INACTIVE", self.src)

    def test_p0_severity_used(self):
        self.assertIn('"P0"', self.src)

    def test_can_apply_flag(self):
        self.assertIn("can_apply", self.src)


# ── Preview Service ───────────────────────────────────────────────────────────

class TestPreviewService(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/engines/admin_catalog/bulk_setup_service.py")

    def test_preview_service_exists(self):
        self.assertIn("AdminBulkSetupPreviewService", self.src)

    def test_has_preview_method(self):
        self.assertIn("async def preview(", self.src)

    def test_preview_no_mutation(self):
        idx = self.src.find("class AdminBulkSetupPreviewService")
        snippet = self.src[idx: idx + 6000]
        self.assertNotIn("self.db.commit()", snippet)

    def test_preview_shows_creates(self):
        self.assertIn("creates", self.src)

    def test_preview_shows_reuses(self):
        self.assertIn("reuses", self.src)

    def test_preview_shows_skips(self):
        self.assertIn("skips", self.src)

    def test_preview_shows_conflicts(self):
        self.assertIn("conflicts", self.src)

    def test_preview_shows_brand_mappings(self):
        self.assertIn("brand_mapping", self.src)

    def test_preview_shows_option_mappings(self):
        self.assertIn("option_mapping", self.src)

    def test_preview_shows_issue_mappings(self):
        self.assertIn("issue_mapping", self.src)

    def test_preview_shows_workflow_mappings(self):
        self.assertIn("workflow_mapping", self.src)

    def test_preview_notes_no_db_change(self):
        self.assertIn("Preview without mutation", self.src)


# ── Apply Service ─────────────────────────────────────────────────────────────

class TestApplyService(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/engines/admin_catalog/bulk_setup_service.py")

    def test_apply_service_exists(self):
        self.assertIn("AdminBulkSetupApplyService", self.src)

    def test_has_apply_method(self):
        self.assertIn("async def apply(", self.src)

    def test_has_list_runs(self):
        self.assertIn("async def list_runs", self.src)

    def test_has_get_run_detail(self):
        self.assertIn("async def get_run_detail", self.src)

    def test_creates_run_record(self):
        self.assertIn("AdminBulkSetupRun(", self.src)

    def test_creates_run_items(self):
        self.assertIn("AdminBulkSetupRunItem(", self.src)

    def test_idempotent_brand_mapping(self):
        self.assertIn("Mapping already exists", self.src)

    def test_idempotent_option_mapping(self):
        self.assertIn("Already mapped", self.src)

    def test_idempotent_service_creation(self):
        self.assertIn("slug exists", self.src)

    def test_records_created_count(self):
        self.assertIn('"created"', self.src)

    def test_records_skipped_count(self):
        self.assertIn('"skipped"', self.src)

    def test_records_errors_count(self):
        self.assertIn('"errors"', self.src)

    def test_apply_updates_draft_status(self):
        self.assertIn("applied", self.src)

    def test_apply_audit_logged(self):
        self.assertIn("admin_bulk_setup.applied", self.src)


# ── Router ────────────────────────────────────────────────────────────────────

class TestBulkSetupRouter(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/engines/admin_catalog/bulk_setup_router.py")

    def test_router_prefix(self):
        self.assertIn("/v1/admin/bulk-setup", self.src)

    def test_requires_super_admin(self):
        self.assertIn("require_super_admin", self.src)

    def test_create_draft_endpoint(self):
        self.assertIn("create_draft", self.src)
        self.assertIn('"/drafts"', self.src)

    def test_list_drafts_endpoint(self):
        self.assertIn("list_drafts", self.src)

    def test_get_draft_endpoint(self):
        self.assertIn("get_draft", self.src)

    def test_update_draft_endpoint(self):
        self.assertIn("update_draft", self.src)

    def test_delete_draft_endpoint(self):
        self.assertIn("delete_draft", self.src)

    def test_available_categories_endpoint(self):
        self.assertIn("available-categories", self.src)

    def test_available_services_endpoint(self):
        self.assertIn("available-services", self.src)

    def test_available_templates_endpoint(self):
        self.assertIn("available-templates", self.src)

    def test_available_brands_endpoint(self):
        self.assertIn("available-brands", self.src)

    def test_available_brand_templates_endpoint(self):
        self.assertIn("available-brand-templates", self.src)

    def test_available_option_groups_endpoint(self):
        self.assertIn("available-option-groups", self.src)

    def test_available_service_options_endpoint(self):
        self.assertIn("available-service-options", self.src)

    def test_available_issue_types_endpoint(self):
        self.assertIn("available-issue-types", self.src)

    def test_available_document_requirements_endpoint(self):
        self.assertIn("available-document-requirements", self.src)

    def test_available_checklist_templates_endpoint(self):
        self.assertIn("available-checklist-templates", self.src)

    def test_available_pricing_templates_endpoint(self):
        self.assertIn("available-pricing-templates", self.src)

    def test_available_commission_templates_endpoint(self):
        self.assertIn("available-commission-templates", self.src)

    def test_available_workflow_templates_endpoint(self):
        self.assertIn("available-workflow-templates", self.src)

    def test_set_category_endpoint(self):
        self.assertIn("set_category", self.src)
        self.assertIn("/category", self.src)

    def test_set_services_endpoint(self):
        self.assertIn("set_services", self.src)
        self.assertIn("/services", self.src)

    def test_set_templates_endpoint(self):
        self.assertIn("set_templates", self.src)
        self.assertIn("/templates", self.src)

    def test_set_brand_mappings_endpoint(self):
        self.assertIn("set_brand_mappings", self.src)
        self.assertIn("brand-mappings", self.src)

    def test_set_option_mappings_endpoint(self):
        self.assertIn("set_option_mappings", self.src)

    def test_set_issue_mappings_endpoint(self):
        self.assertIn("set_issue_mappings", self.src)

    def test_set_document_mappings_endpoint(self):
        self.assertIn("set_document_mappings", self.src)

    def test_set_checklist_mappings_endpoint(self):
        self.assertIn("set_checklist_mappings", self.src)

    def test_set_pricing_mappings_endpoint(self):
        self.assertIn("set_pricing_mappings", self.src)

    def test_set_commission_mappings_endpoint(self):
        self.assertIn("set_commission_mappings", self.src)

    def test_set_workflow_mappings_endpoint(self):
        self.assertIn("set_workflow_mappings", self.src)

    def test_validate_endpoint(self):
        self.assertIn("validate_draft", self.src)
        self.assertIn("/validate", self.src)

    def test_preview_endpoint(self):
        self.assertIn("preview_draft", self.src)
        self.assertIn("/preview", self.src)

    def test_review_endpoint(self):
        self.assertIn("review_draft", self.src)
        self.assertIn("/review", self.src)

    def test_apply_endpoint(self):
        self.assertIn("apply_draft", self.src)
        self.assertIn("/apply", self.src)

    def test_apply_blocked_by_p0(self):
        self.assertIn("APPLY_BLOCKED_BY_P0_ERRORS", self.src)

    def test_list_runs_endpoint(self):
        self.assertIn("list_runs", self.src)
        self.assertIn("/runs", self.src)

    def test_get_run_endpoint(self):
        self.assertIn("get_run", self.src)

    def test_no_provider_or_customer_access(self):
        self.assertNotIn("require_customer", self.src)
        self.assertNotIn("require_technician", self.src)


# ── main.py ───────────────────────────────────────────────────────────────────

class TestMainPy34H(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/main.py")

    def test_imports_bulk_setup_router(self):
        self.assertIn("bulk_setup_router", self.src)

    def test_from_bulk_setup_router_import(self):
        self.assertIn("bulk_setup_router", self.src)

    def test_router_included(self):
        self.assertIn("include_router(bulk_setup_router)", self.src)


# ── Frontend api.ts ───────────────────────────────────────────────────────────

class TestFrontendApiTs34H(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/super-admin/lib/api.ts")

    def test_bulk_setup_draft_interface(self):
        self.assertIn("BulkSetupDraft", self.src)

    def test_bulk_new_service_interface(self):
        self.assertIn("BulkNewService", self.src)

    def test_bulk_setup_payload_interface(self):
        self.assertIn("BulkSetupPayload", self.src)

    def test_bulk_preview_summary_interface(self):
        self.assertIn("BulkPreviewSummary", self.src)

    def test_bulk_blocker_interface(self):
        self.assertIn("BulkBlocker", self.src)

    def test_bulk_setup_run_interface(self):
        self.assertIn("BulkSetupRun", self.src)

    def test_bulk_setup_run_item_interface(self):
        self.assertIn("BulkSetupRunItem", self.src)

    def test_bulk_setup_api_object(self):
        self.assertIn("bulkSetupApi", self.src)

    def test_create_draft_method(self):
        self.assertIn("createDraft", self.src)

    def test_list_drafts_method(self):
        self.assertIn("listDrafts", self.src)

    def test_get_draft_method(self):
        self.assertIn("getDraft", self.src)

    def test_update_draft_method(self):
        self.assertIn("updateDraft", self.src)

    def test_delete_draft_method(self):
        self.assertIn("deleteDraft", self.src)

    def test_get_available_categories_method(self):
        self.assertIn("getAvailableCategories", self.src)

    def test_get_available_services_method(self):
        self.assertIn("getAvailableServices", self.src)

    def test_get_available_templates_method(self):
        self.assertIn("getAvailableTemplates", self.src)

    def test_get_available_brands_method(self):
        self.assertIn("getAvailableBrands", self.src)

    def test_get_available_option_groups_method(self):
        self.assertIn("getAvailableOptionGroups", self.src)

    def test_get_available_service_options_method(self):
        self.assertIn("getAvailableServiceOptions", self.src)

    def test_get_available_issue_types_method(self):
        self.assertIn("getAvailableIssueTypes", self.src)

    def test_get_available_workflow_templates_method(self):
        self.assertIn("getAvailableWorkflowTemplates", self.src)

    def test_set_category_method(self):
        self.assertIn("setCategory", self.src)

    def test_set_services_method(self):
        self.assertIn("setServices", self.src)

    def test_set_templates_method(self):
        self.assertIn("setTemplates", self.src)

    def test_set_brand_mappings_method(self):
        self.assertIn("setBrandMappings", self.src)

    def test_set_option_mappings_method(self):
        self.assertIn("setOptionMappings", self.src)

    def test_set_issue_mappings_method(self):
        self.assertIn("setIssueMappings", self.src)

    def test_set_document_mappings_method(self):
        self.assertIn("setDocumentMappings", self.src)

    def test_set_checklist_mappings_method(self):
        self.assertIn("setChecklistMappings", self.src)

    def test_set_pricing_mappings_method(self):
        self.assertIn("setPricingMappings", self.src)

    def test_set_commission_mappings_method(self):
        self.assertIn("setCommissionMappings", self.src)

    def test_set_workflow_mappings_method(self):
        self.assertIn("setWorkflowMappings", self.src)

    def test_validate_draft_method(self):
        self.assertIn("validateDraft", self.src)

    def test_preview_draft_method(self):
        self.assertIn("previewDraft", self.src)

    def test_review_draft_method(self):
        self.assertIn("reviewDraft", self.src)

    def test_apply_draft_method(self):
        self.assertIn("applyDraft", self.src)

    def test_list_runs_method(self):
        self.assertIn("listRuns", self.src)

    def test_get_run_method(self):
        self.assertIn("getRun", self.src)

    def test_uses_v1_admin_bulk_setup_prefix(self):
        self.assertIn("/v1/admin/bulk-setup", self.src)

    def test_uses_api_fetch(self):
        idx = self.src.find("bulkSetupApi")
        self.assertIn("apiFetch", self.src[idx: idx + 5000])


# ── Frontend Pages ────────────────────────────────────────────────────────────

class TestBulkWizardListPage(unittest.TestCase):
    """NOTE: this list page was rewritten to the enterprise bulkWizardApi
    (migration 098 / app/engines/service_setup) — the Sprint 34H
    bulkSetupApi/BulkSetupDraft backend it originally tested still exists
    (admin_bulk_setup_drafts, unchanged) but is no longer what this specific
    page renders. Assertions updated to match the current
    frontend/super-admin/app/admin/service-setup/bulk-wizard/page.tsx.
    The [draftId] detail page (TestBulkWizardDetailPage below) was NOT
    rewritten and still uses bulkSetupApi — untouched.
    """
    def setUp(self):
        self.src = _read("frontend/super-admin/app/admin/service-setup/bulk-wizard/page.tsx")

    def test_use_client(self):
        self.assertIn('"use client"', self.src)

    def test_imports_bulk_wizard_api(self):
        self.assertIn("bulkWizardApi", self.src)

    def test_imports_draft_interface(self):
        self.assertIn("BulkDraftItem", self.src)

    def test_calls_list_drafts(self):
        self.assertIn("bulkWizardApi.list(", self.src)

    def test_calls_create_draft(self):
        self.assertIn("bulkWizardApi.createDraft(", self.src)

    def test_has_new_bulk_setup_button(self):
        self.assertIn("New Bulk Setup", self.src)

    def test_has_status_filter(self):
        self.assertIn("statusFilter", self.src)

    def test_opens_wizard_modal_for_draft(self):
        self.assertIn("openWizard", self.src)
        self.assertIn("WizardModal", self.src)

    def test_links_to_bulk_runs(self):
        self.assertIn("bulk-runs", self.src)

    def test_shows_step_progress(self):
        self.assertIn("current_step", self.src)

    def test_shows_preview_summary(self):
        self.assertIn("previewSummary", self.src)

    def test_no_hardcoded_service_names(self):
        self.assertNotIn("AC Repair", self.src)
        self.assertNotIn("Geyser Repair", self.src)


class TestBulkWizardDetailPage(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/super-admin/app/admin/service-setup/bulk-wizard/[draftId]/page.tsx")

    def test_use_client(self):
        self.assertIn('"use client"', self.src)

    def test_imports_bulk_setup_api(self):
        self.assertIn("bulkSetupApi", self.src)

    def test_uses_params(self):
        self.assertIn("useParams", self.src)

    def test_has_10_steps(self):
        self.assertIn("STEPS", self.src)
        self.assertIn("Choose Category", self.src)

    def test_step1_category(self):
        self.assertIn("setCategory", self.src)

    def test_step2_services_bulk_input(self):
        self.assertIn("bulkServiceText", self.src)

    def test_step2_existing_service_select(self):
        self.assertIn("selectedServiceIds", self.src)

    def test_step3_template_selection(self):
        self.assertIn("selectedTemplateIds", self.src)

    def test_step9_preview(self):
        self.assertIn("previewDraft", self.src) or self.assertIn("runPreview", self.src)

    def test_step10_apply(self):
        self.assertIn("applyDraft", self.src) or self.assertIn("runApply", self.src)

    def test_preview_blockers_shown(self):
        self.assertIn("blockers", self.src)

    def test_preview_summary_cards(self):
        self.assertIn("previewResult.summary", self.src)

    def test_apply_disabled_with_blockers(self):
        self.assertIn("can_apply", self.src)

    def test_apply_result_shown(self):
        self.assertIn("applyResult", self.src)


class TestBulkRunsListPage(unittest.TestCase):
    """NOTE: rewritten to bulkWizardApi (migration 098) — see
    TestBulkWizardListPage docstring above for why."""
    def setUp(self):
        self.src = _read("frontend/super-admin/app/admin/service-setup/bulk-runs/page.tsx")

    def test_use_client(self):
        self.assertIn('"use client"', self.src)

    def test_imports_bulk_wizard_api(self):
        self.assertIn("bulkWizardApi", self.src)

    def test_calls_list_runs(self):
        self.assertIn("bulkWizardApi.listRuns(", self.src)

    def test_shows_status(self):
        self.assertIn("status", self.src)

    def test_shows_summary(self):
        self.assertIn("StatusBadge", self.src)

    def test_links_to_run_detail(self):
        self.assertIn("bulk-runs/", self.src)

    def test_back_link(self):
        self.assertIn("bulk-wizard", self.src)


class TestBulkRunDetailPage(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/super-admin/app/admin/service-setup/bulk-runs/[runId]/page.tsx")

    def test_use_client(self):
        self.assertIn('"use client"', self.src)

    def test_imports_bulk_setup_api(self):
        self.assertIn("bulkSetupApi", self.src)

    def test_calls_get_run(self):
        self.assertIn("getRun", self.src)

    def test_shows_summary_cards(self):
        self.assertIn("summary_json", self.src)

    def test_shows_items_by_action(self):
        self.assertIn("byAction", self.src)

    def test_shows_entity_type(self):
        self.assertIn("entity_type", self.src)

    def test_shows_action(self):
        self.assertIn("action", self.src)

    def test_back_link(self):
        self.assertIn("bulk-runs", self.src)


if __name__ == "__main__":
    unittest.main()
