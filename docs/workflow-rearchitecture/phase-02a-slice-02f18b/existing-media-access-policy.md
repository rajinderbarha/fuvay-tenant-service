# Existing Media Access Policy

`app.engines.media.access.MediaAccessService` — the centralized,
pre-existing access-control helper for ALL media operations app-wide.
Reused directly by this slice (`assert_can_view`), not duplicated.

## `assert_can_view(actor, asset)` — the method this slice reuses
| Principal | Rule |
|---|---|
| `super_admin` | Always allowed |
| Any role, `asset.is_public == True` | Always allowed |
| `customer`, asset in `CUSTOMER_CONTEXTS` (includes `chat_attachment`) | Only if `asset.customer_id == actor.user_id` |
| `tenant_owner`/`staff`/`technician`, asset in `CUSTOMER_CONTEXTS` | Only if `asset.tenant_id == actor.tenant_id` (tenant-wide for this persona group — existing policy, not narrowed by this slice) |
| Any other role, asset in `CUSTOMER_CONTEXTS`, no match above | Denied |
| `tenant_owner`/`staff`/`technician`, non-customer-context asset, `asset.tenant_id` set | Only if `asset.tenant_id == actor.tenant_id` |
| Any other role, non-customer-context asset, tenant set | Denied |
| No `tenant_id` on asset | Falls through to `uploaded_by_user_id == actor.user_id` check |
| None of the above | Denied |

## `assert_can_upload` / `assert_can_delete` / `assert_can_replace`
Not reused by this slice — `platform_notifications` only ever REFERENCES
already-uploaded assets (no upload/delete/replace capability exists on any
route in this module, confirmed unchanged from 2F-18/2F-18A). Documented
for completeness, not integrated.

## Strongest / weakest callers (existing, unmodified)
- Strongest: `super_admin` (bypasses all checks) and `is_public` assets
  (bypass all checks for any authenticated role).
- Weakest (narrowest): `customer` role against a `CUSTOMER_CONTEXTS` asset
  — exact `customer_id` match required, no tenant-wide fallback.

## Composition decision for this slice
**Reuse directly, composed with `chat_service`'s own thread-authorization.**
`MediaAccessService.assert_can_view` proves the principal may view/use the
SPECIFIC asset; `chat_service.validate_thread_access` (2F-18A) proves the
principal may act in the SPECIFIC thread. Neither subsumes the other — a
technician might be authorized to VIEW a tenant customer-context asset
(via `MediaAccessService`) while NOT being authorized to send into the
thread it's being attached to (via `validate_thread_access`, if not
assigned to that Job) — `send_message` already runs the thread check
BEFORE the attachment check, so this ordering is correct and was not
changed.

## Error privacy of the reused helper
`MediaAccessService.assert_can_view` raises `ServiceOSException` with
codes `MEDIA_CUSTOMER_SCOPE_VIOLATION`, `MEDIA_TENANT_SCOPE_VIOLATION`, or
`MEDIA_ACCESS_DENIED` — all DISTINCT from a "not found" case (there is no
separate not-found check inside `assert_can_view` itself; callers like
`MediaAssetService.get_asset` do their own `_load` existence check
first). This slice's integration in `chat_service._validate_attachments`
catches ALL of these (`except ServiceOSException`) and re-raises the SAME
`ERR_CHAT_ATTACHMENT_NOT_FOUND` regardless of which specific
`MediaAccessService` denial fired — preserving privacy equivalence even
though the underlying helper itself distinguishes denial reasons
internally (those distinctions never reach the client through this
integration).
