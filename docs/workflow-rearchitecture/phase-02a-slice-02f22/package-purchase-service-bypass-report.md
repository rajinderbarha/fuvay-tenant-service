# Service-Layer Bypass Report — Slice 2F-22

Router dependencies do not replace service-layer integrity. Every service
method reachable from `tenant_purchase_package` was enumerated and its full
caller set audited.

## `PackageCommerceService.create_package_assignment`

**Callers (complete, by grep):**

| Caller | Persona | is_paid | payment_authority (2F-22) |
|---|---|---|---|
| `tenant_router.tenant_purchase_package` | `tenant_owner` | `False` (literal) | `tenant_unpaid_request` |
| `admin_router.admin_purchase_package` | admin, `P.PACKAGES_CREATE` | `True` | `admin_attestation` |
| `public_registration` signup | new tenant, post-signature | `True` | `gateway_signature_verified` |

**Weakest caller:** previously the tenant router — the only caller where an
untrusted principal controlled `is_paid`. It is now the *strongest*
constrained: it cannot express paid state at all.

**Strongest caller:** `public_registration`, which holds cryptographic proof.

### Verification of each required property

- **Tenant source** — server-derived in all three callers (JWT for tenant
  router; explicit path param under admin permission for admin router;
  freshly created tenant for signup).
- **Actor source** — `UserContext.user_id` via `_svc()`; signup passes no
  actor (system context), unchanged.
- **Package source** — path parameter, resolved through `_load_package`
  (active + not soft-deleted) in every case.
- **Price source** — `ServicePackage` row; no caller can inject a price.
- **Payment-state source** — now gated by the `payment_authority` allow-list;
  fails closed on the default `"unspecified"`.
- **Credit / entitlement source** — none issued by this method.
- **State validation** — duplicate guard runs for all callers.
- **Transaction behavior** — method flushes only; each caller owns its commit
  (signup additionally uses a SAVEPOINT).

## Bypasses explicitly checked for, and not found

- `tenant_id=None` as a global/unscoped mode — **not possible**;
  `tenant_id` is a required positional parameter and every caller supplies a
  concrete value. (This is the exact defect class found in compliance in
  2F-20; it does not recur here.)
- `mark_paid` from an untrusted caller — **now blocked at the service layer**,
  not merely at the router.
- Client amount or currency — no parameter exists to carry either.
- Unscoped credit issuance — this method issues no credits.
- Duplicate activation — guarded by the pre-existing pending check plus the
  one-shot `verify_tenant` transition.

## Downstream methods (not modified)

`activate_tenant_package_assignment` and `reject_tenant_package_assignment`
are called only from `tenant_engine/admin_service.py` under admin
authorization. Neither is reachable from any tenant-facing route. Audited,
unchanged.

## Tests
`TestServiceLayerPaymentAuthority` (7 tests) and
`TestLegitimateCallersPreserved` (4 tests).
