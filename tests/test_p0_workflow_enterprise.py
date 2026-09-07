"""P0 workflow engine enterprise checks after workflow canonicalization.

Migration 106 remains historical schema, but the production admin/runtime
workflow engine is the service_job_workflow-backed Job-Type Blueprint.
"""
from pathlib import Path


ROOT = Path(__file__).parent.parent
MIGRATION_106 = ROOT / "alembic" / "versions" / "106_workflow_templates_enterprise.py"
MIGRATION_186 = ROOT / "alembic" / "versions" / "186_workflow_lifecycle_and_dead_system_removal.py"
MIGRATION_274 = ROOT / "alembic" / "versions" / "274_service_job_workflow_step_choreography.py"
MAIN_PY = ROOT / "app" / "main.py"
BLUEPRINT_ROUTER = ROOT / "app" / "engines" / "admin_catalog" / "job_type_blueprint_router.py"
WORKFLOW_BUILDER = ROOT / "frontend" / "super-admin" / "app" / "admin" / "catalog-workspace" / "WorkflowStepBuilder.tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_historical_migration_106_is_kept_for_chain_integrity():
    src = _read(MIGRATION_106)
    assert 'revision = "106"' in src
    assert "workflow_templates" in src
    assert "workflow_template_versions" in src


def test_migration_186_documents_old_workflows_engine_removal():
    src = _read(MIGRATION_186)
    assert "service_job_workflow" in src
    assert "DROP TABLE IF EXISTS workflow_template_versions" in src
    assert "DROP TABLE IF EXISTS workflow_templates" in src


def test_migration_274_puts_step_choreography_on_service_job_workflow():
    src = _read(MIGRATION_274)
    assert "service_job_workflow" in src
    assert "steps_json" in src
    assert "transitions_json" in src


def test_dead_workflows_router_is_not_mounted():
    src = _read(MAIN_PY)
    assert "workflow_enterprise_router" not in src
    assert "app.include_router(workflow_enterprise_router)" not in src


def test_live_workflow_router_and_frontend_builder_exist():
    router = _read(BLUEPRINT_ROUTER)
    builder = _read(WORKFLOW_BUILDER)
    assert '"/{service_id}/job-types/{job_type_id}/workflow"' in router
    assert "getWorkflowStepOptions" in builder
    assert "Publish journey version" in builder
