# Boundary Route Resolution — Slice 2F-27

Explicit disposition for the required boundary routes. Inventory classification
is kept strictly separate from security-remediation decisions (WS7).

## Inventory-classification boundary routes

| Route | Final persona | Basis |
|---|---|---|
| `POST /v1/compliance/portability-requests` | TENANT_PROVIDER_MUTATION | body user_id+tenant_id under get_current_user; writes a portability request scoped to a tenant |
| `POST /v1/serviceability/check` | TENANT_PROVIDER_MUTATION | require_permission(SERVICEABILITY_CHECK); customer-conditional; genuine product-decision ambiguity |

## Proposed canonical additions (outside the 123 mixed-persona population)

`DELETE /v1/webhooks/endpoints/{endpoint_id}` and `DELETE /v1/geo/zones/{zone_id}`
are NOT members of the 123-route mixed-persona population; they were surfaced
separately in 2F-26C and hand-verified across 26C–26H. Both remain
`require_permission(P.TENANT_UPDATE)`, genuine deletions, tenant/provider
mutations, absent from canonical, protection UNPROTECTED. **Reconfirmed, NOT
applied** — see the approval gate for why no canonical edit is made this slice.

## Security-observation routes (NOT automatic inventory changes — WS7/WS13)

`POST /v1/security/sessions/{session_id}/revoke`, `POST /v1/security/audit-log`,
`delete_rule`, `delete_kb`, `delete_asset`, `delete_document`,
`badges/recalculate` are carried in the security-observation registry as
**static, unexecuted** observations. Their inventory persona (tenant mutation
or not) is recorded in the final partition, but no security remediation and no
canonical protection-status change is made from them here.