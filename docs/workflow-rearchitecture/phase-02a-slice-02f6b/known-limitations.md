# Known Limitations — Slice 2F-6B

1. **No invoice detail UI exists.** No component in any application
   invokes `provider_issue_invoice`, `provider_record_payment`,
   `staff_create_invoice`, or `staff_add_invoice_item`. The tenant-owner
   and office-staff workflows this backend policy is meant to support
   have no functioning frontend entry point today — this is a
   pre-existing gap, not introduced by this slice, and building it is
   out of scope ("do not redesign the invoice interface"). See
   `frontend-caller-inventory.csv`.

2. **The "View Invoice" row action links to a nonexistent route**
   (`/provider/service-invoices/{id}` has no corresponding
   `[invoice_id]/page.tsx`). Not fixed this slice — fixing it would mean
   building the detail page, out of scope.

3. **No frontend test framework exists** in `frontend/tenant-portal` (no
   jest/vitest, no `test` script in `package.json`). This slice's new
   test file uses Node's built-in `node:test` via a manual
   tsc-compile-then-run workaround, since `npx tsx`'s on-the-fly
   execution failed due to an environment-level npm issue. A future
   slice may want to formally adopt a test runner.

4. **`next lint` could not be run** in this environment (pre-existing
   CLI argument-parsing issue) and no ESLint v9 config file exists in
   this project to run `eslint` directly against. Type checking
   (`tsc --noEmit`) was used as the primary verification instead and
   passed cleanly for the changed file.

5. **Product-policy questions carried over, unresolved**: whether staff
   should get `FIELD_OPS_INVOICE_GEN`, whether technician should ever
   get a narrower payment capability, whether a dedicated finance-staff
   persona is needed, and whether/when to build the missing invoice
   detail UI. See `product-decisions-required.md`.
