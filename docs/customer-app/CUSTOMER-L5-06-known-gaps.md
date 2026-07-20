# CUSTOMER-L5-06 — Known Gaps

## P0

1. **No live runtime certification** — see `CUSTOMER-L5-06-runtime-evidence.md`.
   Identical constraint to every previous sprint's own P0 gap, but with an
   unusually consequential unknown attached: whether real draft creation
   actually succeeds for a real, customer-selected service has genuinely
   not been empirically proven (only reasoned about from source), because
   of finding #2 below.

## P1

2. **Draft creation is keyed to a different, disconnected catalog than the
   one CUSTOMER-L5-04's real service-discovery flow uses.** `offering_slug`
   must resolve against `admin_catalog.MasterService`; the app's real
   `ServiceDetailScreen` is built on `customer_flow.MasterOffering`. No
   migration, seed script, or FK anywhere in this codebase confirms these
   two tables' slugs ever coincide. This is the sprint's most consequential
   structural finding — see contract-matrix.md and draft-architecture.md.
   Closing it requires backend work (a real bridge between the two
   catalogs, or migrating one consumer to the other) that a frontend
   sprint cannot do on its own. This client handles the resulting failure
   honestly (a clear "not available for booking yet" error) rather than
   masking it.
3. **`issue_type_id` and `service_option_ids_json` cannot be synced from
   the CUSTOMER-L5-05 assistant into the draft** — both are real columns on
   `HomeServiceBookingDraft` but neither is in the `PUT` endpoint's
   accepted-field list. Only `brand_id`, `offering_type_id`
   (service-type, via CUSTOMER-L5-05's own documented naming assumption),
   and a synthesized `issue_summary` text field make it through. This is a
   real, disclosed backend gap, not a frontend oversight — see
   contract-matrix.md.
4. **No draft-linked photo can be removed or replaced once linked.** The
   real `/photos` endpoint is append-only (max 5, no delete/replace) — the
   underlying media asset *can* be deleted via the media engine's own
   endpoint, but that would leave a dangling, un-cleanable URL in the
   draft's `photo_urls` list. `BookingMediaScreen`'s delete action is real
   and does call the real endpoint, but this creates a real, disclosed
   inconsistency between "the media asset is gone" and "the draft still
   references it" — see media-architecture.md.
5. **No idempotency key on draft creation or photo upload** — a lost
   response after a successful server-side write can produce a duplicate
   draft (on a retried "start booking" tap) or a duplicate media asset (on
   a retried upload after the link step fails). Neither endpoint supports
   an idempotency key server-side to prevent this — see upload-lifecycle.md.
6. **No component/render tests** for the three new screens — same,
   now-consistent-across-six-sprints deprioritization pattern.

## P2

7. **Media is treated as fully optional** — no real, binding "photo
   required" gate was found for the `booking_issue_photo` context
   specifically (CUSTOMER-L5-05's `requires_photo_upload` flag is
   informational only, not enforced as a hard block in this sprint's UI).
8. **No client-side EXIF-removal verification** — `expo-image-manipulator`'s
   re-encoding almost certainly drops the original file's EXIF block, but
   this environment has no tooling to inspect the resulting binary's
   headers directly to prove it byte-for-byte.
9. **No temporary local file cleanup** — compressed/picked images are left
   in the OS-managed app cache directory rather than explicitly deleted
   after a successful upload (no `expo-file-system` dependency was added
   to manage this).
10. **No background/offline upload queue** — a failed upload requires the
    customer to manually retry while back online; there is no reliable
    queue infrastructure in this app to build a real one on top of, and
    none was fabricated (CUSTOMER-L5-06 §45, followed literally).
11. **`cancelDraft`'s local cleanup proceeds even if the backend call
    fails** — the customer is still navigated away and the local pointer
    still cleared, matching the existing "local protection wins" pattern
    already established for `logout` (CUSTOMER-L5-02), but it means a
    draft could remain non-terminal server-side while the app behaves as
    though it were discarded. Documented, not silently risked.
12. **No analytics events actually wired to a vendor** — same
    now-six-sprints-running gap: no analytics SDK is integrated in this
    app at all; `logger.*` calls are structured logs only.

## P3

13. **Upload progress is coarse-grained (discrete states), not a
    byte-level percentage** — React Native's `fetch` does not expose
    upload progress without a native XHR/`expo-file-system` uploader,
    neither of which this sprint added.
14. **No HEIC-to-JPEG special-case messaging** — the compression step
    always re-encodes to JPEG regardless of the source format, so a HEIC
    capture (rare in Expo's managed workflow, which defaults to JPEG
    output) would already be converted before validation ever sees it;
    this was not independently tested against an actual HEIC file in this
    environment.
