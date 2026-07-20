# Legacy Actor and Tenant Field Authority — Slice 2F-25

| Field | Source after 2F-25 | Classification |
|---|---|---|
| `tenant_id` (mutations) | principal via `_effective_tenant` / scoped lookup | `PRINCIPAL_DERIVED` |
| `tenant_id` (lists) | principal, client value refused if mismatching | `PRINCIPAL_DERIVED` |
| `Review.tenant_id` (on write) | the review's own row | `REVIEW_DERIVED` |
| `customer_id` | `_assert_owns` against the principal | `PRINCIPAL_DERIVED` (customer persona) |
| `replied_by` | `self.actor_id` from the JWT | `PRINCIPAL_DERIVED` |
| `flagged_by` | `self.actor_id` | `PRINCIPAL_DERIVED` |
| `resolved_by` | `self.actor_id` under `require_super_admin` | `PLATFORM_ADMIN_DERIVED` |
| `changed_by` (history) | `self.actor_id` | `PRINCIPAL_DERIVED` |
| `status` | service constants only | not client-settable |
| `flagged_reason` | client string, free text | `CLIENT_SUPPLIED_VALIDATED` (a reason, not authority) |
| `reply` text | client string | `CLIENT_SUPPLIED_VALIDATED` |

## Requirements check

| Requirement | Status |
|---|---|
| Client cannot choose tenant authority | **MET** — was the central defect |
| Client cannot choose provider identity | MET — no provider field exists; tenant is the provider |
| Client cannot choose actor type | MET — no actor-type field on this model |
| Customer action cannot be stored as provider/admin | MET — actor ids are principal-derived; `resolve_flag` is admin-only |
| Provider action cannot be stored as platform-admin | MET — `resolved_by` is only written by the super-admin route |
| Arbitrary status mutation fails closed | MET — statuses are constants; the only tenant-reachable transition is `-> flagged` |

## No actor-type field
Unlike the canonical engine (which has `flagged_by_type` / `ACTOR_PROVIDER`),
the legacy model records only actor **ids**, so there is no attribution string
to impersonate. Reported rather than assumed.
