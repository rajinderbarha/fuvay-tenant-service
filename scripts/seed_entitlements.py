"""FINAL-L5-04B — Canonical Entitlement Seed.

Deterministic, idempotent. Grants distinct entitlement sets to the two
canonical seeded tenants so tenant isolation can be tested:

  Tenant One (demo-ac-services):        Home Services module + AC Services category
  Tenant Two (isolation-test-services): Home Services module + Plumbing category

Rerunning this script creates no duplicate rows — assign_*_entitlement()
is idempotent (returns the existing ACTIVE row unchanged).
"""
from __future__ import annotations

import asyncio
import json
import sys
import uuid

import asyncpg

from app.database import get_session_factory, init_db
from app.engines.entitlement.service import entitlement_service

TENANT_ONE_SLUG = "demo-ac-services"
TENANT_TWO_SLUG = "isolation-test-services"

PLAN = {
    TENANT_ONE_SLUG: {"module": "home_services", "category_code": "ac_services"},
    TENANT_TWO_SLUG: {"module": "home_services", "category_code": "plumbing"},
}


async def main() -> dict:
    await init_db()
    factory = get_session_factory()
    results: dict = {"tenants": []}

    async with factory() as db:
        for slug, plan in PLAN.items():
            row = (await db.execute(
                __import__("sqlalchemy").text("SELECT id FROM tenants WHERE slug = :slug"), {"slug": slug}
            )).fetchone()
            if not row:
                results["tenants"].append({"slug": slug, "status": "SKIPPED_TENANT_NOT_FOUND"})
                continue
            tenant_id = row[0]

            group_row = (await db.execute(
                __import__("sqlalchemy").text("SELECT id FROM service_groups WHERE code = :code"),
                {"code": plan["category_code"]},
            )).fetchone()
            if not group_row:
                results["tenants"].append({"slug": slug, "status": "SKIPPED_CATEGORY_NOT_FOUND"})
                continue
            category_id = group_row[0]

            module_result = await entitlement_service.assign_module_entitlement(
                db, tenant_id=tenant_id, module_key=plan["module"],
                actor_id=None, actor_role="seed_script", source="canonical_seed",
            )
            category_result = await entitlement_service.assign_category_entitlement(
                db, tenant_id=tenant_id, category_id=category_id,
                actor_id=None, actor_role="seed_script", source="canonical_seed",
            )
            results["tenants"].append({
                "slug": slug, "tenant_id": str(tenant_id), "status": "OK",
                "module": module_result, "category": category_result,
            })

    return results


if __name__ == "__main__":
    out = asyncio.run(main())
    print(json.dumps(out, indent=2, default=str))
