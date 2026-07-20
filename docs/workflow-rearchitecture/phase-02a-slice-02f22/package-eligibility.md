# Package Eligibility — Slice 2F-22

Checks performed by `_load_package` + `create_package_assignment`, verified
by source read:

| Requirement | Enforced | Mechanism |
|---|---|---|
| Package exists | YES | `PACKAGE_NOT_FOUND` |
| Not soft-deleted / archived | YES | `ServicePackage.deleted_at.is_(None)` in the query |
| Package is active | YES | `PACKAGE_INACTIVE` on `not pkg.is_active` |
| Price valid (non-negative) | YES, at the schema level | `CheckConstraint("package_price >= 0")` — a negative price cannot be stored |
| Currency supported | YES | `ServicePackage.currency`, `NOT NULL DEFAULT 'INR'`, server-side |
| Free vs paid server-determined | YES | derived from `pkg.package_price`, never client input |
| Contents server-controlled | YES | credits, deposit, quota, commission, validity all read from the package row |

## Concepts that DO NOT EXIST in this model — reported, not invented

The mission's eligibility checklist names several controls with no
counterpart in the schema. This slice did not fabricate them:

- **`is_purchasable` flag** — absent. `is_active` is the only purchasability
  signal.
- **Tenant-private / tenant-restricted packages** — no such column. Every
  active package is visible to every tenant. There is consequently no
  "foreign tenant-private identifier" to leak, and the privacy-safe-error
  requirement does not arise: package existence is not private in this model.
- **Category / vertical restriction** — `vertical_type` exists on the package
  but is not enforced as a purchase restriction. Enforcing it would be new
  product policy.
- **Availability window (start/end dates)** — no such columns.
- **Admin-only / internal package flag** — absent.
  `is_public_signup_visible` controls signup-page visibility only, not tenant
  purchase eligibility.

Each is a candidate product decision recorded in
`product-decisions-required.md`. Inventing any of them would have exceeded
this slice's mandate and its explicit prohibition on redesigning package
pricing or eligibility policy.
