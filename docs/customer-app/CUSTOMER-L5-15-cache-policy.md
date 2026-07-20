# CUSTOMER-L5-15 — Cache Policy

No new query/mutation keys are introduced this sprint — there is no real
cancellation-eligibility, policy, reason, reschedule-eligibility, or
replacement-window endpoint to cache. `cancellation-reschedule-
availability.ts`'s two functions are pure, synchronous, and
unconditional (`false`) — not backed by any network call, so no cache
policy applies to them at all.

The existing `bookings`/`booking` query-key families
(`features/bookings/queries/bookings-queries.ts`,
`features/booking-confirmation/queries/booking-confirmation-queries.ts`)
are unchanged this sprint.
