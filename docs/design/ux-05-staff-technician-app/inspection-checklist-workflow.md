# Inspection + Checklist Execution Workflow

## Real logic (built, unit-tested)
`src/lib/ux05/checklist.ts`: `isItemComplete()` (photo items require `photoAttached`, all others require a
non-empty `value`), `computeProgress()` (percent of complete items across all sections), `missingRequiredItems()`,
`canComplete()` (blocks completion while any required item is incomplete, regardless of optional items) --
6 unit tests, all passing, in `src/lib/ux05/__tests__/checklist.test.ts`.

## UI (built, dev-only showcase)
`InspectionChecklistShowcaseScreen` wires `InspectionForm` + `ChecklistSection`/`ChecklistProgress` to local
draft state, demonstrating: draft editing, pass/fail toggle (44×44pt touch targets), numeric/text response
types, progress bar tied to `computeProgress()`, and a Complete button disabled via `canComplete()` until all
required items are filled -- matching the brief's "prevent accidental completion" requirement for real (not just
visually).

## Real gaps (see backend-contract-blockers.md)
- No live inspection-content or checklist-content endpoint exists. `startInspection`/`completeInspection` in the
  real `jobsApi` are pure state transitions with no payload -- they do not carry the findings/observations/
  checklist-item data this workflow describes. This screen is tagged `MOCK_DESIGN_ONLY` and is reachable only via
  the dev-only `ShowcaseInspectionChecklist` route, never from production nav.
- Draft save/resume across app restarts was not implemented (state is in-memory `useState` only, lost on
  unmount) -- documented as a gap rather than silently claimed as offline-draft-safe.
- No auto-quote-from-inspection conversion exists or is implied.
