# CUSTOMER-L5-02 — Runtime Evidence

## Live Backend Certification: NOT PERFORMED

This environment has **no running backend server and no accessible
database** — there is no `uvicorn`/FastAPI process listening, and no
verified database connection was established during this session. CUSTOMER-
L5-02 §56–58 ("Live Runtime Certification", "Database Evidence", "Failure
Injection") explicitly require proving these flows against a real running
backend or an approved local backend with a real database schema. That
could not be done here.

**What was NOT done, stated plainly:**

- No real `POST /v1/auth/otp/send` was ever actually called over the
  network.
- No real OTP was ever verified end-to-end.
- No real session was created in a live database.
- No real token refresh was executed against a live server.
- No real logout request reached a live server.
- No database evidence (customer row creation, session row creation,
  token rotation, no duplicate customer from duplicate verify, no orphan
  session) was collected, because no database was reachable.

**What was verified instead, and how it substitutes (partially, not
fully) for runtime certification:**

- The exact request/response contracts (`CUSTOMER-L5-02-contract-matrix.md`)
  were verified by reading the real backend source
  (`app/engines/auth/router.py`, `app/engines/auth/service.py`,
  `app/engines/auth/schemas.py`) line by line, not assumed or guessed —
  this is source-level contract verification, not runtime verification.
- Every client-side code path (mapping, validation, token storage, refresh
  coordination, error normalization) is exercised by real unit/integration
  tests against **mocked** HTTP responses shaped exactly like the real
  backend's actual response bodies (copied field-for-field from
  `service.py#_user_to_profile`/`_customer_cat_summary`/etc., not invented).
- `api-client.test.ts` exercises the real `fetch`-based request/retry/
  401-refresh code path with a mocked `global.fetch`, which is as close to
  "real" as this environment can get without a live server — it proves the
  *client's* behavior is correct given a specific server response, not that
  the *server* actually produces that response.

## Honest Gate Impact

Per CUSTOMER-L5-02 §65 ("Runtime" acceptance criteria) and §66's report
format, this sprint **cannot claim** "Real OTP flow executed" / "Real
session created" / "Real profile loaded" / "Real refresh executed" / "Real
logout executed" / "Account-switch isolation proven" against a live
backend. The final gate decision reflects this honestly (PARTIAL, not
PASS) — per the sprint's own explicit instruction: "Do not claim security
certification from unit tests only" and "Do not claim Level 5 completion
after this sprint."

## What Would Close This Gap

Running `uvicorn app.main:app` (or the repository's actual startup command)
against a real or migration-seeded database, with `EXPO_PUBLIC_API_URL`
pointed at it, then manually exercising `OtpLoginScreen` → `ProfileScreen`
→ `SessionsScreen` → sign-out, while inspecting the `users`/`user_sessions`/
`otp_records` tables directly. This was not authorized or possible to set
up within this environment/session.
