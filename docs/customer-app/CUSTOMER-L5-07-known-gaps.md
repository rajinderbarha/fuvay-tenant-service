# CUSTOMER-L5-07 — Known Gaps

## P0

1. **No live runtime certification** — see `CUSTOMER-L5-07-runtime-evidence.md`.
   Identical constraint to every previous sprint's own P0 gap.

## P1

2. **There is no real SLA/service-window selection feature anywhere in
   this backend.** Not a frontend gap — a genuine, structural absence
   confirmed by exhaustive grep (see `CUSTOMER-L5-07-sla-contract.md`).
   The only real, backend-accepted scheduling field is an unvalidated
   free-text `preferred_time_window` string, implemented honestly as such
   rather than as a fabricated multiple-choice selector. This is the
   sprint's most consequential finding.
3. **`_resolve_address_snapshot` performs no address-ownership check**
   server-side — a real, disclosed backend security gap (see
   security-review.md). This client never exploits or relies on the gap
   (it only ever supplies IDs from the customer's own address list), but
   cannot fix it from the frontend.
4. **No component/render tests** for the four new/changed screens — same,
   now-consistent-across-seven-sprints deprioritization pattern.
5. **Attaching an address to the draft has no dedicated error UI** —
   `AddressListScreen.handleSelect`'s failure path only logs
   `draft_save_conflict`; the customer sees no visible feedback beyond
   staying on the same screen. A toast or inline message would improve
   this but was judged lower priority than the core flow given this
   sprint's scope.

## P2

6. **No `preferred_date` collection this sprint** — only
   `preferred_time_window` (free text) is collected on
   `ServiceabilityScreen`; a real date picker for `preferred_date` (also a
   real, unvalidated draft field) was deferred to keep this sprint's
   already-large scope bounded. The field remains fully supported by the
   real `PUT` endpoint whenever a future pass adds a picker for it.
7. **`location_engine`'s public structured city/state/district/zone
   lookup endpoints are real but unused.** Manual free-text entry
   (matching the real `AddressCreate` schema's own field types exactly)
   was used instead of building a cascading picker UI against them, to
   keep this sprint's scope bounded. A future pass could offer both.
8. **No forward geocoding** (address text → coordinates) — no product
   need was identified without a backend consumer for the resulting
   coordinates, and none exists.
9. **`use-current-location.ts` has no dedicated unit tests** against a
   mocked `expo-location` — the module's logic is a thin, sequential
   wrapper with little independent branching to test in isolation; its
   correctness is implicitly exercised through `AddressFormScreen`'s own
   (untested-by-render, per P1 gap 4) usage.
10. **`available_provider_count` is parsed but never surfaced** in the
    UI — a deliberate product-judgment call (CUSTOMER-L5-07 §26), not an
    oversight, but worth flagging in case product later wants it exposed.
11. **No analytics events actually wired to a vendor** — same
    now-seven-sprints-running gap: no analytics SDK is integrated in this
    app at all; `logger.*` calls are structured logs only.

## P3

12. **No accuracy/low-accuracy-location handling distinct from a generic
    "unavailable" outcome** — `use-current-location.ts` does not
    distinguish a low-accuracy fix from a total failure; both surface as
    the same `"unavailable"` outcome. Low severity since the customer can
    always correct the prefilled fields manually regardless.
13. **No timezone-aware date/time formatting was built**, since no date
    picker exists yet (see gap 6) — deferred alongside it.
