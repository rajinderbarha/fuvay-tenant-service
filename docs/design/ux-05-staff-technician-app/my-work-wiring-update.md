# My Work — Wiring Update (Round 3)

`known-limitations.md` (Round 2) flagged that `myWork.ts`'s grouping logic existed and was tested but was not
wired into `JobsListScreen`'s render. This round closes that gap:

- `TABS` changed from the old `All/Assigned/Active/Completed/Cancelled` (an ad-hoc, screen-local status filter)
  to `All/Current/Today/Upcoming/Needs Action/Completed` — the exact same group set `HomeScreen` now also uses.
- Filtering logic changed from an inline `Set`/equality check to `groupJobs(all)[activeTab]`, i.e. the screen now
  calls the real, unit-tested function directly rather than re-implementing the classification.
- `MyWorkGroupKey` (`MyWorkGroup | "all"`) was added to `myWork.ts` as the shared type for both screens' tab
  state, so "all" (a UI-only concept, not a real job classification) can't leak into `groupJobs()`'s return type.

No behavior change to the underlying `jobsApi.myJobs()` call or the job-row rendering — this was purely a
grouping-logic consolidation.
