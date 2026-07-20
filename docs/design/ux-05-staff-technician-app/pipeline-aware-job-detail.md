# Pipeline-Aware Job Detail — Real-Evidence Correction

The UX-05 brief's illustrative status list (`assigned/on_the_way/inspection/in_progress/work_done/completed`) and its
assumption of a live dual `field_ops.Job` / `ServiceJob` pipeline split **inside this specific mobile app** were both
explicitly flagged in the brief as examples to verify against real code, not requirements. Discovery found real,
already-fixed evidence that changes the shape of this workstream:

## What's actually live in mobile/staff-app
`src/lib/api.ts` and `src/lib/transitions.ts` (both carrying MODULE-L5-36 commit-history comments) confirm:

- The `field_ops` `jobs` table has **zero rows platform-wide** (confirmed via direct query during MODULE-L5-36).
- Every real job a technician sees comes from `service_jobs` (`home_service_assignment` + `execution` engines) —
  routed through `/v1/staff/service-jobs*`.
- The real status literal set (verified, not the brief's illustrative one) is:
  `pending_assignment, assigned, accepted, scheduled, on_the_way, reached_site, inspection_started, inspection_done,
  quote_required, service_started, work_done, customer_not_available, completed, cancelled, failed`.
- There is **no separate field_ops.Job mobile surface to build** — building one would mean modeling a pipeline with
  no live data, which the UX-05 hard constraints explicitly warn against fabricating.

## What UX-05's view models do instead
`src/types/ux05.ts`'s `JobProvenanceView` still carries `pipeline`, `sourceBookingId`, `jobId`, `jobModel` on every
job view — but `pipeline` is typed as the single literal `"service_booking_service_job"` rather than a union of two,
so a future field_ops revival cannot be silently merged into this type without every call site failing to compile.
`PipelineBadge` renders this provenance on every job card/detail so the source booking ID and job ID are always
visibly distinct, never collapsed into one ID — matching the brief's underlying intent (never conflate booking and
job identity) even though the union-of-two-pipelines mechanism the brief described isn't applicable here.

## What did NOT change
This finding does not contradict UX-04's tenant-portal domain model, where `field_ops.Job` genuinely is modeled
because the **tenant operations console** (a different surface, reviewed by tenant staff) does need to represent a
booking before/without a transitioned job. The absence is specific to the **technician's own assigned-work view** —
a technician is never shown an untransitioned booking pipeline at all, live or design-fixture.
