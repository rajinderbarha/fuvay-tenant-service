# CUSTOMER-L5-15 — Reschedule State Machine

## For the canonical booking

Not applicable — no reschedule state machine exists at all for
`ServiceJob`/`ServiceBooking`. There is no `PENDING_REASSIGNMENT`,
`REQUIRES_REMATCH`, `PRICE_REVISED`, or any of the spec's aspirational
states anywhere in the real job-status vocabulary
(`booking-status-registry.ts` already exhaustively covers every real
status across all three sprints that touch `ServiceJob.status` —
`final_records`'s dead constants, `execution`'s real ones, and
`quote_checklist`'s real ones — none are reschedule-related).

## For the disconnected legacy `booking` engine (reference only)

```
(reschedule requested) ──► pending ──(tenant: accept)──► resolved, booking.preferred_date/slot overwritten, reschedule_count += 1
                        └─(tenant: reject)──► rejected [terminal for this request]
```

No `PENDING_PROVIDER_REACCEPTANCE`/`PENDING_REASSIGNMENT`/
`REQUIRES_REMATCH`/`PRICE_REVISED` states exist — this engine's
reschedule is a two-party (customer requests, tenant owner
accepts/rejects) date/slot swap with no provider-matching, pricing, or
technician-assignment involvement of any kind.

## This client's implementation

`isRescheduleAvailable(bookingStatus): boolean` in
`cancellation-reschedule-availability.ts`, unconditionally `false` — no
scattered boolean state machine is needed because there is no real
capability to model. `BookingDetailScreen.tsx`'s informational row
covers both cancellation and reschedule together, matching the existing,
already-correct CUSTOMER-L5-12-era copy ("Cancel or reschedule... Not
available in this version yet. Contact support if you need to change
this booking.").
