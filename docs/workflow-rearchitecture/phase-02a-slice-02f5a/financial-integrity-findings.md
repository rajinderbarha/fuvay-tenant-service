# Financial Integrity Review — Workstream 6

## What was inspected
`package_commerce.admin_router`'s wallet endpoints (the only endpoints in
either module whose full internals were traced this slice, since they
delegate to the already-audited canonical `UsageCreditService`) and both
modules' guard/permission composition.

## Findings

### No direct balance overwrites found
Grepped both modules for direct `.credit_balance =` / `SET ... balance`
patterns — zero matches. `admin_topup_wallet`/`admin_adjust_wallet` both
delegate to `UsageCreditService`, which was already the subject of a prior
fix (FINAL-L5-05J, referenced in the router's own code comment) moving it
off a naive `TenantWallet` balance mutation onto the canonical ledger
service.

### Idempotency
`admin_topup_wallet` reads an `idempotency_key` from the payload but
**defaults to a freshly-generated random UUID if the caller doesn't supply
one** (`payload.get("idempotency_key") or f"legacy-credit-wallet-topup:{uuid.uuid4()}"`)
— meaning true idempotency (rejecting a genuine duplicate request) only
works if the caller explicitly supplies a stable key. This is not a new
defect introduced or found this slice; it is the existing, documented
behavior of a "legacy" compatibility path (the variable name itself says
"legacy-credit-wallet-topup"), and `UsageCreditService`'s own idempotency
enforcement internals were not re-audited to confirm whether the service
layer independently protects against duplicates. Flagged, not fixed —
fixing it would require understanding `UsageCreditService`'s full
idempotency contract, which is out of this slice's narrow scope.

### Amount validation
`admin_adjust_wallet` requires a non-empty `reason` (enforced,
`ServiceOSException` on empty) — a real, existing audit-trail safeguard.
Both wallet endpoints convert the client-supplied `amount` via
`Decimal(str(payload.get("amount", 0)))` — no negative-value or
precision-specific validation was found at the router level; whether
`UsageCreditService` validates this internally was not re-audited.

### Permission-bundle gaps (not a code security bug, a product-policy gap)
13 of `package_commerce.admin_router`'s 20 endpoints and 10 of
`finance_hub.admin_router`'s 17 endpoints use permissions granted to no
role except via `super_admin`'s `P.ALL` wildcard. This does not create an
exploitable weakness (super_admin-only is a valid, secure disposition) —
it means these capabilities may be functionally inaccessible to the
`admin_finance` platform role that conceptually should own them. This is
the central, real finding of this slice, escalated in
`product-decisions-required.md`, not fixed by granting permissions
(explicitly prohibited).

## No code change made
No defect conclusively met Workstream 11's bar for a safe, scoped code fix
this slice (a "defect" here is a permission-bundle/product-policy gap, not
a security exploit — granting the missing permissions would itself be a
product decision, explicitly out of scope: "Do not grant new permissions
merely to make endpoints reachable"). The 3 security-deposit
`DEPRECATED_410` stubs are intentional and safe, not a defect. No unsafe
behavior was found that has a "smallest fix" available without a new
product decision.
