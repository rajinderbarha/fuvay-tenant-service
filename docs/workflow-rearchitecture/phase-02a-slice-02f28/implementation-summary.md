# Implementation Summary - Slice 2F-28

## Final status: NEXT_AUTHORIZATION_MODULE_SELECTED

Selected module: **M01_identity_credentials** (`app.engines.auth.router`), 12
canonical unprotected routes.

## Starting position (authoritative, unchanged)

214 / 259, 45 unprotected. Canonical `e7a89231207221aa`, matrix
`ee6011f6ce6a97ab`. Both unchanged by this slice; zero application files
modified.

## What this slice did

- Exported the authoritative **45**-route canonical unprotected queue; every
  route maps to exactly one canonical inventory row.
- Grouped all 45 into **11 coherent implementation modules** by shared
  router/service/model/authorization boundary (counts sum to 45, no route in
  two modules).
- Risk-scored every module with one documented 19-dimension model.
- Cross-referenced all **59** held candidates and the security observations by
  module, without letting any of them touch coverage arithmetic.
- Selected exactly one module and froze three route sets (A canonical, B held
  adjudication, C adjacent exclusions) with hashes.
- Wrote the authorization-evidence requirements, held-route adjudication
  contract, test matrix and the implementation-slice contract.

## Why M01

Highest pure risk score (29 vs 19 next) **and** the largest route count (12),
carrying nearly every critical-risk flag: password/MFA mutation, API-key
create/update/revoke, impersonation, StaffPermission mutation, and staff
invite/deactivate. It is also atomically closeable: a single router
(`auth.router`), a single service (`AuthService`), and — verified this slice —
**zero same-module held candidates**, so no adjudication uncertainty blocks
closure.

## Notable finding

`/v1/auth/api-keys` and `/v1/security/api-keys` are **two distinct API-key
subsystems**: `ApiKey` -> `api_keys` (auth) vs `APIKey` -> `tenant_api_keys`
(security). They are therefore NOT the same boundary; the held security
API-key routes are recorded as adjacent exclusions, not module scope.

## Verification

- tests/test_phase2f28_module_selection.py
- verify_selection_2f28.py: 20 conditions, `--selftest` exits 0
- Canonical + matrix hashes unchanged; zero `app/` files modified
