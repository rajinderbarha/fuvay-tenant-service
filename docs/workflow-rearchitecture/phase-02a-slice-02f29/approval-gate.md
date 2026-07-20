# Slice 2F-29 Approval Gate

## Final status: SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED

**Scoped to M01_identity_credentials only. This is not an application-wide
security claim.**

## Coverage

| Metric | Before | After |
|---|---|---|
| Protected | 214 | **226** |
| Denominator | 259 | 259 |
| Unprotected | 45 | **33** |
| Canonical hash | e7a89231207221aa | fbe7cf863afa0d84 |
| Matrix hash | ee6011f6ce6a97ab | 753653ed32916f4e |

All 12 Set A routes earned full protection: 6
`TENANT_MUTATION_PERMISSION_SCOPE_AWARE`, 1 `PLATFORM_ADMIN_ONLY`, 5
`FULLY_PROTECTED`.

## Quality gates

| Gate | Status |
|---|---|
| Set A 12 routes + frozen hash | MET |
| Set B empty; no held candidate applied | MET |
| Set C unchanged; security API-key subsystem untouched | MET |
| Every route mounted, authority contract frozen | MET |
| Canonical roles/permissions preserved; none added | MET |
| Mutation-capable access scope enforced (6/6) | MET |
| StaffPermission deny precedence + cross-tenant isolation | MET |
| Principal tenant/actor server-derived | MET |
| Target ownership enforced; foreign target no oracle | MET |
| Staff invite/permissions/deactivate tenant-scoped and registry-valid | MET |
| Password/MFA target authority + proof + transitions | MET |
| Impersonation actor/target authority + audit | MET |
| API-key tenant/object scoping; secrets contained | MET |
| Direct service calls fail closed | MET |
| Alternate routes closed or conclusively separate | MET |
| Transactions atomic; no partial write | MET |
| Denominator unchanged at 259 | MET |
| Every verifier condition has an executed fixture | MET |
| Exact failure/error identity reported | MET |
| Full suite green | MET (2213 passed, 0 failed) |

## Honest notes

- **Three real defects were found and fixed**, not just a guard swap: the
  access-scope gap (6 routes), an account-existence oracle in
  `update_permissions`, and unvalidated StaffPermission keys on two write
  paths.
- **Only 2 application files changed**, both on the contract allow-list. The
  third allowed file (`tenant_engine/portal_router.py`) needed no change - its
  alternate route was already closed in 2F-4.
- **Live-database limitation disclosed**: proofs use deterministic doubles plus
  live route/model introspection, not seeded end-to-end HTTP transactions.
- **One pre-existing test was updated deliberately** because it pinned the
  removed oracle; the cross-tenant rejection itself is unchanged and the test
  is now stronger.
- 33 canonical unprotected routes and 59 held candidates remain. No next module
  selected.

Stopping at the Slice 2F-29 approval gate.
