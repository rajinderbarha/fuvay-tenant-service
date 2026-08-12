import runpy
from pathlib import Path


ROUTES = runpy.run_path(
    Path(__file__).parents[1] / "alembic" / "versions" / "247_enabled_vertical_module_routes.py"
)["ROUTES"]


def test_enabled_vertical_route_map_contains_no_placeholder_paths():
    assert ROUTES
    assert all("/catalog-module/" not in path for path in ROUTES.values())


def test_enabled_vertical_route_map_targets_real_admin_workspaces():
    assert ROUTES == {
        "checklist_templates": "/admin/checklists",
        "property_types": "/admin/types-brands",
        "listing_types": "/admin/types-brands",
        "amenities": "/admin/service-options",
        "localities": "/admin/location-mapping",
        "site_visit_workflows": "/admin/workflow-templates",
    }
