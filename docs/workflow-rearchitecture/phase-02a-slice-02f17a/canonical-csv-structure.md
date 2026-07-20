# Canonical CSV Structure — Confirmed Consistent (Design A)

## Decision re-confirmed, not re-litigated
Slice 2F-15C established Design A: the canonical `tenant-mutation-endpoint-inventory.csv` contains tenant/provider mutations ONLY — customer, platform, false-positive, and disconnected rows are physically excluded, not flagged with an `include_in_tenant_denominator` column. This slice's full-application sweep found **zero violations** of this rule (`misclassified-non-tenant-rows.csv`) — confirming the design has been applied with 100% consistency across this entire initiative's history (17+ slices).

## Both canonical CSVs apply identical inclusion rules
- `tenant-mutation-endpoint-inventory.csv` — tenant/provider only, Design A, 226 rows, zero violations found.
- `mutation-enforcement-matrix.csv` — a DIFFERENT, intentionally distinct convention (total mounted mutation routes PER MODULE, not tenant-only) — established and explained in Slice 2F-15C's own `canonical-csv-structure.md`, re-confirmed unchanged this slice. This file was not modified this slice (no module's per-row total required correction).

## No customer/platform/worker/public/false-positive/deprecated/disconnected row affects tenant X/Y
Confirmed exhaustively this slice via the full-application cross-check — not merely asserted. See `misclassified-non-tenant-rows.csv` and `global-coverage-reconciliation.md`.

## Why no structural change was needed
The mission's Workstream 14 asked this slice to "choose one consistent tenant inventory structure" — Design A was already chosen (2F-15C) and is confirmed, by this slice's full sweep, to have zero structural violations. No migration to Design B (a shared file with a persona_category/include_in_tenant_denominator column) is warranted, since Design A's physical-exclusion approach has proven itself robust across the entire initiative with zero drift.
