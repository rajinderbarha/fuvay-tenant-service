# Status Transition Workflow

Already real and production_ready before this phase (`JobDetailScreen` + `src/lib/transitions.ts` + `src/lib/api.ts`
`jobsApi`) -- this pass did not rebuild it, only extended the surrounding screen (customer contact / address /
pipeline badge) and documents it here for completeness since the brief asked for it explicitly.

## Real transition graph (`NEXT_ACTION` in `src/lib/transitions.ts`)
```
assigned            -> accept | reject
accepted            -> onTheWay
on_the_way          -> reachedSite
reached_site        -> startInspection
inspection_started  -> completeInspection
inspection_done     -> startService
service_started     -> workDone | complete
work_done           -> complete
quote_required      -> complete
```
Each transition is a **distinct real endpoint** (`/v1/staff/service-jobs/{id}/on-the-way`, `.../reject`, etc.) --
there is no generic status-PUT. `JobDetailScreen.ACTION_FN` maps each `JobAction` to its own real call.

## Confirmation / evidence requirements
- `reject` requires a non-empty reason (enforced client-side before submit, `REJECTION_REASON_REQUIRED` implied
  server-side).
- `complete` requires both `work_summary` and `collected_amount` (enforced client-side and by the backend --
  `WORK_SUMMARY_REQUIRED`/`COLLECTED_AMOUNT_REQUIRED`).
- No other transition requires a note/evidence payload today.

## Offline / failure
All transitions are `online_required` (see `offline-operation-matrix.csv`) -- none has an idempotency key, so
none is auto-retried on reconnect. `actionState.error` surfaces the real backend error message (never a raw
stack trace) inline in the modal/action area.

## What did NOT change
No skip-ahead, reverse, or invented state was added. The real literal set from `src/lib/transitions.ts` is the
only one referenced anywhere in UX-05's new code (`src/types/ux05.ts`, `myWork.ts`).
