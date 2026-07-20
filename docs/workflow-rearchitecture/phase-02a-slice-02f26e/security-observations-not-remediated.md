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

---

# Carried forward and extended — Slice 2F-26E

Still **none remediated**; no application file was modified. Reading the 24
fresh-holdout handlers added the following observations of the same families.

| Route | Guard | Tenant input | Missing ownership evidence | Confidence | Executed |
|---|---|---|---|---|---|
| `DELETE /v1/pricing/tenants/{tenant_id}/rules/{rule_id}` | `require_permission(P.TENANT_UPDATE)` | path | service is called as `delete_rule(rule_id)` — the path `tenant_id` is **never passed on**, so it cannot be checked | HIGH | no |
| `POST /v1/inventory/tenants/{tenant_id}/items` | `require_permission(P.TENANT_UPDATE)` | path | tenant passed through with no own-tenant assertion | MEDIUM | no |
| `POST /v1/pricing/tenants/{tenant_id}/zones` | `require_permission(P.TENANT_UPDATE)` | path | as above | MEDIUM | no |
| `POST /v1/ds/tenants/{tenant_id}/demand/recompute` | `require_permission(P.TENANT_UPDATE)` | path | as above | MEDIUM | no |
| `POST /v1/commerce/tenants/{tenant_id}/badges/recalculate` | `require_permission(P.TENANT_HEALTH_READ)` | path | a **read** permission gates a write action | MEDIUM | no |
| `POST /v1/analytics/events/ingest` | `get_current_user` | body | any authenticated principal may ingest events attributed to any tenant/actor | MEDIUM | no |
| `POST /v1/security/activity/record` | `get_current_user` | body | same family as the audit-log observation above | MEDIUM | no |
| `POST /v1/payments/invoices` | `require_permission(P.TENANT_BILLING_MANAGE)` | body | tenant and **amount** both client-supplied | MEDIUM | no |
| `POST /v1/dispatch/jobs/{job_id}/dispatch` | `require_permission(P.TENANT_UPDATE)` | body | tenant from body, no assertion | MEDIUM | no |
| `GET /v1/compliance/consent/users/{user_id}` | `get_current_user` | none | any authenticated principal may read any user's consent ledger | MEDIUM | no |
| `GET /v1/ds/tenants/{tenant_id}/demand/forecast` | `get_current_user` | path | read privacy; also a **mutating GET** (persists `DemandForecast`) | HIGH | no |
| `POST /v1/appointments/{appointment_id}/reschedule` | `get_current_user` | none | object addressed by id alone | MEDIUM | no |

The two highest-signal additions:

- **`delete_rule(rule_id)`** — the tenant is present in the URL and then
  discarded before the service call. There is no code path on which it could
  be enforced.
- **`badges/recalculate`** gated by `TENANT_HEALTH_READ`, a read permission,
  for an operation that recalculates and persists.

All observations are from **static reading only**. None was executed against a
live tenant pair. They are recorded so they survive the tooling slices; they
are not promoted to proven vulnerabilities, and fixing them belongs to a
future slice that selects the relevant module.
