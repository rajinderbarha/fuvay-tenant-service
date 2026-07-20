# Offline / Weak-Network Strategy

See `offline-operation-matrix.csv` for the per-operation category table (unchanged this round). This doc covers
the Round 5 additions: real network detection and real draft persistence.

## Network detection (Round 5 — investigated and added for real)
Investigated `@react-native-community/netinfo` per the coordinator's request rather than deferring by default:
- `npm info @react-native-community/netinfo peerDependencies` → `{"react":"*","react-native":">=0.59"}` —
  permissive, no conflict with this app's pinned `react@19.2.3`/`react-native@0.85.0`.
- Installed for real (`npx expo install @react-native-community/netinfo`, version `12.0.1`), verified with
  `npx tsc --noEmit` (zero new errors) and `npx jest` (43/43 passing).
- `src/hooks/useNetworkStatus.ts` rewritten to use `NetInfo.addEventListener` + `NetInfo.fetch()` instead of
  Round 4's `navigator.onLine`-only implementation. NetInfo has its own web implementation (same underlying
  browser APIs), so this single hook now covers **both** native and web with one real dependency, closing the
  "always-online on native" gap flagged in every prior round's `known-limitations.md`.
- Still honest about what's NOT derived: `networkState:"slow"` is not computed (would need
  `state.details.cellularGeneration`/effective-type parsing, which varies by platform and wasn't verified this
  round) — `online`/`offline` are the only two states this hook actually produces.

## Draft persistence (Round 5 — built for real)
`src/hooks/usePersistedDraft.ts` (new): a generic `usePersistedDraft<T>(key, initial)` hook backed by
AsyncStorage. Wired into `InspectionChecklistShowcaseScreen` (both the inspection draft and the checklist draft
persist independently, survive an app restart, and are cleared together when the checklist is marked complete).

**Honest scope**: this is device-local persistence only — it does NOT sync to a backend, does NOT resolve
conflicts, and does NOT auto-submit anything on reconnect (consistent with `offline-operation-matrix.csv`'s
`online_required` category for actual submissions — no consuming screen in this round has a real submit endpoint
to auto-replay against anyway). `JobNotesMediaShowcaseScreen` and `QuoteShowcaseScreen` were NOT converted to
use this hook this round (their drafts remain `useState`-only, lost on unmount) — a real, disclosed remaining
gap, not silently implied as solved everywhere.

**Real test coverage**: 4 tests in `src/hooks/__tests__/usePersistedDraft.test.ts`, including one that unmounts
a hook instance and mounts a fresh one with the same key to genuinely simulate an app restart and assert the
draft survives — not just a smoke-rendered assertion.
