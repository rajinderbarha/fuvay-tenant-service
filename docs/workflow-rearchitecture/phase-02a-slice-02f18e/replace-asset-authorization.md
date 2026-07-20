# replace_asset Authorization

## Every mounted route/caller reaching `replace_asset`
`POST /v1/media/{media_id}/replace` (`new_router.py`) — the ONLY route
that calls `MediaAssetService.replace_asset`, confirmed by full-repo grep.
Guarded at the router layer by `get_current_user` only (any authenticated
role) — service-layer authorization (`assert_can_replace` for non-chat
contexts; this slice's `_assert_chat_attachment_replace_authority` for
`chat_attachment`) is what actually gates the operation.

## Trace (for `chat_attachment` context, this slice's fix)
| Field | Value |
|---|---|
| Acting persona | Any role reaching the route |
| Permission | `require_owner_or_office_staff_mutation`'s role check (`tenant_owner`/`staff`), reused directly — no new permission added |
| Mutation scope | SAME dependency's access-scope check (denies `customer_support_limited` readonly staff) |
| Tenant ownership | `asset.tenant_id == actor.tenant_id` required for the office path |
| Asset ownership | `asset.uploaded_by_user_id == actor.user_id` — the uploader path, independent of role |
| Uploader identity | Directly checked, first branch (fastest path, also covers `super_admin` via early-return before it) |
| Existing claim | Preserved — `replace_asset` copies `old_asset.metadata_json` verbatim to the new row (2F-18D finding, unchanged) |
| Thread authority | For a CLAIMED asset, `_assert_chat_thread_authority` (2F-18D) still runs AFTER this new check, unchanged |
| Client-controlled metadata | None — `replace_asset`'s signature (`media_id`, `file`, `is_public`) accepts no metadata override |
| File/content source | The uploaded `file` bytes, validated by `MediaValidationService` (unchanged) |
| Commit behavior | `await self.db.flush()` then eventual commit by the caller's own session lifecycle — unchanged |

## Required tests — results
| Test | Outcome |
|---|---|
| Uploader replaces own unclaimed asset | ALLOWED — `test_uploader_can_replace_own_asset` |
| Uploader replaces own claimed asset with thread authority | ALLOWED — uploader branch short-circuits before the thread-authority check even runs (uploader is always authoritative regardless of claim state) |
| Tenant owner replaces asset under established admin policy | ALLOWED — `require_owner_or_office_staff_mutation` admits `tenant_owner` |
| Canonical staff with mutation permission replaces asset | ALLOWED — `test_staff_with_mutation_scope_can_replace_tenant_asset` |
| Read-only staff denied | DENIED — `test_readonly_staff_denied_replace` |
| Customer participant replaces provider asset | DENIED — `test_customer_cannot_replace_provider_asset` |
| Technician participant replaces staff/customer asset | DENIED — `test_technician_cannot_replace_unowned_asset` |
| Same-tenant unrelated staff without permission | DENIED via the SAME access-scope mechanism as "read-only staff" (no separate granular per-asset permission exists in this codebase to check beyond role + access_scope — see `known-limitations.md`) |
| Foreign tenant denied | DENIED — `test_foreign_tenant_staff_denied_replace` |
| Claimed asset content replacement preserves claim | Confirmed by code read — `metadata_json=old_asset.metadata_json or {}` copies the claim verbatim; this slice's new authorization check runs BEFORE any content mutation, so a denied replacement never reaches the copy step either |
| Replacement cannot alter customer, visibility, context or claim | Confirmed — `new_asset`'s `customer_id`, `media_context`, and `metadata_json` are all copied verbatim from `old_asset`, never accepted from the request |
| Replacement failure creates no content or metadata change | The OLD asset is untouched until authorization passes; a denial raises before `old_asset.status = "replaced"` is ever set |

## Thread read authority alone never authorizes replacement
Confirmed structurally: `_assert_chat_attachment_replace_authority` does
NOT call `validate_thread_access` or any thread-read mechanism at all —
it is entirely independent of thread membership. A user who can READ a
thread (and therefore its attachments) has no elevated replacement
authority merely from that read access.
