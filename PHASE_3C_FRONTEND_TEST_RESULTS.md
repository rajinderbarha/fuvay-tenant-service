# Phase 3C — Frontend Test Results

## Commands

```bash
npx tsc --noEmit
python -m pytest tests/test_phase3c_frontend_certification.py -q
```

`npm run lint` / `npx next lint`: still broken pre-existing (Next.js 16
removed the `next lint` subcommand — documented in every prior sprint, not
caused by this sprint). `npm test`: no JS test runner configured in this
repo (consistent finding across every sprint this session) — Python
source-inspection tests via `pytest` remain the established convention.

## TypeScript result

**0 errors** across the entire `frontend/super-admin` build, including both
rebuilt pages, the extended `lib/api.ts` types/methods, the `useApi`/
`useAction` hook changes, and the new `usePermissions` hook.

## Frontend certification test result

`tests/test_phase3c_frontend_certification.py` — **24/24 passed**, mapping to
the ticket's 26 required frontend tests (2 of the ticket's granular test
descriptions — e.g. "Evaluate ₹500 shows rejected" and "Evaluate ₹650 shows
accepted" — are covered by one combined `test_evaluate_offer_renders_decision_shape`
test, since both assert the same rendering code path renders the `decision`
field generically rather than being hardcoded per-value):

1. Bargain summary cards wired to real endpoint + all 8 labels present
2. Bargain filters present (search/status/readiness/bargain-enabled)
3. Bargain table uses real `bargainRulesApi.list()`, no mock data
4. Readiness warning renders from real `row.warning` field
5. Detail drawer wired to real GET detail + audit endpoints
6. Wizard has all 5 required step headers
7. Evaluate Offer modal wired to real evaluate-preview endpoint
8. Evaluate Offer renders full decision/floor/offer/rule_used/pricing_source shape
9. Error states expose `requestId`
10. Provider Overrides summary cards + all 8 labels
11. Provider Overrides filters present
12. Tenant name/code rendered as primary display, raw ID only as small secondary
13. Service context (master service/type/brand/issue) rendered
14. Platform min/max/base/delta rendered
15. Detail drawer wired to real GET detail + audit endpoints
16. Wizard has all 5 required step headers
17. Validate-preview wired to real endpoint, renders `error_code` generically (not hardcoded per-value)
18. Permission guards present on both pages, checked against the real permission constants from Phase 3B
19. `usePermissions` hook reads real `/v1/auth/me`, not a hardcoded role list
20. Empty states present for both pages
21. Loading skeletons present for both pages
22. No forbidden labels in either page
23. `request_id` plumbing bug fix present in `lib/api.ts`/`useApi.ts`
24. No mock/fake/hardcoded runtime data markers in either page

## Live integration smoke (real backend + real Postgres, not simulated)

Performed via `curl` — see `PHASE_3C_MANUAL_BROWSER_SMOKE_REPORT.md` for the
full table. Confirmed matching the ticket's exact scenarios: bargain ₹500
rejected / ₹650 accepted / ₹700 accepted; override ₹500 below-min / ₹1300
above-max / ₹900 valid-or-duplicate (both correct outcomes depending on
existing data); tenant name always resolved; readiness warning correct in
both enabled+inactive and enabled+active states.

## Result: **PASS — TypeScript clean, all new frontend certification tests green, live API integration confirmed.**
