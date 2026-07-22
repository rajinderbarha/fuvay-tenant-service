# Authorization Observations — Slice 2F-26D (observed, NOT remediated)

Reading 24 handlers for classifier validation surfaced apparent authorization
weaknesses. **No application file was modified this slice.** This slice
selected no module and holds no mandate to change authorization behaviour;
these are recorded for a future slice to select, prove and close properly.

They are stated as **observations from static reading**, not as confirmed
exploitable defects — none was executed against a live tenant pair.

## O-01 — Client-asserted tenant with no ownership assertion

These accept `tenant_id` from the client (path, query or body) and pass it
to the service without any `_assert_own_tenant_or_super_admin`-style check.
The guard proves the caller holds `TENANT_UPDATE` *somewhere*, not that they
hold it **for the tenant they named**.

| Route | Guard | tenant_id source |
|---|---|---|
| `DELETE /v1/media/tenants/{tenant_id}/files/{file_id}` | `require_permission(P.TENANT_UPDATE)` | path |
| `POST /v1/pricing/tenants/{tenant_id}/rules` | `require_permission(P.TENANT_UPDATE)` | path |
| `POST /v1/appointments/staff/{staff_id}/calendar/block` | `require_permission(P.TENANT_UPDATE)` | query |
| `POST /v1/documents` | `require_permission(P.TENANT_UPDATE)` | body |
| `POST /v1/inventory/reservations/confirm` | `require_permission(P.TENANT_UPDATE)` | body |

Contrast with `/v1/tenants/{tenant_id}/...`, which does assert own-tenant.
The pattern exists in the codebase; it is not applied here.

## O-02 — No tenant scope at all

`DELETE /v1/appointments/calendar/blocks/{block_id}` resolves the block by id
alone — `unblock_calendar_time(block_id)`. Same shape as the IDOR closed in
2F-24 for customer reviews.

## O-03 — Authenticated-only writes carrying a client-supplied subject

| Route | Guard | Concern |
|---|---|---|
| `POST /v1/compliance/consent` | `get_current_user` | both `user_id` **and** `tenant_id` come from the body — an authenticated principal can append to another user's immutable consent ledger |
| `POST /v1/security/audit-log` | `get_current_user` | `tenant_id` and full `before`/`after` from the body — audit entries attributable to another tenant |
| `POST /v1/pricing/compute` | `get_current_user` | `body.tenant_id`; writes an immutable pricing snapshot |

O-03 deserves the most attention: an audit log that any authenticated caller
can write arbitrary entries into weakens every other control that relies on
it as evidence.

## O-04 — Partial check

`POST /v1/geo/tenants/{tenant_id}/staff/{staff_id}/location` correctly blocks
a `staff` principal from spoofing a colleague, but the check is conditioned on
`u.role == "staff"`; other authenticated roles pass unchecked, and
`tenant_id` is client-supplied.

## Reads (outside the mutation denominator, noted for completeness)

`GET /v1/ds/tenants/{tenant_id}/churn/score` is guarded by `get_current_user`
alone with a client-supplied `tenant_id` — a read-privacy concern of the same
family closed for the legacy review engine in 2F-25A.

---

**Status: none remediated, none scheduled.** Recording them here rather than
acting is the correct behaviour for a validation slice; acting would be an
unmandated authorization change outside any selected module.
