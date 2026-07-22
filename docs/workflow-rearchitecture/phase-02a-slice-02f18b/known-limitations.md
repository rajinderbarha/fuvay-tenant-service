# Known Limitations

1. **Cross-Job/cross-conversation media lineage not enforceable** — no
   `job_id`/`thread_id`/`message_id` column exists on `MediaAsset`. See
   `product-decisions-required.md` item 1. This is the slice's single
   largest residual gap.

2. **Technician tenant-wide media view** — existing, reused
   `MediaAccessService` policy, broader than the thread-assignment policy.
   See `product-decisions-required.md` item 2.

3. **Media engine retrieval-path error codes are not privacy-equivalent**
   — pre-existing, general gap outside `platform_notifications`. See
   `attachment-download-read-authority.md`, `media-error-privacy-equivalence.md`,
   `product-decisions-required.md` item 3.

4. **Removed chat participants may retain generic media view authority**
   — two independent authorization systems (thread participation vs.
   media access) don't share revocation state. See
   `product-decisions-required.md` item 4.

5. **`staff_send_message` never forwards `media_ids`** — pre-existing,
   non-functional (not insecure) schema/router mismatch. See
   `product-decisions-required.md` item 5.

6. **`customer_router.py` has no media field at all** — customers cannot
   currently attach media via chat through any live route; this slice's
   fixes apply to the service-layer code path but are not exercisable via
   `customer_router.py` today.

7. **`access_level` column exists but is not consulted** by
   `MediaAccessService.assert_can_view` — set at upload time but not
   branched on anywhere in the current access-control logic. Not modified
   this slice (would be a change to `access.py`).

8. Carried forward, unchanged from 2F-18/2F-18A:
   - `require_staff_or_technician_only` has no access-scope (readonly) check.
   - No `ForeignKey()` DB constraints on any `platform_notifications` model.
   - `list_threads` reflects participant snapshot, not live technician
     assignment.
   - Completed/cancelled Job technician access does not time-box out.

9. **Live-database integration tests could not be run in this environment**
   (no Postgres instance available) — same exclusion as every prior slice
   touching this module.
