# CUSTOMER-L5-13 — Privacy and Security Review

## Ownership Enforcement

`GET /v1/customer/service-jobs/{jobId}/tracking` (`execution/home_service_router.py`)
filters `ServiceJob.customer_id == user.user_id` server-side — this
client sends only the authenticated request and a real `jobId` obtained
from a prior real response (never constructed or guessed).

## Real, Disclosed Mitigation: `notes`/`media` Never Rendered

Per `contract-matrix.md`'s finding: this endpoint's `notes` array (and
each timeline event's own `notes` field) is **not** filtered by any
`is_customer_visible` flag server-side — a real, disclosed backend gap.
This sprint's schema (`execution-timeline-schema.ts`) structurally
excludes `notes` from every parsed shape (via selective `z.object()` key
inclusion, the same "exclude via omission" pattern used since
CUSTOMER-L5-08 for internal-only fields) — verified by a dedicated test
(`execution-timeline-schema.test.ts`'s "structurally strips internal
fields" case) that constructs a raw payload including `notes`/`actor_role`/
`id`/`job_id` and asserts none of them survive parsing. The `media` array
is never fetched or parsed at all this sprint.

## No Coordinates, No Route Geometry, No Phone Numbers

None of these exist anywhere in the real data this sprint touches
(`location-event-contract.md`, `contact-policy.md`) — nothing to
accidentally expose, log, or leak.

## No Sensitive Logging

`service_tracking_load_failed`/`execution_event_unmapped` log calls pass
only reason-category strings and (for the latter) the real, non-sensitive
`event_type` string — never any note text, never a coordinate, never a
phone number. Verified by direct review of every `logger.*` call site
added this sprint.

## No Production Mocks

Grepped `features/service-tracking/` for `mock`, `fake`, `TODO`, `FIXME`
— none found.

## No Fake Technician, Location, Route, or ETA

Per the established, repeatedly-applied discipline: this sprint renders
no technician name/photo (none exists — `technician-profile-contract.md`),
no coordinates/map/marker (none exists —
`location-event-contract.md`/`tracking-architecture.md`), no ETA/route
(none exists — `eta-and-route-contract.md`), and no masked-call action
(none exists — `contact-policy.md`). Every one of these is a deliberate,
documented omission, not an oversight.

## Cross-Tenant/Cross-Customer Isolation

Relies entirely on the backend's own `customer_id` check (above). Query
keys are additionally locale/tenant-scoped (`cache-policy.md`),
preventing any plausible cross-tenant cache collision even before the
backend's own check would reject the request. No new client-side
authorization logic was added that could get this wrong.

## Notification Deep-Link Security (Reused, Not Rebuilt)

Identical to CUSTOMER-L5-12's treatment — the existing, already-tested
`resolveNotificationIntent()` route-allowlist/expiry/dedup/param-validation
logic already covers the newly-promoted `tracking` route generically; no
new deep-link validation code was written this sprint.
