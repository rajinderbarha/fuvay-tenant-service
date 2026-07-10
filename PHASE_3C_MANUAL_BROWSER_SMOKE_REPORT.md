# Phase 3C — Manual Browser Smoke Report

## Environment limitation (same as every prior sprint this session)

No interactive browser automation tool is available in this environment.
Both the real backend (`uvicorn`) and real frontend (`npm run dev`) were
running, and every target page/action was hit over real HTTP (server-side
render + live API calls with a real super_admin JWT) to confirm the full
request/response cycle — this is **not** a substitute for a true browser
walkthrough (no JS execution trace, no DevTools console capture, no visual
screenshot), but it is stronger evidence than static inspection alone.

## Step-by-step

| # | Step | Verified how | Status |
|---|---|---|---|
| 1-3 | Start backend/frontend, login as Super Admin | `uvicorn` + `npm run dev` both running; `POST /v1/auth/login` → 200 with real JWT | ✅ |
| 4 | Open Bargain Rules | `curl http://localhost:3000/admin/pricing/bargain-rules` → 200, page title "Bargain Rules" present in HTML | ✅ SSR-level |
| 5 | Summary cards exist | `GET /v1/admin/pricing/bargain-rules/summary` → real 8-key JSON; page source contains all 8 card labels | ✅ API+source |
| 6 | AC Repair Bargain row shows service context | `GET /v1/admin/pricing/bargain-rules` → `master_service_name: "AC Repair"` | ✅ API-level |
| 7 | Price context shows base ₹800, min ₹600, max ₹1200 | Same response: `base_price:800, min_price:600, max_price:1200` | ✅ API-level |
| 8 | Bargain floor shows ₹650 | `floor_amount: 650.0` | ✅ API-level |
| 9 | Bargaining enabled + inactive → warning | Confirmed both states live: while `status="inactive"`, response included `"warning":"Bargaining is configured but this rule is inactive."`; after `/activate`, `warning` became `null` and `readiness` became `"ready"` | ✅ API-level, both states exercised |
| 10-11 | Detail drawer + tabs | `GET .../{id}` and `GET .../{id}/audit` both 200 with real data; page source contains all tab labels (Overview/Scope/Pricing/Evaluation/Provider Approval combined + Validation + Audit Logs) | ✅ API+source |
| 12-20 | Evaluate Offer ₹500/₹650/₹700 | All 3 executed live against `POST /pricing/bargain/evaluate-preview`: ₹500 → rejected/below floor; ₹650 → accepted; ₹700 → accepted; each response included `rule_used: "AC Repair Bargain"` and `pricing_source: "pricing_rule"` | ✅ API-level, exact ticket values |
| 21-23 | New Bargain Rule wizard, 5 steps | Page source confirmed contains all 5 step headers; not submitted (no test data pollution) | ✅ source-level |
| 24-26 | Provider Overrides page, summary cards, tenant name | `curl .../provider-overrides` → 200; `GET .../summary` real KPIs; `GET .../provider-overrides` → `tenant_name: "Demo AC Services", tenant_code: "demo-ac-services"` | ✅ API+SSR |
| 27-29 | Service context, platform range, delta | Same response: `master_service_name:"AC Repair"`, `platform_min_price:600, platform_max_price:1200, platform_base_price:800, delta_from_base:100` | ✅ API-level |
| 30-31 | Detail drawer + tabs | `GET .../{id}` and `.../{id}/audit` 200; page source has all tab labels | ✅ API+source |
| 32 | New Override wizard opens | Page source confirms 5 step headers (Tenant/Service Scope/Override Price/Approval/Review) | ✅ source-level |
| 33-34 | ₹500 → rejected below min + request_id | `POST .../validate-preview` with 500 → `OVERRIDE_BELOW_PLATFORM_MIN`, `platform_min_price:600`, real `request_id` in response envelope | ✅ API-level |
| 35-36 | ₹900 → valid / duplicate | For a *fresh* tenant/service pair (no existing override) this returns `valid:true`; for the specific seeded tenant/service (which already has an active override from the prior sprint) it correctly returns `DUPLICATE_ACTIVE_OVERRIDE` — both are correct outcomes of the new validation logic, not a bug | ✅ API-level, both paths verified |
| 37-38 | ₹1300 → rejected above max | `OVERRIDE_ABOVE_PLATFORM_MAX`, `platform_max_price:1200` | ✅ API-level |
| 39 | Approve/Reject on safe test override | Not exercised this pass to avoid mutating the shared demo dataset further (already exercised for the identical code path in the Phase 3 and Phase 3B sprints) | ⚠️ not re-run, prior evidence stands |
| 40-41 | Audit Logs show bargain/override actions | `GET .../bargain-rules/{id}/audit` and `.../provider-overrides/{id}/audit` both return real, multi-entry audit histories with `request_id` on each entry | ✅ API-level |
| 42 | No browser console errors | **Not verifiable** — no real browser/DevTools session was opened. The frontend dev server's own log was checked and showed zero errors originating from either pricing page (all logged errors traced to unrelated pre-existing pages: Tenant360, TenantsPage) | ⚠️ partial — log-level check only |
| 43 | No NaN/null/undefined in UI | **Not verifiable visually.** All backend numeric fields confirmed as proper floats/ints (never `null` in the happy-path responses checked); all rendering paths use the shared `money()` helper which returns `"—"` for `null`/`undefined` rather than printing `NaN` | ⚠️ partial — strongest available proxy |
| 44 | No forbidden labels | Grepped both new page files + all edited backend files for all 8 forbidden strings — zero occurrences (also covered by automated test `test_no_forbidden_labels`) | ✅ source-level |

## Bottom line

40 of 44 steps have strong evidence (live API-level or SSR/source-level,
several newly exercised this sprint for genuinely new functionality,
including both states of the "enabled but inactive" warning and both
outcomes — below-min and duplicate — of the ₹900 validation scenario).
Steps 39/42/43 rely on prior-sprint evidence or log-level/proxy checks rather
than a fresh interactive browser session; a true browser walkthrough with
DevTools console capture was never performed in this environment (consistent
with every prior sprint this session — the environment lacks that tool).

Per the ticket's own rule — **"If manual browser smoke is skipped, return
PARTIAL_READY_WITH_PHASE_3C_BLOCKERS"** — since a live interactive browser
session (not curl/SSR proxies) was never actually opened, the honest
classification is that manual smoke was **not fully run**, only strongly
approximated. This is the deciding factor for the final recommendation below.
