# Amount and Currency Integrity — Workstream 9

## Per-route amount classification

| Route | Amount source | Validation |
|---|---|---|
| `create_package` | client-supplied `package_price` etc. | positive-value validated: `package_price`, `security_deposit_amount`, `included_credit_amount` all rejected if negative; `credit_topup` packages rejected if deposit > 0; `security_deposit_rule` packages rejected if credit > 0 (re-verified via direct source read, lines 73-166) |
| `update_package` | client-supplied | `package_price`, `security_deposit_amount`, `included_credit_amount` each explicitly rejected if negative; `credit_topup` packages additionally rejected if `security_deposit_amount > 0` |
| `admin_purchase_package` | server-derived (`pkg.package_price`, read from the loaded row) | immune to client tampering by construction (no price parameter accepted) |
| `admin_topup_wallet` / `admin_adjust_wallet` | client-supplied | cast to `Decimal`; no explicit positive/negative or zero-value check at the router or `UsageCreditService.adjust_credit` boundary beyond `_post`'s `amount == 0` rejection (`INVALID_CREDIT_AMOUNT`) — direction (`credit`/`debit`) determines sign server-side in `_post`, not client-suppliable sign smuggling |
| `admin_calculate_commission` | client-supplied `job_value` | no positivity check found; a negative or zero `job_value` would produce a negative or zero commission amount, which would then either fail or succeed oddly in `deduct_commission`'s debit call — **not independently exploitable** since this endpoint is `require_super_admin`-gated and no live caller was found, but noted as a limitation, not fixed (fixing would mean inventing a new validation rule not evidenced elsewhere in this file) |
| `admin_deduct_commission` | no client amount — reads `record.commission_amount` set by `calculate_commission` | immune to client tampering at this step |

## Finding: none
Both `create_package` and `update_package` were checked for negative-
amount validation. Both are guarded (re-verified this slice, correcting
an initial assumption of asymmetry): `create_package` rejects negative
`package_price`, `security_deposit_amount`, and `included_credit_amount`,
plus enforces the `credit_topup`/`security_deposit_rule` mutual-exclusion
rules; `update_package` independently re-validates the same 3 fields
whenever they are present in the update payload. No amount-validation
defect was found in either package-definition entry point.

## Currency
No multi-currency comparison logic exists in this module. `currency` is
a free-form field on `ServicePackage` (settable via `update_package`) with
no cross-check against a tenant's billing currency or any other package's
currency — consistent with the rest of the platform's single-implicit-
currency pattern observed in Slice 2F-5B. Not flagged as a defect.

## Decimal precision
`update_package` casts all monetary fields through `Decimal(str(...))` —
avoids float-precision loss. `calculate_commission` quantizes to
`Decimal("0.01")` with `ROUND_HALF_UP`. `usage_credits.adjust_credit`
stores raw `Decimal` amounts without a fixed quantization step at the
adapter layer (quantization, if any, happens further down in
`UsageCreditService`, not re-audited this slice as it is owned by that
service, not `package_commerce`).

## Conclusion
No amount-validation defect found in `package_commerce.admin_router`.
The only open items are the pre-existing credit-wallet idempotency-key
contract gap (see `credit-wallet-adapter-integrity.md`, disposition
`PRODUCT_DECISION_REQUIRED`) and `admin_calculate_commission`'s trusted,
client-supplied `job_value` (see `commission-deduction-integrity.md`,
disposition: limitation, not a fixable defect within this module's own
authority).
