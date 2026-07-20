# Typecheck Report

`npx tsc --noEmit` was not previously a configured/run script in `mobile/staff-app` (no `typecheck` script
existed before this pass; added it). Ran for real in WSL against the full `src/` tree after syncing this
pass's additions.

## Result: pre-existing errors found, zero errors in UX-05 code

15 errors surfaced, all in files this phase did not author (pre-existing before `design/ux-05-staff-technician-app`
began; not introduced or worsened by this pass):

- `src/components/Skeleton.tsx` (3 errors) — percentage-string width values typed against a `number | "100%"` prop.
- `src/components/SlaTimer.tsx` (1) — imports a `getSlaStatus` that no longer exists in `lib/transitions.ts`.
- `src/navigation/AppNavigator.tsx` (2) — screen-component prop typing mismatch for `JobDetailScreen`/`ChatRoomScreen`.
- `src/screens/ChatListScreen.tsx`, `HomeScreen.tsx` (×2), `JobsListScreen.tsx`, `NotificationsScreen.tsx` (×2) —
  `useCallback` generic inference producing `[never, never]` against `useApi`'s signature.
- `src/screens/ChatRoomScreen.tsx`, `JobDetailScreen.tsx` (×2), `NotificationsScreen.tsx` — `useAction`'s generic
  `(...args: unknown[])` signature not narrowing to the concrete callback parameter types.

None of these were fixed in this pass (out of scope: they are unrelated to the mobile role/pipeline/parts
workstreams requested, and fixing 6 pre-existing files' generic-inference issues in `hooks/useApi.ts` risks
touching a shared hook every existing screen depends on without dedicated regression coverage). Recorded honestly
rather than silently left invisible (there was no typecheck script before this pass, so these were previously
undetected).

## UX-05-authored files: zero errors
`src/types/ux05.ts`, `src/lib/ux05/permissions.ts`, `src/components/ux05/*.tsx`,
`src/screens/ux05/PartsRequestShowcaseScreen.tsx`, and both new test files compile clean under `tsc --noEmit`.
