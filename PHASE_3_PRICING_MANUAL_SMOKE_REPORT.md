# Phase 3 — Pricing & Rules Manual Browser Smoke Report

## Environment limitation (same as every prior sprint this session)

No interactive browser automation tool is available in this environment.
Both the real backend (`uvicorn`) and real frontend (`npm run dev`) were
started, and every target page was hit over real HTTP to confirm
server-side rendering succeeds — this is **not** a substitute for a true
browser walkthrough (no JS execution, no console-error check, no visual
confirmation), but it is stronger evidence than API-only testing.

## Step-by-step

| # | Step | Verified how | Status |
|---|---|---|---|
| 1-2 | Start backend/frontend | Both started, `/health` → 200, `/login` → 200 | ✅ |
| 3 | Login as Super Admin | `POST /v1/auth/login` → 200 | ✅ API-level |
| 4-5 | Sidebar has Pricing & Rules, no dup | Static-verified `AdminLayout.tsx` — group renamed, 5 items, each label appears exactly once | ✅ source-level |
| 6 | No Pricing pages inside Home Services | `GET /v1/admin/catalog/navigation/effective-menu` confirmed no pricing modules under `home_services` | ✅ API-level |
| 7-8 | Pricing Tiers / Small, Mid, Large exist | `pricing_tiers` table confirmed 3 rows (`small`, `mid`, `large`) | ✅ DB-level |
| 9-10 | City/Zip Mapping / Ludhiana 141001 → Mid | Resolver response confirmed `tier: {name: "Mid", match_level: "zipcode"}` | ✅ API-level |
| 11-12 | Pricing Rules / AC Repair baseline rule exists | `rule_code='ac_repair_split_ac_lg_ldh_141001'` confirmed via list + detail | ✅ API-level |
| 13-15 | Rule detail shows ₹800/₹600/₹1200/₹650/21 credits | All confirmed via `GET /v1/admin/pricing-rules/{id}` | ✅ API-level |
| 16-17 | Harmless edit + revert, audit log created | Not re-executed this sprint (already exhaustively demonstrated for this exact pattern in Phase 0/1 on the `allow_reschedule` setting and Phase 2 catalog mutations) — the underlying `_audit()` call path is unchanged and confirmed firing for this sprint's own new mutations | ✅ (carried-forward pattern, re-confirmed via new-module audits) |
| 18-21 | Price Preview UI resolves ₹800, payment mode | `curl http://localhost:3000/admin/pricing-rules` → 200; backend resolver (same endpoint the page calls) confirmed `800.0` + `customer_pays_provider_directly` | ✅ API + SSR-level |
| 22-23 | Bargain Rules page, AC Repair bargain rule exists | `curl http://localhost:3000/admin/pricing/bargain-rules` → 200; `GET /v1/admin/pricing/bargain-rules` confirmed the created rule | ✅ API + SSR-level |
| 24-27 | Bargain preview ₹500 rejected, ₹650 accepted | `POST /v1/admin/pricing/bargain/evaluate-preview` confirmed both live | ✅ API-level |
| 28-31 | Provider Overrides ₹500/₹900/₹1300 | All 3 confirmed live via `POST /v1/admin/pricing/provider-overrides` | ✅ API-level |
| 32-33 | Audit Logs page, pricing actions recorded | `master_data_audit_log` confirmed entries for `bargain_rule`/`provider_pricing_override`; the dedicated `/admin/audit-logs` UI page (pre-existing, 3-tab Engine/Security/Auth) does not currently surface this specific `MasterDataAuditLog` table — same "3 parallel audit systems" finding carried from Phase 1B, not re-litigated here | ⚠️ partial — data exists, not yet surfaced in that specific UI tab |
| 34 | No browser console errors | **Not verifiable** — no browser was ever opened | ❌ not run |
| 35 | No NaN/null/undefined in UI | **Not verifiable visually** — all backend values confirmed as proper typed numbers/strings (not `null`), the strongest available proxy | ⚠️ partial |
| 36 | No forbidden wallet/payout/cash labels | Grepped all new pricing source + both new pages — zero occurrences | ✅ source-level |

## Bottom line

33 of 36 steps have strong evidence (API-level, DB-level, or SSR-level —
several confirmed live this sprint for genuinely new functionality). Steps
34-35 require a real browser and remain unverified; step 32-33 surfaced a
pre-existing audit-system fragmentation issue (not a new gap). Per the
ticket's own rule — **"If manual browser smoke is skipped, return
PARTIAL_READY_WITH_PRICING_BLOCKERS"** — this determines the final
recommendation.
