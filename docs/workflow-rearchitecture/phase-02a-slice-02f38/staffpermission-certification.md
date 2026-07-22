# StaffPermission Certification

Evidence: existing `tests/test_phase2f*.py` StaffPermission test coverage
(part of the 2445/2445 passing suite, built across Slices 2F-35/36/37),
using ≥2 mocked tenant contexts.

| Claim | Status | Basis |
|---|---|---|
| Explicit deny overrides grant | PASS (mocked) | existing test suite, both grant+deny combination cases |
| Cross-tenant grants never authorize | PASS (mocked) | existing test suite |
| StaffPermission cannot grant platform-admin behavior | PASS (mocked) | existing test suite; platform-admin routes use a separate role check, not StaffPermission at all |
| Designations confer no authorization | PASS (mocked) | reviewed in 2F-35/36 audits — designation fields are display-only |
| `tenant_owner` behavior does not depend on StaffPermission records | PASS (mocked) | `tenant_owner` role check is independent of the StaffPermission table |
| Revoked grant / missing grant / unknown permission | PASS (mocked) | existing test suite |
| Direct service call / alternate route bypass | PASS (mocked, per-module) | reviewed in 2F-35/36/37's own service-layer-enforcement-audit.csv |
| Staff invitation/onboarding path | NOT RE-TESTED THIS SLICE | no new onboarding-flow test added |

**Limitation:** same as `access-scope-certification.md` — mocked-session
evidence only, no live 2-real-tenant PostgreSQL test was performed.
