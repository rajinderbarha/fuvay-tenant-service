"""P0 workflow control-plane retirement/canonicalization tests.

The retired `/admin/workflow-templates` page used `master_workflow_templates`,
which is not read by booking/job execution. The production workflow surface is
the Home Services Catalog Workspace's Job-Type Blueprint tab, backed by
`service_job_workflow`.
"""
from pathlib import Path


ROOT = Path(__file__).parent.parent
ADMIN_ROUTER = ROOT / "app" / "engines" / "admin_catalog" / "admin_router.py"
BLUEPRINT_ROUTER = ROOT / "app" / "engines" / "admin_catalog" / "job_type_blueprint_router.py"
BLUEPRINT_SERVICE = ROOT / "app" / "engines" / "admin_catalog" / "job_type_blueprint_service.py"
WORKFLOW_STEPS = ROOT / "app" / "engines" / "admin_catalog" / "workflow_steps.py"
CATALOG_WORKSPACE = ROOT / "frontend" / "super-admin" / "app" / "admin" / "catalog-workspace" / "page.tsx"
WORKFLOW_BUILDER = ROOT / "frontend" / "super-admin" / "app" / "admin" / "catalog-workspace" / "WorkflowStepBuilder.tsx"
RETIRED_PAGE = ROOT / "frontend" / "super-admin" / "app" / "admin" / "workflow-templates" / "page.tsx"
ADMIN_LAYOUT = ROOT / "frontend" / "super-admin" / "components" / "layout" / "AdminLayout.tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_retired_workflow_templates_page_redirects_to_canonical_workspace():
    src = _read(RETIRED_PAGE)
    assert "redirect" in src
    assert "/admin/catalog-workspace?tab=workflow" in src
    assert "masterDataApi" not in src


def test_retired_workflow_template_api_fails_closed():
    src = _read(ADMIN_ROUTER)
    assert "WORKFLOW_TEMPLATES_RETIRED" in src
    assert '@router.api_route("/workflow-templates"' in src
    assert '@router.api_route("/workflow-templates/{retired_path:path}"' in src
    assert "status_code=410" in src


def test_admin_nav_does_not_list_duplicate_workflow_template_surface():
    src = _read(ADMIN_LAYOUT)
    assert 'href: "/admin/workflow-templates"' not in src
    assert 'label: "Workflows"' not in src
    assert '"/admin/catalog-workspace"' in src


def test_canonical_job_type_workflow_api_is_present():
    router = _read(BLUEPRINT_ROUTER)
    assert '"/{service_id}/job-types/{job_type_id}/workflow"' in router
    assert '"/{service_id}/job-types/{job_type_id}/workflow/step-options"' in router
    assert '"/{service_id}/job-types/{job_type_id}/workflow/step-review"' in router


def test_canonical_workflow_service_is_append_only_and_no_amounts():
    src = _read(BLUEPRINT_SERVICE)
    assert "WORKFLOW_EDITABLE_FIELDS" in src
    assert '"steps", "transitions"' in src
    assert "current.is_current = False" in src
    assert "version_number=current.version_number + 1" in src
    for forbidden in ("price", "amount", "commission", "credit"):
        assert forbidden not in src[src.index("WORKFLOW_EDITABLE_FIELDS"):src.index("class JobTypeBlueprintService")]


def test_catalog_workspace_hosts_the_live_workflow_builder():
    workspace = _read(CATALOG_WORKSPACE)
    builder = _read(WORKFLOW_BUILDER)
    assert '"workflow"' in workspace
    assert "WorkflowStepBuilder" in workspace
    assert "catalogWorkspaceApi.getJobTypeWorkflow" in workspace
    assert "catalogWorkspaceApi.setJobTypeWorkflow" in builder
    assert "getWorkflowStepOptions" in builder
    assert "reviewWorkflowSteps" in builder


def test_workflow_step_engine_uses_execution_status_vocabulary():
    src = _read(WORKFLOW_STEPS)
    assert "JOB_TRANSITIONS" in src
    assert "CANONICAL_JOB_STATUSES" in src
    assert "service_job_workflow_id" in src
