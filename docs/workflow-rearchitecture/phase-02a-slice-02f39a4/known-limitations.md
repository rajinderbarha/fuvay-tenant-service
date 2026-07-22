# Known Limitations — Slice 2F-39A4

## 5 routes remain `PRODUCT_DECISION_REQUIRED`

Each row below records the fields the reviewer specified as the required bar
for this classification to remain valid: fully qualified route identity,
persistent mutation behavior, current authentication, current
permission/scope, tenant/principal derivation, client-controlled
identifiers, service-layer method, known callers, the exact missing
product/caller-model decision, risk if left unchanged, and safe candidate
dispositions.

### 1. `analytics.router::ingest_event` — `POST /v1/analytics/events/ingest`

- **Mutation**: persists a new `AnalyticsEvent` row (idempotent on `event_id`).
- **Auth**: `get_current_user` (any authenticated role).
- **Permission/scope**: none beyond authentication.
- **Tenant/principal derivation**: `tenant_id` and `actor_id` both taken
  directly from the request body, no cross-check against the caller's own
  identity/tenant.
- **Client-controlled identifiers**: `event_id`, `tenant_id`, `actor_id`,
  `entity_type`, `entity_id`, `payload` — all body-supplied.
- **Service-layer method**: `AnalyticsService.ingest_event`.
- **Known callers**: none found in-process; no other engine calls this
  method or route directly. Likely intended as either (a) a webhook-style
  ingestion endpoint for external/internal event producers, or (b) a
  self-reporting endpoint scoped to the caller's own tenant/actor.
- **Missing decision**: which of (a)/(b) is correct — this determines
  whether the fix is "require a system/service credential" or "add
  `_require_trusted_tenant` + force `actor_id` to caller's own identity."
- **Risk if left unchanged**: any authenticated user (including `customer`)
  can inject arbitrary analytics events attributed to any tenant/actor —
  an analytics/KPI-integrity poisoning vector, not a private-data leak.
- **Safe candidate dispositions**: `PLATFORM_INTERNAL_MUTATION` (if only
  system producers should call it) or `CUSTOMER_SELF_SERVICE_MUTATION` with
  server-derived `tenant_id`/`actor_id` (if self-reporting is intended).

### 2. `appointment.router::hold_slot` — `POST /v1/appointments/hold`

- **Mutation**: creates a Redis SETNX hold + DB row for a slot (10-min TTL).
- **Auth**: `get_current_user` (any authenticated role).
- **Permission/scope**: none beyond authentication.
- **Tenant/principal derivation**: `staff_id`, `tenant_id`, `customer_id`
  all body-supplied; no cross-check against caller's own identity.
- **Client-controlled identifiers**: `staff_id`, `tenant_id`, `customer_id`,
  `booking_id`.
- **Service-layer method**: `AppointmentService.hold_slot`.
- **Known callers**: none found in-process. Plausible legitimate flows: a
  customer holding a slot for themselves, OR staff holding a slot on behalf
  of a walk-in customer (staff-assisted booking) — these are mutually
  exclusive interpretations of what "customer_id must match caller" should
  mean.
- **Missing decision**: is staff-assisted booking (non-matching
  `customer_id`) a real, intended flow? If not, add a self-service check
  matching the compliance.router precedent (Slice 2F-39A3).
- **Risk if left unchanged**: any authenticated user can hold a slot "as"
  an arbitrary customer_id (impersonation / hold-lock griefing against a
  real customer), for arbitrary tenant/staff.
- **Safe candidate dispositions**: `CUSTOMER_SELF_SERVICE_MUTATION` (add
  self-check) or `CANONICAL_TENANT_PROVIDER_MUTATION` (if staff-assisted
  holds are intentional, add a tenant-ownership check on `staff_id`/`tenant_id`
  instead, without requiring `customer_id` to match caller).

### 3. `platform_commerce.billing_endpoint::route_operation` — `POST /v1/commerce/billing/route`

- **Mutation**: dispatches a named billing `operation` for a `tenant_id`
  to one of several real financial engines (credit/commission, subscription
  leads, subscription booking), executing actual financial state changes.
- **Auth**: `get_current_user` (any authenticated role).
- **Permission/scope**: none beyond authentication — sibling routes on the
  same router (`get_configs`, `set_config`) both require `require_super_admin`.
- **Tenant/principal derivation**: `tenant_id` and `operation`/`context`
  all body-supplied, no cross-check.
- **Client-controlled identifiers**: `tenant_id`, `operation`, `context`
  (engine-specific parameters).
- **Service-layer method**: `BillingRouterService.route`.
- **Known callers**: none found in-process.
- **Missing decision**: is this meant to be callable by a tenant owner
  triggering their own tenant's billing operations (in which case it needs
  `require_tenant_mutation_permission` + `_require_trusted_tenant`), or is
  it platform-internal-only (in which case it should match its sibling
  config routes at `require_super_admin`)?
- **Risk if left unchanged (HIGH)**: any authenticated user, including a
  `customer`, can trigger real financial dispatch operations against any
  tenant — the most severe of the 5 remaining flagged routes.
- **Safe candidate dispositions**: `PLATFORM_ADMIN_MUTATION` (align with
  sibling config routes) or `CANONICAL_TENANT_PROVIDER_MUTATION` (with
  tenant-ownership enforcement added) — pending an explicit human decision
  given the severity.

### 4. `notification.router::send_notification` — `POST /v1/notifications/send`

- **Mutation**: persists a new `NotificationRecord` and queues dispatch.
- **Auth**: `get_current_user` (any authenticated role).
- **Permission/scope**: none beyond authentication.
- **Tenant/principal derivation**: `tenant_id`, `recipient_id` both
  body-supplied, no cross-check.
- **Client-controlled identifiers**: `tenant_id`, `recipient_id`,
  `recipient_type`, `notif_type`, `channel`, `data`.
- **Service-layer method**: `NotificationService.send`.
- **Known callers**: none found in-process (no other engine calls
  `NotificationService.send` directly — cross-engine notifications
  documented elsewhere in this program, e.g. MODULE-L5-20/21/22/24/25/26/27,
  all raise notifications through other code paths, not this HTTP route).
- **Missing decision**: is this route meant for any authenticated user to
  send a notification to any recipient/tenant (unlikely, given the spam/
  impersonation risk), or should it be restricted to platform-internal
  callers only?
- **Risk if left unchanged**: any authenticated user can send arbitrary
  notifications to arbitrary recipients in arbitrary tenants — a spam/
  social-engineering vector.
- **Safe candidate dispositions**: `PLATFORM_INTERNAL_MUTATION`
  (most likely, given no legitimate end-user caller was found).

### 5. `notification.router::retry` — `POST /v1/notifications/{id}/retry`

- **Mutation**: resets a failed/bounced `NotificationRecord` to `QUEUED`.
- **Auth**: `get_current_user` (any authenticated role).
- **Permission/scope**: none beyond authentication.
- **Tenant/principal derivation**: `notification_id`-only lookup, no
  tenant/ownership filter at all.
- **Client-controlled identifiers**: `notification_id`.
- **Service-layer method**: `NotificationService.retry_failed`.
- **Known callers**: none found in-process.
- **Missing decision**: same as `send_notification` — is this
  platform-internal-only, or should a tenant-ownership check be added
  (analogous to `acknowledge_anomaly`'s fix this slice)?
- **Risk if left unchanged**: any authenticated user can retry any tenant's
  failed notification by guessing/enumerating its UUID — minor (retries a
  legitimate prior send, doesn't forge new content), but still a
  cross-tenant action with no ownership check.
- **Safe candidate dispositions**: `PLATFORM_INTERNAL_MUTATION`, or
  `CANONICAL_TENANT_PROVIDER_MUTATION` with a tenant-ownership check added
  (mirrors `acknowledge_anomaly`'s fix pattern in this slice, if a tenant
  caller model is confirmed).

## N01 territory (not reopened, standing status preserved)

`media.router::initiate_upload`/`confirm_upload`, `media.new_router::delete_media`
— remains `SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED`, unchanged.

## Other

- No dedicated `verify_2f39a4.py` was built.
- The 5 remaining routes above require an explicit human product/caller-model
  decision before any code change — per the mission's constraint against
  guessing product policy, none were force-fixed.
