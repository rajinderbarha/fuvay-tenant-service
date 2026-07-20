# Booking / Parent Coexistence

## Disposition: MUTUALLY_EXCLUSIVE (fixed this slice — previously ambiguous)

## Investigation

- **Which source is authoritative for customer**: both, independently — each rejects a
  disagreeing explicitly-supplied `customer_id` against its OWN record, but neither is checked
  against the other's customer.
- **Which source is authoritative for service**: only `booking_id` (cross-checked against
  `service_type_id`); `parent_job_id` never cross-checks service.
- **Which source controls duplicate prevention**: both, independently (booking → one Job per
  booking; CONSULTATION parent → one repair per consultation) — no combined uniqueness rule was
  ever defined for "one Job per (booking, parent) pair."
- **Which source controls Job type**: neither directly — `job_type` remains independently
  client-supplied/auto-detected in all cases.
- **Which source appears in lineage**: both would be stored on the same `Job` row
  (`Job.booking_id` and `Job.parent_job_id`) if both were allowed, with no documented convention
  for which one "wins" for reverse-lookup purposes (`select(Job).where(Job.booking_id==...)` vs.
  `select(Job).where(Job.parent_job_id==...)` would both match the same row).
- **Whether both can be represented without contradiction**: no explicit semantics were ever
  defined anywhere in this codebase for a Job that is simultaneously "derived from booking X" and
  "a repair spawned from consultation Y" — these represent two different origin stories for the
  same Job that no code path resolves.
- **Whether any live caller submits both**: no (`FRONTEND_MUTATION_SURFACE_ABSENT`; the one
  internal caller, `_spawn_repair_from_consultation`, only ever supplies `parent_job_id`, never
  `booking_id`).
- **Whether existing tests support both**: no test anywhere in this codebase (before this slice)
  exercised both fields together.
- **Whether audit/history clearly records both**: no — `JobStatusHistory`'s reason field is
  generic (`"Job created"`) regardless.
- **Whether reverse lookups treat the Job as booking-derived or repair-derived**: ambiguous — no
  code path disambiguates.

## Fix

Per the mission's explicit fallback ("If no explicit safe semantics exist, reject simultaneous use
before persistence"), `create_job` now rejects any request supplying both `booking_id` and
`parent_job_id` (`AMBIGUOUS_JOB_SOURCE`, 422), before any other validation runs. This does not
silently pick an undocumented precedence — it surfaces the ambiguity to the caller directly.

Supplying either field alone remains fully supported and unaffected (verified:
`test_booking_only_unaffected`, `test_parent_only_unaffected`).
