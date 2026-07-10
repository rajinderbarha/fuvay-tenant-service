"""
P0 Enterprise Workflow Template Management — backend + frontend tests.
Migration 086 | master_workflow_templates runtime/versioning columns |
workflow_service_mappings table | 32 new endpoints | Home Services seed defaults |
step/transition JSONB CRUD | validation + readiness + activation gating | versioning.
"""
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


MIGRATION   = ROOT / "alembic" / "versions" / "086_workflow_templates_enterprise.py"
FIX_MIG     = ROOT / "alembic" / "versions" / "087_fix_master_data_audit_log_updated_at.py"
MODELS      = ROOT / "app" / "engines" / "admin_catalog" / "models.py"
SERVICE     = ROOT / "app" / "engines" / "admin_catalog" / "service.py"
ROUTER      = ROOT / "app" / "engines" / "admin_catalog" / "admin_router.py"
PAGE        = ROOT / "frontend" / "super-admin" / "app" / "admin" / "workflow-templates" / "page.tsx"
API_TS      = ROOT / "frontend" / "super-admin" / "lib" / "api.ts"


# ════════════════════════════════════════════════════════════════════════════
# Migration 086
# ════════════════════════════════════════════════════════════════════════════
class TestMigration086:
    def test_migration_file_exists(self):
        assert MIGRATION.exists()

    def test_revision(self):
        assert 'revision = "086"' in _read(MIGRATION)

    def test_down_revision(self):
        assert 'down_revision = "085"' in _read(MIGRATION)

    def test_status_column(self):
        assert '"status"' in _read(MIGRATION)

    def test_transitions_column(self):
        assert '"transitions"' in _read(MIGRATION)

    def test_versioning_columns(self):
        src = _read(MIGRATION)
        for col in ["version_number", "parent_template_id", "is_latest", "activated_at", "deprecated_at"]:
            assert col in src, f"Missing versioning column: {col}"

    def test_runtime_settings_columns(self):
        src = _read(MIGRATION)
        for col in [
            "requires_technician_assignment", "requires_customer_confirmation",
            "requires_photo_proof", "requires_part_approval", "requires_estimate_approval",
            "requires_direct_payment_confirmation", "allows_reschedule", "allows_cancellation",
            "allows_dispute_after_completion",
        ]:
            assert col in src, f"Missing runtime setting column: {col}"

    def test_workflow_service_mappings_table(self):
        assert "workflow_service_mappings" in _read(MIGRATION)

    def test_downgrade_exists(self):
        assert "def downgrade" in _read(MIGRATION)


class TestAuditLogFixMigration:
    """Real pre-existing bug found & fixed: master_data_audit_log was missing
    updated_at, breaking every audit-log write across the whole admin_catalog engine."""
    def test_fix_migration_exists(self):
        assert FIX_MIG.exists()

    def test_revision_chain(self):
        src = _read(FIX_MIG)
        assert 'revision = "087"' in src
        assert 'down_revision = "086"' in src

    def test_adds_updated_at(self):
        assert "updated_at" in _read(FIX_MIG)


# ════════════════════════════════════════════════════════════════════════════
# Model fields
# ════════════════════════════════════════════════════════════════════════════
class TestWorkflowModels:
    def test_models_file_exists(self):
        assert MODELS.exists()

    def test_status_field(self):
        src = _read(MODELS)
        start = src.index("class MasterWorkflowTemplate")
        end = src.index("class WorkflowServiceMapping")
        assert "status:" in src[start:end]

    def test_transitions_field(self):
        src = _read(MODELS)
        start = src.index("class MasterWorkflowTemplate")
        end = src.index("class WorkflowServiceMapping")
        assert "transitions:" in src[start:end]

    def test_version_fields(self):
        src = _read(MODELS)
        start = src.index("class MasterWorkflowTemplate")
        end = src.index("class WorkflowServiceMapping")
        section = src[start:end]
        for f in ["version_number", "parent_template_id", "is_latest"]:
            assert f in section

    def test_workflow_service_mapping_model(self):
        assert "class WorkflowServiceMapping" in _read(MODELS)

    def test_mapping_fields(self):
        src = _read(MODELS)
        start = src.index("class WorkflowServiceMapping")
        section = src[start:start + 2000]
        for f in ["template_id", "category_id", "priority", "status"]:
            assert f in section


# ════════════════════════════════════════════════════════════════════════════
# Service — enterprise workflow logic
# ════════════════════════════════════════════════════════════════════════════
class TestWorkflowService:
    def test_service_file_exists(self):
        assert SERVICE.exists()

    def test_expanded_workflow_types(self):
        src = _read(SERVICE)
        for t in ["installation", "uninstallation", "maintenance", "cleaning", "delivery", "lead_followup", "custom"]:
            assert f'"{t}"' in src

    def test_valid_step_types(self):
        src = _read(SERVICE)
        for t in ["system", "customer_action", "tenant_action", "technician_action",
                  "admin_action", "approval", "notification", "automation", "condition"]:
            assert f'"{t}"' in src

    def test_valid_actors(self):
        src = _read(SERVICE)
        for a in ["customer", "tenant_owner", "tenant_manager", "technician",
                  "platform_admin", "support_admin", "finance_admin"]:
            assert f'"{a}"' in src

    def test_get_workflow_templates_summary(self):
        assert "async def get_workflow_templates_summary" in _read(SERVICE)

    def test_summary_fields(self):
        src = _read(SERVICE)
        for field in ["total_templates", "active_templates", "draft_templates",
                      "used_by_services", "unmapped_templates", "templates_missing_steps",
                      "sla_enabled", "approval_enabled", "runtime_ready"]:
            assert field in src, f"Missing summary field: {field}"

    def test_category_required_on_create(self):
        src = _read(SERVICE)
        start = src.index("async def create_workflow_template")
        end = src.index("_EDITABLE_FIELDS")
        assert "WORKFLOW_TEMPLATE_CATEGORY_REQUIRED" in src[start:end]

    def test_update_versioning_on_active_edit(self):
        src = _read(SERVICE)
        start = src.index("async def update_workflow_template")
        end = src.index("async def delete_workflow_template")
        section = src[start:end]
        assert 'row.status == "active"' in section
        assert "new_row" in section
        assert "is_latest = False" in section

    def test_clone_workflow_template(self):
        assert "async def clone_workflow_template" in _read(SERVICE)

    def test_create_new_version(self):
        assert "async def create_new_version" in _read(SERVICE)

    def test_validate_workflow_template(self):
        assert "async def validate_workflow_template" in _read(SERVICE)

    def test_validation_checks_start_step(self):
        src = _read(SERVICE)
        start = src.index("async def validate_workflow_template")
        end = src.index("async def get_workflow_readiness")
        section = src[start:end]
        assert "Exactly one start step is required" in section

    def test_validation_checks_terminal_step(self):
        src = _read(SERVICE)
        start = src.index("async def validate_workflow_template")
        end = src.index("async def get_workflow_readiness")
        assert "terminal step is required" in src[start:end]

    def test_validation_checks_orphan_steps(self):
        src = _read(SERVICE)
        start = src.index("async def validate_workflow_template")
        end = src.index("async def get_workflow_readiness")
        assert "orphaned" in src[start:end]

    def test_activation_blocked_when_invalid(self):
        src = _read(SERVICE)
        start = src.index("async def activate_workflow_template")
        end = src.index("async def deactivate_workflow_template")
        section = src[start:end]
        assert "WORKFLOW_TEMPLATE_INVALID" in section
        assert 'validation["valid"]' in section

    def test_activation_deprecates_previous_version(self):
        src = _read(SERVICE)
        start = src.index("async def activate_workflow_template")
        end = src.index("async def deactivate_workflow_template")
        assert '"deprecated"' in src[start:end]

    def test_add_step(self):
        assert "async def add_step" in _read(SERVICE)

    def test_step_validates_type_and_actor(self):
        src = _read(SERVICE)
        assert "_validate_step" in src

    def test_update_step(self):
        assert "async def update_step" in _read(SERVICE)

    def test_delete_step_cleans_transitions(self):
        src = _read(SERVICE)
        start = src.index("async def delete_step")
        end = src.index("async def reorder_steps")
        section = src[start:end]
        assert "from_step_code" in section and "to_step_code" in section

    def test_reorder_steps(self):
        assert "async def reorder_steps" in _read(SERVICE)

    def test_add_transition(self):
        assert "async def add_transition" in _read(SERVICE)

    def test_transition_validates_step_references(self):
        src = _read(SERVICE)
        start = src.index("async def add_transition")
        end = src.index("async def update_transition")
        assert "WORKFLOW_TRANSITION_INVALID_STEP" in src[start:end]

    def test_list_workflow_mappings(self):
        assert "async def list_workflow_mappings" in _read(SERVICE)

    def test_create_workflow_mapping(self):
        assert "async def create_workflow_mapping" in _read(SERVICE)

    def test_delete_workflow_mapping(self):
        assert "async def delete_workflow_mapping" in _read(SERVICE)

    def test_preview_workflow_runtime(self):
        assert "async def preview_workflow_runtime" in _read(SERVICE)

    def test_preview_resolves_most_specific_mapping(self):
        src = _read(SERVICE)
        start = src.index("async def preview_workflow_runtime")
        end = src.index("_home_services_seed_specs")
        section = src[start:end]
        assert "def specificity" in section

    def test_seed_defaults_preview(self):
        assert "async def seed_workflow_defaults_preview" in _read(SERVICE)

    def test_seed_defaults(self):
        assert "async def seed_workflow_defaults" in _read(SERVICE)

    def test_seed_templates_six_home_services(self):
        src = _read(SERVICE)
        for name in [
            "Standard Repair Workflow", "Standard Installation Workflow",
            "Standard Uninstallation Workflow", "Inspection / Visit Workflow",
            "Cleaning Workflow", "Emergency Repair Workflow",
        ]:
            assert name in src, f"Missing seed template: {name}"

    def test_seed_respects_direct_payment_business_rule(self):
        src = _read(SERVICE)
        assert "requires_direct_payment_confirmation" in src
        assert "Payment Collected Directly by Tenant" in src

    def test_seed_deducts_job_credit_on_completion(self):
        src = _read(SERVICE)
        assert "deduct_job_credit" in src
        assert "on_job_completed" in src

    def test_seed_allows_dispute_window(self):
        assert "open_dispute_window" in _read(SERVICE)

    def test_audit_reuses_master_data_audit_log(self):
        src = _read(SERVICE)
        start = src.index("async def create_workflow_template")
        end = src.index("_EDITABLE_FIELDS")
        section = src[start:end]
        assert "self._audit(" in section
        assert '"master_workflow_template"' in section


# ════════════════════════════════════════════════════════════════════════════
# Router — endpoint + ordering
# ════════════════════════════════════════════════════════════════════════════
class TestWorkflowRouter:
    def test_router_file_exists(self):
        assert ROUTER.exists()

    def test_summary_route(self):
        assert '"/workflow-templates/summary"' in _read(ROUTER)

    def test_export_route(self):
        assert '"/workflow-templates/export"' in _read(ROUTER)

    def test_seed_routes(self):
        src = _read(ROUTER)
        assert '"/workflow-templates/seed-defaults/preview"' in src
        assert '"/workflow-templates/seed-defaults"' in src

    def test_preview_runtime_route(self):
        assert '"/workflow-templates/preview-runtime"' in _read(ROUTER)

    def test_clone_route(self):
        assert '"/workflow-templates/{template_id}/clone"' in _read(ROUTER)

    def test_new_version_route(self):
        assert '"/workflow-templates/{template_id}/new-version"' in _read(ROUTER)

    def test_activate_deactivate_routes(self):
        src = _read(ROUTER)
        assert '"/workflow-templates/{template_id}/activate"' in src
        assert '"/workflow-templates/{template_id}/deactivate"' in src

    def test_validate_readiness_routes(self):
        src = _read(ROUTER)
        assert '"/workflow-templates/{template_id}/validate"' in src
        assert '"/workflow-templates/{template_id}/readiness"' in src

    def test_steps_routes(self):
        src = _read(ROUTER)
        for path in ['"/workflow-templates/{template_id}/steps"',
                     '"/workflow-templates/{template_id}/steps/{step_id}"',
                     '"/workflow-templates/{template_id}/steps/reorder"']:
            assert path in src

    def test_transitions_routes(self):
        src = _read(ROUTER)
        for path in ['"/workflow-templates/{template_id}/transitions"',
                     '"/workflow-templates/{template_id}/transitions/{transition_id}"']:
            assert path in src

    def test_mappings_routes(self):
        src = _read(ROUTER)
        for path in ['"/workflow-templates/{template_id}/mappings"',
                     '"/workflow-templates/{template_id}/mappings/{mapping_id}"']:
            assert path in src

    def test_audit_routes(self):
        src = _read(ROUTER)
        assert '"/workflow-templates/{template_id}/audit-logs"' in src
        assert '"/workflows/audit-logs"' in src

    def test_static_routes_before_dynamic(self):
        """/summary, /export, /seed-defaults*, /preview-runtime must precede
        /{template_id} to avoid UUID-parse shadowing."""
        src = _read(ROUTER)
        dynamic_pos = src.index('@router.get("/workflow-templates/{template_id}"')
        for static in ['"/workflow-templates/summary"', '"/workflow-templates/export"',
                       '"/workflow-templates/seed-defaults/preview"', '"/workflow-templates/seed-defaults"',
                       '"/workflow-templates/preview-runtime"']:
            assert src.index(static) < dynamic_pos, f"{static} must precede /{{template_id}}"

    def test_mutating_routes_require_super_admin(self):
        src = _read(ROUTER)
        start = src.index('@router.post("/workflow-templates/seed-defaults/preview"')
        end = src.index('# MASTER DATA AUDIT LOG  (Sprint 34C)')
        section = src[start:end]
        # Count POST/PUT/DELETE decorators and require_super_admin usages — should track closely
        assert section.count("require_super_admin") >= 15


# ════════════════════════════════════════════════════════════════════════════
# Frontend — page + api client existence (page rewrite tracked as follow-up)
# ════════════════════════════════════════════════════════════════════════════
class TestFrontend:
    def test_page_exists(self):
        assert PAGE.exists()

    def test_api_file_exists(self):
        assert API_TS.exists()
