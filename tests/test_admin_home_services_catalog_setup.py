"""Canonical Admin Home Services catalog workspace certification."""
from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/super-admin"
WORKSPACE = (
    FRONTEND / "app/admin/catalog-workspace/page.tsx"
).read_text(encoding="utf-8-sig")
LEGACY = (
    FRONTEND / "app/admin/home-services/service-catalog/page.tsx"
).read_text(encoding="utf-8-sig")
LAYOUT = (
    FRONTEND / "components/layout/AdminLayout.tsx"
).read_text(encoding="utf-8-sig")
NAV = (FRONTEND / "lib/nav-config.ts").read_text(encoding="utf-8-sig")
API = (FRONTEND / "lib/api.ts").read_text(encoding="utf-8-sig")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8-sig")


def test_legacy_route_redirects_to_single_catalog_workspace():
    assert 'redirect("/admin/catalog-workspace")' in LEGACY


def test_navigation_points_to_canonical_workspace_only():
    combined = LAYOUT + NAV
    assert '"hs-service-catalog"' in combined
    assert 'label: "Service Catalog"' in combined
    assert 'href: "/admin/catalog-workspace"' in combined
    assert '"Bargain Rules"' not in combined


def test_workspace_owns_every_catalog_configuration_surface():
    for label in (
        "Dimensions",
        "Problems & Questions",
        "Options & Add-ons",
        "Checklist",
        "Workflow",
        "Tenant Setup Rules",
    ):
        assert label in WORKSPACE


def test_workflow_is_job_type_scoped_and_does_not_set_price_amounts():
    assert "selectedJobTypeId" in WORKSPACE
    assert "getJobTypeWorkflow" in WORKSPACE
    assert "setJobTypeWorkflow" in WORKSPACE
    assert "Never an amount" in WORKSPACE
    assert "tenant sets actual prices" in WORKSPACE


def test_questions_problems_and_checklists_use_real_apis():
    for marker in (
        "listQuestions",
        "listIssueTypesV2",
        "listMappingsDirectory",
        "createMapping",
        "publishVersion",
    ):
        assert marker in WORKSPACE


def test_tenant_rules_reuse_canonical_workflow_and_dimensions():
    assert "service_area_required" in WORKSPACE
    assert "availability_required" in WORKSPACE
    assert "Tenant Setup Rules" in WORKSPACE
    assert "reuse Dimensions" in WORKSPACE


def test_catalog_clients_and_routers_are_registered():
    assert "catalogWorkspaceApi" in API
    assert "home_services_catalog_console_router" in MAIN
    assert "auto_price_admin_router" in MAIN
    assert "auto_price_tenant_router" in MAIN


def test_retired_admin_tier_pricing_is_not_in_catalog_workspace():
    for marker in (
        "Low/Mid/High",
        "Bargain Rules",
        "customer-price-preview",
        "price-experience/preview",
    ):
        assert marker not in WORKSPACE
