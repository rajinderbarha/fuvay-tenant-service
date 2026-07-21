# Tenant Onboarding Live Verification — Round 2 (Workstream 8)

Using the same real demo tenant from Round 1 (`5209ef33-a53e-4fc0-b3f6-006335b8d712`,
"Demo AC Services", `provider@serviceos.local`). NO production tenant data
touched; no write/mutation calls made against onboarding state this round —
read-only verification only.

## Real, live findings

- `GET /v1/provider/onboarding/status` -> real response:
  `progress_percent: 0`, `total_items: 0`, `onboarding_ready: false`,
  `blockers: []`, `next_action: null`.
- `GET /v1/provider/onboarding/items` -> real response: `items: []`,
  `count: 0`.
- `GET /v1/provider/onboarding/package-summary` -> real response:
  `has_package: true`, `status: "pending_review"`, `paid_at: null`,
  `approved_at: null`, `activated_at: null`, `included_credits: 1000.0`.

## Honest interpretation

This demo tenant shows **0 onboarding checklist items and a package status
of `pending_review`** (never approved/activated) via the real onboarding
API, YET it is genuinely operational: it has a real, live, currently
`accepted`-status `ServiceJob` (from Round 1's E2E proof), a real assigned
technician, and real pricing rules. This is a real, disclosed
inconsistency between this tenant's onboarding-checklist state and its
actual operational state.

**Most likely explanation** (not fully confirmed this round): this tenant
was created directly via a database/seed script for prior UX-phase demo
purposes (not through the real `/v1/public/register/*` -> platform-review
-> approval pipeline), so no onboarding-checklist rows were ever generated
for it, and its package assignment was probably manually inserted rather
than progressed through the real payment/approval flow. This would explain
the `pending_review`/no-timestamps state coexisting with real operational
data.

**What this does NOT prove**: this is NOT evidence of an "accidental
marketplace activation before required approval" bug in the REAL
registration pipeline — this specific tenant simply didn't go through that
pipeline. Whether a tenant that genuinely completes real registration
today could similarly end up "operational" while its package sits at
`pending_review` was not tested this round (would require actually
registering a brand-new tenant end-to-end, which was judged too large an
undertaking for this round's remaining budget) — flagged as a real,
specific, worthwhile check for a future round in `deferred-workstreams.md`.

## Not verified this round

- Save-and-resume behavior, missing-section guidance UI, and the actual
  approved/rejected/changes-requested UI presentation — none of these were
  exercised (no browser session, no new tenant registered). Deferred with
  the rest of the Playwright-dependent work.
- Super-admin's side of platform review (approve/reject a real pending
  tenant) was NOT attempted — the demo tenant is not actually in a
  reviewable state via the real onboarding pipeline (see above), and
  creating a genuinely fresh registration to test approval was out of this
  round's time budget.
