# CUSTOMER-FRONTEND-02 — API Contract Report

File: `frontend/customer-app/lib/api/customer-home-services.ts` (confirmed actual location, matches Sprint 01's report).

## Required functions — actual names found (all present, real equivalents)
| Spec name | Actual export |
|---|---|
| getCustomerHomeServicesCatalog | `getCustomerHomeServicesCatalog()` — exact match |
| getCustomerServiceQuestions | No literal match — closest real equivalents are `getFlowConfig()`, `getCustomerServiceOptions()`, `getCatalogServiceTypes()`, `getCatalogIssueTypes()` (documented already in Sprint 01 blocker #5: no single "questions" endpoint exists backend-side) |
| selectProviderForHomeService | `selectProviderForHomeService()` — exact match |
| createCustomerHomeServiceBooking | `createCustomerHomeServiceBooking()` — exact match |
| getCustomerBookings | `getCustomerBookings()` — exact match |
| getCustomerBookingDetail | `getCustomerBookingDetail()` — exact match |
| submitCustomerBookingReview | `submitCustomerBookingReview()` — exact match |
| getCustomerBookingReview | `getCustomerBookingReview()` — exact match |

Additional real functions present: `getCatalogServices`, `getCatalogBrands`, `getCatalogServiceTypes`, `getCatalogIssueTypes`, `startBookingDraft`, `getBookingDraft`, `updateDraftFields`, `checkServiceability`, `confirmPriceChoice`, `buildBookingSummary`, `addDraftPhoto`, `getCustomerBookingTracking`, `cancelCustomerBooking` (intentionally throws — not wired, documented honestly not faked).

## Contract quality checks
- **No direct `fetch(` outside `lib/api/`** — grepped `app/` and `components/` for `fetch(`: zero matches. Every network call routes through `apiFetch()` in `lib/api/client.ts`.
- **Central client used** — every function in `customer-home-services.ts` calls the shared `apiFetch<T>()`.
- **Auth token included** — `apiFetch()` injects `Authorization: Bearer <token>` from `getCustomerToken()` centrally; no per-call token wiring needed/found.
- **request_id parsed** — `parseError()` in `client.ts` extracts `request_id` from both the `{error:{...}}` and RFC7807 (`error_code`/`detail`/`request_id`) response shapes into `CustomerApiError.requestId`.
- **401/403 handling** — 401 triggers refresh-then-redirect-to-login in `apiFetch()`; 403 falls through to `parseError()` and is surfaced via `ErrorBanner` with its request_id (no special 403 UI copy beyond the generic error banner — acceptable per spec, which only requires the request_id to show).

## Verdict: PASS. All 7 of 8 spec-named functions exist with identical names; the 8th ("service questions") has real, documented substitutes rather than a fabricated single endpoint. No architecture violations found.
