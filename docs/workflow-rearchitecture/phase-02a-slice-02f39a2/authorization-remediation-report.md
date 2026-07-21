# Authorization Remediation Report — Slice 2F-39A2

## Fixed this slice (1 real defect, confirmed and closed)

**`security.router::create_api_key`** — two independent, compounding gaps
in the same endpoint:
1. Used `require_permission(P.TENANT_UPDATE)` instead of
   `require_tenant_mutation_permission(P.TENANT_UPDATE)` — bypassed the
   tenant read-only `access_scope='customer_support_limited'` restriction
   entirely.
2. Read `tenant_id` directly from the client-supplied request body with
   zero comparison to the caller's own tenant — a cross-tenant IDOR: any
   `tenant_owner` in any tenant could create an API key scoped to any
   *other* tenant.

Fixed: guard swapped, `tenant_id` now server-derived. 4 new tests prove
it. See `service-layer-bypass-audit.csv` / commit `7eaeca8`.

## Found, NOT fixed this slice (6 real, unresolved findings)

These required a product/architecture decision this slice could not make
responsibly without risking an incorrect guess:

| Route | Gap | Why not fixed |
|---|---|---|
| `POST /v1/security/activity/record` | Bare `get_current_user`, zero permission/scope/ownership check; `tenant_id`/`entity_id`/`activity_type` fully client-controlled | Zero internal callers found anywhere in the codebase (grepped) — cannot confirm whether this is meant to be an internal-service-only endpoint (needing an internal-authority guard) or a genuinely user-facing one (needing ownership checks). Guessing wrong risks either leaving a real gap or breaking an undiscovered legitimate caller. |
| `POST /v1/security/audit-log` | Same class of gap — bare auth, fully client-controlled `tenant_id`/`entity_id`/`operation` for an "append-only, immutable" audit log | Same reasoning — zero internal callers found; intended caller model unclear. |
| `POST /v1/security/sessions` | Bare auth, client-controlled `user_id`/`tenant_id`/`session_id` | Same reasoning. |
| `DELETE /v1/security/sessions/{session_id}` | Bare auth, no ownership check — any authenticated user could revoke any other user's session record by ID | Same reasoning. |
| `POST/PATCH /v1/pricing/tenants/{tenant_id}/rules/{rule_id}/activate,deactivate` | Uses `require_permission` not `require_tenant_mutation_permission` — same class of gap as `create_api_key`, but for pricing rules | Not independently confirmed this is unintentional (vs. e.g. a deliberate design where rule activation is exempt from the read-only-scope restriction) before this slice ran out of time to verify against the pricing engine's own product intent. |

**These 6 are real, evidenced, security-relevant gaps this slice
discovered and is explicitly not concealing.** They are recorded here,
in `final-route-classification.csv` (as `PRODUCT_DECISION_REQUIRED`), and
in `known-limitations.md` — not silently deferred.

## Read-path privacy observations (out of mutation-authorization scope, not fixed)

- `POST /v1/commerce/bookings/preflight` (`run_preflight`): read-only
  (no DB write traced), but accepts a client-supplied `tenant_id` with no
  ownership check — any authenticated user can query another tenant's
  commission rate / health band / wallet buffer via the preflight
  response.
- `POST /v1/pricing/snapshots/{snapshot_id}/replay` (`replay_snapshot`):
  read-only, but fetches `PriceSnapshot` by ID with **no tenant_id filter
  at all** — any authenticated user can view another tenant's historical
  pricing snapshot.

Both are consistent with this program's already-documented,
explicitly-out-of-scope "pricing/read-path tenant privacy" limitation
(carried in every prior slice's `known-limitations.md` since 2F-37) — not
new territory, but now backed by two concrete, named routes rather than a
general statement.
