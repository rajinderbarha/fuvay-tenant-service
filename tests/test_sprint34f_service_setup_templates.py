"""Sprint 34F — Service Setup Templates test suite.

Tests: migration 058, models, service layer, routers, main.py,
       frontend api.ts, frontend pages, seed script.
"""
import os
import ast
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


# ── Migration 058 ─────────────────────────────────────────────────────────────

class TestMigration058(unittest.TestCase):
    def setUp(self):
        self.src = _read("alembic/versions/058_sprint34f_service_setup_templates.py")

    def test_revision_is_058(self):
        self.assertIn('revision = "058"', self.src)

    def test_down_revision_is_057(self):
        self.assertIn('down_revision = "057"', self.src)

    def test_creates_service_setup_templates(self):
        self.assertIn('"service_setup_templates"', self.src)

    def test_creates_service_setup_template_items(self):
        self.assertIn('"service_setup_template_items"', self.src)

    def test_creates_service_setup_template_relationships(self):
        self.assertIn('"service_setup_template_relationships"', self.src)

    def test_creates_service_setup_template_runs(self):
        self.assertIn('"service_setup_template_runs"', self.src)

    def test_creates_service_setup_template_run_items(self):
        self.assertIn('"service_setup_template_run_items"', self.src)

    def test_sst_code_column(self):
        self.assertIn('"code"', self.src)

    def test_sst_slug_column(self):
        self.assertIn('"slug"', self.src)

    def test_sst_template_type_column(self):
        self.assertIn('"template_type"', self.src)

    def test_sst_status_default_draft(self):
        self.assertIn('"draft"', self.src)

    def test_sst_is_system_template(self):
        self.assertIn('"is_system_template"', self.src)

    def test_sst_unique_code(self):
        self.assertIn('"uq_sst_code"', self.src)

    def test_sst_unique_slug(self):
        self.assertIn('"uq_sst_slug"', self.src)

    def test_ssti_item_type(self):
        self.assertIn('"item_type"', self.src)

    def test_ssti_apply_mode_default(self):
        self.assertIn('"create_if_missing"', self.src)

    def test_ssti_payload_json(self):
        self.assertIn('"payload_json"', self.src)

    def test_sstr_relationship_type(self):
        self.assertIn('"relationship_type"', self.src)

    def test_sstr_source_item_id(self):
        self.assertIn('"source_item_id"', self.src)

    def test_sstr_target_item_id(self):
        self.assertIn('"target_item_id"', self.src)

    def test_run_target_scope(self):
        self.assertIn('"target_scope"', self.src)

    def test_run_status_default_running(self):
        self.assertIn('"running"', self.src)

    def test_run_summary_json(self):
        self.assertIn('"summary_json"', self.src)

    def test_run_item_action(self):
        self.assertIn('"action"', self.src)

    def test_downgrade_drops_tables(self):
        self.assertIn("downgrade", self.src)
        self.assertIn("drop_table", self.src)

    def test_index_sst_status(self):
        self.assertIn('"ix_sst_status"', self.src)

    def test_index_ssti_template(self):
        self.assertIn('"ix_ssti_template"', self.src)

    def test_index_sst_run_template(self):
        self.assertIn('"ix_sst_run_template"', self.src)


# ── Models ────────────────────────────────────────────────────────────────────

class TestModels34F(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/engines/admin_catalog/models.py")

    def _window(self, cls_name: str, size: int = 2500) -> str:
        idx = self.src.find(f"class {cls_name}")
        self.assertGreater(idx, -1, f"{cls_name} not found in models.py")
        return self.src[idx: idx + size]

    def test_service_setup_template_class_exists(self):
        self.assertIn("class ServiceSetupTemplate(", self.src)

    def test_service_setup_template_item_class_exists(self):
        self.assertIn("class ServiceSetupTemplateItem(", self.src)

    def test_service_setup_template_relationship_class_exists(self):
        self.assertIn("class ServiceSetupTemplateRelationship(", self.src)

    def test_service_setup_template_run_class_exists(self):
        self.assertIn("class ServiceSetupTemplateRun(", self.src)

    def test_service_setup_template_run_item_class_exists(self):
        self.assertIn("class ServiceSetupTemplateRunItem(", self.src)

    def test_sst_tablename(self):
        w = self._window("ServiceSetupTemplate")
        self.assertIn("service_setup_templates", w)

    def test_sst_has_code(self):
        w = self._window("ServiceSetupTemplate")
        self.assertIn("code", w)

    def test_sst_has_slug(self):
        w = self._window("ServiceSetupTemplate")
        self.assertIn("slug", w)

    def test_sst_has_template_type(self):
        w = self._window("ServiceSetupTemplate")
        self.assertIn("template_type", w)

    def test_sst_has_status(self):
        w = self._window("ServiceSetupTemplate")
        self.assertIn("status", w)

    def test_sst_has_is_system_template(self):
        w = self._window("ServiceSetupTemplate")
        self.assertIn("is_system_template", w)

    def test_sst_has_to_dict(self):
        w = self._window("ServiceSetupTemplate")
        self.assertIn("to_dict", w)

    def test_ssti_has_item_type(self):
        w = self._window("ServiceSetupTemplateItem")
        self.assertIn("item_type", w)

    def test_ssti_has_apply_mode(self):
        w = self._window("ServiceSetupTemplateItem")
        self.assertIn("apply_mode", w)

    def test_ssti_has_payload_json(self):
        w = self._window("ServiceSetupTemplateItem")
        self.assertIn("payload_json", w)

    def test_ssti_has_is_required(self):
        w = self._window("ServiceSetupTemplateItem")
        self.assertIn("is_required", w)

    def test_sstr_has_relationship_type(self):
        w = self._window("ServiceSetupTemplateRelationship")
        self.assertIn("relationship_type", w)

    def test_sstr_has_source_item_id(self):
        w = self._window("ServiceSetupTemplateRelationship")
        self.assertIn("source_item_id", w)

    def test_run_has_target_scope(self):
        w = self._window("ServiceSetupTemplateRun")
        self.assertIn("target_scope", w)

    def test_run_has_summary_json(self):
        w = self._window("ServiceSetupTemplateRun")
        self.assertIn("summary_json", w)

    def test_run_has_completed_at(self):
        w = self._window("ServiceSetupTemplateRun")
        self.assertIn("completed_at", w)

    def test_run_item_has_action(self):
        w = self._window("ServiceSetupTemplateRunItem")
        self.assertIn("action", w)

    def test_run_item_has_target_record_type(self):
        w = self._window("ServiceSetupTemplateRunItem")
        self.assertIn("target_record_type", w)

    def test_sst_before_customer_flow_config(self):
        idx_sst = self.src.find("class ServiceSetupTemplate(")
        idx_cfc = self.src.find("class CustomerFlowConfig(")
        self.assertGreater(idx_cfc, idx_sst)


# ── Service ───────────────────────────────────────────────────────────────────

class TestServiceSetupTemplateService(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/engines/admin_catalog/service_setup_template_service.py")

    def test_file_exists(self):
        self.assertIn("ServiceSetupTemplateService", self.src)

    def test_has_list_templates(self):
        self.assertIn("async def list_templates", self.src)

    def test_has_get_template(self):
        self.assertIn("async def get_template", self.src)

    def test_has_create_template(self):
        self.assertIn("async def create_template", self.src)

    def test_has_update_template(self):
        self.assertIn("async def update_template", self.src)

    def test_has_publish_template(self):
        self.assertIn("async def publish_template", self.src)

    def test_has_archive_template(self):
        self.assertIn("async def archive_template", self.src)

    def test_has_delete_template(self):
        self.assertIn("async def delete_template", self.src)

    def test_has_list_items(self):
        self.assertIn("async def list_items", self.src)

    def test_has_add_item(self):
        self.assertIn("async def add_item", self.src)

    def test_has_update_item(self):
        self.assertIn("async def update_item", self.src)

    def test_has_remove_item(self):
        self.assertIn("async def remove_item", self.src)

    def test_has_list_relationships(self):
        self.assertIn("async def list_relationships", self.src)

    def test_has_add_relationship(self):
        self.assertIn("async def add_relationship", self.src)

    def test_has_remove_relationship(self):
        self.assertIn("async def remove_relationship", self.src)

    def test_has_preview_template(self):
        self.assertIn("async def preview_template", self.src)

    def test_preview_no_mutation_note(self):
        self.assertIn("Preview only", self.src)

    def test_has_apply_template(self):
        self.assertIn("async def apply_template", self.src)

    def test_apply_creates_run_record(self):
        self.assertIn("ServiceSetupTemplateRun(", self.src)

    def test_apply_creates_run_items(self):
        self.assertIn("ServiceSetupTemplateRunItem(", self.src)

    def test_apply_tracks_summary(self):
        self.assertIn("summary_json", self.src)

    def test_has_list_runs(self):
        self.assertIn("async def list_runs", self.src)

    def test_has_get_run_detail(self):
        self.assertIn("async def get_run_detail", self.src)

    def test_has_get_recommended_templates(self):
        self.assertIn("async def get_recommended_templates", self.src)

    def test_audit_logged(self):
        self.assertIn("_audit", self.src)
        self.assertIn("template.created", self.src)
        self.assertIn("template.applied", self.src)

    def test_apply_mode_action_resolve(self):
        self.assertIn("create_if_missing", self.src)
        self.assertIn("skip_if_exists", self.src)
        self.assertIn("map_existing", self.src)
        self.assertIn("update_existing", self.src)

    def test_apply_idempotent_status(self):
        self.assertIn("completed", self.src)
        self.assertIn("completed_with_errors", self.src)

    def test_get_template_raises_on_missing(self):
        self.assertIn("not found", self.src)


# ── Router ────────────────────────────────────────────────────────────────────

class TestServiceSetupTemplateRouter(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/engines/admin_catalog/service_setup_template_router.py")

    def test_admin_router_exists(self):
        self.assertIn("admin_router", self.src)

    def test_provider_router_exists(self):
        self.assertIn("provider_router", self.src)

    def test_admin_prefix(self):
        self.assertIn("/v1/admin/service-setup-templates", self.src)

    def test_provider_prefix(self):
        self.assertIn("/v1/provider/setup/templates", self.src)

    def test_list_endpoint(self):
        self.assertIn('"""\n', self.src) or self.assertIn('"")', self.src)
        self.assertIn("list_templates", self.src)

    def test_create_endpoint(self):
        self.assertIn("create_template", self.src)

    def test_get_endpoint(self):
        self.assertIn("get_template", self.src)

    def test_update_endpoint(self):
        self.assertIn("update_template", self.src)

    def test_publish_endpoint(self):
        self.assertIn("publish_template", self.src)
        self.assertIn("/publish", self.src)

    def test_archive_endpoint(self):
        self.assertIn("archive_template", self.src)
        self.assertIn("/archive", self.src)

    def test_delete_endpoint(self):
        self.assertIn("delete_template", self.src)

    def test_items_list_endpoint(self):
        self.assertIn("list_items", self.src)

    def test_items_add_endpoint(self):
        self.assertIn("add_item", self.src)

    def test_items_update_endpoint(self):
        self.assertIn("update_item", self.src)

    def test_items_remove_endpoint(self):
        self.assertIn("remove_item", self.src)

    def test_relationships_list(self):
        self.assertIn("list_relationships", self.src)

    def test_relationships_add(self):
        self.assertIn("add_relationship", self.src)

    def test_relationships_remove(self):
        self.assertIn("remove_relationship", self.src)

    def test_preview_endpoint(self):
        self.assertIn("preview_template", self.src)
        self.assertIn("/preview", self.src)

    def test_apply_endpoint(self):
        self.assertIn("apply_template", self.src)
        self.assertIn("/apply", self.src)

    def test_runs_list_endpoint(self):
        self.assertIn("list_runs", self.src)

    def test_run_detail_endpoint(self):
        self.assertIn("get_run_detail", self.src)

    def test_provider_recommendations_endpoint(self):
        self.assertIn("get_recommended_templates", self.src)
        self.assertIn("/recommended", self.src)

    def test_admin_requires_super_admin(self):
        self.assertIn("require_super_admin", self.src)

    def test_provider_requires_technician(self):
        self.assertIn("require_technician", self.src)


# ── main.py ───────────────────────────────────────────────────────────────────

class TestMainPy34F(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/main.py")

    def test_imports_sst_admin_router(self):
        self.assertIn("sst_admin_router", self.src)

    def test_imports_sst_provider_router(self):
        self.assertIn("sst_provider_router", self.src)

    def test_imports_from_service_setup_template_router(self):
        self.assertIn("service_setup_template_router", self.src)

    def test_admin_router_registered(self):
        idx = self.src.find("sst_admin_router")
        self.assertGreater(idx, -1)
        self.assertIn("include_router", self.src[max(0, idx-200):idx+700])

    def test_provider_router_registered(self):
        idx = self.src.find("sst_provider_router")
        self.assertGreater(idx, -1)


# ── Frontend api.ts ───────────────────────────────────────────────────────────

class TestFrontendApiTs34F(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/super-admin/lib/api.ts")

    def test_service_setup_template34f_interface(self):
        self.assertIn("ServiceSetupTemplate34F", self.src)

    def test_service_setup_template_item34f_interface(self):
        self.assertIn("ServiceSetupTemplateItem34F", self.src)

    def test_service_setup_template_relationship34f_interface(self):
        self.assertIn("ServiceSetupTemplateRelationship34F", self.src)

    def test_service_setup_template_run34f_interface(self):
        self.assertIn("ServiceSetupTemplateRun34F", self.src)

    def test_service_setup_template_run_item34f_interface(self):
        self.assertIn("ServiceSetupTemplateRunItem34F", self.src)

    def test_setup_template_api_object(self):
        self.assertIn("setupTemplateApi", self.src)

    def test_list_templates_method(self):
        self.assertIn("listTemplates", self.src)

    def test_get_template_method(self):
        self.assertIn("getTemplate", self.src)

    def test_create_template_method(self):
        self.assertIn("createTemplate", self.src)

    def test_update_template_method(self):
        self.assertIn("updateTemplate", self.src)

    def test_publish_template_method(self):
        self.assertIn("publishTemplate", self.src)

    def test_archive_template_method(self):
        self.assertIn("archiveTemplate", self.src)

    def test_delete_template_method(self):
        self.assertIn("deleteTemplate", self.src)

    def test_list_items_method(self):
        self.assertIn("listItems", self.src)

    def test_add_item_method(self):
        self.assertIn("addItem", self.src)

    def test_update_item_method(self):
        self.assertIn("updateItem", self.src)

    def test_remove_item_method(self):
        self.assertIn("removeItem", self.src)

    def test_list_relationships_method(self):
        self.assertIn("listRelationships", self.src)

    def test_add_relationship_method(self):
        self.assertIn("addRelationship", self.src)

    def test_remove_relationship_method(self):
        self.assertIn("removeRelationship", self.src)

    def test_preview_template_method(self):
        self.assertIn("previewTemplate", self.src)

    def test_apply_template_method(self):
        self.assertIn("applyTemplate", self.src)

    def test_list_runs_method(self):
        self.assertIn("listRuns", self.src)

    def test_get_run_detail_method(self):
        self.assertIn("getRunDetail", self.src)

    def test_uses_correct_admin_prefix(self):
        self.assertIn("/v1/admin/service-setup-templates", self.src)

    def test_uses_apiFetch(self):
        idx = self.src.find("setupTemplateApi")
        self.assertIn("apiFetch", self.src[idx:idx + 2000])


# ── Frontend Pages ────────────────────────────────────────────────────────────

class TestTemplatesListPage(unittest.TestCase):
    """NOTE: this page was superseded by migration 097 / app/engines/service_setup
    (the enterprise multi-vertical rewrite) — the Sprint 34F setupTemplateApi /
    ServiceSetupTemplate34F backend it originally tested no longer matches the
    live DB schema (see ServiceSetupTemplate.__tablename__ in admin_catalog/models.py,
    renamed to service_setup_templates_legacy_34f to stop a table-name collision
    with the new engine). Assertions below were updated to match the current
    frontend/super-admin/app/admin/service-setup/templates/page.tsx rather than
    silently left failing against a page that no longer exists in this form.
    """
    def setUp(self):
        self.src = _read("frontend/super-admin/app/admin/service-setup/templates/page.tsx")

    def test_use_client(self):
        self.assertIn('"use client"', self.src)

    def test_imports_service_setup_templates_api(self):
        self.assertIn("serviceSetupTemplatesApi", self.src)

    def test_imports_interface(self):
        self.assertIn("SetupTemplateItem", self.src)

    def test_calls_list_templates(self):
        self.assertIn("serviceSetupTemplatesApi.list(", self.src)

    def test_has_search_input(self):
        self.assertIn("search", self.src.lower())

    def test_has_status_filter(self):
        self.assertIn("filterStatus", self.src)

    def test_has_create_button(self):
        self.assertIn("New Template", self.src)

    def test_has_create_modal(self):
        self.assertIn("showCreate", self.src)

    def test_calls_create_template(self):
        self.assertIn("serviceSetupTemplatesApi.create(", self.src)

    def test_calls_publish_template(self):
        self.assertIn("serviceSetupTemplatesApi.publish", self.src)

    def test_calls_archive_template(self):
        self.assertIn("serviceSetupTemplatesApi.archive", self.src)

    def test_links_to_detail_page(self):
        self.assertIn("templates/${t.id}", self.src)

    def test_has_pagination(self):
        self.assertIn("Page {page} of", self.src)

    def test_no_hardcoded_template_names(self):
        self.assertNotIn("AC Repair Starter", self.src)
        self.assertNotIn("Plumbing Starter", self.src)


class TestTemplateDetailPage(unittest.TestCase):
    """NOTE: rewritten to serviceSetupTemplatesApi (the OLD setupTemplateApi
    endpoint this page called 500'd — its table was renamed to
    service_setup_templates_legacy_34f after migration 097 replaced the live
    schema; see admin_catalog/models.py). Assertions updated to match the
    current frontend/super-admin/app/admin/service-setup/templates/[templateId]/page.tsx,
    which shows modules + items read-only and exposes publish/archive/clone/
    delete/validate actions instead of the old add-item/preview/apply flow
    (the new engine has no per-template apply-to-scope concept — templates
    are consumed by the Bulk Setup Wizard instead)."""
    def setUp(self):
        self.src = _read("frontend/super-admin/app/admin/service-setup/templates/[templateId]/page.tsx")

    def test_use_client(self):
        self.assertIn('"use client"', self.src)

    def test_imports_service_setup_templates_api(self):
        self.assertIn("serviceSetupTemplatesApi", self.src)

    def test_uses_params(self):
        self.assertIn("useParams", self.src)

    def test_loads_template(self):
        self.assertIn("serviceSetupTemplatesApi.get(", self.src)

    def test_shows_modules(self):
        self.assertIn("Modules (", self.src)

    def test_shows_items_grouped_by_module(self):
        self.assertIn("itemsByModule", self.src)

    def test_has_validate_action(self):
        self.assertIn("handleValidate", self.src)
        self.assertIn("serviceSetupTemplatesApi.validate", self.src)

    def test_has_publish_and_archive_actions(self):
        self.assertIn("handlePublish", self.src)
        self.assertIn("handleArchive", self.src)

    def test_has_clone_action(self):
        self.assertIn("handleClone", self.src)

    def test_has_delete_action(self):
        self.assertIn("handleDelete", self.src)

    def test_links_to_bulk_wizard_instead_of_apply(self):
        self.assertIn("/admin/service-setup/bulk-wizard", self.src)

    def test_back_link(self):
        self.assertIn("templates", self.src)


class TestTemplateRunsPage(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/super-admin/app/admin/service-setup/templates/[templateId]/runs/page.tsx")

    def test_use_client(self):
        self.assertIn('"use client"', self.src)

    def test_imports_setup_template_api(self):
        self.assertIn("setupTemplateApi", self.src)

    def test_imports_run_interface(self):
        self.assertIn("ServiceSetupTemplateRun34F", self.src)

    def test_calls_list_runs(self):
        self.assertIn("listRuns", self.src)

    def test_calls_get_run_detail(self):
        self.assertIn("getRunDetail", self.src)

    def test_shows_run_status(self):
        self.assertIn("status", self.src)

    def test_shows_summary(self):
        self.assertIn("summary_json", self.src)

    def test_back_link(self):
        self.assertIn("templateId", self.src)


# ── Seed Script ───────────────────────────────────────────────────────────────

class TestSeedServiceSetupTemplates(unittest.TestCase):
    def setUp(self):
        self.src = _read("scripts/seed_service_setup_templates.py")

    def test_imports_service_setup_template(self):
        self.assertIn("ServiceSetupTemplate", self.src)

    def test_imports_service_setup_template_item(self):
        self.assertIn("ServiceSetupTemplateItem", self.src)

    def test_has_6_templates(self):
        count = self.src.count('"code":')
        self.assertGreaterEqual(count, 6, "Expected at least 6 templates")

    def test_has_ac_repair_template(self):
        self.assertIn("home_ac_repair_starter", self.src)

    def test_has_plumbing_template(self):
        self.assertIn("home_plumbing_starter", self.src)

    def test_has_electrical_template(self):
        self.assertIn("home_electrical_starter", self.src)

    def test_has_cleaning_template(self):
        self.assertIn("home_cleaning_starter", self.src)

    def test_has_coaching_template(self):
        self.assertIn("coaching_ielts_starter", self.src)

    def test_has_real_estate_template(self):
        self.assertIn("real_estate_lead_starter", self.src)

    def test_idempotent_check(self):
        self.assertIn("existing", self.src)
        self.assertIn("skipped", self.src)

    def test_creates_template_items(self):
        self.assertIn("ServiceSetupTemplateItem(template_id=", self.src)

    def test_published_status(self):
        self.assertIn('"published"', self.src)

    def test_is_system_template_true(self):
        self.assertIn('"is_system_template": True', self.src)

    def test_covers_multiple_verticals(self):
        self.assertIn('"home_service"', self.src)
        self.assertIn('"coaching"', self.src)
        self.assertIn('"real_estate"', self.src)

    def test_multiple_apply_modes(self):
        self.assertIn('"create_if_missing"', self.src)
        self.assertIn('"map_existing"', self.src)

    def test_asyncio_run(self):
        self.assertIn("asyncio.run(seed())", self.src)


if __name__ == "__main__":
    unittest.main()
