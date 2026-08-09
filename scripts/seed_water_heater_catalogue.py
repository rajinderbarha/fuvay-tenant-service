"""Seed a bookable Water Heater / Geyser service, for the winter ordering.

Why a script and not a migration: this is CATALOGUE CONTENT tied to a specific
tenant's publishing and service area. A migration would create it on every
deployment, including ones whose providers do not offer it -- which is exactly the
"service nobody can book" state the serviceability rules exist to prevent.

Why it is needed: the seasonal ordering promotes water heating from December, and
the catalogue had no water-heater service or problem at all -- so winter had nothing
to promote and the feature looked broken rather than idle. It also gives the
`consult_intent` section real content, which is why it shipped disabled.

Every row is written through the SAME chain the admin console writes, so what this
produces is indistinguishable from a service an operator set up by hand:

    service_categories        the category, customer-visible
    master_services           the service, priced, inspection-first
    master_service_job_types  linked to a real job type
    master_issue_types        the problems a customer taps
    service_issue_mappings    each problem -> (service, job type), customer-visible
    tenant_services           the provider PUBLISHES it (enabled/active/published)
    tenant_service_area_services  and covers the PIN with it
    service_pricing_rules     a real visit fee, so Review can price it

Idempotent: re-running matches on slug/code and updates rather than duplicating.

    python scripts/seed_water_heater_catalogue.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@127.0.0.1:5432/serviceos",
)

# Guramrit, the demo provider that already publishes the AC catalogue at 140412.
TENANT_ID = "244beeec-fedc-452e-8054-317e45557d4d"
ZIPCODE = "140412"

CATEGORY = {
    "name": "Water Heater",
    "slug": "water-heater",
    "description": "Geyser and water heater service, repair and installation",
    # Display order puts it after the existing categories; the SEASONAL sort is what
    # actually lifts it in winter, so it does not need to jump the queue here.
    "display_order": 10,
}

SERVICE = {
    "service_name": "Water Heater Service",
    "slug": "water-heater-service",
    "description": "Geyser not heating, leaking or tripping -- inspected on site",
    # Inspection-first, like AC Service: a geyser fault cannot be priced from a
    # description, so the customer sees a visit fee that is credited against the work.
    "pricing_model": "inspection_based",
    "visit_fee": 299.00,
    "estimated_duration_minutes": 60,
}

# Real winter faults, phrased the way a customer would say them. "Geyser Not Heating"
# is deliberately the first: it is the fault that actually spikes in December, and it
# is what the seasonal keyword list matches on.
PROBLEMS = [
    ("GEYSER_NOT_HEATING", "Geyser Not Heating", "high"),
    ("GEYSER_WATER_LEAKING", "Water Leaking From Geyser", "high"),
    ("GEYSER_TRIPPING", "Geyser Tripping The MCB", "critical"),
    ("GEYSER_LOW_HOT_WATER", "Not Enough Hot Water", "medium"),
    ("GEYSER_NOISE", "Strange Noise From Geyser", "low"),
    ("GEYSER_INSTALLATION", "New Geyser Installation", "medium"),
]


async def seed() -> None:
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        category_id = await _category(conn)
        job_type_id = await _job_type(conn)
        service_id = await _service(conn, category_id)
        await _job_type_link(conn, service_id, job_type_id)
        problem_ids = await _problems(conn, category_id, service_id)
        await _mappings(conn, service_id, job_type_id, problem_ids)
        await _publish(conn, service_id, category_id, job_type_id)
        await _pricing(conn, service_id, category_id, job_type_id)
        print(f"\nSeeded: category={category_id} service={service_id} problems={len(problem_ids)}")
    await engine.dispose()


# asyncpg binds a Python str as VARCHAR, and Postgres will not compare or insert that
# against a uuid column -- hence the explicit CAST on every id. Passing uuid.UUID
# objects would work too, but the ids travel as strings through the whole script and
# one conversion point is easier to keep right than twenty.
async def _one(conn, sql: str, **params):
    return (await conn.execute(text(sql).bindparams(**params))).first()


async def _category(conn) -> str:
    row = await _one(conn, "SELECT id FROM service_categories WHERE slug = :slug",
                     slug=CATEGORY["slug"])
    if row:
        print(f"category   exists  {CATEGORY['slug']}")
        return str(row[0])
    # Mirrors Air Conditioning's own flags: a home-services category the customer can
    # see and a tenant can register for.
    new_id = str(uuid.uuid4())
    await conn.execute(text("""
        INSERT INTO service_categories
            (id, name, slug, description, display_order, is_active, is_customer_visible,
             vertical_type, tenant_selectable, pricing_supported, requires_location,
             requires_schedule, requires_issue_type, category_type, created_at, updated_at)
        VALUES (CAST(:id AS uuid), :name, :slug, :description, :display_order, true, true,
                'home_services', true, true, true, true, true, 'service', now(), now())
    """).bindparams(id=new_id, **CATEGORY))
    print(f"category   created {CATEGORY['slug']}")
    return new_id


async def _job_type(conn) -> str:
    """Reuse the platform's existing REPAIR job type rather than inventing one.

    Job types carry workflow meaning (assessment, quotes, checklists); a duplicate
    would be a second definition of the same thing for the execution engine to
    disagree about.
    """
    row = await _one(conn, """
        SELECT id FROM job_types
        WHERE is_active AND (lower(key) LIKE '%repair%' OR lower(label) LIKE '%repair%')
        ORDER BY display_order LIMIT 1
    """)
    if row:
        print("job type   reused  repair")
        return str(row[0])
    row = await _one(conn, "SELECT id FROM job_types WHERE is_active ORDER BY display_order LIMIT 1")
    if not row:
        raise SystemExit("No active job type exists; cannot make a service bookable.")
    print("job type   reused  first active")
    return str(row[0])


async def _service(conn, category_id: str) -> str:
    row = await _one(conn, "SELECT id FROM master_services WHERE slug = :slug",
                     slug=SERVICE["slug"])
    if row:
        # Kept in step with this file rather than left as whatever an earlier run
        # wrote -- the seed is the source of truth for its own rows.
        await conn.execute(text("""
            UPDATE master_services
               SET is_active = true, category_id = CAST(:category_id AS uuid),
                   pricing_model = :pricing_model, visit_fee = :visit_fee,
                   requires_issue_type = true, requires_schedule = true,
                   requires_address = true, updated_at = now()
             WHERE id = CAST(:id AS uuid)
        """).bindparams(
            id=str(row[0]), category_id=category_id,
            pricing_model=SERVICE["pricing_model"], visit_fee=SERVICE["visit_fee"],
        ))
        print(f"service    exists  {SERVICE['slug']}")
        return str(row[0])
    new_id = str(uuid.uuid4())
    await conn.execute(text("""
        INSERT INTO master_services
            (id, category_id, service_name, slug, description, pricing_model, visit_fee,
             estimated_duration_minutes, is_active, display_order, requires_issue_type,
             requires_schedule, requires_address, is_brand_required, is_type_required,
             tenant_override_allowed, created_at, updated_at)
        VALUES (CAST(:id AS uuid), CAST(:category_id AS uuid), :service_name, :slug, :description, :pricing_model,
                :visit_fee, :estimated_duration_minutes, true, 0, true,
                true, true, false, false, true, now(), now())
    """).bindparams(id=new_id, category_id=category_id, **SERVICE))
    print(f"service    created {SERVICE['slug']}")
    return new_id


async def _job_type_link(conn, service_id: str, job_type_id: str) -> None:
    row = await _one(conn, """
        SELECT id FROM master_service_job_types
         WHERE master_service_id = CAST(:service_id AS uuid) AND job_type_id = CAST(:job_type_id AS uuid)
    """, service_id=service_id, job_type_id=job_type_id)
    if row:
        print("job link   exists")
        return
    await conn.execute(text("""
        INSERT INTO master_service_job_types
            (id, master_service_id, job_type_id, is_active, display_order, created_at, updated_at)
        VALUES (CAST(:id AS uuid), CAST(:service_id AS uuid), CAST(:job_type_id AS uuid), true, 0, now(), now())
    """).bindparams(id=str(uuid.uuid4()), service_id=service_id, job_type_id=job_type_id))
    print("job link   created")


async def _problems(conn, category_id: str, service_id: str) -> list[str]:
    ids = []
    for order, (code, name, severity) in enumerate(PROBLEMS):
        row = await _one(conn, "SELECT id FROM master_issue_types WHERE code = :code", code=code)
        if row:
            ids.append(str(row[0]))
            continue
        new_id = str(uuid.uuid4())
        await conn.execute(text("""
            INSERT INTO master_issue_types
                (id, category_id, master_service_id, code, name, slug, severity, is_active,
                 display_order, vertical_type, status, customer_visible, requires_photo,
                 requires_description, created_at, updated_at)
            VALUES (CAST(:id AS uuid), CAST(:category_id AS uuid), CAST(:service_id AS uuid), :code, :name, :slug, :severity, true,
                    :display_order, 'home_services', 'active', true, false,
                    false, now(), now())
        """).bindparams(
            id=new_id, category_id=category_id, service_id=service_id, code=code, name=name,
            slug=code.lower(), severity=severity, display_order=order,
        ))
        ids.append(new_id)
    print(f"problems   {len(ids)} present")
    return ids


async def _mappings(conn, service_id: str, job_type_id: str, problem_ids: list[str]) -> None:
    """Each problem mapped to (service, JOB TYPE).

    The job type is the part that matters: a category-only mapping never activates a
    problem at runtime, which is exactly why the standalone Issue Types admin page was
    retired in favour of the Job-Type Blueprint.
    """
    created = 0
    for order, issue_id in enumerate(problem_ids):
        row = await _one(conn, """
            SELECT id FROM service_issue_mappings
             WHERE master_service_id = CAST(:service_id AS uuid) AND issue_type_id = CAST(:issue_id AS uuid)
        """, service_id=service_id, issue_id=issue_id)
        if row:
            continue
        await conn.execute(text("""
            INSERT INTO service_issue_mappings
                (id, master_service_id, issue_type_id, job_type_id, status, customer_visible,
                 is_common, is_default, requires_photo, requires_description, display_order,
                 created_at, updated_at)
            VALUES (CAST(:id AS uuid), CAST(:service_id AS uuid), CAST(:issue_id AS uuid), CAST(:job_type_id AS uuid), 'active', true,
                    true, false, false, false, :display_order, now(), now())
        """).bindparams(
            id=str(uuid.uuid4()), service_id=service_id, issue_id=issue_id,
            job_type_id=job_type_id, display_order=order,
        ))
        created += 1
    print(f"mappings   {created} created")


JOB_TYPE_KEY = "repair"


async def _publish(conn, service_id: str, category_id: str, job_type_id: str) -> None:
    """The provider publishes the service AND covers the PIN with it.

    Both halves are required by `_publisher_filter`: a published service nobody covers
    at the customer's PIN is not bookable there, and coverage without publishing is
    not either. Missing one is the "service exists but never appears" bug.
    """
    row = await _one(conn, """
        SELECT id FROM tenant_services
         WHERE tenant_id = CAST(:tenant_id AS uuid) AND master_service_id = CAST(:service_id AS uuid)
    """, tenant_id=TENANT_ID, service_id=service_id)
    if row:
        await conn.execute(text("""
            UPDATE tenant_services
               SET is_enabled = true, is_active = true, setup_status = 'published',
                   published_at = COALESCE(published_at, now()), updated_at = now()
             WHERE id = CAST(:id AS uuid)
        """).bindparams(id=str(row[0])))
        print("publish    refreshed")
    else:
        await conn.execute(text("""
            INSERT INTO tenant_services
                (id, tenant_id, master_service_id, category_id, job_type_id, is_enabled,
                 is_active, setup_status, published_at, tenant_visit_fee, created_at, updated_at)
            VALUES (CAST(:id AS uuid), CAST(:tenant_id AS uuid), CAST(:service_id AS uuid), CAST(:category_id AS uuid), CAST(:job_type_id AS uuid), true,
                    true, 'published', now(), :visit_fee, now(), now())
        """).bindparams(
            id=str(uuid.uuid4()), tenant_id=TENANT_ID, service_id=service_id,
            category_id=category_id, job_type_id=job_type_id, visit_fee=SERVICE["visit_fee"],
        ))
        print("publish    created")

    area = await _one(conn, """
        SELECT id FROM tenant_service_areas
         WHERE tenant_id = CAST(:tenant_id AS uuid) AND zipcode = :zipcode AND is_active
         LIMIT 1
    """, tenant_id=TENANT_ID, zipcode=ZIPCODE)
    if not area:
        print(f"coverage   SKIPPED -- {TENANT_ID} has no active area for {ZIPCODE}")
        return
    row = await _one(conn, """
        SELECT id FROM tenant_service_area_services
         WHERE tenant_service_area_id = CAST(:area_id AS uuid) AND service_id = CAST(:service_id AS uuid)
    """, area_id=str(area[0]), service_id=service_id)
    if row:
        await conn.execute(text("""
            UPDATE tenant_service_area_services
               SET is_available = true, status = 'ACTIVE', updated_at = now()
             WHERE id = CAST(:id AS uuid)
        """).bindparams(id=str(row[0])))
        print("coverage   refreshed")
        return
    # `job_type` here is the LEGACY text column, still NOT NULL on this table while
    # `job_type_id` is the modern link. Written with the same vocabulary the existing
    # rows use ("repair"/"service"/"installation") rather than left to fail.
    await conn.execute(text("""
        INSERT INTO tenant_service_area_services
            (id, tenant_service_area_id, tenant_id, service_id, job_type, is_available, status,
             base_price, created_at, updated_at)
        VALUES (CAST(:id AS uuid), CAST(:area_id AS uuid), CAST(:tenant_id AS uuid),
                CAST(:service_id AS uuid), :job_type_key, true, 'ACTIVE', :visit_fee, now(), now())
    """).bindparams(
        id=str(uuid.uuid4()), area_id=str(area[0]), tenant_id=TENANT_ID,
        service_id=service_id, visit_fee=SERVICE["visit_fee"], job_type_key=JOB_TYPE_KEY,
    ))
    print("coverage   created")


async def _pricing(conn, service_id: str, category_id: str, job_type_id: str) -> None:
    """A real visit fee, so Review can price the booking.

    Without this the offering resolves but has no valid price, and the booking review
    refuses it with PRICE_OPTIONS_UNAVAILABLE -- a service that looks bookable right up
    to the last screen.
    """
    row = await _one(conn, """
        SELECT id FROM service_pricing_rules
         WHERE master_service_id = CAST(:service_id AS uuid) AND is_active AND deleted_at IS NULL
    """, service_id=service_id)
    if row:
        print("pricing    exists")
        return
    await conn.execute(text("""
        INSERT INTO service_pricing_rules
            (id, master_service_id, category_id, job_type_id, job_type, pricing_model,
             visit_fee, base_price, priority, is_active, rule_name, source,
             created_at, updated_at)
        VALUES (CAST(:id AS uuid), CAST(:service_id AS uuid), CAST(:category_id AS uuid),
                CAST(:job_type_id AS uuid), :job_type_key, 'inspection_based',
                :visit_fee, :visit_fee, 100, true, 'Water heater inspection visit', 'seed',
                now(), now())
    """).bindparams(
        id=str(uuid.uuid4()), service_id=service_id, category_id=category_id,
        job_type_id=job_type_id, visit_fee=SERVICE["visit_fee"], job_type_key=JOB_TYPE_KEY,
    ))
    print("pricing    created")


if __name__ == "__main__":
    asyncio.run(seed())
