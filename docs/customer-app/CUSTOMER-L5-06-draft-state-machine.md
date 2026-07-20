# CUSTOMER-L5-06 — Draft (Session) State Machine

## States

```
IDLE        — no draft resolution has started yet
LOADING     — fetching a locally-cached draft ID's authoritative state
CREATING    — creating a new draft via the real backend
READY       — a non-terminal draft is loaded and current
SAVING      — a mutation (assistant-answer sync) is in flight
SAVE_FAILED — the last mutation failed; the previously-loaded draft is retained
EXPIRED     — the draft's status is "expired" or its expires_at has passed
CANCELLED   — the draft's status is "cancelled"
ERROR       — the draft could not be loaded or created at all
```

Simplified from CUSTOMER-L5-06 §42's aspirational model — no `CONFLICT`
state (no version column exists to conflict against — see
draft-architecture.md), no formal `RESTORING`/`BRANCHING` split (restoration
is just `LOADING` against a locally-cached ID), no `OFFLINE_PENDING` status
(no queued-mutation infrastructure exists to represent — see
local-persistence-policy.md; the existing `OfflineBanner` pattern is used at
the screen level instead).

## Invalid-State Prevention (CUSTOMER-L5-06's own analogous requirement to CUSTOMER-L5-05 §43)

| Impossible state | How it's prevented |
|---|---|
| A terminal (expired/cancelled/confirmed/failed) draft presented as mutable | `draftLoaded()` always classifies the draft's real `status` first — a terminal draft can never resolve to `READY` |
| Mutating an expired draft | `isMutable()` checks both `status !== "READY"` and `isTerminalDraftStatus()`; `BookingDraftScreen`'s continue/discard actions are `disabled` when `!canMutate` |
| Restoring Customer A's draft for Customer B | Local pointer is customer-ID-keyed and cleared on logout/account switch (see draft-architecture.md); the backend's own `_require_draft` ownership check is the actual enforcement boundary, not the client |
| A stale local pointer treated as ground truth | `useDraft` always re-fetches (`staleTime: 0`); the local ID is only ever used to know *which* draft to ask about, never as a substitute for asking |
| Answer sync running more than once per draft | `syncedAnswersRef` in `BookingDraftScreen` guards the one-time sync effect |

## Transition Table

| From | Action | To |
|---|---|---|
| IDLE | local pointer resolved | LOADING (if a cached ID exists) or CREATING (if none) |
| LOADING | fetch succeeds, non-terminal | READY |
| LOADING | fetch succeeds, terminal | EXPIRED or CANCELLED |
| LOADING | fetch fails | CREATING (falls back to creating a new draft) |
| CREATING | create succeeds | READY |
| CREATING | create fails | ERROR |
| READY | assistant-answer sync mutation starts | SAVING |
| SAVING | mutation succeeds | READY (re-derived via `draftLoaded` on the updated draft) |
| SAVING | mutation fails | SAVE_FAILED (draft retained) |
| READY | `cancelDraft` succeeds | CANCELLED (via refetch/invalidation) |

## Restoration Guarantee

App restart, backgrounding, and navigating away and back are all handled
uniformly: the local pointer survives (`AsyncStorage`), and the very next
mount of `BookingDraftScreen` re-runs the full restoration sequence against
the real backend — there is no separate "resume" code path from "cold
start," which is what makes this state machine's restoration story simple
and hard to get subtly wrong.
