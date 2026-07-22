# Route Resolution Report — Slice 2F-39A5

All 5 routes Slice 2F-39A4 left flagged `PRODUCT_DECISION_REQUIRED` are
resolved. Each required a genuine product/caller-policy decision that
could not be derived from code alone; the user was asked directly for
each and explicitly delegated the choice back to the assistant ("choose
yourself"). The disposition applied to each is the most defensible,
fail-closed option given the evidence gathered in Slice 2F-39A4's trace
— not a default or a guess made without asking.

## 1. `platform_commerce.billing_endpoint::route_operation` — `POST /v1/commerce/billing/route`

**Decision**: Platform-internal only.
**Fix**: Router guard changed from `get_current_user` to `require_super_admin`,
matching its sibling config routes (`get_configs`, `set_config`, both
already `require_super_admin`).
**Rationale**: Flagged HIGH risk in 2F-39A4 (real financial dispatch, far
less restricted than its siblings). No in-process caller or evidence of
a legitimate tenant-side use was found in 2F-39A4's trace, so it is
restricted to the same level as its siblings rather than opened to
tenant self-service.

## 2. `appointment.router::hold_slot` — `POST /v1/appointments/hold`

**Decision**: Tenant-ownership check added; `customer_id` remains
unchecked (staff-assisted booking preserved).
**Fix**: `AppointmentService.hold_slot` now calls the service's existing
`_require_trusted_tenant(tenant_id)` helper before proceeding.
**Rationale — corroborated, not guessed**: the already-frozen Slice
2F-26E `fresh-manual-adjudication.csv` corpus independently classifies
this route's persona as `TENANT_PROVIDER_MUTATION` with
`tenant_direction` marked `row_expected` to eventually resolve
`PRINCIPAL_TENANT` — exactly matching this fix's effect. This is
external, pre-existing human-adjudication evidence that the route's
correct model is tenant-side (e.g. staff/dispatch initiating a hold),
not pure customer self-service — so forcing `customer_id == caller`
would risk breaking a real staff-assisted-booking flow the corpus
itself anticipates.

## 3. `analytics.router::ingest_event` — `POST /v1/analytics/events/ingest`

**Decision**: Platform-internal only.
**Fix**: Router guard changed from `get_current_user` to `require_super_admin`.
**Rationale**: No in-process caller was found; arbitrary
`tenant_id`/`actor_id` forgery by any authenticated user (including
`customer`) was a real analytics/KPI-integrity risk with no offsetting
legitimate use case identified.

## 4. `notification.router::send_notification` — `POST /v1/notifications/send`

**Decision**: Platform-internal only.
**Fix**: Router guard changed from `get_current_user` to `require_super_admin`.
**Rationale**: No in-process caller was found. Every other cross-engine
notification in this program (MODULE-L5-20/21/22/24/25/26/27) is raised
server-side through other code paths, never through this HTTP route —
strong evidence no legitimate end-user caller exists.

## 5. `notification.router::retry` — `POST /v1/notifications/{id}/retry`

**Decision**: Platform-internal only.
**Fix**: Router guard changed from `get_current_user` to `require_super_admin`.
**Rationale**: Same as `send_notification` — no in-process caller found,
same file, same ambiguity resolved the same way for consistency.

## Denominator effect

`PRODUCT_DECISION_REQUIRED` count: **5 → 0**. Combined with Slice 2F-39A4:
all 21 routes originally flagged by Slice 2F-39A3 are now resolved (14
fixed across both slices, 4 verified safe, 3 standing N01 blocker,
unchanged).
