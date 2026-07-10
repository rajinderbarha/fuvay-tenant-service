# Admin Frontend TypeScript Error Audit

## Result of `npx tsc --noEmit` at the start of this sprint

```
(no output)
exit code 0
```

Ran 3 times in a row to rule out flakiness (this repo has a concurrent process making live edits throughout this
session — confirmed again this sprint, see below) — all 3 runs returned 0 errors.

## What actually happened

The errors reported in the previous sprint's turn (`admin/tenants/[id]/page.tsx`, 16 errors: missing
`requestChanges`/`sendNotification` on the tenants API client, missing `owner_name`/`email`/`phone`/
`verification_status` on the `Tenant` type, an undefined `menuItemStyle` const, missing `settlement_status` on
`DisputeSettlement`) were **fixed by a concurrent process editing this same file/API-client between that report and
this sprint starting** — a pattern flagged repeatedly throughout this session (see memory: "another process actively
modifying the same repo concurrently"). Confirmed by grepping the current `lib/api.ts` for each missing
identifier — all 6 are now present:

| # | File | Symbol | Status now |
|---|---|---|---|
| 1 | `lib/api.ts:4509` | `adminTenantsApi.requestChanges` | present |
| 2 | `lib/api.ts:4514` | `adminTenantsApi.sendNotification` | present |
| 3 | `lib/api.ts:2591-2592` | `Tenant.owner_name` / `.email` / `.phone` / `.verification_status` | present |
| 4 | `app/admin/tenants/[id]/page.tsx:84` | `menuItemStyle` const | present |
| 5 | `lib/api.ts:917` | `DisputeSettlement.settlement_status` | present |

**No code changes were required to fix these particular errors** — they were already gone before this sprint's audit
ran. This is reported transparently rather than fabricating fixes for errors that no longer existed.

## Root cause classification (for the record, matching what the previous report described)

All 16 previously-reported errors were **API type-mismatch** errors (category: "API response types" / "tenant
summary fields", per Part A's requested classification) — the `page.tsx` file was written against an expected
`Tenant`/`adminTenantsApi` shape that the shared `lib/api.ts` hadn't caught up to yet. None were related to
Service Setup, component-prop mismatches, or enum mismatches.

## A second, real error surfaced mid-sprint (genuinely fixed here)

After the payment-breakdown edits to `admin/tenants/[id]/page.tsx` (Part C/D below), a full `npx tsc --noEmit` run
turned up 3 NEW errors — not in the `[id]` detail page, but in the sibling **tenants list** page:

| # | File | Line | Error code | Root cause | Fix applied | Category |
|---|---|---|---|---|---|---|
| 1 | `app/admin/tenants/page.tsx` | 748 | TS2352 | `adminTenantsApi.getSummary()` declared its `apiFetch` generic as `{ data: TenantsSummary }`, but `apiFetch<T>` already unwraps the backend's `{success,data}` envelope and resolves to `T` directly — double-wrapping made the runtime shape and the page's `as TenantsSummary` cast stop overlapping | Changed to `apiFetch<TenantsSummary>` in `lib/api.ts` | API type mismatch |
| 2 | `app/admin/tenants/page.tsx` | 749 | TS2352 | Same double-wrap bug on `adminTenantsApi.getInsights()` | Changed to `apiFetch<TenantsInsights>` | API type mismatch |
| 3 | `app/admin/tenants/page.tsx` | 751 | TS2352 | Same double-wrap bug on `adminTenantsApi.list()` | Changed to `apiFetch<{ items: TenantListItem[]; pagination: {...} }>` | API type mismatch |

This was a genuine, previously-undetected bug (every other `getSummary`/`getInsights`-style method in `lib/api.ts`
uses the correct un-wrapped generic — these 3 were the only ones written differently). It would have caused
`adminTenantsApi.getSummary()`/`getInsights()`/`list()` to actually return the real unwrapped data at runtime while
being *typed* as a wrapper object, meaning any code doing `summaryData.data.total` (trusting the wrong type) would
have thrown at runtime, or code doing `summaryData as TenantsSummary` (trusting the JS reality, as this page did)
would fail to type-check — exactly what happened. Fixed in `lib/api.ts`; verified `npx tsc --noEmit` clean across 2
repeat runs afterward. Regression test added: `test_admin_tenants_api_does_not_double_wrap_apifetch_generic`.

## A third bug: a TypeScript-invisible SQLAlchemy table collision that broke the whole backend

A second `npx tsc --noEmit` regression check (unrelated file: `app/admin/service-setup/templates/page.tsx`) surfaced
a wrong import path (`"../../../../lib/hooks"` instead of `"../../../../hooks/useApi"`) — fixed trivially. But
running the full backend `pytest` suite immediately after (to prove zero regressions, since TypeScript alone can't
catch backend breakage) turned up something far more serious: **`app/engines/admin_catalog/models.py` and
`app/engines/service_setup/models.py` both declared a SQLAlchemy model named `ServiceSetupTemplate` mapped to the
same table name (`service_setup_templates`)** — a concurrent process had added an entire new enterprise
multi-vertical service-setup engine (migrations 097/098) alongside the older Sprint 34F engine (migration 058)
without either being removed. This crashed Python import of `app.main` outright
(`sqlalchemy.exc.InvalidRequestError: Table 'service_setup_templates' is already defined for this MetaData
instance`), which meant **6 test files failed to even collect**, and — more importantly — **the live backend server
itself could not start**, silently invalidating every "0 TypeScript errors" claim since the actual running app was
broken underneath it.

Root-caused via the live DB's migration history (`alembic_version` = 097, and the live table schema matching the
NEW engine's columns, not the old one's) — the old Sprint 34F model was confirmed stale (its columns don't match
the live table, so its router would already 500 in production regardless of the collision). Fixed by renaming the
old model's table to `service_setup_templates_legacy_34f` (and its sibling item table similarly) — reversible,
additive, doesn't delete any code — then updated this repo's stale `test_sprint34f_service_setup_templates.py`
(9 assertions checking the OLD `templates/page.tsx`, which had also been rewritten to the new API) to match the
current, correct frontend implementation.

Two more schema-drift bugs of the same class surfaced once the backend could actually run: `admin_bulk_setup_runs`
and `service_setup_bulk_runs` were both missing an `updated_at` column their ORM models expect (inherited from
`ServiceOSBase`) — fixed via new migration `099_admin_bulk_setup_runs_updated_at.py`. A third stale test file
(`test_sprint34h_bulk_setup.py`, 7 assertions) was updated the same way for the same reason (its `bulk-wizard` and
`bulk-runs` list pages had also been rewritten to a newer `bulkWizardApi`).

## Work done this sprint

1. Confirmed the previously-reported 16 tenant-detail-page errors were already resolved (see above).
2. Found and fixed the `adminTenantsApi` double-wrap bug in the sibling tenants list page — blocked a clean
   whole-project `tsc` pass.
3. Found and fixed a wrong hooks-import path in `service-setup/templates/page.tsx`.
4. Found and fixed a SQLAlchemy table-name collision that crashed the entire backend app on import (invisible to
   TypeScript, only caught by actually running the Python test suite) — renamed the superseded Sprint 34F model.
5. Found and fixed 2 missing `updated_at` columns (`admin_bulk_setup_runs`, `service_setup_bulk_runs`) via new
   migration 099 — both 500'd on every real API call.
6. Rewired the Service Setup hub page to the current, live-schema-matching APIs (`serviceSetupTemplatesApi`,
   `bulkWizardApi`) instead of the superseded ones it was originally built against.
7. Updated 2 stale legacy test files (16 assertions total) to match the current frontend implementation, with
   comments explaining why, rather than silently leaving them failing or reverting working new code.
8. Fulfilled Part C/D of the ticket — extended the Tenant Detail page's *payment breakdown* field coverage (Bookings
   and Jobs tables), which was incomplete even though it compiled cleanly (a missing field on a type is not a TS
   error if the code never reads it).
