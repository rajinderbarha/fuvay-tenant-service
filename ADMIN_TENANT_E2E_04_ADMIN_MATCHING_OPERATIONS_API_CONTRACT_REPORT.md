# API Contract Report (Part 10)

Verified real imports at the top of each page file (not the spec's illustrative names):

| Page | Real import | Real API module/function |
|---|---|---|
| provider-matching | `import { autoPriceOptionsApi } from "../../../../lib/api"` | `autoPriceOptionsApi.getConfig()` → `/v1/admin/home-services/config` |
| matching-diagnostics | `import { autoPriceOptionsApi, type MatchingDiagnosticsResult } from "../../../../lib/api"` | `autoPriceOptionsApi.runMatchingDiagnostics(...)` → POST `/v1/admin/home-services/matching/diagnostics` |
| completed-job-deduction | `import { homeServicesCatalogConsoleApi, catalogApi } from "../../../../lib/api"` | `homeServicesCatalogConsoleApi.listServices()` + `catalogApi.listPricingRules(...)` |
| service-jobs | `import { enterpriseApi } from "../../../../lib/api"` (grid data itself via a page-local `fetchJobs` using **direct `fetch()`**, not a `lib/api.ts` function) | `enterpriseApi.createExport(...)` for export; direct `fetch(`${API}/v1/admin/final-records/jobs?...`)` for the list |
| operations | `import { jobsApi, staffApi } from "../../../lib/api"` | `jobsApi.adminList/adminSummary/slaAlerts/reassign`, `staffApi.listByTenant` |
| operations/[jobId] | `import { jobsApi, staffApi } from "../../../../lib/api"` | `jobsApi.get/history/overrideStatus/forceClose/reassign` |
| finance/usage-credits | `import { usageCreditsAdminApi } from "../../../../lib/api"` | `usageCreditsAdminApi.getTenantLedger/addCredits` |

## Findings
- All pages except `service-jobs` use the real central `lib/api.ts` client exclusively (which wraps `apiFetch`, attaches the bearer token from `localStorage.serviceos_admin_token`, and parses `request_id` from the response envelope — confirmed by reading `apiFetch`'s usage pattern elsewhere in `lib/api.ts`).
- `service-jobs/page.tsx` has a **direct `fetch()` call** (`fetchJobs`), bypassing the centralized `apiFetch`/`lib/api.ts` pattern — it manually reads the token from `localStorage`, manually constructs the Authorization header, and manually unwraps `json.data`. This is a real, documented deviation from the "always use the central client" standard (same category of finding as the pre-existing `audit-logs` page direct-fetch noted in E2E-02). It still hits a real backend endpoint (`/v1/admin/final-records/jobs`) with real auth — not a mock — but it does not benefit from the central client's shared request_id parsing / error normalization.
- Auth token included: confirmed on all 7 pages (either via the central client's automatic attachment, or manually on `service-jobs`).
- `request_id` parsed: confirmed for all pages using the central client's `useApi`/`useAction` hooks (which surface `.requestId`); NOT parsed/surfaced by the `service-jobs` page's direct fetch (no request_id shown anywhere on that grid).
- No fake runtime data where a real API exists: confirmed — see Mock Data Scan (Part 11).

## Verdict
**PASS with one documented deviation** (`service-jobs` direct-fetch bypassing the central client) — a real, pre-existing-pattern gap, not a fabricated-data problem. All other pages fully comply with the central API client contract.
