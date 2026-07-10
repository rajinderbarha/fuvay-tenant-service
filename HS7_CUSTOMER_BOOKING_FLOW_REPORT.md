# HS7 — Customer Home Services Booking Flow Report

## Scope of this pass
HS7's backend flow (`app/engines/home_service_booking/*`) already existed
from Sprint 16 and was extended/certified in HS6/HS6B, but had **never
actually been exercised end-to-end against the real database** — every
prior sprint's live verification used direct pure-function calls or
partial curl chains. Running the full 8-step flow for real, for the
first time, surfaced 6 real, confirmed, previously-undetected bugs that
made the flow completely non-functional. All are fixed and live-verified
in this pass (see `HS7_LIVE_BOOKING_VERIFICATION_REPORT.md`).

## Bugs found and fixed

1. **`start_booking_draft` (Step 1) queried an empty legacy table.**
   `MasterOffering` — the table `start_booking_draft`, `_get_offering`,
   `_compute_price_snapshot`, and `_enrich_draft` all resolved offerings
   against — has **0 rows** in the real database. Every real Home
   Services catalog surface (admin catalog, `/v1/catalog/master/services`,
   HS6/HS6B provider-first matching/pricing) uses `MasterService`
   instead. This meant **the very first step of the customer booking
   flow could never succeed for any real service.** Fixed by switching
   all 5 call sites in `service.py` and `serviceability_service.py` to
   `MasterService`, with field-name mapping (`name`→`service_name`,
   `requires_slot`→`requires_schedule`, `default_*`→bare names).

2. **`check_serviceability` (Step 3) filtered by an unpopulated column.**
   `Tenant.category_id` is `NULL` for every real tenant in the dev
   database — this isn't how tenant↔category association actually works
   anywhere else in the codebase. The check always returned "not
   serviceable," even for a zipcode the provider genuinely covers per
   HS5B's canonical `tenant_service_area_services` table. Fixed to join
   that canonical table instead, scoped by the actual offering being
   booked — consistent with what HS6B's matching engine will find a step
   later.

3. **4 tables missing the `updated_at` column** their ORM models declare
   via `TimestampMixin`: `home_service_booking_draft_events`,
   `customer_booking_confirmations`, `final_creation_audit_logs`,
   `service_job_assignment_events`. Every INSERT into these — draft
   creation, price-choice, booking confirmation, and tracking-timeline
   reads — raised `UndefinedColumnError`. Fixed via migrations 122-125.
   (A broader scan found ~20 more event/audit/log tables across the
   codebase with the same gap, outside Home Services scope — documented
   in Remaining Blockers, not fixed here.)

4. **`mark_ready_for_confirmation` was dead code.** Defined but never
   called from any router (same for Coaching/RealEstate's equivalents).
   The customer-facing `/confirm` endpoint checked `draft.status ==
   "ready_for_confirmation"`, but nothing ever set that status — every
   real confirm attempt would have failed with `ERR_CONFIRMATION_NOT_READY`.
   Fixed by wiring it into `customer_router.py`'s `/confirm` handler
   (skipped on retry of an already-confirmed draft, to preserve
   idempotency), and rewriting its readiness check to reflect the real
   provider-first flow (selected provider + confirmed price tier) instead
   of the legacy flat-price gate, plus a live bookability re-check.

5. **`build_booking_summary` (Step 7) destroyed the customer's price
   choice.** It unconditionally overwrote `draft.booking_summary`, wiping
   out `selected_price_tier`/`customer_offer` that `confirm_price_choice`
   had just written — meaning calling Review after Price Selection (the
   ticket's own required step order) would make the subsequent `/confirm`
   fail. Fixed to merge onto the existing summary instead of replacing it.

6. **Internal provider scoring leaked to the customer** on two endpoints:
   `confirm-price-choice`'s response and `/summary`'s `selected_provider`
   both included `internal_score` and a full `matching_score_snapshot`
   breakdown — a direct violation of the hard customer-safety gate. Fixed
   by stripping those keys before they reach `booking_summary`.

## Missing reference data (not a code bug, fixed as test-data setup)
`bargain_rules` had **0 rows** in the entire database — the real
provider-facing catalog range (`service_pricing_rules`, populated)
existed, but the customer-facing bargain configuration never did for any
service. Inserted one real row for AC Repair / Split AC / LG (customer
700–850, 10% fee — the ticket's own canonical example) to complete live
verification. Documented as a pre-existing catalog-completeness gap, not
created by this sprint.

## What's still missing
**No customer-facing web frontend exists for this flow.** `mobile/customer-app`
has UI screens (`BookServiceScreen`, `AIChatScreen`) but they call a
disconnected, generic `bookingsApi.create` — not the booking-draft API at
all. No `frontend/customer-portal` or equivalent Next.js app exists. This
sprint's time went entirely into making the (previously completely
broken) backend flow real and correct; no frontend work was done. See
`HS7_CUSTOMER_BOOKING_UI_REPORT.md` and `HS7_REMAINING_BLOCKERS.md`.
