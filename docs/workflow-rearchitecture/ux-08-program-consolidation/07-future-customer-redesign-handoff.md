# UX-08 Workstream 18: Future Customer App Redesign — Functional Contract Handoff

Status: FRESH THIS PASS (spec document, no new code). Purpose: the next
design pass on `mobile/customer-app` is expected to be a visual redesign,
not a functional rebuild — this document exists so that redesign can happen
without re-deriving what each screen must actually DO. Every contract below
is drawn from the real, currently-shipping source (read this pass, see doc
04 for the full route inventory it's built from) plus the real backend
shapes confirmed live in UX-06/UX-07 evidence (cited, not re-verified this
pass since the DB is unreachable — see doc 05).

**This document intentionally says nothing about pixel layout, color, or
spacing** — that is explicitly out of scope (see doc 08, responsive
handoff, and the brief's instruction that visual work now would be wasted
ahead of a planned design replacement). It documents only: what data each
screen needs, what actions it must support, what real API contracts back
those actions, and what's currently a known gap so the redesign doesn't
accidentally "fix" something that was actually a deliberate, documented
disposition (e.g. a MOCK_DESIGN_ONLY screen dev-only status).

## Functional contract per screen

### Home
- **Needs**: authenticated user's active-booking summary (if any), a
  service search entry point, SmartBot CTA, popular-service category tiles,
  a trust-signal row.
- **Actions**: navigate to SmartBot with an optional pre-selected category
  (`initialCategoryLabel` handoff, real, implemented UX-07 Pass 3d — do not
  re-ask "what service do you need" if the user tapped a category tile);
  navigate to Bookings, ServiceDetail.
- **Backing contract**: real, no known gaps.

### Bookings (list)
- **Needs**: the authenticated user's booking list with status.
- **Backing contract**: real (`ServiceBooking` records, per doc 05's
  workflow chain — statuses observed live: created → assigned → accepted →
  completed).

### BookingDetail
- **Needs**: single booking's full detail — status, assignment info,
  scheduled date/time, address, price, payment mode, linked job id/status.
- **Real field list confirmed live** (per UX-07 Round 3, cited in doc 05):
  `booking_id`, `booking_number`, `status`, `assignment_status`,
  `assignment_message`, `preferred_date`, `preferred_time_window`, `city`,
  `address`, `issue_summary`, `selected_provider`, `selected_price_option`,
  `selected_price_amount`, `payment_mode`, `job_id`, `job_status`,
  `scheduled_date`, `scheduled_time_window`. **No online-payment/card/
  wallet/escrow field exists — on-site payment only, by policy. A redesign
  must not add a "Pay Now" card-entry UI; there is nothing behind it.**
- **Known gap, do not silently "fix" in redesign**: no cancel/reschedule
  action exists on this screen or anywhere in customer-app (per user memory
  `project_module_l5_29_booking_cancel_reschedule.md`, cancel/reschedule WAS
  built as a backend capability at some point — MODULE-L5-29 — but this
  pass did not re-verify whether `mobile/customer-app` currently exposes it
  in its UI; if the redesign wants to add cancel/reschedule affordances,
  first re-check whether `bookingsApi` already has the calls wired (it may,
  post-L5-29) before assuming it needs backend work.

### ServiceDetail
- **Needs**: category/offering detail, price, real availability/
  serviceability check.
- **Known real backend gap (TICKET-UX08-004, doc 06)**: `ac_repair`'s
  pricing resolution requires `offering_type_id` in practice even though
  the draft's own `required_fields` response doesn't say so. A redesign
  that changes this screen's form fields must keep `offering_type_id`
  collectable somewhere in the flow (currently done via a brand/type
  selector) — do not remove it as "seems optional" without confirming the
  backend ticket above is resolved first.

### JobTracking
- **Needs**: real-time-ish job status for the assigned technician (accepted
  → in-progress → completed), technician identity if assigned.
- **Backing contract**: real, confirmed live per doc 05's chain.

### QuoteApproval
- **Needs**: present a technician-authored repair quote for
  approve/reject.
- **Backing contract**: real approve/reject wired on the customer side.
  Note: the **staff-side quote-authoring** adapter is `MOCK_DESIGN_ONLY`
  per doc 06's registry — the two ends of "quote" are at different
  readiness levels; a redesign should not assume quote-authoring is real
  just because quote-approval is.

### Review
- **Needs**: eligibility check (`GET /v1/customer/reviews/eligibility?
  record_type=service_job&record_id={job_id}`), then submit
  (`overall_rating` required, `review_title`/`review_text` optional).
- **CRITICAL, currently unimplemented (TICKET-UX08-003, doc 06)**: the real
  submit endpoint exists and its exact shape is fully known (doc 05/06), but
  `ReviewScreen.tsx` does not call it yet — it still shows a static "not
  available yet" message. **This is the single most valuable, cheapest,
  most concrete pre-redesign fix in the whole program** — wiring it up
  before or alongside a visual redesign (rather than during, when the
  contract would need re-discovery) is strongly recommended, but it is
  explicitly NOT done in this UX-08 pass per the "no new code features"
  rule.
- **500-on-misnamed-field defect (TICKET-UX08-002)**: the redesign's data
  layer must use the exact real field names (`overall_rating`, not
  `rating`/`score`) — the backend does not validate gracefully.

### Invoice
- **Needs**: read-only invoice display tied to a completed job — amount,
  line items, payment mode.
- **Backing contract**: real, no known gaps found this pass.

### Settings / Notifications / Profile / AddressBook / ServiceHistory / HelpSupport / PaymentMethods
- **Needs**: standard account-management CRUD/read surfaces.
- **Backing contract**: all real, `ACTIVE_PRODUCTION` per doc 04. No
  redesign-relevant functional gaps found this pass.

### Chat
- **Needs**: real human/provider support thread (distinct from SmartBot).
  Relocated (not deleted) from a primary tab to Profile > Support >
  "Messages" in UX-07 Pass 3d.
- **Backing contract**: real, per repo history (MODULE-L5-14/19/20/34).

### SmartBot (DeepSeekChatScreen)
- **Needs**: multilingual DeepSeek-backed conversational booking flow.
  **Per user memory (`project_language_architecture_correction.md`):
  multilingual UI is scoped ONLY to this SmartBot chat surface — it is NOT
  an app-wide requirement.** A redesign must not assume every other screen
  needs localization; only this one does.
- **Backing contract**: real, live-verified (UX-06 Round 3), category
  handoff from Home real (UX-07 Pass 3d).

## Theme system (real, keep as-is functionally)

`ThemeContext` provides System/Light/Dark mode resolution with persistence
(real, tested — see doc 03, all customer-app tests including theme tests
pass 76/76). A visual redesign will presumably replace the actual palette
values, but the mode-resolution/persistence mechanism itself is a real,
working piece of infrastructure — reuse it, don't rebuild it.

## What NOT to inherit into the redesign as "the plan"

The current 5-tab bottom nav (Home/Bookings/SmartBot/Notifications/Profile)
and the specific screen list above are FUNCTIONAL requirements (what must
be reachable and what data/actions each surface needs), not a mandate to
keep the same IA shape. The redesign is free to reorganize navigation as
long as every functional contract above is still satisfiable somewhere in
the new IA.
