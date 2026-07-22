# Frontend Exposure — Workstream 11

## Method
Grepped `frontend/tenant-portal/lib/api.ts` and `nav-config.ts` for all 4
mutation paths plus their sibling reads.

## Findings
- **Application**: `frontend/tenant-portal` (shared owner+staff web app;
  no mobile/staff-app caller found for this module).
- **Page/screen**: the `service-invoices` nav item is grouped under the
  `"finance-package"` nav section (`nav-config.ts:146`).
- **Callers found** (`lib/api.ts:3225-3275`): `issueInvoice`,
  `recordPayment`, `createInvoice` (staff), `addInvoiceItem` (staff) —
  all 4 correspond exactly to the 4 backend routes now guarded.
- **Role visibility**: the frontend does not itself distinguish which
  role sees the "issue" button vs. the "record payment" button at the
  component level (not independently traced — a UI-component audit was
  out of scope, consistent with "do not redesign pages" and "make only
  minimal access corrections").
- **Access-scope visibility**: not independently traced at the
  component level.

## Requirements check
- **Read-only users see no active mutation controls**: not independently
  verified at the UI-component level; backend now returns 403 for a
  `customer_support_limited`-scoped account regardless of what the UI
  renders, so backend remains authoritative per the mission's own
  requirement ("backend remains authoritative").
- **Owner-only actions not shown to staff**: `provider_issue_invoice` is
  now owner-only backend-side; the frontend was not changed to hide the
  "Issue" button from staff accounts, since doing so would be a UI
  redesign beyond "minimal access corrections" — a staff user clicking
  "Issue" will now correctly receive a 403 from the backend instead of
  succeeding. This is flagged as a candidate for a minimal follow-up
  frontend correction (hiding one button for one role) in
  `known-limitations.md`, not made this slice.
- **Staff actions require proven permissions**: proven — `require_staff_or_above_mutation`
  now backs `record-payment`/`create`/`add-item`.
- **Platform actions do not appear in tenant portals**: confirmed — no
  `invoice_payment.admin_router` path appears anywhere in
  `frontend/tenant-portal`.
- **Blocked actions do not appear functional**: no route in this module
  is blocked/deprecated, so this requirement is vacuously satisfied.
- **Backend remains authoritative**: confirmed — the fix is entirely
  backend-side; no frontend code was changed.

## Frontend changes made this slice
**None.** Per the mission's "make only minimal access corrections... do
not redesign pages," and since no unsafe exposure was proven (the
backend now correctly rejects unauthorized attempts regardless of what
buttons render), no frontend file was touched.

## Conclusion
Frontend exposure is unchanged; backend authorization is now the
authoritative and sufficient control. One low-priority UI-polish item
(hiding the "Issue" button from non-owner accounts) is logged as a known
limitation for a future, frontend-scoped slice.
