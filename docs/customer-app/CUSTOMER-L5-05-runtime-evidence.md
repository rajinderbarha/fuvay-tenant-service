# CUSTOMER-L5-05 — Runtime Evidence

## Live Backend Certification: NOT PERFORMED

Identical constraint to every previous sprint's runtime-evidence.md: this
environment has no running backend server and no reachable database. None
of CUSTOMER-L5-05 §64's 15 required proof points were executed against a
real system.

**Stated plainly, none of the following were done:**

- No real authenticated customer opened a real service and started the
  assistant against a live backend.
- No real `GET /v1/customer/catalog/issue-types`,
  `/v1/customer/catalog/service-options`, `/v1/catalog/master/brands`, or
  `/v1/catalog/master/service-types` request ever left this machine.
- No real conditional branch (`requires_photo`/`requires_description`) was
  exercised against live data.
- No real answer revision was exercised against live data.
- No real completion boundary was reached against live data.
- No screenshots, request IDs, or status codes from a live run exist.
- Points 6, 7, 8, 11 of §64 ("the backend validates the answer," "the
  backend returns the correct next question," "an earlier answer is
  edited... downstream branch state is recalculated [by the backend],"
  "invalid answers are rejected [by the backend]") are **not applicable at
  all** in this architecture, live or otherwise — there is no backend
  answer-submission/next-question endpoint to exercise. This is not a gap
  in *this sprint's* runtime proof; it is a gap in the backend's own
  capability, documented in contract-matrix.md.

## What Was Verified Instead

- The exact real backend contract for all four catalog endpoints, via
  direct source-code reading of `admin_catalog/service_option_customer_router.py`,
  `admin_catalog/service_option_service.py`, and
  `admin_catalog/customer_router.py` — cross-checked by an independent
  research pass reaching identical conclusions (see contract-matrix.md and
  baseline-verification.md).
- Every client-side code path (schema validation, step-plan construction,
  branch derivation, answer normalization, state-machine transitions,
  renderer resolution) is exercised by 67 new unit tests using fixtures
  shaped exactly like the real backend's actual response bodies.
- `npx tsc --noEmit`: 0 new errors (31 pre-existing, unchanged, all in
  untouched legacy `src/screens/*.tsx` files).
- `npx jest`: 425/425 passing, up from 370 at the start of this sprint —
  see `CUSTOMER-L5-05-test-evidence.md` for the exact file-by-file
  breakdown, including the pre-existing `booking-boundary.test.ts` rewrite
  (not a removal) to match the real, no-longer-dev-gated boundary.
- `npx eslint`: 0 errors, 36 pre-existing warnings (baseline unchanged).

## Honest Gate Impact

Per CUSTOMER-L5-05 §64's acceptance criteria, this sprint cannot claim a
hard PASS — both because live runtime proof was not possible in this
environment (consistent with every prior sprint) and because several of
§64's specific proof points (backend answer validation, backend next-question
resolution, backend branch recalculation) describe backend capabilities
that do not exist to prove. The gate decision reflects PARTIAL.

## What Would Close the Environment Gap

Run the actual backend (`uvicorn app.main:app`) against a seeded database
with real `master_issue_types`/`master_service_options`/`brands` rows
mapped to at least one category, point `EXPO_PUBLIC_API_URL` at it,
authenticate a real test customer, open a real service whose category has
issue types with `requires_photo`/`requires_description` set, and manually
exercise: issue-type selection → conditional description/photo steps →
service-option multi-select → brand selection → completion → the dev
placeholder handoff, plus an answer revision mid-flow and a logout
mid-flow.

## What Would Close the Capability Gap (Backend Work, Not This Sprint)

Add a real answer-submission/next-question/branch-recalculation backend
capability if product wants server-authoritative diagnostic validation —
out of scope for a frontend sprint, and explicitly not fabricated here.
