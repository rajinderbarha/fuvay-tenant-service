# CUSTOMER-L5-05 — Known Gaps

## P0

1. **No live runtime certification** — see `CUSTOMER-L5-05-runtime-evidence.md`.
   Identical constraint to every previous sprint's own P0 gap. The primary
   reason this sprint's gate is PARTIAL.

## P1

2. **No backend answer-validation, next-question, or branch-recalculation
   capability exists at all** — not a gap this sprint failed to close, but a
   structural absence in the backend itself (see contract-matrix.md). Every
   "backend validates the answer" / "backend returns the next question" /
   "backend recalculates the branch" requirement in the original sprint
   prompt describes an operation this codebase has no endpoint for. This is
   the single most consequential finding of the sprint and shapes
   everything else in this list.
3. **Diagnostic catalog data is category-scoped, not service-scoped.** The
   real endpoints (`issue-types`, `service-options`, `brands`,
   `service-types`) filter by `category_id`; the app's real, working
   `ServiceDetailScreen` (CUSTOMER-L5-04) is built around `MasterOffering`,
   which has no relationship to the `MasterService`/`category_id`-keyed
   catalog rows these endpoints ultimately serve. A customer booking one
   specific offering may see issue types, options, or brands that were
   configured for a *different* service in the same category. Not
   fabricated data — genuinely real, admin-configured catalog rows — just
   coarser precision than an ideal offering-scoped catalog would give.
   Closing this gap requires backend work (a real FK between
   `MasterOffering` and `MasterService`, or a service-scoped diagnostics
   endpoint keyed to the offering ID space) — out of scope for a frontend
   sprint.
4. **`requires_type` → service-types-catalog mapping is a documented
   assumption, not a confirmed link.** CUSTOMER-L5-04's `required_fields.requires_type`
   flag (from `MasterOffering.is_type_required`) is used to gate the
   `service_type` step, and that step's *options* come from
   `/v1/catalog/master/service-types` (an unrelated `ServiceType`/
   `MasterService` table). No FK or shared identifier confirms these two
   concepts are actually "the same kind of type" for a given offering —
   this is the most defensible real-data mapping available, but it is an
   inference, stated as such.
5. **No client-side rules exist for multi-select min/max/mutual-exclusion**
   (CUSTOMER-L5-05 §19) — `MasterServiceOption` has no such columns to
   enforce (see contract-matrix.md), so `MultiSelectRenderer` allows any
   combination of the fetched options with no constraint checking. Not an
   oversight; there is nothing real to check.
6. **No offline handling was added to `BookingAssistantScreen`** — unlike
   `CategoryDetailScreen`/`SearchScreen` (CUSTOMER-L5-04), this screen does
   not render the shared `OfflineBanner`. A catalog-load failure while
   offline surfaces through the same generic error state as any other
   failure, without a distinct "you're offline" message.
7. **No component/render tests** for the two new screens or four renderer
   components — same, now-consistent-across-five-sprints deprioritization
   pattern documented in test-evidence.md.

## P2

8. **Tampering resistance is UI-level only, not cryptographic.** `submitAnswer`'s
   `stepId`-match guard and the "options only come from the fetched list"
   pattern prevent accidental corruption and casual tampering, but since no
   backend endpoint validates a submitted answer at all, a sufficiently
   determined client could submit anything through a modified build. This
   is an accepted, disclosed limitation of an architecture with no backend
   answer-validation surface (see gap 2) — not something a frontend-only
   sprint can close.
9. **`AUTH_REQUIRED` booking-boundary outcome remains architecturally
   unreachable in practice** — `bookingAssistant`'s own route access
   (`"authenticated"`) already prevents an unauthenticated customer from
   reaching `BookingAssistantScreen` at all. Same defensive-completeness
   rationale as CUSTOMER-L5-03's and CUSTOMER-L5-04's identical notes for
   their own unreachable states.
10. **No analytics events actually wired to a vendor** — same
    now-five-sprints-running gap: no analytics SDK is integrated in this
    app at all; `logger.*` calls are structured logs only.
11. **`BookingAssistant`'s pre-existing `featureKey: "booking-assistant"`
    gate was unreachable** (no matching remote-config module defined
    anywhere) — the identical bug pattern CUSTOMER-L5-04 found and fixed
    for `serviceDetails`'s `"service-discovery"` gate. Fixed this sprint by
    removing the module gate and using `access: "authenticated"` directly,
    consistent with `home`/`categoryDetail`/`serviceDetails`/`search`'s own
    precedent for core, always-on functionality.

## P3

12. **Multi-select options have no images/icons** even though the design
    allows for them conceptually — `MasterServiceOption`'s customer-facing
    shape has no icon field, so `MultiSelectRenderer` is text-only. Not
    fabricated.
13. **Brand logos are rendered nowhere in this sprint's UI** — `ValidatedBrand.logo_url`
    is parsed and validated but `SingleSelectRenderer` (used for the brand
    step) only ever renders `label`, not an image; adding brand-logo
    rendering would require extending `SingleSelectOption` with an
    `imageUrl` field, deferred as a minor, real, low-priority polish item.
