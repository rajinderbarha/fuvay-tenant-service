# CUSTOMER-FRONTEND-01 — Customer Safety Report

## Scan performed
```
grep -rniE "admin_min_price|admin_max_price|provider_min_price|provider_max_price|internal_score|ranking_score|bookability_score|usage_credit_balance|completed_job_deduction|commission|security_deposit|ledger|audit|excluded_providers|debug|source_table" frontend/customer-app/app frontend/customer-app/components frontend/customer-app/lib
```
Result: **zero matches** (confirmed 2026-07-09 in this session).

## How each field is prevented from ever reaching the customer, structurally
- `internal_score`/`ranking_score`/`bookability_score`: the real backend endpoint
  `match_and_price` is called with `reveal_internal_score=False` hardcoded in
  `home_service_booking/customer_router.py` — the frontend has no code path that
  could display it even if the flag were flipped, since `ProviderCard` only
  destructures `provider_name`, `rating`, `review_count`, `public_badges`/`badges`,
  `city`/`service_area`, `estimated_visit_window`.
- `admin_min_price`/`admin_max_price`/`provider_min_price`/`provider_max_price`:
  `PriceStep` only reads `options.low`/`options.mid`/`options.high` from the
  match response; no other keys are ever read or rendered.
- `usage_credit_balance`/`completed_job_deduction`/`commission`/`security_deposit`/
  `ledger`/`audit`: none of these fields are referenced anywhere in
  `lib/api/customer-home-services.ts` or any page/component. The booking detail
  endpoint itself (`home_service_assignment/customer_router.py`) only exposes
  `_customer_safe_provider()` output (provider_name/rating/public_badges) plus
  booking_number/status/assignment_message/price snapshot's selected tier+amount
  — the backend itself never returns these internal fields to this endpoint, so
  there is nothing for the frontend to accidentally leak.
- `excluded_providers`: never requested; the matching endpoint returns exactly
  one selected provider, never a list of candidates or exclusions.
- `debug`/`source_table`: no debug/admin permission is ever sent by this app
  (only a customer JWT), and no code inspects or renders such keys.

## Verified live (see Live API Verification Report)
The real `/v1/customer/bookings/{booking_id}` and `/tracking` handlers were read
in full; both explicitly build minimal customer-safe dicts server-side
(`_customer_safe_provider()`, `_safe_event_label()`) rather than passing through
raw model objects, which is a strong structural guarantee independent of what
the frontend does.

## Residual risk
This scan is static (source grep) — it does not prove no *future* backend
response could add a new leaking field, since some fields in the API module
(e.g. `matchResult.provider`) are typed as `any` for pragmatism. If the backend
changes to return an internal field under a differently-named key not in the
scan list above, it would render only if a component destructures it by name —
today no component does. Recommended follow-up: add explicit TypeScript
interfaces (not `any`) for provider/price responses so any new field must be
deliberately added to a type before it can be rendered.
