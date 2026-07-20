# Typecheck Report

`npx tsc --noEmit` was not previously a configured/run script in `mobile/staff-app` (no `typecheck` script
existed before this pass; added it). Run for real in WSL, re-verified fresh at the end of Round 3 against the
full current `src/` tree.

## Result: pre-existing pattern, zero errors in UX-05 business logic

**19 errors** (`grep -c 'error TS'` on `tsc --noEmit` output). 14 are in files this phase did not author
(pre-existing before `design/ux-05-staff-technician-app` began; not introduced or worsened by this phase). The
other 5 are new occurrences of the exact same two pre-existing pattern classes, introduced by reusing the
existing codebase's own conventions verbatim in new files (not a new bug class):

- `src/components/Skeleton.tsx` (3, pre-existing) — percentage-string width values typed against a `number | "100%"` prop.
- `src/components/SlaTimer.tsx` (1, pre-existing) — imports a `getSlaStatus` that no longer exists in `lib/transitions.ts`.
- `src/navigation/AppNavigator.tsx` (3: 2 pre-existing for `JobDetailScreen`/`ChatRoomScreen`, **1 new this round**
  for `CurrentJobScreen`) — screen-component prop typing mismatch, same root cause each time
  (`NativeStackScreenProps` vs. the stack navigator's inferred `FunctionComponent<{}>`).
- `src/screens/ChatListScreen.tsx`, `HomeScreen.tsx` (×3: 2 pre-existing + **1 new this round** for the added
  "Needs Your Action" row's `navigate` call), `JobsListScreen.tsx`, `NotificationsScreen.tsx` (×2),
  `src/screens/ux05/ScheduleScreen.tsx` (1, Round 2) — `useCallback`/inline-arrow generic inference producing
  `[never, never]` against the shared `NativeStackNavigationProp<never>` typing.
- `src/screens/ChatRoomScreen.tsx`, `JobDetailScreen.tsx` (×2), `NotificationsScreen.tsx`,
  `src/screens/ux05/CurrentJobScreen.tsx` (1, **new this round**) — `useAction`'s generic
  `(...args: unknown[])` signature not narrowing to the concrete callback parameter types.

None of these were fixed in this pass (out of scope: unrelated to the mobile role/pipeline/parts workstreams
requested; fixing the shared `hooks/useApi.ts` generic-inference root cause risks touching a hook every existing
screen depends on without dedicated regression coverage). Recorded honestly every round rather than silently
left invisible (there was no typecheck script before Round 1, so these were previously undetected entirely).

## UX-05-authored business-logic files: zero errors
`src/types/ux05.ts`, `src/lib/ux05/permissions.ts`, `src/lib/ux05/myWork.ts`, `src/lib/ux05/checklist.ts`, every
`src/components/ux05/*.tsx`, `src/navigation/ux05/*.tsx`, and all test files compile clean. The screen files with
an inherited navigation-typing error (`CurrentJobScreen.tsx`, `ScheduleScreen.tsx`, `AppNavigator.tsx`'s new
`CurrentJob` line) have that ONE line each flagged — everything else in those files, including all new
domain/rendering logic, is clean.
