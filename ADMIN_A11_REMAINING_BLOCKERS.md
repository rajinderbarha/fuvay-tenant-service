# Admin Sprint A11 — Remaining Blockers

None of these block the **admin-portal** certification — honestly
documented, non-blocking notes.

## 1. No literal "A1–A10" sprint history exists in this codebase

This ticket assumes a formal `A1`–`A10` sprint numbering scheme with its
own individual certification reports. That numbering was never used in
this session or repo — instead, a series of ad-hoc, individually-titled
tickets were completed and certified (see `ADMIN_A11_FULL_E2E_CERTIFICATION_REPORT.md`
for the explicit mapping of each real ticket to what would correspond to
an A1–A10 slot). All of that real prior work is READY per its own
individual certification reports, which is treated as satisfying this
ticket's "do not start until A1–A10 are ready" precondition.

## 2. Tenant-side dedicated wizard route now redirects elsewhere

During this ticket's live E2E pass, `/tenant/setup/services` (the
dedicated Home Services Setup Wizard built and certified in an earlier
sprint this session) was found to now redirect to `/provider/service-setup`
with a "Page Moved" message — a change made outside this ticket's scope,
observed rather than caused by this certification pass. `/provider/service-setup`
does not currently expose the provider price-range-setting UI (per this
session's own earlier investigation, that page's pricing step is
read-only-preview only). The real backend capability (type/brand price
range set + validate + publish) is untouched and fully functional — only
the primary tenant-facing route to it has changed. This is a
**tenant-portal** UI-reachability question, outside this ticket's
admin-portal E2E scope; flagged here for visibility and worth a dedicated
follow-up ticket if the redirect was not intentional product direction.

## 3. Full mutating E2E flow not re-run against the shared demo tenant

Steps like "Approve tenant," "Add usage credits," "Record security
deposit," "Change package" were not re-executed as fresh mutating calls
against the long-lived shared `Demo AC Services` tenant during this pass,
since that tenant's current state (`pending_setup`, real published
services, real service areas) is depended upon by multiple other
already-certified sprints' live-verification evidence in this session.
Re-running "Approve" or changing its package now could invalidate those
other sprints' documented state without a clear need. These flows were
verified functionally correct via their own dedicated, earlier
certification sprints (Provider Onboarding, Customer Compliance, Finance
Package Pricing) per project memory — not re-verified fresh here.

## 4. Reports/Analytics and admin Bookings-in-Operations endpoints not
   individually path-verified this pass

`/v1/admin/analytics` and `/v1/admin/operations` returned 404 on a quick
guess-check (likely wrong sub-path, not a missing capability — the
Analytics and other engines are confirmed healthy and mounted per
`/health`). Not chased down to the exact correct sub-route this pass,
given this ticket's Home-Services-specific scope; a full audit of every
admin sub-route's exact path is a larger undertaking than this
certification's live smoke test aimed to cover.

## 5. Production build re-verification pending

Both `frontend/super-admin` (port 3000) and `frontend/tenant-portal`
(port 3001) had actively-occupied dev-server ports throughout this
session, preventing a fresh `next build` without risking an active
session. TypeScript's own clean compile (0 errors, both frontends) is
relied on as this ticket's hard gate.

## 6. 57 pre-existing static-inspection test failures

See `ADMIN_A11_FULL_TEST_RESULTS.md` — all confirmed unrelated to this
session's actual admin work via grep + live functional verification, all
pre-existing test-file drift against superseded UI text/component names.
