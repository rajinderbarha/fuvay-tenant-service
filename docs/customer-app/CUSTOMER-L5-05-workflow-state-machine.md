# CUSTOMER-L5-05 — Workflow (Session) State Machine

See `CUSTOMER-L5-05-assistant-architecture.md` for why this is a client-only,
in-memory session rather than a backend-tracked workflow — no backend
session/workflow engine exists.

## States

```
READY     — a current step exists and awaits an answer (or "completion" is reached)
COMPLETED — the customer explicitly acknowledged the completion step
ERROR     — an internal-consistency guard failed (e.g. a stale/tampered submission)
```

`IDLE` is implicit — before `useBookingAssistant`'s catalog queries settle,
`session` is simply `null` and the screen shows a loading state; there is no
separate `IDLE` value in `AssistantStatus` because nothing meaningful can
happen before catalogs load anyway.

## Invalid-State Prevention

| Impossible state (CUSTOMER-L5-05 §43) | How it's prevented here |
|---|---|
| Current question without a workflow | `session` is `null` until `createAssistantSession` runs — no screen renders a question before that |
| Completed workflow with a pending question | `completeSession` only transitions when `isAtCompletion(state)` is true (i.e. `currentStepId === "completion"`) — a no-op otherwise |
| Submit active without an answer | `submitAnswer` requires a caller-constructed `AnswerRecord`; renderers only call it from an explicit selection/continue action, never automatically |
| Answer history from another workflow version | Not applicable — no workflow version exists; `baseSteps` is fixed at session creation and never silently swapped |
| Customer switched while old session remains | The session lives in component state, unmounted with the screen — see security-review.md |
| Logout while session cache remains | Same — nothing to clear, since it was never a persistent cache entry |
| Branch recalculation and previous-navigation racing | `deriveSteps` is a pure function recomputed from `baseSteps` + `selectedIssueType` on every read — there is no separate mutable "recalculation in progress" state to race against |
| Expired workflow accepting answers | Not applicable — no expiry exists to violate |
| Stale/tampered answer submission | `submitAnswer` fails closed to `ERROR` if `record.stepId !== currentStepId(state)` |

## Transition Table

| From | Action | To | Notes |
|---|---|---|---|
| (none) | `createAssistantSession` | READY, step 0 | Runs once per `useBookingAssistant` mount, guarded by `if (session) return` |
| READY | `submitAnswer` (matching step) | READY, step+1 | May grow `baseSteps`' effective length via `deriveSteps` if `stepId === "issue_type"` |
| READY | `submitAnswer` (mismatched step) | ERROR | Fails closed, does not advance |
| ERROR | any submit | ERROR (no-op) | `submitAnswer` early-returns unchanged state when `status !== "READY"` |
| READY (step > 0) | `goToPreviousStep` | READY, step−1 | No-op at step 0 |
| READY | `reviseAnswer(stepId)` | READY, jumped to `stepId`'s index | Clears that step's answer and every answer after it |
| READY, at "completion" | `completeSession` | COMPLETED | No-op if not at "completion" |

## Restoration Within the Active Session

Navigating away (e.g. to `Profile`) and back, backgrounding/foregrounding
the app, an orientation change, a theme change, and a locale change all
preserve the in-memory `session` object as-is, since none of those unmount
`BookingAssistantScreen` — React Navigation keeps the screen instance alive
on the stack. A full app restart, reinstall, or navigating fully away and
back via `navigation.goBack()` past the screen does lose it — this is the
explicit, documented boundary with CUSTOMER-L5-06's durable persistence
scope (CUSTOMER-L5-05 §37).
