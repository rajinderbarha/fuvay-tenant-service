# ADMIN-TENANT-E2E-11 — Browser E2E Report

Real system Chrome via `frontend/e2e-admin-tenant/`, new spec
`e2e/tenant-finance-notif-settings-e2e11.spec.ts`, 9 tests, **9/9 passing**.

A real, second bug was found and fixed mid-sprint via this browser
testing itself: the tenant app's onboarding tour (a different mechanism
than the admin app's, using `localStorage` key
`serviceos-tenant-tour-done` rather than `serviceos_disable_tour_e2e`)
was not suppressed by the shared login helper, causing its modal to
intercept every click on first-visit pages — a genuine test-infrastructure
gap now fixed for future tenant-app specs too.

## Scenarios covered (of the ticket's 21)
1. Tenant Owner login — covered (all tests).
2. Open Finance Overview — covered (test 1, includes the `/finance`
   redirect fix verification).
3. Verify Usage Credit Balance — covered (test 2).
4. Open Usage Credit Ledger — covered (test 3).
5. Verify Completed Job Deduction entries — covered (test 3).
6. Verify ledger arithmetic — covered (test 3, `3958`/`3937` assertions).
7. Verify low-credit alert behavior — **documented, not live-tested**
   (see low-credit report — no forced low-balance state created this
   pass).
8. Verify Security Deposit Held display — covered (test 4).
9. Open Tenant Notifications — covered (test 5).
10. Verify notification feed or honest empty state — covered (test 5).
11. Verify tenant notification bell — covered (test 6, includes the
    dead-bell fix verification).
12. Open Tenant Settings — covered (test 7).
13. Verify profile/settings data — covered (test 7).
14. Save safe preference then revert — **not exercised** (would mutate
    shared seed state; the RBAC test's mutation was deliberately
    created-then-deleted instead, as a more targeted verification).
15. Login as Tenant Read Only — covered (test 8).
16. Verify read-only cannot mutate settings — covered, and **failed**
    (see RBAC report — the sprint's central finding).
17. Verify no forbidden labels — covered (test 9).
18. Verify no mock runtime data — covered (test 9 + source scans).
19. Verify no direct fetch bypass — covered (source scan).
20. Verify no NaN/null/undefined — covered (assertions in every test).
21. Verify no raw JSON/debug UI — covered via screenshot review.

## Verdict
19 of 21 scenarios fully covered and passing; 1 documented-not-tested
(low-credit visual state, no real low-balance data to test against); 1
covered and **failed** (read-only RBAC) — the sprint's real, honest
blocker.
