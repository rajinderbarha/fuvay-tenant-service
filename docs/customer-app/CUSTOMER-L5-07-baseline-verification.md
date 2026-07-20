# CUSTOMER-L5-07 — Baseline Verification

## Previous Sprint Verification

| Sprint | Claimed status | Verified status | Notes |
|---|---|---|---|
| CUSTOMER-L5-00 through L5-06 | PARTIAL (documented) | Confirmed PARTIAL, unchanged | No regressions; 489 tests passing at sprint start. |

1. Authentication: confirmed working, unmodified since L5-02.
2. Current customer loads: confirmed.
3. Real service/workflow IDs retained: confirmed (branded IDs throughout).
4. Real booking draft exists: confirmed — `HomeServiceBookingDraft`, real CRUD (L5-06).
5. Draft restoration: confirmed working (local pointer + backend re-fetch).
6. Draft versioning: **confirmed absent** — no version/revision column exists (L5-06's own finding, re-verified, unchanged).
7. Required media backend-confirmed: N/A — media in this app is optional (L5-06 finding).
8. Address boundary exists: confirmed — `AddressSelectionPlaceholderScreen`, explicit dev-only placeholder naming this sprint as owner.
9. Marketplace/tenant context: confirmed present in query keys defensively; real endpoints carry no marketplace concept (unchanged finding).
10. Query caches customer/context scoped: confirmed.
11. Logout/account switch clear sensitive draft state: confirmed (L5-06).
12. Connectivity state: confirmed (`OfflineBanner`).
13. Existing location/map libraries: `expo-location` (~18.1.5) and `react-native-maps` (^1.20.1) are installed but **completely unused anywhere in `src`** — confirmed by repo-wide grep. This sprint is their first real use.
14. Existing address models: **two conflicting implementations found** — see Repository Findings below.
15. Existing serviceability endpoints: real, but the app has never called any of them.
16. Existing SLA endpoints: **none exist** — see Real Backend Contract below, the sprint's central finding.
17. Analytics/logging redaction: confirmed unmodified pattern.
18. Existing tests pass: confirmed — 489/489 at sprint start.
19. Production mock serviceability: none found in the real feature code (see #14 for a legacy exception).
20. Working tree: understood — unrelated changes in other engines/frontends from parallel work streams, none touched.

## Repository Findings

- **Existing address implementation — legacy, dead-end**: `src/screens/AddressBookScreen.tsx` + `src/lib/api.ts`'s `addressApi` target a **nonexistent backend path** (`/v1/commerce/customers/{cid}/addresses`) with a field shape (`label`, `address_line`, `pincode`, `lat`, `lng`) that does not match the real `CustomerAddress` model at all (missing `state`, wrong field names, no `address_line_1`/`_2` split). This is pre-existing legacy code (part of the `LegacyAppNavigator` stack, predating CUSTOMER-L5-00) — left untouched, matching every previous sprint's established boundary of not modifying the 19-screen legacy stack. This sprint builds a new, real address feature under `features/address/` instead of reusing or fixing the legacy one.
- **Existing address implementation — real, already scaffolded**: `features/booking-draft/domain/draft-schema.ts` (CUSTOMER-L5-06) already models `address_id`, `city`, `zipcode`, `serviceability_status`, `preferred_date`, `preferred_time_window`, and the `"serviceability_checked"` draft status — all correctly mirroring the real backend, confirming L5-06 anticipated this sprint accurately.
- **Existing location permission flow**: none.
- **Existing map integration**: none (`react-native-maps` unused).
- **Existing serviceability implementation**: none in the app; real backend capability never called.
- **Existing zone/zipcode logic**: none in the app.
- **Existing SLA implementation**: none in the app or backend (see below).
- **Placeholder behavior found**: `AddressSelectionPlaceholderScreen` — static dev-only placeholder, explicitly naming this sprint as successor.
- **Duplicate implementations**: the legacy `addressApi`/`AddressBookScreen` vs. this sprint's new, real implementation — not reconciled (legacy is unreachable from the real, production `MainNavigator` stack this app actually uses for the booking flow, so there is no runtime collision, only source-level duplication left as pre-existing debt).

## Real Backend Contract — Central Findings

1. **Real, complete customer address CRUD exists** (`app/engines/serviceability/router.py`, prefix `/v1/customers/me/addresses`) — list/create/get/update/delete(soft)/set-default, backed by a real `CustomerAddress` model with genuine ownership enforcement and automatic default-address management (first address auto-defaults; deleting the default promotes the next one). Verified real, complete, and directly usable.
2. **The booking-draft's serviceability check is a separate, simpler, *correctly ID-scoped* local check** (`HomeServiceServiceabilityService.check`, called from `POST /{draftId}/serviceability-check`) — matches `category_id`/`offering_id` (the same `MasterService`-space IDs the draft already uses, so no cross-catalog mismatch here, unlike L5-06's draft-creation finding) against real `TenantServiceArea`/`TenantServiceAreaService` coverage rows, by exact zipcode then falling back to city. Returns a simple `{serviceable, available_provider_count, matched_by, message, reason_code}` — not the aspirational multi-state enum.
3. **A separate, richer general serviceability engine exists (`/v1/serviceability/*`) but is never used by the booking-draft flow** — it is keyed to yet a *third*, disconnected catalog (`service_catalog.ServiceCatalogItem`, tenant-scoped, unrelated to both `MasterOffering` and `MasterService`). Deliberately not adopted this sprint, matching L5-06's precedent of not creating a parallel coverage model.
4. **No geocoding capability exists anywhere in the backend** — confirmed by an exhaustive grep. Any "current location" feature can only ever produce a customer-editable prefill via the *device's own* OS-level reverse geocoding (`expo-location`'s `reverseGeocodeAsync`), never a backend-confirmed address.
5. **Zone and city-tier concepts exist as real, admin-managed master data** (`location_engine` and `geo` engines) but are **not wired to the booking-draft flow at all** — the draft's real serviceability check never resolves or returns a zone or city tier. Not fabricated for this sprint.
6. **There is no real SLA/service-window selection feature.** `TenantServiceAreaService.sla_minutes` is an unused admin-only integer never exposed to any customer-facing endpoint. The draft's only time-related field is `preferred_time_window` — an **unvalidated free-text string**, with no backend-defined option set, enum, or endpoint anywhere. This is the sprint's most consequential finding, on par with L5-05's "no diagnostic workflow engine" and L5-06's "no draft versioning" — the aspirational SLA-options UI is not built (see known-gaps.md).
7. **`_resolve_address_snapshot` has no address-ownership check** — a genuine, disclosed backend gap (copies any `address_id`'s fields into the draft snapshot without verifying it belongs to the requesting customer). Not fixable from this frontend sprint; documented in security-review.md.

## Blockers

None preventing implementation of an honestly-scoped sprint.

## Corrections Completed

None to prior sprints' code.

## Deferred Issues

See `CUSTOMER-L5-07-known-gaps.md`.
