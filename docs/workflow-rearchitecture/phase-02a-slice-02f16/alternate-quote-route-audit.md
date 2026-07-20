# Alternate Quote Route Audit (Other Modules)

Searched for any route outside `quote_checklist` and outside `field_ops` (already audited separately, see `field-ops-quote-alternate-audit.md`) that reaches `ServiceJobQuote`/`ServiceJobQuoteItem`/`ServiceJobChecklist`/`ServiceJobChecklistItem` by ID.

- **ServiceJob routers** (`app/engines/final_records/*`) — repo-wide search for `ServiceJobQuote`/`ServiceJobChecklist` imports outside `quote_checklist` finds none. `final_records` exposes `ServiceJob` itself but does not reach into quote/checklist tables.
- **ServiceBooking routers** — no reference.
- **Provider Portal** (`app/engines/provider_portal/*`) — no reference to quote_checklist models.
- **Tenant Portal backend routes** — quote_checklist IS the tenant-portal's quote backend (this module); no OTHER tenant-portal-facing router duplicates this capability.
- **Customer routers elsewhere** — no other customer router references `ServiceJobQuote`.
- **Inspection engines** — no dedicated "inspection" engine exists separate from `quote_checklist`'s own `ServiceJobChecklist` (checklist_type can be `"inspection"`, but this is a value within the SAME model, not a separate inspection table/router).
- **Booking routers** — no reference (confirmed also in `quote-parent-pipeline-boundary.md`).
- **Invoice/payment routers** — `app.engines.invoice_payment.invoice_service` DOES reference `ServiceJobQuote`/`ServiceJobQuoteItem` directly (`_copy_from_quote`, used by `create_invoice` when `source="approved_quote"`) — this is a real, one-directional read integration, not a route duplicating quote_checklist's own mutation surface. It had a same-record bypass (no tenant/status validation on the referenced quote) which is fixed this slice — see `quote-financial-boundary.md`. This is the ONE exception to "no other module reaches quote_checklist records"; it is a READ-only cross-reference (copies items into a NEW invoice row, never mutates the source quote), not an alternate mutation path for the quote itself.
- **Admin routes** — `quote_checklist.admin_router` IS the admin surface for this module (already inventoried); no OTHER admin router reaches these tables.
- **Internal workers** — no background/worker job scheduler references quote_checklist models (searched for `ServiceJobQuote`/`ServiceJobChecklist` usage outside `app/engines/quote_checklist/`).

## Conclusion
**No mounted same-record mutation outside `app.engines.quote_checklist`'s own 3 routers exists.** This is a genuinely self-contained module with a single set of entry points, all inventoried and classified in `quote-checklist-final-route-inventory.csv`.
