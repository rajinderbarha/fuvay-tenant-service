# Known Limitations

1. **Office (tenant_owner/staff) unclaimed-asset access remains
   tenant-wide** — deliberately unmodified this slice. See
   `product-decisions-required.md` item 1.

2. **Claim relationship is a JSONB convention, not a first-class schema
   column** — no index, no referential integrity, no query support beyond
   direct key lookup. See `product-decisions-required.md` item 2.

3. **ServiceJob cancellation/completion does not time-box media access**
   — carried forward from 2F-18A/2F-18C, unchanged. See
   `product-decisions-required.md` item 3.

4. **Only the CURRENT two writers of `metadata_json` are hardened** — a
   future new writer would need to independently adopt the same
   claim-key-stripping discipline; there is no enforcement mechanism
   (e.g., a database trigger or check constraint) preventing a
   not-yet-written future writer from clobbering a claim. See
   `product-decisions-required.md` item 4.

5. **`_load`'s lifecycle filter (`status == "deleted"` only) remains
   narrower than attach-time validation** (carried forward from 2F-18C,
   unchanged this slice).

6. **`list_threads` for technicians still reflects participant snapshot,
   not live assignment** (carried forward from 2F-18A, unchanged).

7. **`require_staff_or_technician_only` has no access-scope (readonly)
   check** (carried forward, unchanged).

8. **No `ForeignKey()` DB constraints on any `platform_notifications`
   model** (carried forward, unchanged).

9. **Concurrency guarantees rely on real Postgres row locking, not
   independently verifiable with the mocked unit-test suite used in this
   environment** — `test_asset_lookup_uses_select_for_update` proves the
   QUERY is constructed correctly (contains `FOR UPDATE`); it does not
   (and cannot, without a live database) prove the lock actually
   serializes two real concurrent transactions. This is consistent with
   every prior slice's inability to exercise true concurrency without a
   live Postgres instance.

10. **Live-database integration tests could not be run in this
    environment** (no Postgres instance available) — same exclusion as
    every prior slice touching this module.
