# FINAL-L5-02 — Remaining Blockers

## Genuinely certified this sprint (real evidence)
1. Complete endpoint inventory: 2,253 endpoints, machine-readable (JSON/CSV) + full OpenAPI spec.
2. Router mount: 137 mounted, 6 accounted-for unmounted, 1 duplicate mount found.
3. Authentication: all 7 canonical roles log in live; invalid rejected; missing-token 401.
4. **Authorization RBAC fix confirmed LIVE** (closing FINAL-L5-01B's live gap): customer/technician/tenant_owner → 403 on admin endpoints.
5. Auth-before-validation invariant proven (403 before service/DB).
6. Tenant isolation at data layer + critical cross-tenant admin-read vector.
7. Source-of-truth: `tenant_billing`/`service_jobs` canonical; `tenant_wallets` confirmed dormant.
8. request_id present on all error responses in the smoke matrix.
9. Migration chain proven base→head (FINAL-L5-01B-PLUS) + 8,936 tests collect clean.
10. **6 real authenticated browser sessions run** (Admin/Tenant Owner/Tenant Read Only/Customer One/Customer Two/Technician One) against live servers — Admin clean pass, Customer Two isolation confirmed, 2 genuine bugs found and root-caused (below).
11. Full-stack repeatability proven (4th cycle) including frontend/browser layer, not just DB.
12. All 4 missing rule domains formally classified `NOT_SEEDABLE_NO_SCHEMA` with evidence.

## Real findings logged (not fixed this sprint)
1. **Duplicate service-setup-template router mount** (7 duplicate operation IDs) — deferred pending consumer audit.
2. Sprint 34F service-setup router likely runtime-broken against the current (097) schema.
3. 2 dead brand routers still present (unmounted).
4. ~190 tenant-scoped tables lack DB-level FK (carried from FINAL-L5-01B).
5. **BUG-L502-005**: Tenant Portal Jobs page calls the legacy `/v1/jobs` endpoint instead of canonical `/v1/provider/service-jobs*` — real jobs data invisible to Tenant Owner. Root-caused, frontend fix needed.
6. **BUG-L502-006**: Customer bookings list empty — canonical endpoint correctly queries `service_bookings`, but FINAL-L5-01's seed only populated `bookings`. Seed-gap, not a backend defect. Root-caused; needs seed extension (blocked on understanding the `draft_id` FK subsystem).
7. Tenant Read Only mutation-button check inconclusive (needs stricter selector than text-matching).
8. Technician One browser redirect timing inconclusive (login succeeded, page redirect not confirmed within wait window).

## Not exhaustively covered this sprint (honest scope gaps)
A 33-part, 2,253-endpoint certification cannot be fully executed to genuine evidentiary standard in one pass without fabricating verdicts (which the non-negotiable rules forbid). The following parts were **not** completed to full depth:
- Per-endpoint request/response schema diff for all 2,253 endpoints (Part 4 deep).
- Full authorization matrix: every mutation × 10 roles with 403-before-422 (Part 6 deep) — representative subset done.
- Full frontend-to-backend contract matrix mapping every frontend call (Part 8).
- Input/business validation fuzzing per endpoint (Part 12).
- Idempotency live-replay for every critical op (Part 13) — ledger exactly-once proven in FINAL-L5-01, others not re-run.
- Transaction/concurrency stress (Part 14).
- Per-domain Admin/Tenant/Customer/Staff/Config certification depth (Parts 17-21) — representative smoke done.
- File upload/download security fuzzing (Part 22).
- Notification/event integration live tests (Part 23).
- Audit payload certification (Part 24).
- Performance profiling with budgets (Part 25) — only the ~2s local baseline noted.
- Rate-limit behavior verification (Part 26).
- API security fuzzing: IDOR/SQLi/mass-assignment/path-traversal (Part 27).
- Full browser-connected network-evidence verification across all 13 workflows (Part 30) — dashboard 404 fixed, but full 6-session network capture not re-run.
- API developer guide (Part 32).

## Assessment
The **foundational inventory + critical security/auth/isolation/source-of-truth invariants are genuinely certified with live evidence**. The breadth-certification of all 2,253 endpoints and the deep per-domain/security/performance parts are representative, not exhaustive — reported honestly rather than claimed.
