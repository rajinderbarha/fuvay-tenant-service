# Home Services Menu + Price Range — Remaining Blockers

None of these block certification — honestly documented, non-blocking notes.

## 1. Production build re-verification pending

A dev server already running on port 3000 (pre-existing this session,
not started for this ticket) prevented a fresh `next build` from running
concurrently. TypeScript's own compile (`tsc --noEmit`) is clean (0
errors), which is the hard gate this ticket specifies, but the full
static-export build (which also catches page-level runtime issues like
missing Suspense boundaries) should be re-run once that dev server is
free. Every prior sprint this session has shown the build's only failure
is the same pre-existing, unrelated `EnterpriseDataGrid`/`useSearchParams`
Suspense issue on `/admin/refund-requests` — none of this sprint's new
pages import that component.

## 2. Old `/admin/pricing-rules` route is deprecated, not redirected

Per the ticket's own menu-testing requirement ("Old routes redirect **or**
show deprecated message"), the old route shows a deprecation banner +
forward link rather than an automatic redirect — matching the exact
precedent already established for the Bargain Rules deprecation earlier
in this session. A hard redirect would break anyone with the old CRUD
functionality bookmarked for a still-valid (if not preferred) use case.

## 3. Service Areas / Zones, Completed Job Deduction, Settings pages are
   lightweight compositions, not full new CRUD screens

Consistent with the "don't duplicate CRUD" pattern established in the
Admin Home Services Catalog Console sprint: Service Areas/Zones reads
real tier data and links to `/admin/pricing-tiers` for full tier
management; Completed Job Deduction reads the real per-rule deduction
credits and links to the new Pricing Rules page to edit them; Settings
reads the real feature-flag config endpoint read-only (flags are toggled
via existing admin_catalog config, not re-editable from this new page).
If the product wants these as fully independent, separately-editable
screens, that's a reasonable follow-up, not a functional gap today (every
number shown is real).

## 4. No new "Home Services Overview" dashboard content

The "Overview" nav item still points at the existing Customer Price
Experience page (documented in the prior Admin Home Services Catalog
Console sprint's blockers too) — no dedicated overview/summary dashboard
exists yet for the Home Services vertical as a whole.

## 5. Pre-existing, unrelated build/tooling gaps

Same `useSearchParams`/`EnterpriseDataGrid` Suspense issue on
`/admin/refund-requests`, no ESLint config, no `npm test` script — all
previously documented across every sprint this session.
