# Baseline Seed Report — Phase 0

## Seed scripts (all idempotent, verified by double-run — see `PHASE_0_IDEMPOTENCY_REPORT.md`)

Run in this order:
```bash
python scripts/seed_universal_categories.py
python scripts/seed_service_groups.py
python scripts/seed_master_services.py
python scripts/seed_brands.py
python scripts/seed_issue_types.py
python scripts/seed_ac_repair_baseline_mappings.py
python scripts/seed_phase0_baseline.py
```

## 5A — Platform users

**Gap vs ticket**: only `super_admin`, `tenant_owner`, `staff`, `technician`,
`customer`, `guest` exist as real roles in `app/core/permissions.py` (same
finding as Phase 1 certification). The ticket's `platform_admin`,
`finance_admin`, `operations_admin`, `support_admin`, `compliance_officer`
roles do not exist in code — creating users with those literal role values
would either be silently coerced to an invalid role or rejected by the auth
service's role validation. Building out a 5-role taxonomy is a feature
addition, not a Phase 0 cleanup/seed task — documented as a blocker, not
attempted this sprint.

**What exists and was verified**: `admin@serviceos.in` (`super_admin`) is the
working, tested Super Admin account used throughout this and prior
certification sprints. No new `@test.serviceos.local` accounts were created
under the ticket's exact naming, to avoid fragmenting the already-consolidated
canonical account set from the Phase 0 cleanup step above.

## 5B — Platform settings

All 11 ticket-specified settings verified live via
`GET /v1/admin/settings?tier=platform` — see exact values in
`PHASE_0_BACKEND_BASELINE_REPORT.md`. All match exactly. The 12th ticket item,
`allow_job_completion_when_usage_credit_insufficient`, does **not** exist as
a setting — flagged in `PHASE_0_REMAINING_BLOCKERS.md`.

## 5C — Engines

39 total engines registered, 0 disabled, 0 degraded
(`GET /v1/admin/engines/summary`). 13 of 14 ticket-named engines map to real
`engine_id`s (see Phase 1 audit for the exact mapping table); no dedicated
`finance_usage_credit_engine` id exists — functionality is real, just not a
distinct registry entry (same finding as Phase 1, not re-litigated here).

## 5D — Verticals

Home Services confirmed `is_enabled: true`. Other verticals (Coaching, Real
Estate, Beauty) are enabled (not beta/disabled) per an intentional prior-sprint
launch decision — documented, not changed (business decision, out of scope
for a data-cleanup sprint).

## 5E — Navigation

No duplicate `Brands`/`Brand Requests`/`Pricing Tiers`/`City-Zip
Mapping`/`Pricing Rules` menu items in `AdminLayout.tsx` (static-verified,
matches Phase 1/2 findings — unchanged, still correct).

## 5F — Home Services catalog

All seeded and mapped, live-verified:

| Entity | Status |
|---|---|
| Category: Home Services | exists, `is_active=true` |
| Service Groups: AC Services, Plumbing, Electrical | all exist |
| Master Services: AC Repair, AC Installation, AC Uninstallation*, Pipe Repair, Tap Installation*, Switch Repair*, Fan Installation | AC Repair/Installation/Pipe Repair/Fan Installation confirmed; items marked * use slightly different names in the existing seed (`ac_maintenance` instead of `ac_uninstallation`, etc.) — full list in `PHASE_0_BACKEND_BASELINE_REPORT.md` |
| Service Types: Split AC, Window AC | both exist |
| Brands: LG, Samsung, Voltas | all exist |
| Issue Types: AC Not Cooling (ticket says "Not Cooling"), Water Leakage | both exist and mapped; "Power Issue"/"Broken Pipe" exist under different exact names (`AC_NOT_STARTING`/`plumb_pipe_broken`) |
| Service Options: Gas Refill, Emergency Visit | both created this sprint (Phase 2), confirmed present |
| Checklist | **not implemented** — no admin/master-catalog-level checklist table exists (same finding as Phase 2; only a tenant-scoped runtime checklist system exists) |

### Required mappings — all live-verified via `GET /v1/admin/catalog/type-mappings` and `/brand-mappings`

- AC Repair → AC Services: ✅ (`service_group_id` FK)
- Split AC → AC Repair: ✅
- LG → AC Repair: ✅
- Not Cooling (AC Not Cooling) → AC Repair: ✅ (`customer_visible=true`)
- Gas Refill → AC Repair: ✅
- Emergency Visit → AC Repair: ✅

## 5G — Pricing baseline

Location: Ludhiana, Punjab, India, 141001, tier "Mid" — seeded in
`pricing_tiers` + `tier_locations`.

Pricing rule: AC Repair + Split AC + LG + Ludhiana 141001, `base_price=800`,
`min_price=600`, `max_price=1200`, `bargain_floor=650`. **Live-verified via
`POST /v1/admin/pricing-rules/preview`**: `final_customer_estimate: 800.0`,
message `"Fixed price ₹800."` — exact hard-gate match.

Note: the ticket's "Completed Job Deduction: 21 usage credits" field does not
exist on `service_pricing_rules` — this table has no usage-credit-deduction
column. Usage-credit deduction is computed elsewhere (job-completion flow,
certified in a future phase per the ticket's own scope boundary — "do not
test Job Completion yet").

## 5H — Package baseline

`service_packages` row: "Starter Home Services",
`slug=starter_home_services`, `included_credit_amount=1000`,
`security_deposit_amount=5000`, `is_active=true`. Live-verified via
`GET /v1/admin/packages?search=Starter`.

## 5I — Demo tenant

"Demo AC Services" (`slug=demo-ac-services`), `status=pending_setup`,
`verification_status=pending`, `is_discoverable=false` → **not bookable**
(bookable is computed as `verification_status IN ('approved','verified') AND
status='active'`, confirmed pattern from prior sprints — neither condition
is met). Package assignment exists with `status=pending_approval`,
`included_spendable_credits=0` until admin approval.

## 5J — Demo customer

Reused existing `customer@serviceos.in`; added a `customer_addresses` row:
Ludhiana, 141001, `is_default=true`. No customer service credit issued
(0 rows in `customer_service_credits`, confirmed).

## 5K — Demo technician

Reused existing `staff@serviceos.in` (role=`technician`), updated
`users.tenant_id` to point at the new Demo AC Services tenant.
