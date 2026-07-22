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

---

# Carried forward and extended — Slice 2F-26F

All prior observations are retained. **None remediated; zero application files
modified.** All remain **static-reading only — none executed against a live
tenant pair.** They must not be described as proven exploits.

## Explicitly restated, as required

| Route | Static evidence | Potential impact | Confidence | Executed |
|---|---|---|---|---|
| `DELETE /v1/pricing/tenants/{tenant_id}/rules/{rule_id}` | handler calls `delete_rule(rule_id)`; the path `tenant_id` is **never passed on** | a permission holder in tenant A could delete tenant B's rule; there is no code path on which tenant could be enforced | HIGH | no |
| `POST /v1/commerce/tenants/{tenant_id}/badges/recalculate` | gated by `P.TENANT_HEALTH_READ` — a **read** permission — while the service recalculates and persists | write reachable with read-only authority | MEDIUM | no |
| `POST /v1/security/audit-log` | `get_current_user`; `tenant_id`, `entity_id`, `before`/`after` all from the body | any authenticated principal may append arbitrary audit entries attributed to another tenant, weakening every control that cites the audit log as evidence | MEDIUM | no |
| Other client-asserted tenant cases | `require_permission(P.TENANT_UPDATE)` with tenant from path/query/body and no own-tenant assertion | cross-tenant mutation | MEDIUM | no |

## New this slice (from third-holdout reading)

| Route | Static evidence | Potential impact | Confidence | Executed |
|---|---|---|---|---|
| `POST /v1/security/sessions/{session_id}/revoke` | `get_current_user`; `revoke_session(session_id, reason)` — the principal is **never referenced**, session addressed by id alone | any authenticated principal could revoke any other user's session given its id | HIGH | no |
| `DELETE /v1/pricing/tenants/{tenant_id}/zones/{zone_id}` | `delete_zone(zone_id)` — same tenant-discard shape as `delete_rule` | cross-tenant deletion | HIGH | no |
| `POST /v1/compliance/consent/withdraw` | `user_id` **and** `tenant_id` both from body under `get_current_user` | withdraw another user's consent; mirrors the `POST /v1/compliance/consent` observation | MEDIUM | no |
| `POST /v1/payments/tenants/{tenant_id}/payout` | tenant from path, `amount` from body, no own-tenant assertion | payout initiated against another tenant | MEDIUM | no |
| `POST /v1/payments/orders` | `tenant_id`, `customer_id`, `amount` all from body | order created against another tenant | MEDIUM | no |
| `POST /v1/security/api-keys` | `tenant_id` from body; returns a raw API key once | API key minted for another tenant | MEDIUM | no |
| `GET /v1/ds/tenants/{tenant_id}/customers/{customer_id}/ltv` | `get_current_user`, client tenant; **also a mutating GET** (`db.add` + `flush`) | cross-tenant customer-value read, plus unexpected persistence on a GET | MEDIUM | no |
| `POST /v1/appointments/hold` | `tenant_id`, `customer_id`, `staff_id` all from body | hold created against another tenant | MEDIUM | no |

### Recommended route-specific investigation

The two highest-signal items are `POST /v1/security/sessions/{session_id}/revoke`
(no principal reference at all) and the `delete_rule` / `delete_zone` pair
(tenant present in the URL and discarded before the service call). Each needs a
runtime two-tenant test before any conclusion is drawn.

---

# Carried forward — Slice 2F-26G

All 20 prior observations retained. **None remediated; zero application files
modified; all static-reading only — none executed against a live tenant pair.**

Prominently re-tracked, as required:

| Route | Static evidence | Confidence | Executed |
|---|---|---|---|
| `POST /v1/security/sessions/{session_id}/revoke` | revokes by session id; principal never referenced | HIGH | no |
| `DELETE /v1/pricing/tenants/{tenant_id}/rules/{rule_id}` | `delete_rule(rule_id)` discards URL tenant_id | HIGH | no |
| `POST /v1/commerce/tenants/{tenant_id}/badges/recalculate` | gated by read permission `TENANT_HEALTH_READ` while writing | MEDIUM | no |
| `POST /v1/security/audit-log` | accepts arbitrary authenticated audit entries | MEDIUM | no |
| client-asserted tenant cases lacking ownership proof | `require_permission(TENANT_UPDATE)` + client tenant | MEDIUM | no |

## New this slice (from fourth-holdout reading, static only)

| Route | Static evidence | Confidence | Executed |
|---|---|---|---|
| `DELETE /v1/settings/tenants/{tenant_id}/{key}` | `delete_tenant_setting(tenant_id, key)` — tenant IS passed, but no own-tenant assertion vs principal | MEDIUM | no |
| `DELETE /v1/media/{media_id}` | `delete_asset(media_id)` — object by id, no tenant, no principal ownership evident in handler | MEDIUM | no |
| `DELETE /v1/rag/knowledge-bases/{kb_id}` | `delete_kb(kb_id)` — same discard shape as delete_rule | MEDIUM | no |
| `POST /v1/pricing/tenants/{tenant_id}/prices/set` | client tenant, versions prices; no own-tenant assertion | MEDIUM | no |
| `POST /v1/geo/tenants/{tenant_id}/zones` | client tenant, no assertion | MEDIUM | no |
| `POST /v1/chat/conversations` | `tenant_id` from body under `get_current_user` | MEDIUM | no |
| `POST /v1/compliance/deletion-requests` | `user_id` + `tenant_id` from body | MEDIUM | no |
| `POST /v1/inventory/reservations` | `tenant_id` from body, no assertion | MEDIUM | no |

The `delete_rule` / `delete_kb` / `delete_asset` family — objects addressed by
id with the tenant either discarded or absent — remains the highest-signal
group and warrants a runtime two-tenant test before any conclusion.
