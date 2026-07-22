# Product Decisions Required — Slice 2F-6B (not resolved this slice)

## 1. Should the invoice detail UI be built at all?
The central finding of this slice is that no detail page or mutation
form exists anywhere in the frontend for any of the 4 invoice/payment
capabilities — only a list page with a dead "View Invoice" link. Whether
and when to build this UI is a product decision, not made here (out of
scope: "do not redesign the invoice interface"). The 2 new helper
functions (`canManageProviderInvoices`, `canIssueProviderInvoice`) are
ready for that future work.

## 2. Should staff later receive `FIELD_OPS_INVOICE_GEN`?
Carried over from Slice 2F-6/2F-6A, still unresolved.

## 3. Should technicians later receive a narrower payment capability?
Carried over from Slice 2F-6A. No mobile/staff-app client currently
exists to justify this; would require new evidence (a real client)
before reconsideration.

## 4. Is a dedicated finance-staff persona eventually needed?
Not evaluated this slice — no evidence found either way.

## 5. Frontend test infrastructure
This app (`frontend/tenant-portal`) has no jest/vitest configured. This
slice added a direct-but-standalone `node:test`-based test file since no
framework exists; a future slice may want to formally adopt a test
runner (e.g., vitest) and wire it into `package.json`'s `scripts`, which
was not done here (a build/tooling decision beyond this narrow slice).

## Recommendation (non-binding)
If the product team wants a working invoice detail page, that is the
natural next step — the authorization-helper groundwork is now in place
so that slice would be pure UI work with no new authorization design
needed.
