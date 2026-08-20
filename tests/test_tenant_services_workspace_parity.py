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
        "service_area_required": False,
        "availability_required": False,
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
        "requires_service_area": False,
        "requires_availability": False,
        "pricing_behavior": "range",
        "workflow_version": 4,
        "source": "service_job_workflow",
    }


def test_workspace_legacy_projection_matches_master_service_setup_fields():
    master = SimpleNamespace(
        is_type_required=False,
        is_brand_required=True,
        requires_checklist=True,
        requires_schedule=False,
        requires_address=False,
        pricing_model="inspection_quote",
    )

    master.requires_issue_type = False
    projected = project_tenant_blueprint(master, None)

    assert projected["type_mode"] == "optional"
    assert projected["brand_mode"] == "required"
    assert projected["requires_checklist"] is True
    assert projected["requires_estimate_approval"] is True
    assert projected["requires_schedule"] is False
    assert projected["requires_service_area"] is False
    assert projected["requires_availability"] is False
    assert projected["workflow_version"] is None
    assert projected["source"] == "master_service_legacy"
    assert projected["pricing_behavior"] == "inspection_quote"


def test_normalized_dimension_rules_override_legacy_type_brand_flags():
    master = SimpleNamespace(
        is_type_required=False,
        is_brand_required=True,
        requires_checklist=False,
        requires_schedule=False,
        requires_address=False,
        pricing_model="range",
        requires_issue_type=False,
    )
    projected = project_tenant_blueprint(master, None, {
        "type": {"enabled": True, "required": True, "show_during_tenant_setup": True},
        "brand": {"enabled": True, "required": False, "show_during_tenant_setup": True},
    })

    assert projected["type_mode"] == "required"
    assert projected["brand_mode"] == "optional"


def test_workflow_setup_gates_are_projected_for_tenant_publish():
    master = SimpleNamespace(
        is_type_required=False,
        is_brand_required=False,
        requires_checklist=False,
        requires_schedule=False,
        requires_address=False,
        requires_issue_type=False,
        pricing_model="fixed",
    )
    workflow = {
        "checklist_required": False,
        "quote_approval_required": False,
        "technician_required": False,
        "schedule_required": True,
        "service_area_required": True,
        "availability_required": True,
        "version_number": 2,
    }

    projected = project_tenant_blueprint(master, workflow)
    assert projected["requires_service_area"] is True
    assert projected["requires_availability"] is True
    assert projected["pricing_behavior"] == "fixed"
