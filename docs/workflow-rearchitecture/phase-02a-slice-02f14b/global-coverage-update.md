# Global Coverage Update — Slice 2F-14B

## Starting canonical baseline

158 protected of 210 tenant-facing mutation routes (Slice 2F-14A).

## Routes newly protected this slice

9 of `field_ops.router`'s remaining 11 unprotected routes:
`create_job`, `convert_to_repair`, `spawn_repair` (creation/conversion — now
`TENANT_MUTATION_PERMISSION_SCOPE_AWARE`), `create_quote`, `create_job_quote`, `send_job_quote`
(now `STAFF_EXECUTION_ROLE_SCOPE_AWARE` via `require_staff_or_above_mutation`),
`respond_to_quote`, `approve_job_quote`, `reject_job_quote` (now
`CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED` via `require_customer`).

## Routes remaining unprotected (by tool convention)

`add_note`, `add_media` — 2 routes. Both have a real, verified service-level ownership fix
(Slice 2F-14A) that the runtime dependency-introspection tool cannot see (the fix is inside the
service method, not a named FastAPI dependency). Documented consistently with Slice 2F-14A's own
disclosure — not counted as protected in the canonical figure.

## New canonical result

**167 protected of 210 tenant-facing mutation routes** (up from 158/210).

Recount methodology unchanged from Slice 2F-14A: `VERIFIED` set =
`{TENANT_MUTATION_PERMISSION_SCOPE_AWARE, TENANT_MUTATION_ROLE_SCOPE_AWARE,
STAFF_EXECUTION_ROLE_SCOPE_AWARE, PLATFORM_ADMIN_ONLY, PUBLIC_NO_AUTH,
CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED, FULLY_PROTECTED}`.

## field_ops-specific subtotal

40 rows total (6 staff_router + 6 checklist_router + 28 router), **38 protected** (up from 29).

## Verification

- Zero duplicate `(method, path, module)` keys (re-confirmed).
- Zero `FALSE_POSITIVE` rows (re-confirmed).
- Both figures (167/210 total, 38/40 field_ops) are recounted directly against the single master
  CSV by an automated test (`TestCanonicalCoverageRecount`, updated this slice).
- No "headline convention" — one number pair reported.
