# CUSTOMER-L5-13 — Failure Matrix

| Failure | Detection point | Customer impact | Screen state | Message | Retry | Cache behavior | Analytics | Log level | Severity |
|---|---|---|---|---|---|---|---|---|---|
| Booking unavailable (network/validation) | Reused `useBookingDetail` error | Cannot resolve a job to track | Error state | `serviceTracking.unavailableTitle`/`unavailableDescription` | Yes | Cache untouched | N/A (reuses L5-11's own logging) | warn | P1 |
| No job exists yet | `booking.job` is `null` | Cannot see any service activity | "No service activity yet" state | `serviceTracking.noJobTitle`/`noJobDescription` | N/A (not a failure — a real, honest state) | N/A | N/A | info | NOT_APPLICABLE (correct, honest behavior) |
| Execution timeline fetch fails | `useJobExecutionTracking` error | Status/timeline section shows a retry prompt; rest of screen (header) still renders | Section-level error | `serviceTracking.unavailableDescription` | Yes | Cache untouched | `service_tracking_load_failed` | warn | P1 |
| Malformed timeline response | `parseExecutionTracking` returns `null` | Same as above — fails closed | Section-level error | Same | Yes | Cache untouched | `service_tracking_load_failed` (reason: validation) | warn | P1 |
| Individual timeline event malformed | Per-item resilience in `parseExecutionTracking` | That one event silently dropped; rest of timeline renders normally | No visible change | N/A | N/A | N/A | N/A (silent, per-item) | P3 |
| Unrecognized/unmapped real event type | `resolveExecutionEventLabelKey` returns `null` | That event simply doesn't appear in the rendered timeline | No visible disruption | N/A | N/A | N/A | `execution_event_unmapped` | warn | P3 |
| Unknown job status | `resolveBookingStatus` fallback (shared registry) | Sees a generic "Processing" label | No visual disruption | `bookings.status.processing` | N/A | N/A | N/A (a real, handled case) | N/A | NOT_APPLICABLE (correct, honest behavior) |
| Wrong customer (theoretical, unreachable via real UI) | Backend `customer_id` check | N/A — no real UI path constructs this | N/A | N/A | N/A | N/A | N/A | N/A | NOT_APPLICABLE |
| Wrong Tenant / wrong marketplace (theoretical) | Same backend check | N/A | N/A | N/A | N/A | N/A | N/A | N/A | NOT_APPLICABLE |
| Offline | `ApiError` `network_error` category | Same generic failure UI per-section | Various (see above) | Generic error text | Yes, once reconnected | `staleTime: 0` means immediate refetch on next mount, never trusted as current while offline | N/A | N/A | P3 |
| Logout/account switch mid-flow | `queryClient.clear()` (CUSTOMER-L5-02 pattern, reused) | Redirected away, no foreign state persists | Redirected to Authentication/BaselineLanding | Existing auth flow copy | N/A | Cache discarded | N/A | N/A | NOT_APPLICABLE (correct behavior) |

## Explicitly Not Applicable (per the real backend's confirmed absence)

Tracking-session expiry/revocation, location staleness, connection
interruption/reconnect, ETA/route unavailability, and masked-call failures
from the spec's requested failure list (§64) are omitted from this
matrix — none of them correspond to any real, reachable backend behavior
in this pipeline (see `tracking-architecture.md`/`eta-and-route-contract.md`/
`contact-policy.md`). Including placeholder rows for them would
misrepresent untested, non-existent behavior as a real, covered failure
mode.
