# HS4B — Bookability Refresh Fix Report

## Root cause
`POST /v1/provider/status/refresh` (`app/engines/provider_portal/router.py`)
was a literal no-op stub:
```python
async def refresh_provider_status(...):
    return ok({"refreshed": True}, request_id=rid)
```
No computation, no DB write. Meanwhile `GET /v1/provider/status` read
from a real, pre-existing table (`provider_visibility_statuses`) that
had every field this ticket needed (`is_visible`, `is_bookable`,
`visibility_blockers`, `bookability_blockers`, `last_evaluated_at`) —
the table just never got written to after its initial (default) row, so
every tenant appeared permanently stuck at `is_visible=false,
is_bookable=false, last_evaluated_at=null` regardless of real setup
progress.

## Fix
Implemented `_evaluate_provider_bookability(db, tenant_id)` — a real
computation function reading actual signals:

| Check | Real source |
|---|---|
| Tenant not suspended/rejected | `tenants.status`, `tenants.verification_status`, `tenants.suspended_at` |
| Business profile complete | `tenants.business_name`, `address_line1`, `city` all non-empty |
| At least one published service | `tenant_services.setup_status='published'` |
| Provider price range configured | `tenant_services`/`tenant_service_types`/`tenant_service_brands` — any non-null `tenant_min_price` on a published service |
| Active service area | `tenant_service_areas.is_active=true` count > 0 |
| Availability configured | `provider_availability_rules.is_active=true` count > 0 |
| Usage credits available | `tenant_billing.credit_balance > 0` |
| Security deposit satisfied | `tenant_billing.security_deposit_paid=true` OR no deposit required (`security_deposit_amount` not set/zero) |

`POST /status/refresh` now calls this function and **upserts** the
result into `provider_visibility_statuses` (update if a row exists,
insert otherwise), then returns the persisted row plus `status`,
`passed_checks`, `failed_checks`, `warnings` — matching the ticket's
exact required response shape.

## No migration needed
`provider_visibility_statuses` already had every column the ticket
asked for (`is_visible`, `is_bookable`, `bookability_blockers`,
`visibility_blockers`, `last_evaluated_at`) — confirmed via `psql \d`
before writing any code. No schema change was required.

## Documented policy (per ticket's explicit request)
- **`is_bookable`** requires **all** critical checks: tenant active,
  business profile complete, ≥1 published+priced service, ≥1 active
  service area, ≥1 availability rule, positive usage-credit balance,
  security deposit satisfied.
- **`is_visible`** is a lighter bar: tenant active, business profile
  complete, ≥1 published service — a tenant can be discoverable
  (visible) before being fully bookable, matching the ticket's own
  suggested policy split.

## Live verification (real backend, real DB, this sprint)
1. Fresh refresh on the real seed tenant → `is_visible=false,
   is_bookable=false`, correctly flagged `BUSINESS_PROFILE_INCOMPLETE`
   (real: `address_line1` was empty) and `USAGE_CREDITS_INSUFFICIENT`
   (real: no `tenant_billing` row existed at all).
2. Fixed `address_line1` + inserted `tenant_billing` row with credits →
   `is_visible=true, is_bookable=true, status="bookable",
   failed_checks=[]`.
3. Set `tenants.suspended_at=now()` → `is_visible=false,
   is_bookable=false` (suspended gate works).
4. Cleared `suspended_at` → `is_bookable=true` again (restoration
   confirmed).

Each of these produced a real, different, correctly-computed response
— not a cached or fabricated value.

## Verdict
Bookability refresh: **fixed, real computation, live-verified against 4
distinct scenarios, persists to the real DB**. No longer a no-op.
