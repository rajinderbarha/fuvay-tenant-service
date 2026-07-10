"""Seed demo users for local development and testing.

Idempotent: upserts users by email. Updates password and ensures is_active=True.
Creates a demo tenant if no tenant exists for provider/staff users.

Demo accounts:
  admin@serviceos.local    / Password123! / super_admin   / tenant_id=null
  provider@serviceos.local / Password123! / tenant_owner  / tenant_id=<demo>
  staff@serviceos.local    / Password123! / technician    / tenant_id=<demo>
  customer@serviceos.local / Password123! / customer      / tenant_id=null
"""
from __future__ import annotations
import asyncio
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select, text
from app.database import init_db, close_db, get_db_session
from app.engines.auth.models import User
from app.engines.auth.utils import hash_password

DEMO_PASSWORD = "Password123!"

DEMO_USERS = [
    {
        "email": "admin@serviceos.local",
        "full_name": "Super Admin",
        "role": "super_admin",
        "tenant_id": None,
    },
    # Non-.local aliases (work with strict email validators)
    {
        "email": "admin@serviceos.in",
        "full_name": "Super Admin",
        "role": "super_admin",
        "tenant_id": None,
    },
    {
        "email": "provider@serviceos.local",
        "full_name": "Demo Provider",
        "role": "tenant_owner",
        "tenant_id": "DEMO",   # resolved below
    },
    {
        "email": "provider@serviceos.in",
        "full_name": "Demo Provider",
        "role": "tenant_owner",
        "tenant_id": "DEMO",
    },
    {
        "email": "staff@serviceos.local",
        "full_name": "Demo Staff",
        "role": "technician",
        "tenant_id": "DEMO",   # resolved below
    },
    {
        "email": "staff@serviceos.in",
        "full_name": "Demo Staff",
        "role": "technician",
        "tenant_id": "DEMO",
    },
    {
        "email": "customer@serviceos.local",
        "full_name": "Demo Customer",
        "role": "customer",
        "tenant_id": None,
    },
    {
        "email": "customer@serviceos.in",
        "full_name": "Demo Customer",
        "role": "customer",
        "tenant_id": None,
    },
]


async def get_or_create_demo_tenant(db) -> uuid.UUID:
    """Return the ID of any tenant (or create a demo one)."""
    row = await db.execute(
        text("SELECT id FROM tenants ORDER BY created_at LIMIT 1")
    )
    existing = row.scalar_one_or_none()
    if existing:
        return existing

    # Create a minimal demo tenant using the real schema columns
    tenant_id = uuid.uuid4()
    await db.execute(text("""
        INSERT INTO tenants (id, tenant_name, subdomain, slug, status, vertical, plan_type, created_at, updated_at)
        VALUES (:id, 'Demo Tenant', 'demo', 'demo-tenant', 'active', 'home_services', 'starter', now(), now())
        ON CONFLICT (subdomain) DO NOTHING
    """), {"id": str(tenant_id)})

    row2 = await db.execute(
        text("SELECT id FROM tenants WHERE slug = 'demo-tenant' LIMIT 1")
    )
    return row2.scalar_one()


async def upsert_user(db, email: str, full_name: str, role: str, tenant_id) -> None:
    hashed = hash_password(DEMO_PASSWORD)

    row = await db.execute(select(User).where(User.email == email))
    user = row.scalar_one_or_none()

    if user:
        user.hashed_password = hashed
        user.is_active = True
        user.failed_login_attempts = 0
        user.locked_until = None
        user.role = role
        if tenant_id:
            user.tenant_id = tenant_id
        print(f"  UPDATED  {email}  role={role}")
    else:
        user = User(
            id=uuid.uuid4(),
            email=email,
            full_name=full_name,
            hashed_password=hashed,
            role=role,
            tenant_id=tenant_id,
            is_active=True,
            is_verified=True,
            onboarding_complete=True,
        )
        db.add(user)
        print(f"  CREATED  {email}  role={role}")


async def main() -> None:
    await init_db()
    print("Seeding demo users...")

    async with get_db_session() as db:
        demo_tenant_id = await get_or_create_demo_tenant(db)
        print(f"  Demo tenant ID: {demo_tenant_id}")

        for spec in DEMO_USERS:
            tid = demo_tenant_id if spec["tenant_id"] == "DEMO" else spec["tenant_id"]
            await upsert_user(db, spec["email"], spec["full_name"], spec["role"], tid)

        await db.commit()

    print("Done. Demo users seeded.")
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
