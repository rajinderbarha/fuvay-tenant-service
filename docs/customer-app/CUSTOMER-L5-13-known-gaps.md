# CUSTOMER-L5-13 — Known Gaps

## P0

1. **No live runtime certification** — see `CUSTOMER-L5-13-runtime-evidence.md`.
   Identical constraint to every previous sprint's own P0 gap.

## P1

2. **No customer-facing technician profile exists anywhere** —
   `ProviderTeamMember.full_name`/`profile_photo_url`/`skills` are real DB
   columns with zero customer-facing endpoints exposing them. No
   verification status, badges, experience, or languages fields exist at
   all. See `technician-profile-contract.md` — this is the sprint's most
   consequential finding.
3. **No live GPS location, map, ETA, or route capability exists for this
   pipeline** — a real GPS table and a crude ETA heuristic exist in the
   codebase (`app/engines/geo/`) but are architecturally orphaned from
   the real customer booking pipeline, feeding only a separate, legacy,
   disabled-by-default dispatch stack instead. See
   `tracking-architecture.md`/`location-event-contract.md`/
   `eta-and-route-contract.md`.
4. **No real-time transport (websocket/SSE) exists anywhere** in this
   FastAPI application — confirmed by direct inspection of `app/main.py`
   (only an aspirational doc-comment, no actual route).
5. **No masked-call/in-app contact system exists anywhere** — see
   `contact-policy.md`.
6. **A real, computed per-technician rating aggregate
   (`StaffRatingSummary`) exists but is never exposed to customers** — a
   real backend gap (computed, not surfaced), not an absence of
   computation. See `technician-profile-contract.md`.
7. **The execution-tracking endpoint's `notes` field (both top-level and
   per-event) is not filtered by any customer-visibility flag
   server-side** — a real, disclosed backend gap this client mitigates by
   never parsing or rendering `notes` at all. See
   `privacy-and-security-review.md`.
8. **No component/render tests** for `ServiceTrackingScreen` — same,
   now-consistent-across-thirteen-sprints deprioritization pattern.

## P2

9. **`react-native-maps` remains an installed, unused dependency** —
   confirmed present in `package.json` since before this sprint, with no
   coordinate data anywhere in the real pipeline to render. Not removed
   this sprint (out of scope to modify dependencies), but flagged for
   awareness — a future sprint that wires up the orphaned `geo` engine to
   this pipeline would finally have a real use for it.
10. **No analytics events actually wired to a vendor** — same
    now-thirteen-sprints-running gap: no analytics SDK is integrated in
    this app at all; `logger.*` calls are structured logs only.
11. **`service-tracking-api.ts`/hook composition files have no dedicated
    unit tests** — consistent with the established, repo-wide pattern for
    thin API wrappers and hook-composition layers.
12. **This client's own client-authored execution-event labels
    (`execution-event-labels.ts`) have not been reviewed against real
    product copy guidelines** — written directly by this sprint based on
    the real, confirmed event semantics, but not validated against any
    existing product-copy style guide (none was found in the repo for
    this specific screen).

## P3

13. **Punjabi/Hindi translations of the new `serviceTracking.*`/
    `bookings.status.*` keys were written by this sprint and have not
    been reviewed by a native-speaking product reviewer** — same
    disclosed caveat pattern as every previous sprint's localization
    additions.
14. **No genuine multi-event, real-time-ordered execution timeline test
    was performed against a live backend** — see `runtime-evidence.md`.
15. **The `diagnosis_added`/`before_photo_uploaded`/`after_photo_uploaded`/
    `work_note_added` real event types are confirmed but deliberately
    unmapped** — they represent execution detail (notes/media) a future
    sprint could build a dedicated, properly-filtered notes/media gallery
    around (once the backend's own `notes` customer-visibility filtering
    gap, #7 above, is fixed) — not this sprint's milestone-timeline scope.
