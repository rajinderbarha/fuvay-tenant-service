# Backend Contract Handoff

Consolidated from diagnostic work done across UX-06/UX-07. No backend code
is changed in UX-08 — these are handoff tickets for a separate backend
remediation phase.

## OFFERING_TYPE_REQUIRED_FIELD

- **Endpoint**: pricing resolution path used by `match_provider_and_price()`
  (`app/engines/home_service_booking/service.py`) and the tenant catalog/
  pricing admin surfaces.
- **Backend module**: `app/engines/admin_catalog` (`master_services`,
  `ServicePricingRule`).
- **Problem**: `master_services.is_type_required = False` for `ac_repair`
  despite 100% of its `ServicePricingRule` rows being type-scoped — a
  catalog data/contract inconsistency, not a code bug.
- **Frontend screen**: Customer category/offering selection, SmartBot
  guided flow.
- **Expected behavior**: `is_type_required` should accurately reflect
  whether pricing resolution actually requires `offering_type_id` for a
  given master service.
- **Actual behavior**: flag says "not required" while pricing rules are
  100% type-scoped for this service.
- **Risk**: low today — frontend already defensively requires the field
  for `ac_repair` — but the contract mismatch could silently break pricing
  for a newly added type-scoped service that doesn't get the same
  defensive frontend treatment.
- **Required backend decision**: correct the catalog data or the contract
  documentation so `is_type_required` is trustworthy going forward.
- **Frontend safe-state requirement**: none needed beyond the existing
  defensive requirement already in place.

## REVIEW_VALIDATION_500

- **Endpoint**: `POST /v1/customer/reviews`
- **Backend module**: `app/engines/customer_reviews/customer_router.py`
  (confirmed via read-only inspection during UX-07 Round 3).
- **Reproduction**: malformed requests (missing rating, invalid rating
  range, wrong field type, missing/invalid booking reference, unknown
  booking, cross-tenant/cross-customer reference, duplicate submission)
  produce a raw `500` instead of a controlled `4xx`.
- **Expected behavior**: `422` for schema-shape violations, `400`/`404` for
  invalid/unknown references, `409` for duplicate submission.
- **Actual behavior**: an unguarded dict-access / exception path surfaces
  as a raw `500` for at least the malformed-input cases exercised.
- **Risk**: low for normal customers (frontend validates before submit,
  so a normal user cannot trigger this), but a real API-robustness gap —
  any other client (future mobile version, integration, or malicious
  actor probing the endpoint) can trigger an unhandled exception.
- **Required backend decision**: add proper request validation and
  exception mapping to the correct 4xx status per case.
- **Required tests**: one test per malformed-input case listed above,
  asserting the correct 4xx, not 500.
- **Frontend safe-state requirement** (already met): frontend validates
  rating/required fields before submit, preserves entered text on
  failure, shows a professional error with no stack trace — this does
  NOT make the backend defect acceptable, it only means normal customers
  can't trigger it through the app.

## QUOTE_CHECKLIST_INTEGRATION

- **Frontend screens**: Staff/Technician quote and checklist screens;
  Customer `QuoteApprovalScreen`.
- **Problem**: real backend endpoints exist for some quote operations
  (`GET/POST /v1/customer/quotes/*`), confirmed live-wired on the customer
  side during UX-07 Pass 3b; checklist completion is less consistently
  backend-wired across the technician flow.
- **Required backend decision**: confirm and complete the checklist
  completion contract end-to-end (technician submits → tenant/customer
  sees real state), matching the pattern the quote endpoints already
  provide.
- **Frontend safe-state requirement** (already met): fixture-only UI is
  not presented as working production functionality per the UX-07 Pass 3b
  screen-disposition audit.

## TECHNICIAN_PARTS_CREATION

- **Frontend screen**: Staff/Technician parts-request flow.
- **Problem**: technician-side parts-request *creation* is not fully
  supported end-to-end in the active application flow; viewing and
  tenant/provider approval-or-rejection is more consistently wired.
- **Required backend decision**: confirm whether a real creation endpoint
  exists; if not, build it; if it exists but isn't reachable from the
  technician app, wire it.
- **Canonical permission to preserve**: technician must never be able to
  mark parts as installed — only tenant/provider records installation.
  This constraint held throughout UX-05/07 and must not regress.

## CUSTOMER_CANCELLATION_RESCHEDULING

- **Frontend screens**: Customer booking detail / booking list.
- **Problem**: no connected capability exists for the canonical
  `ServiceBooking`/`ServiceJob` flow — this was never built, by design,
  across UX-06 and UX-07.
- **Required product/backend decision**: define the cancellation/
  rescheduling policy (cutoff windows, fee handling, technician
  notification) before any endpoint or UI work begins.
- **Frontend safe-state requirement** (already met): no fake cancel/
  reschedule action is shown anywhere in the app.
