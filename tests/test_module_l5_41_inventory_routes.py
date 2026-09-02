"""MODULE-L5-41 — the tenant-portal inventory feature was wholesale broken:
the entire inventoryApi called a URL scheme that doesn't exist.

Found via the openapi-vs-frontend audit (same technique as L5-39/L5-40). Every
inventoryApi call in frontend/tenant-portal/lib/api.ts 404'd -- it used
/v1/inventory/items, /stock/receive, /stock/balance, /stock/transactions,
/stock/low, /stock/replenish, /reservations/{id}/confirm|release, none of
which exist. The real inventory engine (app/engines/inventory/router.py)
carries tenant_id/item_id/location_id in the PATH for most operations, and
reservation confirm/release identify the reservation by
job_id+item_id+location_id in the BODY (not a reservation_id in the path).

The response shapes were also wrong: StockBalance.available (real:
available_qty), LowStockItem.current_quantity/shortfall/reserved_qty (real:
current_qty/deficit, no reserved_qty).

Fixed the whole inventoryApi (routes + signatures), the TS interfaces, and the
page's field references. Verified live end-to-end: create item -> receive ->
balance -> transactions -> low-stock -> replenish -> reserve -> confirm.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[1]
API_TS = ROOT / "frontend/tenant-portal/lib/api.ts"
PAGE = ROOT / "frontend/tenant-portal/app/(tenant)/inventory/page.tsx"

BASE = "http://localhost:8000"
PROVIDER_EMAIL = "provider@serviceos.in"
PASSWORD = "Password123!"


def _inv_block(src: str) -> str:
    block = src.split("export const inventoryApi")[1].split("\n};")[0]
    return "\n".join(l for l in block.splitlines() if not l.strip().startswith("//"))


def test_inventory_api_uses_the_real_routes():
    block = _inv_block(API_TS.read_text(encoding="utf-8"))
    assert "/v1/inventory/tenants/${tid}/items" in block
    assert "/locations/${locationId}/receive" in block
    assert "/locations/${locationId}/balance" in block
    assert "/v1/inventory/tenants/${tid}/low-stock" in block
    assert "/v1/inventory/reservations/confirm" in block
    # dead scheme is gone
    for dead in ("/v1/inventory/items\"", "/stock/receive", "/stock/balance",
                 "/stock/low", "/stock/replenish", "/stock/transactions"):
        assert dead not in block, f"dead route still present: {dead}"


def test_page_uses_real_response_fields():
    src = "\n".join(l for l in PAGE.read_text(encoding="utf-8").splitlines()
                    if not l.strip().startswith("//"))
    assert "available_qty" in src
    # The consolidated workspace expresses low stock through each inventory
    # row's real below_minimum state; the standalone low-stock DTO still uses
    # current_qty/deficit in the API contract.
    api = API_TS.read_text(encoding="utf-8")
    assert "current_qty" in api and "deficit" in api
    assert "below_minimum" in src
    for dead in (".current_quantity", ".shortfall", "balance.data.available "):
        assert dead not in src, f"page still uses dead field: {dead}"


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        if r.status_code != 200:
            return None
        data = r.json()["data"]
        return data["access_token"], data["user"]["tenant_id"]


class TestLive:
    async def test_full_inventory_flow_on_real_routes(self):
        login = await _login(PROVIDER_EMAIL)
        if not login:
            pytest.skip("provider login unavailable")
        tok, tenant_id = login
        sku = f"L541T-{uuid.uuid4().hex[:6]}"
        item_id = None
        location_ids = []
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as c:
            # dead route 404s
            dead = await c.get(f"/v1/inventory/items?tenant_id={tenant_id}")
            assert dead.status_code == 404

            for suffix, kind in (("Warehouse", "warehouse"), ("Van", "van")):
                location = await c.post(
                    f"/v1/inventory/tenants/{tenant_id}/locations",
                    json={"location_name": f"L541 {suffix} {sku}", "location_type": kind},
                )
                assert location.status_code == 201, location.text
                location_ids.append(location.json()["data"]["location_id"])

            created = await c.post(f"/v1/inventory/tenants/{tenant_id}/items",
                                   json={"name": "L541 Widget", "sku": sku, "unit": "pcs",
                                         "unit_cost": 50, "selling_price": 75,
                                         "min_quantity": 30})
            assert created.status_code == 201, created.text
            item_id = created.json()["data"]["item_id"]

            try:
                fetched = await c.get(f"/v1/inventory/items/{item_id}")
                assert fetched.status_code == 200 and fetched.json()["data"]["sku"] == sku

                updated = await c.put(
                    f"/v1/inventory/tenants/{tenant_id}/items/{item_id}",
                    json={"name": "L541 Widget Updated", "selling_price": 80},
                )
                assert updated.status_code == 200, updated.text
                assert updated.json()["data"]["name"] == "L541 Widget Updated"
                assert float(updated.json()["data"]["selling_price"]) == 80

                listed = await c.get(
                    f"/v1/inventory/tenants/{tenant_id}/items", params={"search": sku}
                )
                assert listed.status_code == 200, listed.text
                assert any(row["item_id"] == item_id for row in listed.json()["data"]["items"])

                source, destination = location_ids
                rcv = await c.post(f"/v1/inventory/items/{item_id}/locations/{source}/receive",
                                   json={"tenant_id": tenant_id, "quantity": 25})
                assert rcv.status_code == 200, rcv.text

                counted = await c.post(
                    f"/v1/inventory/items/{item_id}/locations/{source}/count",
                    json={"tenant_id": tenant_id, "counted_quantity": 24,
                          "reason": "Operation-level integration audit",
                          "idempotency_key": str(uuid.uuid4())},
                )
                assert counted.status_code == 200 and counted.json()["data"]["adjustment"] == -1

                transferred = await c.post(
                    f"/v1/inventory/items/{item_id}/transfer",
                    json={"tenant_id": tenant_id, "from_location_id": source,
                          "to_location_id": destination, "quantity": 4,
                          "reason": "Operation-level integration audit",
                          "idempotency_key": str(uuid.uuid4())},
                )
                assert transferred.status_code == 200, transferred.text

                source_bal = await c.get(f"/v1/inventory/items/{item_id}/locations/{source}/balance")
                destination_bal = await c.get(f"/v1/inventory/items/{item_id}/locations/{destination}/balance")
                assert source_bal.json()["data"]["quantity"] == 20
                assert destination_bal.json()["data"]["quantity"] == 4
                assert source_bal.json()["data"]["reconciliation_ok"] is True
                assert destination_bal.json()["data"]["reconciliation_ok"] is True

                ledger = await c.get(
                    f"/v1/inventory/items/{item_id}/locations/{source}/transactions"
                )
                assert ledger.status_code == 200 and ledger.json()["data"]["transactions"]

                low = await c.get(f"/v1/inventory/tenants/{tenant_id}/low-stock")
                assert low.status_code == 200 and "items" in low.json()["data"]
                assert any(row["item_id"] == item_id for row in low.json()["data"]["items"])

                replenish = await c.post(
                    f"/v1/inventory/tenants/{tenant_id}/items/{item_id}/replenish",
                    json={"quantity": 10},
                )
                assert replenish.status_code == 200
                assert replenish.json()["data"]["quantity_requested"] == 10

                archived = await c.delete(f"/v1/inventory/tenants/{tenant_id}/items/{item_id}")
                assert archived.status_code == 200 and archived.json()["data"]["deleted"] is True
            finally:
                import asyncpg
                conn = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
                iid = uuid.UUID(item_id)
                for tbl in ("stock_reservations", "stock_transactions", "stock_balances"):
                    await conn.execute(f"DELETE FROM {tbl} WHERE item_id=$1", iid)
                await conn.execute("DELETE FROM inventory_items WHERE id=$1", iid)
                for location_id in location_ids:
                    await conn.execute("DELETE FROM stock_locations WHERE id=$1", uuid.UUID(location_id))
                await conn.close()
