# React Version-Pin Mismatch Investigation — Round 3 (Workstream 5)

## Background

Round 2 found `frontend/tenant-portal` pins `react`/`react-dom: 19.2.7`
while `frontend/super-admin` pins `19.2.0` — a real mismatch causing a
duplicate-React-instance bug (`Invalid hook call`) in 3 of tenant-portal's
16 test suites. Round 2 deliberately deferred fixing it, citing the
UX-05 react-test-renderer precedent (a root-level `overrides` pin) as the
candidate safe fix but not attempting it due to time budget.

## What was actually tried this round

Added a root `package.json` `"overrides": {"react": "19.2.0", "react-dom":
"19.2.0"}` (matching super-admin's already-verified-working pin) and did a
genuinely fresh install (`rm -rf node_modules` at every level +
`package-lock.json`, full reinstall).

### Result: made things WORSE, not better — real, reproducible evidence

Before the override: **3 of 16 suites failed** (`PartsRequestList`,
`PartsRequestSummary`, and one more — `Invalid hook call`).

After the override + fresh install: **5 of 16 suites failed** — a
DIFFERENT and worse failure: `Error: Cannot find module 'react'` inside
`frontend/packages/design-system/node_modules/lucide-react/dist/cjs/
lucide-react.js`. The override successfully deduplicated the two
`react`/`react-dom` copies down to matching `19.2.0` versions in both
`tenant-portal/node_modules/react` and `super-admin/node_modules/react`
(confirmed via direct `cat package.json | grep version` on both) — but in
doing so, it changed npm's hoisting decisions enough that
`design-system`'s own dependency `lucide-react` (which the design system
re-exports icons from) lost its ability to resolve `react` at all,
breaking a DIFFERENT, previously-passing set of tests.

## Decision: REVERTED this round

The override was reverted (`package.json` restored to its Round 2 state,
no `overrides` field) and a fresh install was re-run to restore the known
baseline. **This is NOT the same, safely-applicable fix pattern as UX-05's
react-test-renderer override** — that fix targeted a single dev-only test
dependency (`react-test-renderer`) with no other package depending on it
in a way that would be affected by hoisting changes. THIS mismatch
involves `react`/`react-dom` themselves, which are foundational
dependencies of `next`, `design-system`, AND `lucide-react` simultaneously
— forcing a single version via `overrides` has cascading hoisting effects
across the whole workspace that a one-line override cannot safely predict
without a full audit of every workspace member's dependency tree.

## Firmer reason for continuing to defer (per the brief's explicit "or
provide a firmer reason" option)

A genuinely safe fix here requires one of:
1. **Aligning the actual `package.json` pins** (not just an override) —
   i.e., changing `tenant-portal`'s own `react`/`react-dom` dependency
   declaration from `19.2.7` to `19.2.0` directly (or vice versa on
   super-admin) — and then doing a full `next build` verification on
   BOTH apps to confirm neither breaks. This was not attempted this round
   because a `next build` run for both apps (on top of everything else
   this round covered) did not fit the remaining time budget, and doing
   the pin-only edit WITHOUT the build verification would violate the
   brief's own standing rule against unverified version changes.
2. **A design-system-scoped fix**: adding `lucide-react` as an explicit
   peer/dev dependency resolution inside `design-system`'s own
   `package.json` so it doesn't rely on ambient hoisting — a more
   surgical fix than a blanket workspace override, not attempted this
   round (would need its own verification cycle).

## Recommendation for Round 4

Attempt fix option 1 above (direct pin alignment + full `next build` on
both apps) as a dedicated, isolated piece of work with enough time
budgeted to run both builds to completion and re-verify all 16
tenant-portal test suites afterward — do not attempt a rushed override
again without that build verification step.
