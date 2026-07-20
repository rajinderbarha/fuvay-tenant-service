# CUSTOMER-L5-06 — Baseline Verification

## Previous Sprint Verification

| Sprint | Claimed status | Verified status | Notes |
|---|---|---|---|
| CUSTOMER-L5-00 through L5-04 | PARTIAL (documented) | Confirmed PARTIAL, unchanged | No regressions; 425 tests passing at sprint start. |
| CUSTOMER-L5-05 | PARTIAL (documented) | Confirmed PARTIAL, unchanged | Assistant collects real issue-type/service-option/brand answers client-side, in-memory only; completion boundary (`DiagnosticCompletionScreen`) was an explicit dev-only placeholder with a doc comment naming this sprint as its successor. |

1. Authentication: confirmed working, unmodified since CUSTOMER-L5-02.
2. Current customer loads: confirmed via `useAuthSession`.
3. Service discovery stable IDs: confirmed (`CategoryId`/`ServiceId` branded types).
4. Assistant initialization: confirmed real (category-scoped catalog fetches, CUSTOMER-L5-05).
5. Real diagnostic answers submitted: confirmed — collected in-memory via the CUSTOMER-L5-05 state machine, never fabricated.
6. Workflow IDs/versions retained: **not applicable** — CUSTOMER-L5-05 already established there is no backend workflow/session engine to retain an ID or version for.
7. Completion boundary exists: confirmed (`DiagnosticCompletionScreen`, dev-only, `productionEnabled: false`).
8. No hardcoded production workflow: confirmed by re-reading `assistant-steps.ts`.
9. Marketplace/tenant scoping: confirmed present in query keys (locale/tenant), though the real endpoints used have no marketplace concept (unchanged finding from L5-04/05).
10. Assistant state clears on logout/account switch: confirmed — CUSTOMER-L5-05's session lives in component `useState`, unmounted with the screen; no persistent cache to clear.
11. Secure storage adapter: confirmed (`secure-storage.ts`, `expo-secure-store`), used for tokens only.
12. API client supports authenticated uploads or signed-upload workflows: **not yet** — `apiClient` (`api-client.ts`) only supports JSON bodies via `fetch`; no multipart/FormData support exists in the customer app before this sprint.
13. Connectivity state: confirmed (`OfflineBanner`, `useConnectivity`).
14. Error normalization: confirmed (`api-errors.ts`, unmodified).
15. Analytics/logging redaction: confirmed unmodified pattern from every previous sprint.
16. Existing tests pass: confirmed — 425/425 passing before this sprint's changes.
17. Production mock booking flows: none found.
18. Working tree: understood — unrelated changes in other engines/frontends from parallel work streams, none touched by this sprint.

## Existing Implementation Found

- **Booking-draft implementation**: none in the mobile app. `DiagnosticCompletionScreen.tsx` was a static dev-only placeholder with no data fetching, explicitly documenting itself as awaiting this sprint.
- **Upload implementation**: none. No file in `mobile/customer-app/src` references `expo-image-picker`, any media endpoint, or any booking-draft endpoint prior to this sprint (confirmed by repo-wide grep).
- **Media picker**: not wired up. `expo-image-picker` is installed (`package.json`) but unused.
- **Local persistence for a draft**: none.
- **Resume behavior**: none.

## Real Backend Contract Discovered — the Central Findings of This Sprint

1. **A real, working, auth-required booking-draft API exists** (`app/engines/home_service_booking/customer_router.py`, `HomeServiceBookingDraft` model) — create, get, update, cancel, and an append-only photo-linking endpoint. No version/revision/ETag column exists anywhere on the model — optimistic concurrency is genuinely not supported server-side, not merely unbuilt client-side.
2. **A real, working, direct-multipart media upload engine exists** (`app/engines/media/new_router.py`, `MediaAsset` model, "Phase 0A" — the authoritative table). No signed-URL flow is used by it (a separate, older, effectively-placeholder signed-URL flow exists in `app/engines/media/router.py` but is not used by anything this sprint touches — see contract-matrix.md). `booking_issue_photo` is a real, already-access-controlled media context that has never been called by any router in this codebase before this sprint.
3. **Draft creation is keyed to `MasterService` (the `admin_catalog` engine), not `MasterOffering` (the `customer_flow` engine that CUSTOMER-L5-04's real `ServiceDetailScreen` is built on).** This is the same cross-engine ID-space mismatch CUSTOMER-L5-04 and CUSTOMER-L5-05 already documented for the discovery/diagnostic catalogs — here it is more consequential, because it means **draft creation itself may fail** for a service the customer selected through the app's real, working discovery flow, since there is no confirmed slug/ID bridge between the two tables. This is handled honestly (attempted with the real `category_slug`/`offering_slug` the app has, with a clear, non-crashing error state if the backend rejects it) rather than worked around with a fabricated bridge.
4. **The draft's `PUT` endpoint does not accept `issue_type_id` or `service_option_ids_json`**, despite both being real columns on the model — only `brand_id`, `offering_type_id`, and free-text fields (`issue_summary`, etc.) are in its accepted-field allowlist. This means CUSTOMER-L5-05's issue-type and service-option answers cannot be synced into the draft via any endpoint that exists today; only the brand answer (and, via a documented naming assumption carried over from CUSTOMER-L5-05, the service-type answer → `offering_type_id`) can be. `issue_description`/`customer_note` answers map cleanly onto the draft's genuine `issue_summary` text field.

## Blockers

None preventing implementation of an honestly-scoped sprint — see corrections/deferred issues below and `CUSTOMER-L5-06-known-gaps.md`.

## Corrections Completed

None to prior sprints' code — CUSTOMER-L5-05's completion boundary was already correctly built as a placeholder awaiting this exact sprint.

## Deferred Issues

See `CUSTOMER-L5-06-known-gaps.md`.
