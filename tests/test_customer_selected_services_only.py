"""Customer catalog surfaces expose only provider-selected services."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_home_quick_issues_are_scoped_to_exact_bookable_master_services():
    home = source("app/engines/customer_home/service.py")

    assert 'get("master_service_id")' in home
    assert "ServiceIssueMapping.master_service_id.in_(master_service_ids)" in home
    assert 'ServiceIssueMapping.status == "active"' in home
    assert "ServiceIssueMapping.customer_visible.is_(True)" in home


def test_home_groups_services_and_categories_require_canonical_bookability():
    home = source("app/engines/customer_home/service.py")

    assert home.count("latest_provider_bookable(Tenant.id)") >= 3
    assert "TenantServiceAreaService.service_id == MasterService.id" in home
    assert 'TenantService.setup_status == "published"' in home


def test_search_and_catalog_receive_and_apply_customer_zipcode():
    router = source("app/engines/customer_flow/router.py")
    flow = source("app/engines/customer_flow/service.py")
    mobile_search = source("mobile/customer-app/src/api/home/customerSearchApi.ts")
    mobile_query = source("mobile/customer-app/src/api/home/useCustomerSearchQuery.ts")

    assert router.count("zipcode: str | None = Query(None)") >= 3
    assert flow.count("_publisher_filter(zipcode)") >= 4
    assert "zipcode=${encodeURIComponent(zipcode)}" in mobile_search
    assert "searchCustomerCatalog(q, zipcode)" in mobile_query
