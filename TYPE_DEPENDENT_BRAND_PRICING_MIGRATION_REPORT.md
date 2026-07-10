# Type-Dependent Brand Pricing — Migration Report

## Schema migration
`alembic/versions/120_type_dependent_brand_pricing.py` — applied live
against the real dev DB (`alembic upgrade head`, 119 → 120, confirmed
via `psql \d tenant_service_brands` and `\d service_pricing_rules`
showing the new column/constraints). Idempotent-guarded (checks
`inspector.get_columns()`/`get_unique_constraints()` before altering),
consistent with this repo's established migration convention.

## Data cleanup script
`scripts/migrate_type_dependent_brand_pricing.py` — supports `--dry-run`
(default) and `--apply`.

### Dry-run output (real, against the live dev DB)
```
[DRY-RUN] old global admin brand rules found: 2
  - rule 23d1a31e...: master_service=a96e625a... brand=64a3b25f...(LG) range=Rs.1100.00-1100.00
  - rule 178dcd87...: master_service=a96e625a... brand=f95699ab...(Voltas) range=Rs.950.00-950.00
  affected services: 1
  affected brands: 2

[DRY-RUN] old global tenant brand price rows found: 0
```

### Apply strategy (matches the ticket exactly — no blind copy)
- Admin-side rows: marked `is_active = false` (deprecated), never
  auto-converted into per-type rules — an admin must explicitly create
  the correct per-type replacement rules, since guessing which type(s)
  a global ₹1100 LG price should apply to would be wrong as often as
  right.
- Tenant-side rows: price fields would be cleared (`tenant_min_price`/
  `tenant_max_price` set to `NULL`) rather than the row deleted, so the
  provider's brand *selection* is preserved but the setup wizard would
  show "needs pricing" per type again. (0 such rows existed in the real
  dev DB — the tenant-side bug was caught before any real tenant had
  set brand-level pricing for a type-based service.)

### Apply run (real, against the live dev DB)
```
[APPLY] old global admin brand rules found: 2
  -> marked 2 admin rule(s) inactive (manual_review — admin must recreate per-type)
[APPLY] old global tenant brand price rows found: 0
```
Confirmed via `psql`: both legacy rules now have `is_active = false`;
the real dev tenant's brand data was otherwise untouched.

## Verdict
Migration + cleanup script: **complete and live-verified**. Real legacy
data (found during this sprint's own testing setup) was correctly
detected and safely deprecated, not silently mismapped.
