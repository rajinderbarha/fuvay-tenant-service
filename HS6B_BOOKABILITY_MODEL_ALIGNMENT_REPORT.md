# HS6B — Bookability Model Alignment Report

## Fix
`_passes_full_eligibility_gate` now reads **only**
`provider_visibility_statuses.is_bookable` (computed by
`_evaluate_provider_bookability`, the exact function `POST /v1/provider/
status/refresh` calls) for every bookability-adjacent signal
(tenant active/suspended is still separately checked at the base-query
level via `Tenant.status`/`Tenant.suspended_at`, which is a distinct,
legitimate concern — vertical/account-status, not readiness). No second,
independent readiness calculation remains.

## Real bug confirmed and fixed
A real dev-DB tenant had `provider_enabled_offerings.status =
'pending_approval'` — an unrelated admin-approval workflow field —
which the OLD eligibility gate used as a hard requirement
(`status != "active"` → excluded). This tenant's canonical
`is_bookable` (HS4B) was `true`. **Live-verified**: before the fix,
this would have silently excluded a genuinely bookable tenant from
matching. After the fix, the same tenant is correctly included.

## Live verification (real DB, real function calls)
1. Real tenant, `is_bookable=true` (via canonical refresh) → **included**
   in matching results (`candidate_count: 1, excluded_count: 0`,
   provider selected).
2. Same tenant, `is_bookable` manually set `false` → **excluded**
   (`excluded_count: 1, signals: None`).
3. Restored via a real `POST /v1/provider/status/refresh` call (not a
   manual flip-back) → confirmed `is_bookable: true` again, proving the
   canonical computation is deterministic and correct both directions.

## Verdict
Bookability alignment: **complete**. Single canonical source, live-
verified to correctly gate matching in both directions.
