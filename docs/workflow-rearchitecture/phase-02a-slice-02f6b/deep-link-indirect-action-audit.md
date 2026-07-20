# Deep-Link and Indirect Invocation Review — Workstream 5

## Method
Searched for any route, drawer, modal, context menu, shared action menu,
or mobile deep link that could reach any of the 4 invoice/payment
mutation endpoints, beyond the (nonexistent) primary controls already
documented.

## Findings
- **Direct page URLs**: `/provider/service-invoices/{id}` is not a
  registered Next.js route (no `[invoice_id]/page.tsx` file exists under
  `app/(tenant)/provider/service-invoices/`) — navigating to it directly
  produces Next.js's standard 404 page, not a mutation form.
- **Detail drawers / modals**: none found referencing
  `ServiceInvoiceRecord`, `providerInvoiceApi`, or `staffInvoiceApi`
  anywhere in `frontend/tenant-portal`.
- **Context menus / shared action menus**: the list page's only row
  action is "View Invoice" (the dead link above) — no second, alternate
  action exists for issue/record-payment/create/add-item.
  `EnterpriseDataGrid`'s `rowActions` prop is the only mechanism in use;
  it was read in full for this page and contains exactly one action.
- **Keyboard actions**: no custom keyboard-shortcut handlers were found
  tied to invoice mutation.
- **Mobile deep links**: `mobile/staff-app` contains zero references to
  `service-invoices` or any of the 4 endpoint paths (confirmed via grep).
- **Cached page state**: not applicable — there is no mutation form to
  cache stale role/scope state into.

## Verification against the mission's specific checks
- Technician deep links do not expose the mutation form: **true, and
  vacuously true** — no mutation form is reachable by any role today.
- Read-only deep links do not expose active submission controls: same.
- Staff cannot reach Issue Invoice through another component: confirmed
  — no component anywhere calls `providerInvoiceApi.issue`.
- Customer and guest surfaces have no provider mutation controls:
  confirmed — `frontend/customer-app` has zero references to any of the
  4 endpoints or their API client methods.
- Hiding a primary button does not leave a second callable control: not
  applicable — no primary button exists to hide, and no second control
  was found either.

## Conclusion
No deep-link or indirect-invocation bypass exists, because no
mutation-capable UI path exists at all for any of the 4 capabilities.
Backend denial (Slice 2F-6/2F-6A) remains the sole, and currently only
necessary, security boundary for these endpoints.
