# CUSTOMER-L5-13 — Tracking Architecture

## Real Flow (Honest, Non-Map)

```
booking (customer opens BookingDetail, L5-12)
→ real job.id resolved via GET /v1/customer/my-activity/bookings/{id} (reused, L5-11)
→ "Track provider" button shown only when a job exists (real signal)
→ customer taps → Tracking screen (bookingId param)
→ real GET /v1/customer/service-jobs/{jobId}/tracking
→ real job.status (via the shared, centralized status registry)
→ real execution-event timeline (client-side customer-safe labels)
→ no map, no marker, no live location, no ETA, no route, no masked-call
```

## Why No Map / Live GPS / ETA / Route / Masked-Call

Exhaustively verified this sprint (`baseline-verification.md`'s Central
Findings #4, cross-checked by an independent research pass):

- A real live-GPS table (`geo.StaffLocation`) exists, but is
  architecturally orphaned — only written/read by a separate, legacy,
  `is_enabled_by_default: False` dispatch stack
  (`field_ops`/`dispatch`/`booking` engines) that this app's real pipeline
  (`home_service_booking`/`home_service_assignment`/`execution`) never
  touches.
- No websocket/SSE endpoint exists anywhere in the FastAPI app.
- The only ETA calculation anywhere (`geo/service.py`'s crude
  `road_dist/0.5` heuristic) serves a disconnected dispatch-radius search,
  never a specific assigned technician's job.
- No route/directions integration exists anywhere.
- No masked-call/contact system exists anywhere.
- `react-native-maps` is an installed mobile dependency but has no
  coordinate source to render for this pipeline.

Building any of the above would mean fabricating data with zero real
backend support — directly prohibited by this project's central
discipline (§65's explicit "Do not fabricate... locations... routes...
ETA"). This sprint instead builds the **real, honest alternative the spec
itself explicitly allows for**: a "non-map tracking fallback" — a
status-milestone timeline, which is exactly what real backend data
(`ServiceJobExecutionEvent`) actually supports.

## No Tracking-Session Model

Since there is no live, continuously-updating location stream, there is
no real "tracking session" to authorize, expire, or reconnect — the
tracking screen's data is a stateless, always-safely-re-fetchable
timeline (`staleTime: 0`, refetch-on-mount, matching every other read
screen's established pattern since CUSTOMER-L5-09). §21-23's aspirational
"tracking eligibility"/"tracking session"/"tracking transport" models are
therefore `NOT_APPLICABLE` — there is nothing to model, since re-fetching
this real, idempotent, read-only endpoint is inherently safe at any time
a job exists.

## Reuse, Not Duplication

- Job-ID resolution reuses CUSTOMER-L5-11's `useBookingDetail` hook
  directly (`features/booking-confirmation/queries/`) — no duplicate
  booking-detail client was built.
- Status display reuses CUSTOMER-L5-12's centralized status registry
  (`features/bookings/domain/booking-status-registry.ts`), extended
  additively with this sprint's newly-confirmed real statuses — not a
  second, competing registry.

## Background/Foreground and Reconnect

Not applicable in the aspirational, continuous-connection sense (§31-32)
— since there is no live connection to reconnect, "foreground
reconciliation" is simply React Query's standard refetch-on-mount
behavior (`staleTime: 0`), already satisfied by this screen's existing
design with no additional code.
