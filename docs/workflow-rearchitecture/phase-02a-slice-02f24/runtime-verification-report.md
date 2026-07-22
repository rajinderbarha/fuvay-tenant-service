# Runtime Verification Report — Slice 2F-24

## Module
`app.engines.customer_reviews.provider_router`

| Metric | Value |
|---|---|
| Selected mutations | **2** |
| Related alternate mutations | 5 (customer flag/submit/edit; admin moderation family) |
| Related reads | 9 (3 provider, 2 customer, 4 public) + admin reads |
| Capability | `PROVIDER_REPLY_CREATE`, `PROVIDER_REVIEW_FLAG` |
| Persona | `tenant_owner` (+`super_admin`) |
| Mutation-scope enforcement | ENFORCED — read-only `access_scope` denied |
| Review tenant/provider authority | `DIRECT_TENANT_COLUMN` via central scoped lookup |
| Customer authority | `DIRECT_CUSTOMER_COLUMN`, self-scoped |
| Actor attribution | server-derived id + allow-listed type |
| Reply integrity | one per review; `REPLY_ALREADY_EXISTS` preserved |
| Flag integrity | ownership-scoped; tenant from review; no aggregate effect |
| State-machine enforcement | provider/customer reach only `flagged`; admin owns all other transitions |
| Alternate-route status | no weaker same-record route remains |
| Read/privacy status | both detail-read IDORs closed |
| Legacy 410 status | **PRESERVED** |
| Protected selected count | **2 of 2** |
| Unverified count | **0** |
| Documentation/runtime consistency | verified — live recount 226/209 |

## Live route walk (post-change)

```
POST /v1/provider/reviews/{review_id}/reply -> TENANT_MUTATION_ROLE_SCOPE_AWARE
POST /v1/provider/reviews/{review_id}/flag  -> TENANT_MUTATION_ROLE_SCOPE_AWARE
POST /v1/customer/reviews/{review_id}/flag  -> (customer surface; ownership-enforced)
POST /v1/reviews                            -> 410 GONE (legacy, preserved)
TOTAL_MUTATION_ROUTES = 1186  (unchanged — inventory remains complete)
```

Note on the customer route's guard_status: the walker reports the *dependency*
class, and `require_customer` is a role check rather than a tenant-scope one.
Its protection is object-ownership (`customer_id` predicate), which the
walker's vocabulary does not model. Stated explicitly so the label is not
mistaken for a gap.

## Exit conditions (verifier must exit non-zero if any hold)

| Condition | Result |
|---|---|
| A selected route remains bare-authenticated | **NO** |
| A primary-key-only lookup authorizes a mutation | **NO** — `_get_review` is admin-read only, documented |
| Cross-tenant or cross-provider review mutation remains | **NO** — SQL predicate |
| A customer can submit a provider reply | **NO** — persona guard |
| A customer action is attributed as provider | **NO** — guard + allow-list |
| Client tenant ID remains authoritative | **NO** — rejected by schema, derived from review |
| Arbitrary review status can be selected | **NO** — service constants only |
| A weaker same-record route remains | **NO** |
| Legacy `POST /v1/reviews` reactivated | **NO** — still 410 |
| An unsafe route marked FULLY_PROTECTED | **NO** |
| Documentation disagrees with runtime | **NO** |

**Runtime verification exits zero.**

## Test-suite exit codes
- `test_phase2f24_customer_review_authorization.py` — 46 passed, exit 0
- `test_sprint24_customer_reviews.py` — 37 passed, exit 0
- Full slice-suite set — 276 passed, exit 0
