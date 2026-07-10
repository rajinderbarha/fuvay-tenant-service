"""FINAL-L5-01B — One-time privileged database bootstrap.

Solves the empty-database migration-replay blocker found in FINAL-L5-01:
`alembic upgrade head` fails on `CREATE EXTENSION IF NOT EXISTS vector`
because the normal application runtime user (`serviceos`) is correctly
NOT a superuser and lacks CREATE EXTENSION privilege.

This script connects with a SEPARATE, explicitly-provided superuser
connection string (never the app's normal DATABASE_URL) to create only
the required extension, then exits. The normal application user remains
non-superuser for all runtime and migration work. Idempotent — safe to
run twice (CREATE EXTENSION IF NOT EXISTS).

Superuser credentials are read from BOOTSTRAP_SUPERUSER_DATABASE_URL,
never hardcoded, never logged. This script does not touch the app's
normal DATABASE_URL connection at all.

Run against a freshly created empty database:
  BOOTSTRAP_SUPERUSER_DATABASE_URL="postgresql+asyncpg://postgres:<pw>@127.0.0.1:5432/<dbname>" \
  python scripts/bootstrap_database_final_l5_01b.py
"""
from __future__ import annotations
import asyncio
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

REQUIRED_EXTENSIONS = ["vector"]


def _mask(url: str) -> str:
    return re.sub(r"://[^:]+:[^@]+@", "://***:***@", url)


async def run() -> None:
    su_url = os.environ.get("BOOTSTRAP_SUPERUSER_DATABASE_URL")
    if not su_url:
        print("[REFUSED] BOOTSTRAP_SUPERUSER_DATABASE_URL not set. Aborting. "
              "This script requires an explicit, separate superuser connection "
              "string — it never reuses the app's normal DATABASE_URL.")
        sys.exit(1)

    print(f"[TARGET] bootstrap connection: {_mask(su_url)}")
    engine = create_async_engine(su_url, echo=False)
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        for ext in REQUIRED_EXTENSIONS:
            await conn.execute(text(f"CREATE EXTENSION IF NOT EXISTS {ext}"))
            print(f"[OK] extension '{ext}' present (created or already existed)")
    await engine.dispose()
    print("\n[BOOTSTRAP COMPLETE] The normal application/migration user remains "
          "non-superuser. Run `alembic upgrade head` next using the normal "
          "DATABASE_URL.")


if __name__ == "__main__":
    asyncio.run(run())
