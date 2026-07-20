# CUSTOMER-L5-06 — Runtime Evidence

## Live Backend Certification: NOT PERFORMED

Identical constraint to every previous sprint: this environment has no
running backend server, no reachable database, and no reachable object
storage. None of CUSTOMER-L5-06 §71's 17 required proof points were
executed against a real system.

**Stated plainly, none of the following were done:**

- No real authenticated customer created or restored a real draft against
  a live backend.
- No real `POST /v1/customer/home-services/booking-drafts` request ever
  left this machine — meaning the sprint's central open question (does
  `offering_slug` from a real `MasterOffering`-backed service ever
  successfully resolve against `MasterService`?) was **not** empirically
  resolved, only reasoned about from source code. This is the single most
  important open question a live run would answer.
- No real photo was ever uploaded through `POST /v1/media/upload` or
  linked via `POST /{draftId}/photos`.
- No real app-restart restoration was exercised against live data.
- No real logout/account-switch clearing was exercised against a live
  multi-customer dataset.
- No request IDs, status codes, or screenshots from a live run exist.

## What Was Verified Instead

- The exact real backend contract for every endpoint used, via direct
  source-code reading of `home_service_booking/customer_router.py`,
  `service.py`, `models.py`, `constants.py`, and
  `media/new_router.py`, `asset_service.py`, `models.py`, `validation.py`,
  `access.py` — cross-checked by an independent research pass reaching
  identical conclusions on every point, including the central
  `MasterOffering`/`MasterService` mismatch finding.
- Every client-side code path (draft schema validation, media schema
  validation, media validation limits, the media-item state machine, the
  draft-session state machine, the assistant-answer mapping, local-store
  isolation) is exercised by 63 new unit tests using fixtures shaped
  exactly like the real backend's actual response bodies (field-for-field,
  taken from `to_dict()`'s literal dict construction).
- `npx tsc --noEmit`: 0 new errors (31 pre-existing, unchanged, all in
  untouched legacy `src/screens/*.tsx` files).
- `npx jest`: 489/489 passing (426 carried forward + 63 new).
- `npx eslint`: 0 errors, 36 pre-existing warnings (baseline unchanged).
- `npx prettier --check`: clean.

## Honest Gate Impact

Per CUSTOMER-L5-06 §71's acceptance criteria, this sprint cannot claim a
hard PASS — both because live runtime proof was not possible in this
environment (consistent with every prior sprint) and because the sprint's
central structural finding (the `MasterOffering`/`MasterService` ID-space
mismatch) means draft creation's real-world success rate against actual
seeded data is genuinely unverified, not merely undemonstrated. The gate
decision reflects PARTIAL.

## What Would Close the Environment Gap

Run the actual backend (`uvicorn app.main:app`) against a seeded database
where at least one `MasterService` row shares a slug with a real,
customer-visible `MasterOffering` row (or confirm they don't and treat that
as a backend defect to fix), authenticate a real test customer, walk
Home → Category → Service → Assistant → Draft → Media end to end, restart
the app to prove restoration, and exercise a second test customer to prove
isolation.
