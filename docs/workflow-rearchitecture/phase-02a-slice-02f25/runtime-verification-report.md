# Runtime Verification Report — Slice 2F-25

## Module: `app.engines.review` (legacy)

| Metric | Value |
|---|---|
| Mounted legacy routes | **15** (14 functional + `/meta`) |
| Mutations | **5** (1 deprecated-410, 3 tenant, 1 platform-admin) |
| Reads | **10** |
| Tenant mutations added to the denominator | **3** |
| Platform-admin mutations (outside X/Y) | 1 (`resolve_flag`) |
| Deprecated (outside X/Y) | 1 (`POST /v1/reviews`, 410) |
| Protected legacy tenant routes | **3 of 3** |
| Unverified routes | **0** |
| Legacy 410 status | **PRESERVED** |
| Frontend caller status | tenant-portal live; compatible without change |
| Documentation/runtime consistency | verified — live recount 229/212 |

## Live route walk (post-change)

```
POST /v1/reviews                       -> AUTHENTICATED_ONLY_NO_PERMISSION_CHECK  (410 GONE; no service call)
POST /v1/reviews/{review_id}/reply     -> TENANT_MUTATION_PERMISSION_SCOPE_AWARE
POST /v1/reviews/{review_id}/flag      -> TENANT_MUTATION_PERMISSION_SCOPE_AWARE
POST /v1/reviews/{review_id}/resolve   -> PLATFORM_ADMIN_ONLY
POST /v1/reviews/requests              -> TENANT_MUTATION_PERMISSION_SCOPE_AWARE
TOTAL_MUTATION_ROUTES = 1186   (unchanged -- inventory remains complete)
```

The walker still labels `POST /v1/reviews` by its dependency shape; the route
raises 410 before any handler logic and calls no service method. It is
classified `DEPRECATED` and excluded from the denominator, not counted as an
unprotected mutation.

## Exit conditions

| Condition | Result |
|---|---|
| A route remains authenticated-only | **NO** (the 410 route excepted, and it mutates nothing) |
| Primary-key-only mutation remains | **NO** |
| Primary-key-only private read remains | **NO** for review content; 3 non-content reads disclosed as residuals |
| Cross-tenant mutation remains | **NO** |
| Cross-tenant private read remains | **NO** for review content |
| Client tenant authority remains | **NO** — mismatches refused |
| Actor impersonation remains | **NO** — no actor-type field; ids principal-derived |
| A genuine tenant mutation omitted from the denominator | **NO** — 3 found and added |
| Legacy `POST /v1/reviews` reactivated | **NO** |
| Documentation disagrees with runtime | **NO** |

**Runtime verification exits zero.**

## Test-suite exit codes
- `test_phase2f25_legacy_review_engine_authorization.py` — 49 passed, exit 0
- Canonical + recount + prior-slice suites — all passing
