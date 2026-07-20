# Typecheck Report

`npx tsc --noEmit` was not previously a configured/run script in `mobile/staff-app` (no `typecheck` script
existed before this pass; added it). Run for real in WSL, re-verified fresh at the end of Round 2 (after
navigation/screens/components/showcases were added) against the full current `src/` tree — result unchanged
from Round 1: still exactly 15 errors, same locations.

## Result: pre-existing errors found, zero errors in UX-05 business logic

15 errors surfaced. 14 are in files this phase did not author (pre-existing before
`design/ux-05-staff-technician-app` began; not introduced or worsened by this pass). One new occurrence
(`src/screens/ux05/ScheduleScreen.tsx:57`) reuses the exact same `navigation.navigate("JobDetail" as never, {...}
as never)` pattern already present in `HomeScreen.tsx`/`JobsListScreen.tsx` — copied verbatim from the existing
codebase convention rather than a new class of bug; it shares the identical root cause (the shared
`NativeStackNavigationProp<never>` typing) as the 6 pre-existing `useCallback`/`useAction` generic-inference
errors below.

- `src/components/Skeleton.tsx` (3 errors) — percentage-string width values typed against a `number | "100%"` prop.
- `src/components/SlaTimer.tsx` (1) — imports a `getSlaStatus` that no longer exists in `lib/transitions.ts`.
- `src/navigation/AppNavigator.tsx` (2) — screen-component prop typing mismatch for `JobDetailScreen`/`ChatRoomScreen`.
- `src/screens/ChatListScreen.tsx`, `HomeScreen.tsx` (×2), `JobsListScreen.tsx`, `NotificationsScreen.tsx` (×2) —
  `useCallback` generic inference producing `[never, never]` against `useApi`'s signature.
- `src/screens/ChatRoomScreen.tsx`, `JobDetailScreen.tsx` (×2), `NotificationsScreen.tsx` — `useAction`'s generic
  `(...args: unknown[])` signature not narrowing to the concrete callback parameter types.
- `src/screens/ux05/ScheduleScreen.tsx` (1, new this round) — same `[never, never]` navigation-typing pattern as above.

None of these were fixed in this pass (out of scope: they are unrelated to the mobile role/pipeline/parts
workstreams requested, and fixing the pre-existing files' generic-inference issues in `hooks/useApi.ts` risks
touching a shared hook every existing screen depends on without dedicated regression coverage). Recorded honestly
rather than silently left invisible (there was no typecheck script before this pass, so these were previously
undetected).

## UX-05-authored business-logic files: zero errors
`src/types/ux05.ts`, `src/lib/ux05/permissions.ts`, `src/lib/ux05/myWork.ts`, `src/lib/ux05/checklist.ts`, every
`src/components/ux05/*.tsx`, every `src/screens/ux05/*.tsx` (aside from the one inherited navigation-typing line
in `ScheduleScreen.tsx` noted above), `src/navigation/ux05/*.tsx`, and all test files compile clean under
`tsc --noEmit`.
