# Deferred Items — Slice 2F-23

| Item | Reason deferred | Next step |
|---|---|---|
| **Fix `flag_review` cross-tenant IDOR** | This is a discovery/selection slice, explicitly prohibited from implementing | **Slice 2F-24** — highest priority; see `selected-next-module-security-plan.csv` |
| Fix `submit_reply` provider impersonation | same | Slice 2F-24 (same module) |
| Close `customer_router.flag_review` client-trusted `tenant_id` | same; it is a same-record alternate the implementation slice must handle | Slice 2F-24, in scope per `selected-next-module-boundaries.md` |
| Analytics zero-auth + export privacy | not selected; ranked HIGH | Slice 2F-25 candidate |
| profile.router technician-edits-tenant-identity | not selected; ranked HIGH | Slice 2F-25/26 candidate |
| media.new_router persona split (brand vs self) | not selected; ownership already enforced | bundle with profile.router |
| marketing_automation zero-auth | not selected; low blast radius, no external effect | small future slice |
| admin_catalog parent-child ownership (3 routers, 4 routes) | not selected | bundle catalog routers |
| Full read-privacy audit of the 19 | this slice audited mutation surfaces | each implementation slice |
| Frontend/mobile caller audit for the 19 | mission allows "where immediately discoverable" | each implementation slice |
| Trace analytics `filters` to its terminus | not required to rank the module | Slice implementing analytics |
| Full-application sweep for net-new routes | last done 2F-17A; out of this slice's 19-row scope | periodic re-sweep slice |
| Package Commerce payment integration | 2F-22 product decision | dedicated payment slice |
| Duplicate-pending unique index | migration-dependent | migration-enabled slice |
| Compliance export worker / dedup | 2F-20 product decision | dedicated slice |
| Slice-2D canary tests | explicitly prohibited from rewriting | requires `tenant-readonly-decision.md` conclusion |
| `mutation-enforcement-matrix.csv` staleness | legacy summary, non-authoritative | optional cleanup |

## Remaining queue after this slice
8 modules / 19 routes remain unprotected. 2 routes are selected for 2F-24;
the other 17 across 7 modules are ranked in `non-selected-module-queue.csv`.
