# Slice 2F-18 — Implementation Summary

## Mission
Close authorization, ownership, sender/recipient integrity, and read-privacy
gaps in `app.engines.platform_notifications.provider_router` — the module
selected and confirmed by Slices 2F-17/2F-17A as the next implementation
target (sole `CRITICAL`-severity module, 10 unprotected tenant/provider
mutation routes, part of the 190/226 canonical baseline).

## What this module actually is
`provider_router.py` contains 5 `APIRouter`s covering three DISTINCT
capabilities, not one:
1. **In-app notifications** (list/unread-count/mark-read/mark-all-read/
   preferences) — `provider_notif_router` + `staff_notif_router`.
2. **Job/booking/complaint-linked chat threads** (list/create/get/messages/
   send/mark-read) — `provider_chat_router` + `staff_chat_router`.
3. **Tenant-scoped audit log reads** — `provider_audit_router` (no
   mutations; GET-only).

All 20 routes (10 selected mutations + 10 associated reads) previously used
only `Depends(get_current_user)` — any authenticated role could call any of
them, relying entirely on service-layer `user_id`/`tenant_id` filtering
(trusted from the JWT) rather than FastAPI-level RBAC.

## Findings and fixes

1. **Missing role dependency (all 20 routes).** Fixed: `provider_*` routers
   now use `require_owner_or_office_staff_mutation` (existing dependency —
   `super_admin`/`tenant_owner`/`staff`, read-only access-scope denied),
   matching the established `provider_router.py` convention used elsewhere
   in this codebase (e.g. `field_ops.router`). `staff_*` routers now use
   `require_staff_or_technician_only` (existing dependency — `staff`/
   `technician` only), matching `field_ops.staff_router`'s convention.

2. **Weaker same-record alternate route: `customer_router.py`.** The
   sibling `customer_notif_router`/`customer_chat_router` in the SAME module
   reach the identical `InAppNotification`/`ChatThread`/`ChatMessage`
   tables via the identical service methods, and were equally guarded by
   only `get_current_user` (not the existing `require_customer`
   dependency). Per Workstream 19, a weaker live same-record route must be
   fixed, not merely noted — fixed alongside the selected module (this is
   the same module directory, not a second unrelated module).

3. **Chat thread record-ownership bypass** (`chat_service.create_thread`).
   A caller-supplied `record_id` was resolved best-effort and any failure
   silently fell back to `(None, None)` — a provider could create a thread
   pinned to a nonexistent record, or (because the caller's own `tenant_id`
   was always used when supplied) pin a thread to a `service_job`/
   `service_booking`/`complaint` belonging to ANOTHER tenant, and a
   customer could pin a thread to another customer's booking. Fixed: for
   the three record types the service can actually resolve
   (`service_booking`, `service_job`, `complaint`), a caller that omits
   `tenant_id` or `customer_id` (i.e. every real router caller) now gets an
   enforced resolve step — nonexistent records raise
   `CHAT_RECORD_NOT_FOUND`, and a resolved tenant/customer that disagrees
   with the caller's own identity raises `CHAT_RECORD_ACCESS_DENIED`.

4. **Message visibility fail-open** (`ChatMessage.is_visible_to`). An
   unrecognized `visibility` string fell through to `return True` (visible
   to every viewer type) — combined with `visibility` being a fully
   client-controlled free-text field on `SendMsgIn`, any sender could set
   `visibility="anything"` and it would leak to all viewer types instead of
   being restricted. Fixed in two places: (a) `is_visible_to`'s fallback
   now fails closed (`admin`-only); (b) `send_message` now validates
   `visibility` against the known enum and rejects any non-`thread` value
   from a non-admin sender (a provider/staff/customer cannot mark their own
   message `admin_only`/`provider_only`/`customer_only` to hide it from or
   fake exclusivity toward the other side of the conversation).

5. **Unvalidated notification preference identity**
   (`NotificationService.update_preference`). `event_key`/`channel` were
   persisted verbatim from the request body with no check against
   `NotificationEventRegistry`/`ALL_CHANNELS`. Fixed: both are now
   validated before any write; invalid values raise
   `NOTIFICATION_PREFERENCE_INVALID` before persistence.

## What was investigated and found NOT to need a code change
- **Sender identity** (`sender_user_id`/`sender_type`/`actor_user_id`) is
  already 100% server-derived from the JWT in every router — no request
  schema exposes a sender/tenant override field (proven directly by
  `TestSenderIdentityServerDerived`).
- **Recipient authority for notification reads/marks** — already
  service-scoped to `user_id == caller` with a real ownership check
  (`mark_notification_read` raises `IN_APP_NOTIFICATION_NOT_FOUND` on
  cross-user IDs) — proven pre-existing, unchanged.
- **Bulk/broadcast** — no bulk-send or broadcast capability exists
  anywhere in `provider_router.py`; `FALSE_POSITIVE_NON_MUTATION` /
  not-applicable for this module.
- **External delivery side effects from chat** — `_notify_other_participants`
  writes only an in-app `InAppNotification` row synchronously in the same
  transaction as the message; no email/SMS/push/worker/queue call exists on
  this path at all (`channel_providers.py` for other channels is reached
  only from admin/internal `dispatch_pending`, never from this router).
- **Technician tenant-wide thread visibility** — `list_threads` deliberately
  shows a provider/staff caller every thread for their tenant (not only
  ones they are a listed participant of), per an explicit design comment in
  `chat_service.py`. This was evaluated against Workstream 10/19's
  assignment-limiting requirement and NOT restricted, because doing so
  would break the intentional, currently-relied-upon handoff behavior (a
  technician reassigned mid-job must still see the existing thread) without
  clear product direction on the replacement rule — flagged
  `PRODUCT_DECISION_REQUIRED`, see `product-decisions-required.md`.

## Coverage
**190/226 → 200/226.** All 10 selected mutations are now protected; the
canonical tenant denominator (226) is unchanged. See
`canonical-coverage-update.md`.

## Tests
49 new tests (`tests/test_phase2f18_platform_notifications_authorization.py`),
all passing. Existing `platform_notifications` unit/mock test suites (52
pre-existing tests across `test_sprint27_notifications.py`,
`test_module_l5_20_chat_notify.py`, `test_module_l5_19_staff_chat.py`,
`test_module_l5_14_chat.py`, `test_module_l5_11_*`) still pass; only the 3
pre-existing LIVE-DATABASE tests (which require a running Postgres this
environment doesn't have) are excluded, same as every prior slice. See
`test-report.md` and `regression-report.md`.

## Final status
**SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED** — see `approval-gate.md`.
