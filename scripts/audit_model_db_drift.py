"""Final Phase end-to-end audit: compare every loaded SQLAlchemy model's
declared columns against its table's REAL columns in the live database.

Rationale: this session found repeated instances of ORM models missing
columns that genuinely exist in the migrated DB and are actively used by
service code (WorkSession, CompletionProof, ServicePaymentRecord,
ProviderTeamMember.availability_state, TenantDocument.staff_member_id) --
each one only discovered by hitting a live 500. This script finds all of
them in one pass instead of one crash at a time.

Import app.main first so every engine's models get registered onto
ServiceOSBase.metadata (mirrors how the real app loads them).
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings


async def main():
    # Import the whole app so every engine's models module gets imported
    # and registered onto ServiceOSBase.metadata -- same effect as the
    # real server booting.
    from app.main import create_app
    create_app()

    from app.models.base import ServiceOSBase

    engine = create_async_engine(get_settings().DATABASE_URL)
    async with engine.connect() as conn:
        db_tables = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        ))
        real_tables = {row[0] for row in db_tables.fetchall()}

        model_tables = {}
        for table_name, table in ServiceOSBase.metadata.tables.items():
            model_tables[table_name] = {c.name for c in table.columns}

        missing_tables = []
        model_missing_columns = {}  # table -> columns in DB but not in model
        db_missing_columns = {}     # table -> columns in model but not in DB

        for table_name, model_cols in sorted(model_tables.items()):
            if table_name not in real_tables:
                missing_tables.append(table_name)
                continue
            db_cols_result = await conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=:t"
            ), {"t": table_name})
            db_cols = {row[0] for row in db_cols_result.fetchall()}

            missing_from_model = db_cols - model_cols
            missing_from_db = model_cols - db_cols
            if missing_from_model:
                model_missing_columns[table_name] = sorted(missing_from_model)
            if missing_from_db:
                db_missing_columns[table_name] = sorted(missing_from_db)

    await engine.dispose()

    print(f"\n=== Total tables mapped by loaded models: {len(model_tables)} ===")
    print(f"=== Total real tables in DB: {len(real_tables)} ===\n")

    if missing_tables:
        print(f"--- Tables in a loaded model but NOT in the DB ({len(missing_tables)}) ---")
        for t in missing_tables:
            print(f"  {t}")
        print()

    if db_missing_columns:
        print(f"--- CRITICAL: model has columns the DB does NOT have ({len(db_missing_columns)} tables) ---")
        print("--- (inserts/updates on these columns will 500 with UndefinedColumnError) ---")
        for t, cols in db_missing_columns.items():
            print(f"  {t}: {cols}")
        print()

    if model_missing_columns:
        print(f"--- Real DB columns MISSING from the ORM model ({len(model_missing_columns)} tables) ---")
        print("--- (service code referencing these will AttributeError) ---")
        for t, cols in model_missing_columns.items():
            print(f"  {t}: {cols}")
        print()

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
