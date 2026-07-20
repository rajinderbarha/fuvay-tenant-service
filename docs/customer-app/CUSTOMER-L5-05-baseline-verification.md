# CUSTOMER-L5-05 — Baseline Verification

## Previous Sprint Verification

| Sprint | Claimed status | Verified status | Notes |
|---|---|---|---|
| CUSTOMER-L5-00 | Complete | Confirmed | No regressions. |
| CUSTOMER-L5-01 | Complete | Confirmed | Startup/navigation/remote-config intact. |
| CUSTOMER-L5-02 | PARTIAL (documented) | Confirmed PARTIAL, unchanged | Auth/session/refresh-coordinator real and working; live runtime proof still not possible in this environment. |
| CUSTOMER-L5-03 | PARTIAL (documented) | Confirmed PARTIAL, unchanged | Home loads real categories; module registry intact. |
| CUSTOMER-L5-04 | PARTIAL (documented) | Confirmed PARTIAL, unchanged | Category/service/search screens real and working against `customer_flow`/`MasterOffering` data; 370 tests passing at sprint start. |

- Authentication: confirmed working (session store, refresh coordinator unmodified since L5-02).
- Customer profile: loads via `useAuthSession`, unmodified.
- Home: loads real `/v1/customer/categories` data, confirmed by reading `home-queries.ts`.
- Category/service discovery: use stable IDs (branded `CategoryId`/`ServiceId`), confirmed in `route-types.ts`.
- Service detail: real backend data via `useServiceDetail`, confirmed in `service-detail-queries.ts`.
- Booking-assistant entry: `ServiceDetailScreen`'s "Book service" button already used typed navigation (`{ serviceId, categoryId }`) — confirmed, but landed on a **dev-only placeholder screen** (`BookingAssistantPlaceholderScreen`), not a real assistant.
- No fake price/provider data found anywhere in the existing booking-boundary code.
- Query cache scoping (locale/tenant), cross-customer clearing on logout, deep-link guards, error normalization, and redacted logging were all re-confirmed unmodified from CUSTOMER-L5-02/03/04.
- 370 tests passing at the start of this sprint (confirmed by running `npx jest` before any change).

## Existing Repository Findings

- **Existing assistant implementation**: `BookingAssistantPlaceholderScreen.tsx` — a static "coming soon" screen with no questions, no data fetching, no state. This is what this sprint replaces.
- **Existing diagnostic/questionnaire engine**: none in the frontend.
- **Existing branching**: none.
- **Existing state management for a multi-step flow**: none — no prior sprint built a multi-step wizard/state-machine pattern in this app.
- **Placeholder assistant behavior found**: the entire `BookingAssistant` route was `productionEnabled: false` (CUSTOMER-L5-04), gated to development builds only, with `evaluateBookingBoundary()` deliberately blocking it in production since "CUSTOMER-L5-05 doesn't exist yet" (verbatim from that function's own doc comment).

## Backend Contract Mismatches Found — the Central Finding of This Sprint

A dedicated backend research pass (see `CUSTOMER-L5-05-contract-matrix.md` for full detail) found, by direct reading of `app/engines/*`:

**There is no stateful diagnostic-workflow engine anywhere in this backend.** No model named `DiagnosticQuestion`, `WorkflowSession`, `CustomerAnswer`, or `BranchingRule` exists. No endpoint returns "the next question" given prior answers. No endpoint tracks a `session_id` + `current_question` + `status` for a structured questionnaire. The closest things that exist are:

1. **Flat, stateless catalog endpoints** — `GET /v1/customer/catalog/issue-types` and `GET /v1/customer/catalog/service-options` (`admin_catalog/service_option_customer_router.py`, tagged "Customer Service Diagnostics") — independent lists, filterable by `category_id`/`master_service_id`, each carrying only two real conditional flags (`requires_photo`, `requires_description` on an issue type) as the *only* genuine branching signal in the entire backend.
2. **A second, ID-mismatched catalog** (`GET /v1/catalog/master/brands`, `/service-types`) — also flat, also category-scoped.
3. **A real, auth-required, linear booking-draft entity** (`home_service_booking/customer_router.py`, `POST /v1/customer/home-services/booking-drafts`) that a customer app *could* eventually `PUT` collected diagnostic values onto — but building against this durable draft object is explicitly CUSTOMER-L5-06's scope, not this sprint's, per the prompt's own exclusion list ("Do not implement durable booking-draft persistence").

**A second, equally important mismatch**: the diagnostic catalog endpoints are scoped by `category_id`/`master_service_id` (the `admin_catalog` engine's `MasterService`/`ServiceCategory` tables), while CUSTOMER-L5-04's real, working `ServiceDetailScreen` is built entirely around `MasterOffering` (the `customer_flow` engine's own, unrelated table — confirmed no FK between `MasterOffering` and `MasterService` anywhere in `admin_catalog/models.py`). The only ID the two catalogs share is `category_id`. This means the assistant can fetch category-scoped diagnostic data for the category a service belongs to, but **cannot** fetch data scoped precisely to the specific offering the customer is booking — a real, structural gap, not an implementation oversight.

## Blockers

None preventing implementation of an honestly-scoped sprint. The blocker is scope-shaping, not scope-blocking: this sprint cannot deliver the spec's aspirational "dynamic, backend-branching, multi-type diagnostic workflow with session ID and version binding" because that engine does not exist. What it can honestly deliver — and does — is a client-side-sequenced, in-memory-only assistant over real, backend-served catalog data (issue types, service options, brands), with the one real conditional-branching signal the backend actually provides (`requires_photo`/`requires_description`), landing on a typed, dev-only completion boundary for CUSTOMER-L5-06 to build on.

## Corrections Completed

- None required to prior sprints' code — CUSTOMER-L5-04's booking-boundary architecture (`evaluateBookingBoundary`, dev-only `BookingAssistant` route) was already correctly built to be replaced by this sprint, not reworked.

## Deferred Issues

See `CUSTOMER-L5-05-known-gaps.md`.
