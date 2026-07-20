# Known Limitations

1. **Unclaimed `chat_attachment` assets remain tenant-wide viewable** —
   before first successful attach, no thread claim exists to check
   against. See `product-decisions-required.md` item 1.

2. **`_load`'s lifecycle filter (`status == "deleted"` only) is narrower
   than attach-time validation (`status != "active"`)** — a quarantined
   (but not literally `"deleted"`) `chat_attachment` asset is rejected at
   attach time but not necessarily at retrieval time. See
   `product-decisions-required.md` item 2.

3. **Thread-claim lock is a JSONB convention, not a first-class schema
   relationship** — no index, no referential integrity, no query
   support beyond direct key lookup. Functionally correct for this
   slice's authorization purpose but not queryable/reportable the way a
   real column would be. See `product-decisions-required.md` item 3.

4. **Non-`chat_attachment` media contexts remain retrieval-privacy-unfixed**
   — this slice's fix is deliberately scoped narrow. See
   `product-decisions-required.md` item 4.

5. **Participant-removal revocation only applies to `chat_attachment`
   assets via chat threads** — no other context is affected (none other
   is currently reachable from chat, so not a live gap today). See
   `product-decisions-required.md` item 5.

6. **`list_threads` for technicians still reflects participant snapshot,
   not live assignment** (carried forward from 2F-18A, unchanged) — a
   technician's THREAD list may not include a thread they could actually
   access directly; this slice's retrieval fix does not change that
   listing behavior.

7. **`require_staff_or_technician_only` has no access-scope (readonly)
   check** (carried forward, unchanged).

8. **No `ForeignKey()` DB constraints on any `platform_notifications`
   model** (carried forward, unchanged).

9. **Live-database integration tests could not be run in this
   environment** (no Postgres instance available) — same exclusion as
   every prior slice touching this module.
