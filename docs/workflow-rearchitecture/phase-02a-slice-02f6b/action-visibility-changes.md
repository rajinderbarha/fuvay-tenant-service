# Action Visibility Changes — Workstream 4

## Central finding
No visibility change was applied to any button, form, or control for any
of the 4 capabilities (Issue Invoice, Create Invoice, Add Invoice Item,
Record On-Site Payment), because **no such control exists anywhere in the
frontend today** (see `frontend-caller-inventory.csv`). The
`app/(tenant)/provider/service-invoices/page.tsx` list page's only related
element is a "View Invoice" row action that links to a detail route
(`/provider/service-invoices/{id}`) that does not exist in the app
directory — clicking it produces a 404, not an invoice detail page.

## Per-capability disposition

### Issue Invoice
No control exists. `canIssueProviderInvoice(role, accessScope)` is now
available in `lib/api.ts` for whenever a detail page is built. Not
applied to any component this slice — none exists.

### Create Invoice
No control exists. `canManageProviderInvoices(role, accessScope)` is
available for future use. Not applied — none exists.

### Add Invoice Item
No control exists. Same disposition.

### Record On-Site Payment
No control exists. Same disposition.

## Why no UI was built this slice
The mission explicitly states "do not redesign the invoice interface"
and "no visual redesign occurs." Building the missing detail page (with
its Issue/Record-Payment/Create/Add-Item forms) would be implementing
new interface, not aligning existing controls to policy — a
significantly larger change than this "narrow frontend policy alignment
slice" authorizes. The correct, minimal-scope action is to (a) discover
and honestly document that no controls exist, (b) prepare the exact
policy-matching helper functions so a future slice that does build the
detail page has zero authorization-design work left to do, and (c)
correct the prior slices' documentation that incorrectly assumed the
controls already existed.

## Preserved behavior
- The existing list page (`service-invoices/page.tsx`) is unchanged —
  its columns, filters, and "View Invoice" row action are untouched.
- No existing form behavior, confirmation dialog, or validation message
  was touched, because none exists for these 4 capabilities.
- The API client methods (`providerInvoiceApi.issue`/`.recordPayment`,
  `staffInvoiceApi.create`/`.addItem`) are preserved unchanged and
  unremoved, per "do not remove reusable API methods merely because one
  persona cannot call them" — they remain available for future use.

## Conclusion
Zero UI files were modified. One file (`lib/api.ts`) gained 2 new,
unused-today helper functions. This is the smallest possible change that
satisfies Workstream 3's requirement to have policy-matching
authorization helpers ready, without redesigning or inventing new
interface.
