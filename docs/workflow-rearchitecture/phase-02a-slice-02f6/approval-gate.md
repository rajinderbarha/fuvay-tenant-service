# Approval Gate — Slice 2F-6

## Status
**SECURITY_CLOSED_PRODUCT_POLICY_BLOCKED**

All 4 mutation routes on `invoice_payment.provider_router` now enforce
role/permission separation where previously there was none: tenant roles
outside the qualifying set (`customer`, `guest`) are denied on every
route, read-only access-scope accounts are denied despite an otherwise-
qualifying role, cross-tenant targeting is rejected (pre-existing
service-layer check, re-verified), unknown roles fail closed, and
unauthenticated callers get 401. Zero unclassified or unverified routes
remain in the selected module. This is "product policy blocked" rather
than fully closed because whether `staff` should ever be granted
`FIELD_OPS_INVOICE_GEN` (to issue invoices without owner involvement)
remains an open, undecided product question — not resolved here per the
"do not grant a permission merely because no role currently has it" rule.

## Quality gates (33) — summary
All satisfied. Full itemized results are distributed across the other 16
files in this directory (priority matrix, scope lock, mutation inventory,
policy/enforcement matrices, domain security review, alternate-route
audit, service-bypass report, frontend exposure, direct test matrix,
global coverage update, product decisions, test report, known
limitations, deferred items). No gate was skipped; no gate was marked
passed without underlying evidence in this directory.

## Global coverage after this slice
89/183 tenant-facing mutations now protected (up from a re-confirmed 85
pre-slice baseline) — see `global-coverage-update.md` for the full
reconciliation, including the correction of an initial miscalculation
during this slice's own drafting (caught and corrected before delivery).

## Stop condition honored
Per instruction, this slice stops here. Only one new module
(`invoice_payment.provider_router`) was investigated and closed. No
previously-closed module was modified. `finance_hub.admin_router` and
`package_commerce.admin_router` were not touched, and no
`PACKAGES_*`/`FINANCE_PAYOUTS_*`/`FINANCE_CLAIMS_*` permission was
granted. `readonly@demo-ac-services.local` was not touched. Migration 144
was not applied. No visual redesign occurred.
