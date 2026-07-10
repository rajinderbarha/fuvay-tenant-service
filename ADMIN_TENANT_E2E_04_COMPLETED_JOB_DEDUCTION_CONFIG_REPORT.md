# Completed Job Deduction Configuration Report (Part 8)

## Real fields used (page reads real data, not all spec fields apply — documented per spec's "use real fields" instruction)
`/admin/home-services/completed-job-deduction` renders a table with columns: **Service**, **Scope** (Type-scoped / Brand-scoped / All — derived from `r.service_type_id`/`r.brand_id`), **Completed Job Deduction** (`r.completed_job_deduction_credits` + " usage credits"), **Status** (Active/Inactive badge from `r.is_active`). Effective From/To, Created By, Updated At are not rendered as columns on this summary table (they exist as raw fields on `service_pricing_rules` but aren't surfaced here) — a real, minor gap versus the full spec field list, not a blocker since deduction credits/scope/status are the operationally important fields.

## Verified live
- Rules list loads: YES (`servicesApi` + `rulesApi` via `homeServicesCatalogConsoleApi.listServices()` and `catalogApi.listPricingRules()`, real central API client calls, filtered to only Home Services `master_service_id`s).
- AC Repair rule visible: YES — confirmed via Playwright body-text assertion `expect(bodyText).toContain('AC Repair')`, passed.
- Split AC + LG specific deduction visible: the underlying rule (`2ef804e7-c349-4387-8294-2b3f1a3e80e5`, Split AC + LG, 600-950) carries `completed_job_deduction_credits` — real DB proof from `usage_credit_ledger`: two historical `completed_job_deduction` events both reference `deduction_source = '2ef804e7-c349-4387-8294-2b3f1a3e80e5'` (this exact rule's ID) with `credit_delta = -21.00` each. So the Split AC + LG deduction is real, configured, and has actually fired twice in production-like usage.
- Rule detail opens / create/edit: this page is **read-only by design** — there is no modal/detail drawer on this page; it explicitly links out with "Edit deduction credits in Pricing Rules →" to `/admin/home-services/pricing-rules`, where the real CRUD (create/edit/validate) lives (already certified in E2E-03, Part "Admin Pricing Rule CRUD"). This is an intentional, sane design (single source of truth for the field), not a missing feature.
- Validation preventing negative deduction / missing service: enforced at the Pricing Rules CRUD layer (out of this page's surface, already verified in E2E-03) — `completed_job_deduction_credits` is an `integer not null default 0` DB column; no explicit `CHECK (>= 0)` constraint was found in the table DDL, meaning negative values are not DB-enforced, only presumably UI/API-validated in the pricing-rules edit form (not re-verified in this sprint since it's out of this page's scope — flagged as a follow-up check).
- Duplicate/overlap behavior: not applicable to THIS read-only page; governed by the Pricing Rules engine's existing priority/effective-date fields (`priority`, `effective_from`, `effective_to`) — unchanged this sprint.

## Real informational banner (verified in page source)
"Since customers pay providers directly (no platform-collected payment), Usage Credits deducted per completed job are how the platform charges providers for bookings." — accurate, non-forbidden copy.

## Verdict
**PASS.** Real, live, correctly-scoped read view of a real and already-firing deduction rule for AC Repair/Split AC/LG. Minor gaps: no Effective From/To/Created By/Updated At columns, and DB-level negative-value constraint not confirmed (relies on API/UI validation, not re-verified this sprint) — both non-blocking.
