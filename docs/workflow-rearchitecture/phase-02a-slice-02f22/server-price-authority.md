# Server Price Authority — Slice 2F-22

## Verdict: already server-authoritative; confirmed, not changed

This is why Slice 2F-21's `CLIENT_AMOUNT_TRUSTED` label was wrong. Every
monetary and entitlement value written to the assignment is read from the
`ServicePackage` row inside the service method:

| Assignment field | Source |
|---|---|
| `price_amount` | `pkg.package_price` |
| `security_deposit_amount` | `pkg.security_deposit_amount` |
| `included_spendable_credits` | `pkg.included_credit_amount` |
| `lead_credits` | `pkg.lead_credits` |
| `validity_days` | `pkg.validity_days` |
| `billing_cycle` | `pkg.billing_cycle` |
| `package_type` | `pkg.package_type` |
| storage quota / commission (at activation) | `pkg.storage_quota_gb` / `pkg.commission_rate` |

Findings:

- The client could never override amount or currency, even pre-2F-22 — such
  fields were **silently ignored**. They are now explicitly **rejected**, so
  the request contract can no longer be misread as accepting terms the server
  does not honour.
- The assignment stores a **stable server-derived snapshot** at selection
  time, so later edits to the package definition do not retroactively change
  an existing selection's commercial terms.
- Zero price is distinguished from missing price: `package_price` is
  `NOT NULL DEFAULT 0.00`, so a free package is an explicit `0`, not a null.
- Negative price is impossible at the storage layer:
  `CheckConstraint("package_price >= 0")`.
- Currency is a server column with a non-null default; an unsupported
  currency cannot be introduced by a caller.

## Not invented

No tax, discount, coupon, promotional, tenant-specific, geographic or
effective-date pricing logic exists in this model, and none was invented.
Where the mission's checklist names such a concept, the honest finding is
"mechanism absent" — recorded in `product-decisions-required.md`.

Rounding is inherited from `Numeric(12, 2)` column precision; there is no
application-level rounding step to audit.

## Tests
`TestServerPriceAuthority` (3 tests).
