# Keyboard / Focus Report

Real browser evidence, 2 targeted tests (each run across 3 projects, 6
executions total, all passing):

1. **parts-approval**: the Approve button (now genuinely rendered thanks
   to this pass's fixture fix — see `prerequisite-bug-fix-report.md`) is
   reachable via `.focus()` and confirmed via `toBeFocused()`; `Enter` is
   pressed on it without throwing.
2. **parts-list**: the search input is focused and confirmed; `Tab` moves
   focus to the status `<select>`, confirmed via `toBeFocused()` — proving
   a sane, linear tab order between the two filter controls.

**Not tested this pass** (real, stated limitations): Escape-closes-overlay
and focus-trap-and-return, because no UX-04/04A/04B showcase route renders
a modal/drawer (same scope note as `hydration-verification-report.md`).
Disabled-action-does-not-activate was not separately browser-tested this
pass (covered at the unit-test level instead — `PartsRequestSummary.test.tsx`
and `PartsRequestList.test.tsx` assert that when an action is unavailable,
no button renders at all, which is a stronger guarantee than "disabled
button doesn't activate").
