# Expanded Application-File Allow-List (WS0)

Every application file modified in this slice, and why. No file outside
this list was touched.

| File | Why | New/expanded? |
|---|---|---|
| `app/core/permissions.py` | Add `require_mutation_access_scope` (WS2 — no pre-existing scope-only guard existed) | Expanded (already allow-listed in 2F-31, function is new) |
| `app/engines/media/new_router.py` | Swap guard on `upload_media`/`replace_media` (WS2) | Expanded (already allow-listed in 2F-31) |
| `app/engines/media/router.py` | `_svc()` now passes `actor_role`/`actor_tenant_id` to `MediaService` (WS3/WS4) | **New** — this file was explicitly out of scope in 2F-31; brought in this slice because 3 of its routes are residual |
| `app/engines/media/service.py` | Add `_require_trusted_tenant`, wire it into `initiate_upload`/`delete_file`, add session-ownership check to `confirm_upload`, sanitize `file_name` before storage-key construction (WS4/WS6) | **New** — discovered via `inspect.getsourcefile(MediaService)`, not assumed; this is the exact file backing `router.py`'s 3 residual routes |

## Files considered but NOT modified (with the required justification)

- `app/engines/media/access.py` (`MediaAccessService`) — WS5 requires direct
  evidence that a residual route cannot be closed without it. All 5 residual
  routes were closed via router-level guard swaps and service-level tenant
  authority checks; `MediaAccessService`'s existing `assert_can_delete` /
  `assert_can_replace` / `assert_can_view` needed no change. Not modified.
- `app/engines/media/asset_service.py` (`MediaAssetService`) — backs
  `upload_media`/`replace_media`. Already resolves `tenant_id` from
  `self.actor.tenant_id` server-side (confirmed by reading `upload()` and
  `replace_asset()`), and already calls `assert_can_upload`/`assert_can_replace`
  before mutating. No evidence required modifying it. Not modified.
- `tests/test_phase2f21_remaining_queue_reconciliation_and_selection.py`,
  `tests/test_phase2f28_module_selection.py`, and other `tests/test_phase2f*.py`
  files — modified as directly affected by the coverage-count/hash change
  (test files were explicitly permitted; these are not application files).
- `scripts/workflow_rearchitecture/verify_*.py` — modified as tooling that
  tracks live state (explicitly distinct from the frozen historical `docs/`
  artifacts under WS1's immutability rule).

## Mission constraint compliance

- `MediaAssetService` and `MediaAccessService` were NOT modified — mission
  said they may be touched "only when direct evidence proves a residual
  route cannot be closed without them," and no such evidence existed.
- No file beyond this list was touched. Any further application file would
  have required stopping at `IMPLEMENTATION_SCOPE_BLOCKED` — this did not
  occur.
