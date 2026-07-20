# Quote Checklist Module Lineage

## Exact module paths (not assumed — discovered)
```
app/engines/quote_checklist/
  __init__.py
  models.py            -- 7 SQLAlchemy tables (Sprint 22 "Quote Approval + Checklist Engine")
  constants.py          -- statuses, transitions, item types, event types, error codes
  quote_service.py       -- ServiceJobQuoteService
  checklist_service.py    -- ServiceChecklistService
  provider_router.py     -- 3 routers: provider_router, staff_router, checklist_router
  customer_router.py     -- customer_router
  admin_router.py        -- 2 routers: admin_router, admin_quote_router
  notifications.py       -- quote-sent / decision notification helpers
```

## Mounted routers (confirmed in `app/main.py`, lines 559-575)
| Router variable | Prefix | Persona |
|---|---|---|
| `qc_provider_router` | `/provider/quotes` | Tenant/provider (read + cancel) |
| `qc_staff_router` | `/staff/quotes` | Tenant/provider (full quote administration) |
| `qc_checklist_router` | `/staff/checklists` | Tenant/provider (checklist administration) |
| `qc_customer_router` | `/customer/quotes` | Customer (decision) |
| `qc_admin_router` | `/admin/checklist-templates` | Platform (super_admin) |
| `qc_admin_quote_router` | `/admin/quotes` | Platform (super_admin) |

## Parent pipeline — determined, not assumed
Every quote/checklist model's `job_id` resolves against **`app.engines.final_records.models.ServiceJob`** — confirmed by direct import in `quote_service.py` (`from app.engines.final_records.models import ServiceJob`) and `_get_job`'s query (`select(ServiceJob).where(ServiceJob.id == uuid.UUID(job_id))`). This slice's fix to `checklist_service.py::create_checklist` adds the identical import and lookup.

**This is NOT `field_ops.Job`.** `field_ops.Job` has its own, entirely separate `JobQuote` model (`app/engines/field_ops/models.py`) reached by `create_job_quote`/`send_job_quote`/`approve_job_quote`/`reject_job_quote`/`respond_to_quote` in `field_ops/router.py` — a distinct pipeline with its own table, its own state machine, and its own routes, already closed in the field_ops.router 28/28 closure from Slice 2F-14 series. See `field-ops-quote-alternate-audit.md` for the full boundary proof.

**Not Booking, not ServiceBooking directly** — `booking_id` is stored denormalized on every quote_checklist row (copied from `job.booking_id` at creation time) for query convenience, but no quote_checklist model has a direct FK relationship to `Booking`/`ServiceBooking`; all ownership and lifecycle logic operates through `ServiceJob`.

## Outcome
**ServiceJob quote workflow** — a distinct, standalone customer quote-approval and per-job checklist system, correctly separate from field_ops.Job's own quote capability, from Booking/ServiceBooking, and from PartsRequest (no reference exists — see `parts-request-boundary.md`). Not a disconnected scaffold: it has live frontend callers (`frontend/tenant-portal/lib/api.ts` for provider/staff, `frontend/customer-app/lib/api/customer-quotes.ts` for customer decisions) — see `frontend-mobile-exposure-audit.md`.
