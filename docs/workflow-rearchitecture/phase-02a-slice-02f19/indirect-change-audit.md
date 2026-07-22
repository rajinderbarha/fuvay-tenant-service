# Indirect Change Audit

## Method
The `platform_notifications` series (2F-18 through 2F-18E) modified exactly
two files outside `app/engines/platform_notifications/`:
`app/engines/media/asset_service.py` and (read-only import, no
modification) `app/core/permissions.py` / `app/dependencies/auth.py`
(existing dependencies were REUSED, never changed). Every remaining
canonical route was checked against these touch points.

## `app/engines/media/asset_service.py` — the one shared file
Four of the 26 remaining routes DO reach this file:
`upload_provider_logo`, `remove_provider_logo`, `upload_provider_shop_photo`,
`remove_provider_shop_photo` (and the two staff-profile-photo routes,
`upload_staff_profile_photo`/`remove_staff_profile_photo` — 6 total,
all in `app.engines.media.new_router`).

Every 2F-18-series addition to this file is unconditionally gated on
`media_context == "chat_attachment"`:
- `_assert_chat_thread_authority` (2F-18C) — called only when
  `asset.media_context == "chat_attachment"` (both call sites in
  `get_asset`/`get_local_file_for_serve` check this explicitly before
  calling it).
- `_assert_chat_attachment_lifecycle` (2F-18E) — returns immediately
  (`if asset.media_context != "chat_attachment": return`) for any other
  context.
- `_assert_chat_attachment_replace_authority` (2F-18E) — only invoked in
  `replace_asset` inside an `if old_asset.media_context ==
  "chat_attachment":` branch; the `else` branch still calls the
  ORIGINAL, unmodified `self._access.assert_can_replace(self.actor, rec)`.
- `_strip_claim_key` (2F-18D) — applied unconditionally inside `upload()`,
  but its effect (stripping a `chat_thread_id` key from `extra_metadata`)
  is a no-op for any upload that never sets that key — confirmed the
  profile-logo/shop-photo/staff-photo upload call sites never pass
  `extra_metadata` at all (grepped, single caller path, no such argument
  supplied), so this strip never has anything to strip for these routes.

**Direct verification**: re-ran the runtime inventory tool against these 6
routes (`runtime-reverification.csv`) — `guard_status` is IDENTICAL to
before the 2F-18 series began (`PERMISSION_ONLY_NOT_SCOPE_AWARE`,
`require_technician` unchanged). No behavior change occurred.

## Every other remaining route
The remaining 20 routes (`admin_catalog`, `profile.router`'s non-media
routes, `compliance.provider_router`, `marketing_automation.provider_router`,
`analytics.provider_router`, `customer_reviews.provider_router`,
`package_commerce.tenant_router`) do not import from
`app.engines.platform_notifications` or `app.engines.media` at all —
confirmed by grep, no shared dependency, service, serializer,
object-ownership helper, transaction helper, or error-mapping code was
touched by the `platform_notifications` series that any of these 20
routes reach.

## Conclusion
**Zero routes among the 26 had their protection status change, directly
or indirectly, as a result of Slices 2F-18 through 2F-18E.** No row-level
evidence exists to justify marking any remaining row as
`ALREADY_PROTECTED_STALE_ROW`.
