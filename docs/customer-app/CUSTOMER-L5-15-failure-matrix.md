# CUSTOMER-L5-15 — Failure Matrix

Given no real cancellation/reschedule mutation exists, most of §64's
failure-injection scenarios (commit-then-lost-response, policy/fee
changing mid-confirmation, provider/technician changes during
reschedule, tracking-cleanup-worker failure, etc.) have no real code
path to inject a failure into. This matrix instead covers the failure
modes that genuinely apply to this sprint's actual deliverable — the
honest informational treatment.

| Scenario | Behavior |
|---|---|
| Customer opens Booking Detail for any booking status | "Cancel or reschedule" informational row always renders (never an interactive button) — `isCancellationAvailable`/`isRescheduleAvailable` both always `false` |
| A future engineer adds a real cancel/reschedule endpoint and wires the client without updating these functions | `cancellation-reschedule-availability.test.ts` continues asserting `false` for every status — the informational row keeps rendering even though a real action now exists, a **safe-but-stale** failure mode (under-permissive, not over-permissive) that a code reviewer would need to catch by noticing the tests never changed, rather than a runtime crash or data leak |
| Customer navigates away and back to Booking Detail | No state to leak or duplicate — the row is derived fresh from `booking.status` on every render, no cached "cancellation in progress" flag exists |
| Two devices, same booking, both viewing Booking Detail | Both show the same informational row; no mutation exists for either device to race against |

## Why the spec's full failure-injection matrix is not exercised

Every scenario in §64 (commit-then-lost-response, provider/technician
changes mid-reschedule, price revision, parts-request conflict, tracking
cleanup worker failure, notification delivery failure, app termination
during mutation) presupposes a real mutation in flight. None exists. This
sprint does not simulate failures against a fabricated mutation, since
doing so would itself be a form of building a convincing-looking fake.
