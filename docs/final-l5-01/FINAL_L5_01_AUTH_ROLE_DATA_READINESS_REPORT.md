# FINAL-L5-01 — Authentication and Role Data Readiness Report

## Canonical login principals — all present

| User | Role | Tenant | Active | Verified |
|---|---|---|---|---|
| admin@serviceos.local | super_admin (platform_role=super_admin) | none (platform) | true | true |
| admin.ops@serviceos.local | super_admin (platform_role=operations) | none | true | true |
| admin.finance@serviceos.local | super_admin (platform_role=finance) | none | true | true |
| admin.readonly@serviceos.local | super_admin (platform_role=read_only) | none | true | true |
| owner@demo-ac-services.local | tenant_owner | Demo AC Services | true | true |
| manager@demo-ac-services.local | tenant_manager | Demo AC Services | true | true |
| readonly@demo-ac-services.local | tenant_readonly | Demo AC Services | true | true |
| tech1@demo-ac-services.local | technician | Demo AC Services | true | true |
| tech2@demo-ac-services.local | technician | Demo AC Services | true | true |
| tech.inactive@demo-ac-services.local | technician | Demo AC Services | **false** (deliberate negative test user) | true |
| customer1@serviceos.local | customer | none (platform-level) | true | true |
| customer2@serviceos.local | customer | none | true | true |
| owner@isolation-test-services.local | tenant_owner | Isolation Test Services | true | true |

## Rules compliance

| Rule | Status |
|---|---|
| Passwords are environment-safe test credentials | Yes — single shared canonical test password, not a production-strength secret |
| Password values not printed in public reports | Confirmed — no report in `docs/final-l5-01/` contains the plaintext password; it is defined once as a constant in `scripts/canonical_seed_final_l5_01.py` (source code, not a report) and documented for testers only in `.backups/final-l5-01/e2e_credentials.local.txt` (gitignored) |
| Passwords hashed in database | Confirmed — `hash_password()` from `app.engines.auth.utils` used for every user, verified via successful login against the live API (`POST /v1/auth/login` with `admin@serviceos.local` returned a valid JWT) |
| Accounts active | 12 of 13 active; 1 deliberately inactive (negative test user) |
| Verification state correct | All `is_verified=true` |
| Role assignments correct | Confirmed per table above |
| Tenant memberships correct | Confirmed — platform users have `tenant_id=NULL`, tenant users/staff correctly scoped to their tenant, customers platform-level |
| No user has accidental extra privileges | Live-tested and **FAILED**: `customer1@serviceos.local` successfully authenticated and received a `200 OK` with real tenant data from `GET /v1/admin/tenants` (expected `403`). This is a genuine RBAC enforcement gap in the live backend, not a seed-data problem — the seed correctly assigned `role='customer'` with no elevated privileges; the backend's authorization check on that admin endpoint is not correctly rejecting non-admin roles. **Flagged as a real security finding, not fixed in this data-seeding sprint** — see remaining blockers. |

## Credential storage
Test credentials are written to `.backups/final-l5-01/e2e_credentials.local.txt` (gitignored via the `.backups/` rule added this sprint) rather than any committed file or report.
