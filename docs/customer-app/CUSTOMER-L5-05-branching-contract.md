# CUSTOMER-L5-05 — Branching Contract

## Branch Evaluator

`domain/assistant-steps.ts#deriveSteps(baseSteps, selectedIssueType)` — a
pure function, not a backend call (none exists). Recomputed from
`baseSteps` on every read, never mutated incrementally, which is what makes
answer revision safe without a separate "undo" function that could drift.

## Workflow Version

Not applicable — there is no workflow, so there is no version to bind to,
mismatch against, or invalidate a cache on. `baseSteps` is computed once
per session from real, current gates (`ValidatedOfferingDetail.required_fields`
plus real catalog-presence booleans) and is immutable for the session's
lifetime — the closest analog to "version binding" this architecture has.

## Answer Submission → Branch Recalculation

```
customer answers "issue_type"
  → submitAnswer(state, record, selectedIssueTypeObject)
  → state.selectedIssueType = selectedIssueTypeObject
  → effectiveSteps(state) = deriveSteps(baseSteps, selectedIssueType)
      → if requires_description: insert "issue_description" after "issue_type"
      → if requires_photo (and not already in baseSteps): insert "photo_boundary" after "issue_type"
  → currentStepIndex advances into the (possibly grown) plan
```

This is the one real, backend-driven conditional branch in this sprint —
verified real via `MasterIssueType`/`ServiceIssueMapping`'s
`requires_photo`/`requires_description` columns (contract-matrix.md), not
invented.

## Answer Revision → Downstream Invalidation

```
customer taps "Edit" on an earlier answer (AnswerHistory component)
  → reviseAnswer(state, stepId)
  → currentStepIndex jumps to stepId's position in the *current* effective steps
  → every answer at or after that position is discarded (not "preserved but marked invalid" — discarded, since nothing downstream has been re-validated against the new answer yet)
  → if stepId === "issue_type": selectedIssueType is cleared to null
      → effectiveSteps recomputes from baseSteps alone (no branch) until re-answered
      → this naturally drops a no-longer-applicable issue_description/dynamically-inserted photo_boundary
```

Example: customer picks "Not cooling" (requires_description: true) →
answers the description → answers service_option → then edits "issue_type"
to "Strange noise" (requires_description: false). `reviseAnswer` clears
`issue_description` and `service_option` answers and resets
`selectedIssueType`; once "Strange noise" is re-submitted,
`effectiveSteps` no longer includes `issue_description` at all — the
customer proceeds straight to `service_option`, which they must re-answer
(their old selection was discarded, not silently reused, since it was
recorded against a different branch context).

## Conflict Handling

Not applicable in the backend sense (`QUESTION_NOT_CURRENT`,
`WORKFLOW_VERSION_CHANGED`, `SESSION_ALREADY_COMPLETED` — CUSTOMER-L5-05 §61
— all presuppose a server-tracked session). The one conflict this
architecture *can* detect is a stale/tampered client-side submission
(`record.stepId !== currentStepId(state)`), handled by `submitAnswer`
failing closed to `ERROR` — see workflow-state-machine.md.

## Expiry Handling

Not applicable — nothing to expire. No workflow, no session ID, no
version. Documented explicitly rather than fabricating a client-side expiry
timer with no real event to expire against.

## Hidden-Branch-Question Reachability

Since `effectiveSteps` is always derived fresh from `baseSteps` +
`selectedIssueType`, a step that isn't currently in the effective plan
(e.g. `issue_description` before `issue_type` is answered, or after it's
answered with a non-triggering issue type) has no index for
`currentStepId`/`reviseAnswer` to resolve to — it is structurally
unreachable, not merely hidden by UI, matching CUSTOMER-L5-05 §28's "hidden
branch questions cannot be reached."
