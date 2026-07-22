# UX-08 Workstream 12-13: Unsupported Capability Registry + Backend Contract Tickets

Status: CONSOLIDATED-FROM-PRIOR-EVIDENCE for items 1-4 below (already
diagnosed in UX-06/UX-07, cited not re-derived); FRESH THIS PASS for
`TICKET-UX08-001` (found during this pass's own test reconciliation, doc
03).

## Registry of MOCK_DESIGN_ONLY / unsupported capabilities (cited, not re-derived)

Per `docs/design/ux-05-staff-technician-app/frontend-adapter-contract.md`
(staff-app), the following adapters are `MOCK_DESIGN_ONLY` — no live
endpoint exists, intended shape only, every consuming screen is a dev-only
showcase never linked from production navigation, with an explicit
on-screen `MOCK_DESIGN_ONLY` disclosure string:

- Inspection
- Checklist
- Quote (staff-side authoring; distinct from customer-app's real
  `QuoteApprovalScreen`, which IS wired to a real approve/reject endpoint)
- Parts (technician-side parts request/creation — see also
  `TICKET-UX08-001` below, which affects the tenant-portal *viewing* side of
  a related parts surface)
- Notes
- Media
- Availability (partial — see staff-app's `AvailabilityControl`, which per
  this pass's Workstream 14 test run is fully tested and passing, but the
  underlying write endpoint disposition is unchanged from UX-05's audit)
- Staff work-queue summary endpoint (technician home/my-work is
  `production_ready`; staff home is `api_contract_required` — no
  work-queue-summary endpoint exists)
- StaffPermission fetch (`GET /v1/staff/{id}/permissions` — not real;
  `api_contract_required` + `product_decision_required`)

Also cited: the mock/fixture census (`mock-fixture-census.csv` in UX-07's
docs) records that tenant-portal has known dev/ux-03 and dev/ux-04
fixture-driven showcase routes (`lib/ux03/fixtures.ts` confirmed to exist),
and a full cross-app fixture census was explicitly deferred by UX-07 —
still deferred this pass (see doc 09, deferred-items.md).

## Backend contract tickets

### TICKET-UX08-001 — tenant-portal React version pin mismatch (frontend tooling, no backend dependency) — FRESH THIS PASS

- **Found**: this pass, Workstream 14 (doc 03), via a genuine fresh
  `npx vitest run` in `frontend/tenant-portal`.
- **Symptom**: 11 of 53 tests fail with `TypeError: Cannot read properties
  of null (reading 'useState')` in `SetupWizard.tsx` and
  `PartsRequestList.tsx` — the duplicate-React-instance failure mode.
- **Root cause**: `frontend/tenant-portal/package.json` pins `"react":
  "19.2.7"` / `"react-dom": "19.2.7"`, while the rest of the npm workspace
  (`frontend/super-admin/package.json`) pins `"react": "19.2.0"` /
  `"react-dom": "19.2.0"`. npm workspace hoisting cannot unify these, so
  `tenant-portal` gets its own nested React copy, and the Vitest/RTL harness
  ends up exercising components against two different React module
  instances in some code paths.
- **Owner**: frontend tooling/dependency management (not the backend team;
  filed here per the brief's Workstream 12-13 slot since it's the natural
  home for "ticket" writeups in this doc set, but it requires no backend
  API or database change).
- **Recommended fix**: align `frontend/tenant-portal`'s React pin to
  `19.2.0` (matching the rest of the workspace) OR bump `super-admin`'s pin
  to `19.2.7` — whichever is the actually-intended target version — then
  re-run `npm install` at the workspace root and re-run both suites in full
  to confirm 0 regressions. Out of scope for this UX-08 pass (a real
  dependency-realignment task, not a "small, evidence-backed" fix).
- **Precedent**: this repo has hit this exact failure class before in
  `mobile/staff-app` (commit `514169b`, "duplicate-react-test-renderer-
  instance bug", fixed via a version-pin correction + a defensive
  `overrides` entry). The same remediation pattern applies here.

### TICKET-UX08-002 — `POST /v1/customer/reviews` 500-on-misnamed-field (backend) — cited from UX-07 Round 3, still open

- **Symptom**: submitting the review-creation body with plausible-but-wrong
  field names (`rating`, `score`, `comment` instead of the real
  `overall_rating`/`review_title`/`review_text`) crashes with a raw,
  unhandled `500 INTERNAL_ERROR` instead of a structured `422` validation
  error.
- **Root cause** (per
  `.../ux-07-cross-app-production-readiness/completion-commission-review-verification.md`):
  direct `body["tenant_id"]` / `int(body["overall_rating"])` dictionary
  access in `app/engines/customer_reviews/customer_router.py:32-60`, no
  try/except around the resulting `KeyError`.
- **Owner**: backend (`customer_reviews` engine).
- **Recommended fix**: wrap the required-field extraction in a proper
  Pydantic request model (or an explicit try/except producing a structured
  `422`) so missing/misnamed fields never reach a raw 500.
- **Status**: not fixed by any UX round to date, including this one (out of
  UX-08's frontend-only scope). Carried forward as-is.

### TICKET-UX08-003 — customer-app `ReviewScreen.tsx` not wired to the real review-submit endpoint (frontend, contract already known) — cited from UX-07 Round 3, still open

- **Symptom**: `mobile/customer-app/src/screens/ReviewScreen.tsx` still
  shows "Review submission isn't available yet" even though UX-07 Round 3
  confirmed a real `POST /v1/customer/reviews` endpoint exists and fully
  documented its exact request/response shape (see doc 05, cross-app
  workflow map, and the cited UX-07 doc).
- **Owner**: frontend (customer-app).
- **Recommended fix**: wire `reviewsApi` (currently only
  `eligibility`/`list`/`get`) to add a real `submit`/`create` call using the
  now-known shape (`tenant_id`, `record_type`, `record_id`,
  `overall_rating` required; `review_title`/`review_text` optional), gated
  by the existing `eligibility` check.
- **Status**: not implemented this pass — per the UX-08 brief's explicit
  "no new code features" constraint, this is documented as ready-to-build
  spec, not built. Flagged as the single highest-value, most concrete
  follow-up item across the whole program (per UX-07 Round 3's own
  framing, reaffirmed here).

### TICKET-UX08-004 — `offering_type_id` required-field contract gap (backend) — cited from UX-07 Round 2, still open

- Full detail already exists verbatim in
  `docs/workflow-rearchitecture/ux-07-cross-app-production-readiness/backend-remediation-ticket-offering-type.md`
  (read in full this pass) — not reproduced in full here to avoid
  duplication; cited as still-open. Summary: `master_services.
  is_type_required = False` for `ac_repair`, but its only real
  `ServicePricingRule` rows are all `service_type_id`-scoped with no
  unscoped fallback, so `match-and-price` fails whenever
  `offering_type_id` is omitted even though the draft's own
  `required_fields` response doesn't ask for it. Recommended minimal fix:
  set `is_type_required = True` for `ac_repair` and audit all other
  offerings for the same pattern.
- **Owner**: backend (`app/engines/home_service_booking` /
  `app/engines/admin_catalog`).
- **Status**: not implemented this pass (backend change, out of UX-08
  frontend-only scope). Carried forward as-is.

## Not re-diagnosed this pass (per brief's "don't re-diagnose from scratch" instruction)

Quote/checklist/parts fixture status, technician parts creation gap, and
customer cancellation/rescheduling gap are all already documented across
UX-05/UX-06/UX-07's own artifacts (frontend-adapter-contract.md files,
`docs/design/ux-06-customer-app/` booking-flow docs). This pass did not
find new evidence that would change their disposition and did not spend
time re-deriving them — they are carried forward as-is via the citations
above and in doc 04 (route inventory) and doc 09 (deferred items).
