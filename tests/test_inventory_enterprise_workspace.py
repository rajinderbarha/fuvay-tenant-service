"""Enterprise inventory workspace regression contract."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = (ROOT / "app/engines/inventory/service.py").read_text(encoding="utf-8")
ROUTER = (ROOT / "app/engines/inventory/router.py").read_text(encoding="utf-8")
MODEL = (ROOT / "app/engines/inventory/models.py").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend/tenant-portal/app/(tenant)/inventory/page.tsx").read_text(encoding="utf-8")
API = (ROOT / "frontend/tenant-portal/lib/api.ts").read_text(encoding="utf-8")
EXECUTION = (ROOT / "app/engines/execution/home_service_service.py").read_text(encoding="utf-8")
EXECUTION_PAGE = (ROOT / "frontend/tenant-portal/app/(tenant)/service-jobs/[id]/execution/page.tsx").read_text(encoding="utf-8")


def test_provider_and_customer_prices_are_not_conflated():
    assert "selling_price" in MODEL
    assert "Provider acquisition cost" in PAGE
    assert "Customer part price" in PAGE
    assert "service_group_id" in MODEL
    assert "inventory_category_requires_active_tenant_entitlement" in SERVICE


def test_reservation_is_a_hold_then_confirmation_is_consumption():
    reservation = SERVICE.split("async def create_reservation", 1)[1].split("async def confirm_reservation", 1)[0]
    confirmation = SERVICE.split("async def confirm_reservation", 1)[1].split("async def release_reservation", 1)[0]
    release = SERVICE.split("async def release_reservation", 1)[1].split("async def list_below_minimum", 1)[0]
    assert "StockTxnType.RESERVATION, 0" in reservation
    assert "bal.reserved_qty += quantity" in reservation
    assert "StockTxnType.CONFIRMATION, -res.quantity" in confirmation
    assert "StockTxnType.RETURN, 0" in release
    assert "bal.quantity += res.quantity" not in release


def test_workspace_has_real_filters_pagination_locations_and_ledger():
    for token in ("search:", "category_id:", "stock_status:", "offset:", "include_archived:"):
        assert token in ROUTER
    for route in ("workspace-summary", '"/tenants/{tenant_id}/locations"', "transactions", '"/items/{item_id}/transfer"', '"/items/{item_id}/locations/{location_id}/count"'):
        assert route in ROUTER
    for control in ("Search inventory", "Stock status", "Pagination", "Stock locations", "Stock ledger"):
        assert control in PAGE
    assert "TenantLayout" not in PAGE


def test_cycle_count_and_transfer_are_locked_ledger_operations():
    assert "async def count_stock" in SERVICE
    assert "StockTxnType.ADJUSTMENT" in SERVICE
    assert "async def transfer_stock" in SERVICE
    assert "sorted((from_location_id, to_location_id), key=str)" in SERVICE
    assert SERVICE.count("StockTxnType.TRANSFER") >= 2
    assert "Cycle count" in PAGE and "Transfer stock" in PAGE


def test_frontend_uses_server_backed_workspace_contract():
    for token in ("getWorkspaceSummary", "listLocations", "createLocation", "selling_price", "service_group_id"):
        assert token in API
    assert "inventoryApi.listItems({" in PAGE


def test_final_part_approval_reserves_and_installation_consumes_stock():
    assert "_reserve_parts_inventory" in EXECUTION
    assert "_consume_parts_inventory" in EXECUTION
    assert "if not pr.customer_approval_required" in EXECUTION
    assert "await self._reserve_parts_inventory(db, pr, customer_id)" in EXECUTION
    assert "await inv.confirm_reservation" in EXECUTION
    assert "Fulfilment source" in EXECUTION_PAGE
    assert "Provider inventory (reserve stock)" in EXECUTION_PAGE
    assert "External purchase (no stock movement)" in EXECUTION_PAGE
