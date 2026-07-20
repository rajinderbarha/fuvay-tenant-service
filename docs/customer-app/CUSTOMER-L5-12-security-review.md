# CUSTOMER-L5-12 — Security Review

## Ownership Enforcement

`/v1/customer/bookings` (list), `/{id}`, `/{id}/tracking`, `/{id}/rating`
all filter/check `ServiceBooking.customer_id == customer_id` server-side
(`home_service_assignment/customer_router.py`) — this client sends only
the authenticated request and a real `bookingId` obtained from a prior
real response (list item or navigation param); it never constructs or
guesses one.

## Real, Server-Side Provider Safety (Better Than CUSTOMER-L5-11's Endpoint)

Unlike `final_records`'s `provider_snapshot` (raw, unstripped — required
client-side schema stripping in CUSTOMER-L5-11), this router's
`_customer_safe_provider()` strips to exactly `provider_name`/`rating`/
`public_badges` **server-side**, for both the list and detail responses.
This client's own schemas (`listItemProviderSchema`,
`detailProviderSchema`) additionally enforce this shape structurally (no
`.passthrough()`, unknown keys stripped by default) — defense in depth,
not reliance on the backend alone.

## No Private Contact Information

Neither endpoint returns technician or provider phone/email/address —
confirmed by the real response shapes read directly from source. This
sprint's UI renders only `provider_name`/`rating` — no contact fields
exist to accidentally expose.

## No Coordinates

`address_snapshot`'s real shape has never included latitude/longitude
(unchanged since CUSTOMER-L5-09's original finding) — nothing to strip,
nothing to expose.

## No Sensitive Logging

`bookings_list_load_failed`, `booking_detail_load_started/_failed`,
`booking_timeline_load_failed` log calls (added this sprint) pass only
reason-category strings — never the address, provider name, or any
timeline event content. Verified by direct review of every `logger.*`
call site added this sprint.

## No Production Mocks

Grepped `features/bookings/` for `mock`, `fake`, `TODO`, `FIXME` — none
found. Every rendered field traces to a real, schema-validated backend
response from one of the three real endpoints this sprint uses.

## No Fake Timeline, No Fake Technician Assignment, No Fake Action Availability

Per the established, repeatedly-applied discipline: the timeline renders
only real `ServiceJobAssignmentEvent`-derived rows (plus the one real
synthetic "Booking confirmed" row the backend itself always prepends);
`assignment_status`/`job_status` are rendered exactly as returned, never
inferred or upgraded client-side (e.g., this client never claims
"Technician assigned" unless `assignment_status`/the timeline actually
says so); the six informational action rows carry no real/fake
distinction risk since they are explicitly, visibly non-interactive text,
never buttons implying a capability that doesn't exist.

## Notification Deep-Link Security (Reused, Not Rebuilt)

`resolveNotificationIntent`'s existing route-allowlist/expiry/dedup/
param-validation logic (unchanged, CUSTOMER-L5-01) already satisfies
§44's authentication/ownership/route-allowlist/parameter-validation/
consume-once requirements for the `bookingDetail` target — this sprint
adds no new deep-link validation code, since the existing mechanism
already covers it generically for any route with `notificationEnabled:
true`. Booking *ownership* itself is enforced by the real backend
`GET /bookings/{id}` call the screen makes after any navigation
(deep-link-triggered or otherwise) — the intent resolver only validates
the *route*, never asserts booking ownership itself (that would be a
false client-side authority; the backend remains the sole real check).

## Cross-Tenant/Cross-Customer Isolation

Relies entirely on the backend's own customer_id check (above). This
sprint's query keys are additionally locale/tenant-scoped
(`cache-policy.md`), preventing any plausible cross-tenant cache
collision even before the backend's own check would reject the request.
No new client-side authorization logic was added that could get this
wrong.
