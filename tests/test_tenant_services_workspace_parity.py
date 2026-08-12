"""Regression tests for setup/dashboard Services & Pricing parity."""
from types import SimpleNamespace

from app.engines.admin_catalog.tenant_service import project_tenant_blueprint


def test_workspace_projects_real_workflow_fields_without_hardcoded_requirements():
    master = SimpleNamespace(
        is_type_required=True,
        is_brand_required=False,
        requires_checklist=False,
        requires_schedule=True,
        pricing_model="range",
    )
    workflow = {
        "checklist_required": True,
        "quote_approval_required": True,
        "technician_required": False,
        "schedule_required": False,
        "version_number": 4,
    }

    master.requires_issue_type = True
    projected = project_tenant_blueprint(master, workflow)

    assert projected == {
        "type_mode": "required",
        "brand_mode": "optional",
        "requires_issue_type": True,
        "requires_checklist": True,
        "requires_estimate_approval": True,
        "requires_technician": False,
        "requires_schedule": False,
        "workflow_version": 4,
        "source": "service_job_workflow",
    }


def test_workspace_legacy_projection_matches_master_service_setup_fields():
    master = SimpleNamespace(
        is_type_required=False,
        is_brand_required=True,
        requires_checklist=True,
        requires_schedule=False,
        pricing_model="inspection_quote",
    )

    master.requires_issue_type = False
    projected = project_tenant_blueprint(master, None)

    assert projected["type_mode"] == "optional"
    assert projected["brand_mode"] == "required"
    assert projected["requires_checklist"] is True
    assert projected["requires_estimate_approval"] is True
    assert projected["requires_schedule"] is False
    assert projected["workflow_version"] is None
    assert projected["source"] == "master_service_legacy"
