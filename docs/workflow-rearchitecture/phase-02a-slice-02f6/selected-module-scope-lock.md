# Selected Module Scope Lock — Slice 2F-6

## Selected module
`app.engines.invoice_payment.provider_router`

## Runtime mutation count
**4** mounted POST mutations (re-verified via runtime walk):
1. `POST /v1/provider/service-invoices/{invoice_id}/issue` (`provider_issue_invoice`)
2. `POST /v1/provider/service-invoices/{invoice_id}/record-payment` (`provider_record_payment`)
3. `POST /v1/staff/service-invoices` (`staff_create_invoice`)
4. `POST /v1/staff/service-invoices/{invoice_id}/items` (`staff_add_invoice_item`)

(The file also mounts 5 GET routes and 2 additional GET-only sub-routers
— wallet and subscription-status — which are reads, not mutations, and
are out of this slice's mutation-coverage scope.)

## Why it outranks the others
Per the mission's stated priority order:
1. **User/role/session administration** — no remaining unclosed module
   matches this category; `tenant_engine.router` already closed it.
2. **Finance or credit mutations exposed to tenant personas** —
   `invoice_payment.provider_router` is the only remaining unclosed
   module in this category, and it was found completely unprotected
   (`AUTHENTICATED_ONLY_NO_PERMISSION_CHECK` on all 4 routes — any
   authenticated user of *any* role, including `customer` or `guest`,
   could issue an invoice or record a payment before this slice).
   Recording an on-site cash/card payment and issuing a formal invoice
   are real-money-adjacent actions with zero role separation — the
   highest-severity, best-evidenced gap among all remaining modules.

Compared to the next-highest candidates:
- `app.engines.serviceability.router` (8 mutations, `PERMISSION_ONLY_NOT_SCOPE_AWARE`)
  is a service-area/coverage config module — real risk, but category-3
  ("service catalog/pricing/business config"), one tier below finance.
- `app.engines.admin_catalog.tenant_router` (10 mutations) is already
  9/10 access-scope-protected from a prior, undocumented-in-this-series
  fix — the smallest remaining gap, lowest priority.
- All other remaining modules (`complaints`, `real_estate`, `coaching`,
  `field_ops.checklist_router`, `compliance.provider_router`,
  `platform_notifications.provider_router`, `media.new_router`, etc.)
  fall into categories 5-7 (operational/low-risk/compatibility).

## Highest-risk endpoints
- `provider_record_payment` — records a real on-site payment
  (cash/card/UPI) against an invoice; previously reachable by anyone
  authenticated, any role, any tenant membership status.
- `provider_issue_invoice` — formally issues (locks in) a customer-facing
  invoice and transitions the linked `ServiceJob` status.
- `staff_create_invoice` / `staff_add_invoice_item` — create/modify a
  draft invoice's line items (price-bearing).

## Current guards (before this slice)
All 4: `Depends(get_current_user)` only — `AUTHENTICATED_ONLY_NO_PERMISSION_CHECK`.
No role check, no permission check, no access-scope check. Tenant
isolation exists only at the service layer (`tenant_id` is always
server-derived from `user.tenant_id`, never client-supplied — so
cross-tenant targeting via a spoofed tenant_id was never possible, but
role separation was completely absent).

## Expected personas (evidence-based, re-verified this slice)
- `provider_issue_invoice`: **TENANT_OWNER_SELF_SERVICE** — gated by the
  existing, previously-unwired `FIELD_OPS_INVOICE_GEN` permission
  (`"field_ops:invoice:generate"`), granted only to `tenant_owner` in the
  current role bundle (re-verified via `app/core/permissions.py:545`).
- `provider_record_payment`: **TENANT_OWNER_OR_DELEGATED_STAFF** — no
  more specific permission exists for "recording a payment"; the closest
  evidence is `FIELD_OPS_JOBS_CLOSE`'s own documented capability
  ("Record direct customer payment + close own jobs"), already granted
  to `tenant_owner`, `staff`, and `technician` — role-gated via
  `require_staff_or_above_mutation`.
- `staff_create_invoice`, `staff_add_invoice_item`: **DELEGATED_STAFF_MUTATION**
  — ServiceJob-linked staff actions, same role-gate as above, consistent
  with the `/v1/staff/` path prefix and the already-closed
  `home_service_assignment.staff_router` precedent for "staff acting on
  their own job."

## Expected permissions
`FIELD_OPS_INVOICE_GEN` (route 1 only); no new permission created for
routes 2-4 — role-gated instead, since no more specific existing
permission was found for those 3 actions.

## Expected access-scope behavior
All 4 routes use the existing `TENANT_READONLY_ACCESS_SCOPES` mechanism
(via `require_tenant_mutation_permission` for route 1,
`require_staff_or_above_mutation` for routes 2-4) — a `tenant_owner` or
`staff` account with `access_scope="customer_support_limited"` is denied
regardless of role/permission, per the platform's established
deny-over-grant precedence.

## Known alternate routes
- `invoice_payment.admin_router` — platform-admin (`require_super_admin`)
  equivalent CRUD over the same `ServiceInvoice`/`ServicePaymentRecord`
  tables — a **stronger**, not weaker, alternate; no action required.
- `invoice_payment.customer_router` — `customer_apply_credit`/
  `customer_confirm_payment` — a distinct, correctly ownership-scoped
  (`user.user_id`-matched) customer-only capability, not a weaker
  alternate for the same provider/staff actions.

## Known service callers
`ServiceInvoiceService.create_invoice/add_item/issue_invoice` and
`ServicePaymentService.record_onsite_payment` — re-verified via grep to
have **no callers anywhere in `app/`** other than
`invoice_payment/provider_router.py` itself (customer_router and
admin_router call different methods on the same service classes, not
these four).

## Explicitly excluded modules (not investigated in depth this slice)
`app.engines.serviceability.router`, `app.engines.admin_catalog.tenant_router`,
`app.engines.complaints.provider_router`, `app.engines.execution.real_estate_router`,
`app.engines.execution.coaching_router`, `app.engines.field_ops.checklist_router`,
`app.engines.field_ops.staff_router`, `app.engines.compliance.provider_router`,
`app.engines.platform_notifications.provider_router`, `app.engines.media.new_router`,
`app.engines.marketing_automation.provider_router`, `app.engines.customer_reviews.provider_router`,
`app.engines.profile.router`, `app.engines.admin_catalog.brand_provider_router`,
`app.engines.admin_catalog.recommendation_router`,
`app.engines.admin_catalog.service_option_provider_router`,
`app.engines.analytics.provider_router`, `app.engines.package_commerce.tenant_router`
— ranked in `remaining-module-priority-matrix.csv`, none selected, none modified.
