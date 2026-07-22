# Access-Scope Certification

Evidence: `verify_2f37.py` R05 ("all 19 routes have mutation access-scope
guard live") plus the `require_mutation_access_scope` guard's own unit
tests within `tests/test_phase2f*.py` (part of the 2445/2445 passing
suite — includes explicit mutation-capable/read-only/unknown/missing-scope
cases against a mocked session, established across Slices 2F-35/36/37).

| Claim | Status | Basis |
|---|---|---|
| Mutation-capable scope permits allowed mutations | PASS (mocked) | existing test suite |
| Read-only scope denies every mutation | PASS (mocked) | existing test suite |
| Unknown scope fails closed | PASS (mocked) | existing test suite |
| Missing scope fails where required | PASS (mocked) | existing test suite |
| Scope cannot be widened through client input | PASS (mocked) | `_require_trusted_tenant`-style helpers reject client-supplied override |
| Session refresh does not widen scope | NOT TESTED THIS SLICE | requires live session/token refresh flow against a real auth server |
| Revoked sessions remain revoked | NOT TESTED THIS SLICE | requires live database (`user_sessions.revoked_at`) |
| Internal callers use explicit trusted scope | PASS (mocked) | reviewed in 2F-35/36/37 service-layer audits |
| Demo read-only accounts cannot mutate through alternate paths | PARTIALLY — the mapped-role concept (`admin_readonly`/read-only scopes generally) is proven to deny mutation in mocked tests; the *specific* `readonly@demo-ac-services.local` account was not live-tested (no database), and today has zero role-based permissions anyway (its invalid role isn't in `ROLE_PERMISSIONS`) |

**Limitation:** all "PASS" results above are against the existing mocked
`AsyncSession` test suite, not a live PostgreSQL-backed request. No new
live-database access-scope test was performed this slice (consistent with
`postgres-environment-evidence.md`).
