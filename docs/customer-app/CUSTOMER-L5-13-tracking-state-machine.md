# CUSTOMER-L5-13 — Tracking State Machine

## A Deliberately Small State Set

Given no live connection/session/location-stream concept exists
(`tracking-architecture.md`), this sprint's `ServiceTrackingScreen` uses a
small, real set of states — not the spec's full aspirational
`NOT_AVAILABLE/PENDING/ACTIVE/PAUSED/STALE/ENDED/EXPIRED/REVOKED/FAILED`
model (§22), since none of those distinctions have any real backend
signal behind them:

| State | Real trigger |
|---|---|
| Loading booking | `useBookingDetail` pending (reused from L5-11) |
| Booking unavailable | `useBookingDetail` error |
| No job yet | `useBookingDetail` succeeds, `job` is `null` |
| Loading timeline | `useJobExecutionTracking` pending |
| Timeline unavailable | `useJobExecutionTracking` error |
| Ready | Both queries succeeded — real `status` + real timeline rendered |

## No Reconnect / Background / Foreground State Machine

Per `tracking-architecture.md`: there is no live connection to
reconnect or pause. Re-opening the screen (including after backgrounding
the app) simply re-runs both real queries fresh (`staleTime: 0`) —
existing, already-tested React Query behavior, not new state-machine code
this sprint had to build.

## No Reassignment-During-Tracking Handling

Since there is no live session to invalidate, "reassignment during
tracking" (§35) reduces to: the next time this screen is opened (or its
queries refetch), it shows whatever the real, current `job.status`/
timeline are — inherently consistent, since there is no stale local state
retained between visits.

## No Expiry/Arrival-Triggered Cleanup

Since there is no session or location cache to clear, `work_done`/
`completed` are simply rendered as the current status via the same
registry every other status uses — no special-cased "stop tracking"
transition exists or is needed.

## Test Coverage

The real state transitions this screen actually has (loading/error/no-job/ready
for both the booking and tracking queries) are standard React Query
states already exercised by this app's established, deprioritized
"no component/render tests" pattern — the real logic worth testing (schema
parsing, status registry, event-label mapping) is covered by
`execution-timeline-schema.test.ts`, `execution-event-labels.test.ts`, and
the extended `booking-status-registry.test.ts`.
