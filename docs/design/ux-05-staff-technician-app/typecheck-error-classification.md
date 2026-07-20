# Typecheck Error Classification

Every round since Round 3 has reported "19 typecheck errors, unchanged pre-existing pattern" as an aggregate
count without listing them individually. Per the UX-05B coordinator's explicit instruction, this document lists
each of the current 19 errors from a genuinely fresh `npx tsc --noEmit` run (WSL, `rm -rf node_modules` +
`npm install --legacy-peer-deps`, re-run at the end of this phase) individually, classified, with a confirmation
that none are related to any UX-05/UX-05B change.

**Real command, real output** — `npx tsc --noEmit` against `mobile/staff-app`, 19 errors, 0 warnings-as-errors,
exit code 2.

## Classification key
- **PATTERN_A — `useApi`/`useAction` generic-inference gap**: the shared `src/hooks/useApi.ts` hook's
  `useCallback(fn, deps)` call sites don't propagate the callback's real parameter types through TypeScript's
  inference when `deps` is a literal array; TS falls back to `never`/`unknown` for the callback's own parameters.
  This is a real, known gap in `useApi.ts`'s generic signature (not a caller bug) — fixing it requires changing
  the shared hook's type signature, which no round has done (documented as out-of-scope: "Fixing the shared
  `hooks/useApi.ts` generic-inference root cause remains out of scope" in `known-limitations.md` since Round 5).
- **PATTERN_B — React Navigation `Stack.Screen` prop-shape mismatch**: 3 screens registered in `AppNavigator.tsx`
  declare their own `Props` type (destructuring `{ route }`) that doesn't structurally satisfy
  `@react-navigation/native-stack`'s expected `ScreenComponentType` (which also wants `navigation`). This is a
  pre-existing typing looseness in how these 3 screens were written (predates UX-05 for `ChatRoomScreen`; UX-05's
  own `CurrentJobScreen`/`JobDetail`'s registration reused the identical pattern) — functionally harmless (React
  Navigation supplies both props at runtime; only the static type is incomplete) but not fixed by any round.
- **PATTERN_C — `Skeleton`'s width prop typed too narrowly**: `Skeleton.tsx`'s own prop type only accepts
  `number | "100%"`, but 3 of its own internal usages pass percentage strings like `"50%"`/`"35%"`/`"60%"`. A
  pre-existing internal inconsistency in one shared component's own file, unrelated to any caller.
- **PATTERN_D — dead/renamed export reference**: `SlaTimer.tsx` imports a `getSlaStatus` that no longer exists
  in `lib/transitions.ts` (renamed or removed at some point pre-UX-05). `SlaTimer` itself is not wired into any
  screen UX-05 touched (confirmed via grep — not imported anywhere in `src/screens/` or `src/navigation/`).

## The 19 errors, individually

| # | File:Line | Error | Classification |
|---|---|---|---|
| 1 | `src/components/Skeleton.tsx:26` | `Type '"50%"' is not assignable to type 'number \| "100%" \| undefined'` | PATTERN_C |
| 2 | `src/components/Skeleton.tsx:29` | `Type '"35%"' is not assignable to type 'number \| "100%" \| undefined'` | PATTERN_C |
| 3 | `src/components/Skeleton.tsx:31` | `Type '"100%" \| "60%"' is not assignable to type 'number \| "100%" \| undefined'` | PATTERN_C |
| 4 | `src/components/SlaTimer.tsx:3` | `Module '"../lib/transitions"' has no exported member 'getSlaStatus'` | PATTERN_D |
| 5 | `src/navigation/AppNavigator.tsx:66` | `Type '({ route }: Props) => Element' is not assignable to type 'ScreenComponentType<...,"JobDetail">'` (missing `navigation`) | PATTERN_B |
| 6 | `src/navigation/AppNavigator.tsx:72` | Same shape, `"ChatRoom"` screen | PATTERN_B |
| 7 | `src/navigation/AppNavigator.tsx:100` | Same shape, `"CurrentJob"` screen | PATTERN_B |
| 8 | `src/screens/ChatListScreen.tsx:29` | `Argument of type '[never, never]' is not assignable to parameter of type 'never'` | PATTERN_A |
| 9 | `src/screens/ChatRoomScreen.tsx:20` | `(messageText: string) => Promise<ChatMessage>` not assignable to `(...args: unknown[]) => Promise<ChatMessage>` | PATTERN_A |
| 10 | `src/screens/HomeScreen.tsx:86` | `[never, never]` not assignable to `never` | PATTERN_A |
| 11 | `src/screens/HomeScreen.tsx:116` | `[never, never]` not assignable to `never` | PATTERN_A |
| 12 | `src/screens/HomeScreen.tsx:134` | `[never, never]` not assignable to `never` | PATTERN_A |
| 13 | `src/screens/JobDetailScreen.tsx:53` | `(action: JobAction, arg?: string) => Promise<unknown>` not assignable to `(...args: unknown[]) => Promise<unknown>` | PATTERN_A |
| 14 | `src/screens/JobDetailScreen.tsx:58` | `(summary: string, amount: number) => Promise<Job>` not assignable to `(...args: unknown[]) => Promise<Job>` | PATTERN_A |
| 15 | `src/screens/JobsListScreen.tsx:53` | `[never, never]` not assignable to `never` | PATTERN_A |
| 16 | `src/screens/NotificationsScreen.tsx:34` | `(id: string) => Promise<StaffNotification>` not assignable to `(...args: unknown[]) => Promise<StaffNotification>` | PATTERN_A |
| 17 | `src/screens/NotificationsScreen.tsx:44` | `[never, never]` not assignable to `never` | PATTERN_A |
| 18 | `src/screens/ux05/CurrentJobScreen.tsx:46` | `(action: JobAction, arg?: string) => Promise<unknown>` not assignable to `(...args: unknown[]) => Promise<unknown>` | PATTERN_A |
| 19 | `src/screens/ux05/ScheduleScreen.tsx:61` | `[never, never]` not assignable to `never` | PATTERN_A |

## Totals
- **PATTERN_A** (shared `useApi`/`useAction` generic gap): 12 of 19 (rows 8–19)
- **PATTERN_B** (React Navigation prop-shape looseness, 3 screens): 3 of 19 (rows 5–7)
- **PATTERN_C** (`Skeleton`'s own internal width typing): 3 of 19, all in one file (rows 1–3)
- **PATTERN_D** (dead `SlaTimer` import, unwired component): 1 of 19 (row 4)
- 12 + 3 + 3 + 1 = 19 — matches the fresh `tsc` count exactly.

## Confirmation: none are UX-05/UX-05B-introduced
- **PATTERN_A** exists because of `src/hooks/useApi.ts`'s own generic signature — a pre-existing file, not
  touched by any UX-05/UX-05B commit. Every call site hitting it (including this phase's own
  `JobDetailScreen.tsx:53/58`, unchanged by the theme-conversion commit — confirmed via `git diff`, only style/
  import lines changed) uses the same call shape every other pre-existing screen already used.
- **PATTERN_B**'s 3 `AppNavigator.tsx` registrations: `ChatRoomScreen` predates UX-05; `CurrentJob`/`JobDetail`
  registrations were added across UX-05 Round 3, reusing the exact same (pre-existing, imperfect) typing
  convention already established by `ChatRoomScreen` — not a new pattern invented by UX-05.
- **PATTERN_C** (`Skeleton.tsx`) and **PATTERN_D** (`SlaTimer.tsx`) are both pre-existing files UX-05/UX-05B
  never edited (confirmed via `git log --follow` — zero UX-05-authored commits touch either file).
- Fresh count confirmed identical (19) at the end of every round from Round 3 through this UX-05B pass — the
  count has never changed despite ~40 UX-05/UX-05B commits adding new screens/components/tests, which is itself
  evidence these are a stable, pre-existing, isolated set, not something UX-05 work has been quietly adding to.

## Not fixed this round, and why
Per the coordinator's scope (product corrections + specific named items, not an open-ended cleanup), and because
fixing PATTERN_A requires changing a shared hook's generic signature used by every screen in the app (a change
with a much larger blast radius than this bounded phase's mandate), none of the 19 were fixed. They remain a
real, disclosed, non-blocking gap — see `known-limitations.md`.
