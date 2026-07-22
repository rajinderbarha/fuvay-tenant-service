# Lead Assignment Read Boundary — Slice 2F-11A (Workstream 5)

## Direct verification performed

| Scenario | Mechanism | Result |
|---|---|---|
| Foreign-tenant lead rejection | `tenant_id` filter in `_get_lead`/`get_timeline`/`get_notes` (existing, unmodified) | Not found — no row matches; re-verified via `TestTenantIsolationOnReads` |
| Same-tenant unassigned technician | Previously: any tenant match sufficed (no assignment filter). Now: denied at the persona layer before reaching any query at all | STATE fixed: `require_owner_or_office_staff_read` denies technician outright |
| Same-tenant assigned technician | Same as above — technician has no path at all now, assigned or not | Denied (no evidence supports even assigned-technician read access) |
| Foreign-tenant technician | Denied at persona layer (same as same-tenant technician) | Denied |
| Staff lead access (same tenant) | `require_owner_or_office_staff_read` admits, `tenant_id` filter scopes to their own tenant | Allowed, tenant-scoped |
| Tenant-owner lead access | Same | Allowed, tenant-scoped, business-wide within tenant |
| Request `agent_id` override | No route accepts an `agent_id`/assignment field in any read request — reads take only `lead_id` (path) | Structurally impossible |
| Request `tenant_id` override | No read route schema accepts a `tenant_id` field — always sourced from `user.tenant_id` | Structurally impossible |
| Lead ID path substitution | Tenant filter rejects any lead outside the caller's own tenant | Rejected (not found) |
| Timeline ID substitution | Same tenant filter applies to `get_timeline` | Rejected |
| Notes lead-ID substitution | Same tenant filter applies to `get_notes` | Rejected |
| Customer tracking ID substitution | Combined `id` + `customer_id` filter in the inline query | Rejected (not found) — re-verified via `test_foreign_customer_lead_not_found` |

## Important caveat honestly recorded
A 404/not-found result from a genuinely mismatched fixture (foreign
tenant_id, foreign customer_id) is accepted here as ownership proof
**because the query construction itself was directly inspected** (the
`tenant_id`/`customer_id` filter is present in the actual `WHERE` clause,
confirmed by source read), not merely because a mocked test happened to
return `None`. This satisfies the mission's explicit warning that "a
read returning 404 due to a malformed fixture is not ownership proof" —
the proof here is the query construction, with the test as
corroboration, not the sole evidence.
