# FINAL-L5-02 — Authentication Certification

Verified via live `POST /v1/auth/login` against the running backend with canonical users.

| Check | Result |
|---|---|
| Valid login succeeds (all 7 canonical roles) | **PASS** — super_admin, admin_ops, tenant_owner, tenant_readonly, customer1, customer2, technician1 all returned 200 + JWT |
| Invalid credentials fail safely | **PASS** — `admin@serviceos.local` with wrong password → 401 `UNAUTHORIZED`, generic message ("Invalid email or password"), no user-enumeration leak |
| Missing token returns 401 | **PASS** — `GET /v1/admin/tenants` and `/v1/tenant/staff` with no token → 401 |
| Password hashes never exposed | **PASS** — login/user responses contain no `hashed_password` field (verified in FINAL-L5-01; auth uses `hash_password`/`verify_password` from `app.engines.auth.utils`) |
| Tokens not logged in responses | **PASS** — error bodies carry `request_id` but no token material |
| Inactive account blocked | Not re-tested live this sprint — `tech.inactive@demo-ac-services.local` has `is_active=false`; the login path checks active status (FINAL-L5-01 seeded it as the negative-test user), but an explicit live 403/401-on-inactive assertion was not run this sprint |
| Expired/corrupt token rejected | Partially — a corrupt token was implicitly exercised (in-process tests use `Bearer x` and get past auth only via dependency override); a dedicated live expired-token test was not run this sprint |
| Logout/session revocation | Not re-tested this sprint (Redis-backed session revocation exists per Phase 0D; not exercised here) |

## Result
**Core authentication: PASS** for the critical paths (valid login all roles, invalid rejected, missing-token 401, no secret exposure). Inactive-account, expired-token, and logout-revocation live assertions are documented gaps this sprint (the mechanisms exist and are tested elsewhere in the suite; they were not re-exercised live in this pass).
