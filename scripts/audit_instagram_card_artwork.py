"""Report every catalog picture the Instagram booking bot cannot show.

Meta fetches card artwork from its own servers. When that fetch fails it
renders the card with a blank picture, answers the send with 200 and tells us
nothing — which is why a broken upload can sit in the catalog for weeks. This
walks the tables the bot reads, normalises each URL exactly as the sender does
and fetches it the way Meta would, then prints the rows that would render
blank without the runtime fallback.

Run: python -m scripts.audit_instagram_card_artwork
     python -m scripts.audit_instagram_card_artwork --all   (also list the good)

Read-only. Nothing is written or repaired; the output names the row and the
column an admin has to re-upload.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text  # noqa: E402

from app.database import close_db, get_session_factory, init_db  # noqa: E402
from app.engines.messaging_gateway.problem_cards import (  # noqa: E402
    _artwork_client, _fetchable, instagram_card_image_url,
)

#: (label, table, id column, name column, artwork columns best-first). These
#: are the tables `flow._category_step`, `_offering_step`, `_dimension_step`
#: and `_problem_step` read their pictures from.
SOURCES = (
    ("Category", "service_categories", "id", "name", ("image_url", "icon_url")),
    ("Service", "master_services", "id", "service_name", ("image_url", "icon_url")),
    ("Problem", "master_issue_types", "id", "name", ("image_url", "icon_url")),
    ("Type", "service_types", "id", "name", ("image_url", "icon_url")),
    ("Brand", "brands", "id", "name", ("image_url", "logo_url")),
)


async def _rows(session, table: str, id_column: str, name_column: str,
                columns: tuple[str, ...]) -> list[tuple]:
    selected = ", ".join((id_column, name_column, *columns))
    where = " OR ".join(f"NULLIF(BTRIM({c}), '') IS NOT NULL" for c in columns)
    return (await session.execute(text(
        f"SELECT {selected} FROM {table} WHERE {where} ORDER BY {name_column}"
    ))).all()


async def main(show_all: bool) -> int:
    await init_db()
    factory = get_session_factory()
    checked: dict[str, bool] = {}
    findings: list[tuple[str, str, str, str, str]] = []
    total = 0

    try:
        async with factory() as session, _artwork_client(10.0) as client:
            for label, table, id_column, name_column, columns in SOURCES:
                try:
                    rows = await _rows(session, table, id_column, name_column, columns)
                except Exception as exc:  # noqa: BLE001 -- a missing table is a finding
                    print(f"!! {label} ({table}): {exc}")
                    # Postgres refuses every later statement on a poisoned
                    # transaction, so one bad table would silently blank the
                    # rest of the report.
                    await session.rollback()
                    continue
                for row in rows:
                    name = str(row[1])
                    for column, raw in zip(columns, row[2:]):
                        value = str(raw or "").strip()
                        if not value:
                            continue
                        total += 1
                        url = instagram_card_image_url(value, fallback_name=name)
                        if url not in checked:
                            checked[url] = await _fetchable(client, url)
                        if checked[url]:
                            if show_all:
                                print(f"ok   {label:9s} {name} [{column}]")
                        else:
                            findings.append((label, str(row[0]), name, column, value))
    finally:
        await close_db()

    print(f"\n{total} artwork URLs across {len(SOURCES)} tables; "
          f"{len(checked)} distinct; {len(findings)} unfetchable.\n")
    for label, row_id, name, column, value in findings:
        print(f"BLANK {label:9s} {name}")
        print(f"      {column} = {value}")
        print(f"      id = {row_id}")
    if findings:
        print("\nThe bot substitutes its bundled card for each of these, so no "
              "customer sees a blank card — but re-uploading the artwork through "
              "the catalog media picker is what actually fixes them.")
    return 1 if findings else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true",
                        help="also print the artwork that fetches fine")
    sys.exit(asyncio.run(main(parser.parse_args().all)))
