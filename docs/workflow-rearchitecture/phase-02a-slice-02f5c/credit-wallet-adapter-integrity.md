# Credit-Wallet Adapter Integrity — Workstream 6

## What the 2 endpoints do
`admin_topup_wallet` and `admin_adjust_wallet` (both under
`/v1/admin/tenants/{tenant_id}/credit-wallet/*`) are **thin adapters**
directly over `UsageCreditService.adjust_credit` — re-verified this
slice by direct source read: neither endpoint touches `TenantWallet` or
any package_commerce-owned table. Both:
- Instantiate `UsageCreditService` inline (not via `PackageCommerceService`).
- Call `svc.adjust_credit(tenant_id=..., direction=..., amount=..., reason_code="manual_operational_adjustment", reason=..., idempotency_key=...)`.
- `await db.commit()` immediately after.

This confirms the Slice 2F-5A/FINAL-L5-05J finding that these are
canonical-ledger adapters, not independent ledgers — re-verified against
current code, not merely carried forward.

Capability: `admin_topup_wallet` performs a credit-only top-up
(`direction="credit"`); `admin_adjust_wallet` performs a signed
adjustment (`direction` derived from `entry_type` in the payload — credit
or debit). Neither is a freeze, reversal-with-linkage, or display-only
update; both are real ledger-posting mutations.

## Per-endpoint verification

| Check | `admin_topup_wallet` | `admin_adjust_wallet` |
|---|---|---|
| Tenant account ownership | `tenant_id` from URL path, passed straight through to `UsageCreditService` — no cross-tenant account ID exists in the payload to substitute | same |
| Amount source | client-supplied `payload["amount"]`, cast to `Decimal` | same |
| Positive/negative | top-up always credits (positive direction); adjust supports both via `entry_type` | same |
| Reason requirement | defaults to a generic string if omitted (not required) | **required** — raises `INVALID_ADJUSTMENT_REASON` (422) if blank |
| Acting persona | admin_finance or super_admin | same |
| Permission | `FINANCE_USAGE_CREDITS_TOP_UP` | `FINANCE_USAGE_CREDITS_ADJUST` |
| Idempotency key | `payload.get("idempotency_key") or f"legacy-credit-wallet-topup:{uuid4()}"` | `payload.get("idempotency_key") or f"legacy-credit-wallet-adjust:{uuid4()}"` |
| Duplicate request (same key reused) | correctly deduped — `UsageCreditService._post` looks up `UsageCreditLedger.idempotency_key` and returns the existing entry with `idempotent: True` | same |
| Ledger entry | `UsageCreditLedger` row created, `TenantBilling.credit_balance` updated under `with_for_update()` row lock | same |
| Transaction boundary | row-locked read + flush + explicit `db.commit()` | same |
| Audit event | `usage_credit.adjusted` via `record_platform_audit` | same |
| Alternate route | none found calling the same tenant credit ledger with a different guard | none found |

## The flagged idempotency-key behavior
Confirmed: when the client omits `idempotency_key`, the router generates
a **random** `uuid4()`-based key on every call — not a stable,
request-derivable value. Since `UsageCreditService._post`'s dedup lookup
is keyed on exact string match, two retries of the same logical request
(e.g. a client timeout-and-retry) that both omit the key will each get a
different random key, and **both will post separately** — a duplicate
top-up/adjustment is possible on retry when the key is omitted.

When the client *does* supply a key, deduplication works correctly
(verified via `usage_credits/service.py:121-127`).

### Disposition: **PRODUCT_DECISION_REQUIRED**

Reasoning:
- This is a real, provable contract gap, not a hypothetical.
- It predates this slice (pattern already present, not introduced here).
- Fixing it requires choosing between (a) making `idempotency_key`
  mandatory at this router (a breaking API contract change for any
  caller that omits it today) or (b) deriving a stable server-side key
  from some natural business reference — but **no natural business
  reference exists** for a manual admin credit adjustment (unlike
  `retry_credit_posting`'s topup-order ID or `deduct_commission`'s
  job-id/record-id). Inventing one (e.g. hashing amount+reason+tenant+day)
  would itself be a product-policy decision about what "the same
  logical request" means for a manual adjustment, and risks incorrectly
  deduping two *legitimately distinct* same-amount adjustments made on
  the same day.
- Per the interim policy and fix-safety criteria ("no product-policy
  decision required," "no speculative changes"), this is **not fixed**
  in this slice.
- Risk is currently low: zero frontend callers were found calling either
  endpoint (confirmed via grep of `frontend/super-admin/lib/api.ts`) —
  this is a "legacy path," not live UI traffic today.

Logged in `product-decisions-required.md` for a future slice.

## Constraints honored
- Internal credits are not described as cash anywhere in this document.
- No balance is overwritten directly — both endpoints only ever call the
  ledger-posting primitive, which derives the new balance from the
  locked row read.
- No cross-tenant credit account ID is possible (tenant_id is the URL
  path parameter, not a payload field).
- No unlogged manual adjustment is possible — every call creates a
  `UsageCreditLedger` row and an audit event.
