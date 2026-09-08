"""One-off: move every media_assets row still on local disk (storage_driver=
'local') to Cloudinary, once Cloudinary is configured (admin-console
Notification & Provider Settings -> Media storage, or the CLOUDINARY_* env
vars). Local files predate that config -- switching the driver only affects
uploads going forward, it does not retroactively move what's already there.

For each local asset this:
  1. Reads the file from local disk (uploads/<storage_key>).
  2. Uploads it to Cloudinary via the same code path a live upload uses.
  3. Updates the media_assets row (storage_driver/key/bucket/public_url).
  4. Rewrites every known denormalized *_url column that held the OLD
     local URL (service_categories, service_groups, master_services,
     service_types, brands, master_offerings, master_issue_types,
     catalog_questions, tenants, tenant_branding, users) to the new
     Cloudinary URL, so nothing keeps pointing at the file that's about to
     stop being the source of truth.

Local files are left in place (not deleted) -- this only adds the Cloudinary
copy and repoints references to it. Re-running is safe: only storage_driver
='local' rows are touched, so already-migrated assets are skipped.

Dry-run by default; pass --execute to apply. Must run inside the API
container (relies on the same uploads/ working directory a live upload
uses).
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import text

logging.disable(logging.INFO)

# (table, column) pairs known to hold a media asset's public_url directly.
DENORMALIZED_URL_COLUMNS = [
    ("service_categories", "icon_url"), ("service_categories", "image_url"),
    ("service_groups", "icon_url"),
    ("master_services", "image_url"), ("master_services", "icon_url"),
    ("service_types", "icon_url"),
    ("brands", "logo_url"),
    ("master_offerings", "image_url"), ("master_offerings", "icon_url"),
    ("master_issue_types", "icon_url"),
    ("catalog_questions", "icon_url"),
    ("tenants", "logo_url"),
    ("tenant_branding", "logo_url"), ("tenant_branding", "favicon_url"),
    ("users", "avatar_url"),
]


async def run(execute: bool) -> None:
    from app.database import init_db, get_session_factory
    from app.engines.media.storage import MediaStorageService
    from app.engines.media.models import MediaAsset

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        storage = MediaStorageService(db=db)
        creds = await storage._resolve_cloudinary_credentials()
        if not creds:
            print("Cloudinary is not configured (neither the admin console nor CLOUDINARY_* "
                  "env vars) -- configure it first, then re-run.")
            return
        print(f"Using Cloudinary cloud '{creds[0]}'.")

        rows = (await db.execute(
            text("SELECT id, storage_key, media_context, file_name_stored, mime_type, "
                 "owner_id, public_url FROM media_assets WHERE storage_driver = 'local'")
        )).fetchall()
        print(f"Found {len(rows)} local-stored assets.")
        if not rows:
            return

        migrated = 0
        failed: list[str] = []
        ref_updates: dict[str, int] = {}

        for row in rows:
            old_url = row.public_url
            path = storage.get_local_path(row.storage_key)
            if not path:
                failed.append(f"{row.id}: local file missing at {row.storage_key}")
                continue
            try:
                file_bytes = path.read_bytes()
                stored = await storage._store_cloudinary(
                    file_bytes, row.file_name_stored, row.media_context,
                    str(row.owner_id), "unused-checksum", creds,
                )
            except Exception as exc:
                failed.append(f"{row.id}: upload failed ({exc})")
                continue

            report = (f"[EXECUTE] " if execute else "[DRY RUN] ") + \
                f"{row.id} ({row.media_context}): {old_url} -> {stored.public_url}"
            print(report)

            if not execute:
                migrated += 1
                continue

            await db.execute(text(
                "UPDATE media_assets SET storage_driver='cloudinary', storage_key=:key, "
                "storage_bucket=:bucket, public_url=:url WHERE id=:id"
            ), {"key": stored.storage_key, "bucket": stored.storage_bucket,
                "url": stored.public_url, "id": row.id})

            if old_url:
                for table, column in DENORMALIZED_URL_COLUMNS:
                    result = await db.execute(text(
                        f"UPDATE {table} SET {column} = :new WHERE {column} = :old"
                    ), {"new": stored.public_url, "old": old_url})
                    if result.rowcount:
                        ref_updates[f"{table}.{column}"] = ref_updates.get(f"{table}.{column}", 0) + result.rowcount

            migrated += 1

        if execute:
            await db.commit()
            print(f"\nCommitted. Migrated {migrated} of {len(rows)} assets.")
        else:
            await db.rollback()
            print(f"\nDry run only -- nothing written. {migrated} of {len(rows)} would migrate. "
                  "Re-run with --execute to apply.")

        if ref_updates:
            print("\nDenormalized references repointed:")
            for key, count in sorted(ref_updates.items()):
                print(f"  {key}: {count}")

        if failed:
            print(f"\n{len(failed)} asset(s) failed and were skipped:")
            for line in failed:
                print(f"  {line}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Actually apply the changes (default: dry run)")
    args = parser.parse_args()
    asyncio.run(run(execute=args.execute))
