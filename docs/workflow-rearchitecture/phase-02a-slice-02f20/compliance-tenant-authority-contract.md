# Tenant Authority Contract

## One authoritative tenant source
For every one of the 6 selected routes (and `download_export`), the
tenant identity used to scope EVERY database query and EVERY write is
`_require_tenant(u)` — which reads `u.tenant_id` (server-derived from the
JWT via `get_current_user`, never client-supplied) and raises
`ServiceOSException("FORBIDDEN", ...)` if absent. This was already true
before this slice (the helper itself was not broken) — what this slice
fixed was ensuring that value is CONSISTENTLY and ATOMICALLY the one
written into `metadata_json["tenant_id"]` at creation, and CONSISTENTLY
the one passed through to `ConsentRecord.tenant_id` on withdrawal.

## Requirements checklist
- **Principal tenant is server derived** — TRUE, unchanged (`u.tenant_id`
  from JWT).
- **Request tenant_id cannot broaden access** — TRUE, structurally: no
  route in `provider_router.py` accepts a `tenant_id` field in its request
  body at all (confirmed by reading all 6 handlers' body-parsing code —
  only `reason`, `response`, `confirm_understanding`, `details`,
  `request_type` are ever read from `r.json()`).
- **JSON/metadata tenant scope is validated and type checked** — TRUE for
  the WRITE path (this slice's atomic `metadata_json` fix guarantees the
  value written is always the caller's own `tenant_id_str`, a UUID string
  derived from `u.tenant_id`). For the READ/comparison path, the
  `metadata_json["tenant_id"].astext == tenant_id_str` SQLAlchemy/Postgres
  JSONB operator naturally fails closed for non-dict or missing metadata
  (`astext` on a missing/null path evaluates to SQL `NULL`, and
  `NULL == <string>` is `NULL`/falsy in Postgres, so the row is excluded)
  — confirmed by the existing, unmodified query pattern across all 4
  routes that need it.
- **Missing metadata tenant scope fails closed** — TRUE, per the above
  (a request row somehow lacking `tenant_id` in its metadata simply never
  matches any tenant's query — it becomes permanently unreachable by ANY
  tenant, not accessible-by-none-in-error, which is the fail-closed
  outcome).
- **Malformed tenant scope fails closed** — TRUE, same mechanism (a
  non-string, non-matching, or corrupted value at that JSON path never
  equals a valid UUID string).
- **Conflicting tenant sources fail closed** — N/A structurally: there is
  only ONE tenant source per record (`metadata_json["tenant_id"]`) — no
  second, competing tenant field exists on `ComplianceRequest` to conflict
  with it.
- **Cross-tenant request/export IDs reveal no content** — TRUE, unchanged:
  every lookup is `WHERE id == X AND metadata_json["tenant_id"] ==
  caller_tenant` — a cross-tenant ID simply doesn't match, producing the
  SAME "not found" outcome as a genuinely missing ID (see
  `compliance-read-privacy.md` for the explicit privacy-equivalence
  verification).
- **Service methods cannot silently operate with `tenant_id=None`** —
  FIXED THIS SLICE for `revoke_consent`/`withdraw_consent` (the one place
  this WAS happening); `create_request` never had this problem for
  tenant_id specifically (only the `metadata_json` drop-and-patch issue).
- **Tenant ownership is verified before mutation, worker enqueue, or file
  access** — TRUE for mutation (verified before every `db.add`/status
  change); N/A for worker enqueue (no worker exists, see
  `compliance-export-worker-discovery.md`); TRUE for file access
  (`download_export`'s tenant check, unchanged, now additionally gated by
  `require_tenant_owner_mutation`).

## One central helper, not six duplicated implementations
This slice did NOT introduce a new shared Python helper function for the
`metadata_json["tenant_id"].astext == tenant_id_str` pattern — the
EXISTING pattern (a SQLAlchemy WHERE-clause fragment, not Python logic)
is already identical and correct across all 4 routes that need it
(`customer_tenant_response` uses `related_tenant_id` instead, correctly,
since it's scoping a CUSTOMER's request via the tenant's link to it, not
the tenant's own request). Introducing a Python-level abstraction over a
single-line SQLAlchemy WHERE fragment was judged unnecessary duplication
risk reduction for a pattern that is already textually identical at each
of its 4 call sites — flagged as a minor code-quality opportunity in
`known-limitations.md`, not built, to avoid unnecessary abstraction for a
one-line expression per Slice discipline (no premature abstraction).
