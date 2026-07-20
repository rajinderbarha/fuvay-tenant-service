# Current Job Mode

`CurrentJobScreen` (new, `src/screens/ux05/CurrentJobScreen.tsx`) is a focused single-job view distinct from
`JobDetailScreen` (which also handles browsing/accepting/rejecting/completing any assigned job, including ones
not yet started). Current Job mode reuses the same real `jobsApi`/`transitions.ts` state machine — no parallel
transition logic was invented.

## Layout
Header (job number, real status badge, `PipelineBadge`, plain-language "Current state" line) → real
`CustomerContactCard` + `AddressCard` (built from the same safe `BookingSummary`, no extra call) → completion
data if present → an inspection/checklist/parts/media placeholder block (intentionally not duplicating the real
interaction patterns already built in the three separate showcases — pointing there instead of maintaining two
divergent implementations of the same not-yet-backed workflow) → a sticky `NextActionBar` at the bottom showing
the single next real action.

## What it does NOT do
- `complete` and `reject` (the two actions requiring extra input — work summary/amount, or a reason) redirect
  the user to `JobDetailScreen`'s existing modal flow rather than reimplementing that input UI a second time —
  avoids two different code paths that could drift out of sync on a real, money-touching action.
- No offline-queueing of any action — `offline` state is a local placeholder (`useState(false)`), not yet wired
  to a real network-status detector (see `known-limitations.md`).
