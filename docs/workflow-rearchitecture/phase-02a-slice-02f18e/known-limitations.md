# Known Limitations

1. **Office first-use rule uses a static `thread.customer_id is not None`
   gate** — no mechanism exists to change a thread's customer linkage
   after creation (confirmed absent), so this is not currently exploitable,
   but flagged for awareness. See `product-decisions-required.md` item 1.

2. **`replace_asset` authorization uses coarse role+access-scope, not a
   granular per-asset permission** — see `product-decisions-required.md`
   items 2-3.

3. **True concurrent-transaction behavior is not independently verified
   without a live Postgres instance** — this slice adds deterministic
   unit-level proof of the CODE's correctness (lock request, no
   intermediate commit, no swallowed failures) but cannot prove Postgres
   itself correctly serializes two real concurrent transactions in THIS
   environment. See `product-decisions-required.md` item 4.

4. **`_load`'s base lifecycle filter (`status == "deleted"` only) remains
   unchanged for non-`chat_attachment` contexts** — this slice's stricter
   `status != "active"` check is scoped to `chat_attachment` only,
   consistent with every prior slice's narrow-scope mandate.

5. **Office (tenant_owner/staff) UNCLAIMED-asset VIEW access (not
   first-use claim) remains tenant-wide** — this slice narrowed
   first-use CLAIMING specifically; merely viewing an unclaimed asset's
   metadata (without attaching it to anything) is unaffected, consistent
   with the ratified, unmodified office-viewing policy since 2F-18B.

6. **Carried forward, unchanged from 2F-18/2F-18A/2F-18B/2F-18C/2F-18D**:
   - `require_staff_or_technician_only` has no access-scope (readonly) check.
   - No `ForeignKey()` DB constraints on any `platform_notifications` model.
   - `list_threads` reflects participant snapshot, not live technician
     assignment.
   - Completed/cancelled Job technician access does not time-box out.
   - Cross-Job/cross-conversation media lineage relies on the
     `metadata_json` convention, not a first-class schema column.

7. **Live-database integration tests could not be run in this
   environment** (no Postgres instance available) — same exclusion as
   every prior slice touching this module.
