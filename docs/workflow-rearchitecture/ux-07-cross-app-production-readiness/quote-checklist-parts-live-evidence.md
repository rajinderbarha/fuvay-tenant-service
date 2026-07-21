# Quote/Checklist/Parts Live Evidence — Round 3 (Workstream 2)

Audited from actual source (not re-derived from prior workstream docs),
cross-referenced with the real job's actual transition path this round.

## Checklist

`mobile/staff-app/src/lib/ux05/checklist.ts`'s own header comment states,
verbatim: **"API_CONTRACT_REQUIRED -- no live checklist-content endpoint
exists ... these operate purely on the typed view model ... even though
the data source is a design fixture today."** Confirmed by grep: no
`apiFetch`/`fetch(`/`/v1/` call exists anywhere in that file. The
`InspectionChecklistShowcaseScreen.tsx` and `ChecklistSection.tsx`
components consume this same fixture-only view model — real, honestly
pre-disclosed, unchanged this round. Our real job's transition graph
(`inspection_started -> inspection_done` via `start-inspection`/
`complete-inspection`) does NOT require or expose any checklist-content
payload at the API level — those two endpoints are simple state
transitions with no body, confirmed live this round (see
`status-transition-verification.md`).

## Quote

No `quote` API call exists in `mobile/staff-app/src/lib/api.ts` at all
(grep-confirmed). `QuoteShowcaseScreen.tsx` is, per its name and the same
pattern as the checklist screens, a fixture-driven dev showcase, not a
production-wired flow. Our real job never entered the `quote_required`
status this round (its real path was `service_started -> work_done ->
completed`, not through a quote branch) — consistent with there being no
real quote-creation endpoint to exercise even if it had.

## Parts requests

UNLIKE quote/checklist, parts-request endpoints ARE real and exist on the
TENANT-PORTAL side (confirmed in Round 1's `api-contract-audit.csv`):
`GET/POST /v1/provider/service-jobs/{id}/parts-requests`,
`.../parts-requests/{id}/approve`, `.../reject`, `.../install`. These are
provider/tenant-facing (approve/reject/record-install), matching the
canonical rule that technician NEVER marks installed. However,
`mobile/staff-app/src/lib/api.ts` has NO parts-request CREATE call
(grep-confirmed: no `parts-request` string anywhere in that file) — so the
technician-side "request parts" half of this real backend contract has NO
real frontend wiring in the staff app; only the tenant-side
approve/reject/install half is real and wired (in tenant-portal). This is
a real, previously-undocumented-in-this-precise-form finding: the backend
supports the full parts-request lifecycle, but the TECHNICIAN'S half of it
(actually creating a request) has no real client anywhere in this
codebase today — `PartsRequestShowcaseScreen.tsx` on staff-app is,
consistent with the naming pattern, a fixture-only showcase.

## Why this round's real job didn't exercise parts requests

The real job's path this round never needed replacement parts (a repair
job that completed via the direct `work_done -> completed` route) — there
was no in-flow trigger to create one, and even if there were, no real
staff-app client call exists to do so. Not exercised, honestly disclosed.

## Summary table

| Feature | Backend endpoint real? | Technician-side client real? | Tenant-side client real? |
|---|---|---|---|
| Checklist | NO (no content endpoint) | NO (fixture only) | not checked this round |
| Quote | NO (not found) | NO (fixture only) | not checked this round |
| Parts request CREATE | YES (`POST .../parts-requests`) | **NO** (no client call in staff-app) | n/a (technician-only per canonical rule) |
| Parts approve/reject/install | YES | n/a (technician never installs, per rule) | YES (tenant-portal's `api.ts` has all 3 real calls) |
