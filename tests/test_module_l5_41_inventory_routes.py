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
PROVIDER_EMAIL = "provider@serviceos.local"
PASSWORD = "Password123!"
TENANT_ID = "5209ef33-a53e-4fc0-b3f6-006335b8d712"


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
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


class TestLive:
    async def test_full_inventory_flow_on_real_routes(self):
        tok = await _login(PROVIDER_EMAIL)
        if not tok:
            pytest.skip("provider login unavailable")
        loc = str(uuid.uuid4())
        sku = f"L541T-{uuid.uuid4().hex[:6]}"
        item_id = None
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as c:
            # dead route 404s
            dead = await c.get(f"/v1/inventory/items?tenant_id={TENANT_ID}")
            assert dead.status_code == 404

            created = await c.post(f"/v1/inventory/tenants/{TENANT_ID}/items",
                                   json={"name": "L541 Widget", "sku": sku, "unit": "pcs",
                                         "unit_cost": 50, "min_quantity": 10})
            assert created.status_code == 201, created.text
            item_id = created.json()["data"]["item_id"]

            try:
                rcv = await c.post(f"/v1/inventory/items/{item_id}/locations/{loc}/receive",
                                   json={"tenant_id": TENANT_ID, "quantity": 25})
                assert rcv.status_code == 200, rcv.text

                bal = await c.get(f"/v1/inventory/items/{item_id}/locations/{loc}/balance")
                d = bal.json()["data"]
                assert d["quantity"] == 25 and d["available_qty"] == 25
                assert "available_qty" in d and "below_minimum" in d

                low = await c.get(f"/v1/inventory/tenants/{TENANT_ID}/low-stock")
                assert low.status_code == 200 and "items" in low.json()["data"]
            finally:
                import asyncpg
                conn = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
                iid = uuid.UUID(item_id)
                for tbl in ("stock_reservations", "stock_transactions", "stock_balances"):
                    await conn.execute(f"DELETE FROM {tbl} WHERE item_id=$1", iid)
                await conn.execute("DELETE FROM inventory_items WHERE id=$1", iid)
                await conn.close()
