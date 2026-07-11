# FINAL-L5-03 — Shared Error Handling Standard

## Current state
Every API error in all 3 apps surfaces as a `ServiceOSError`/thrown `Error` with `.message` (backend-provided, human-readable) and, where the backend supplied one, `.requestId`. Pages render this inline (a red-bordered alert box with the message + `Request ID: {id}` when present) — this pattern is repeated per-page rather than via one shared `ApiErrorAlert` component, but is visually and behaviorally consistent (same colors, same "Request ID:" wording) because every page copies the same small inline JSX block, not because of a shared component.

## Required states — coverage found
| State | Coverage |
|---|---|
| Inline field error | Not standardized — 422 field errors are read from `err.context` ad-hoc per page where needed |
| Form-level error | Standardized inline pattern (see above), present on every mutation form checked |
| Page-level error | Present via each `useApi` hook's `.error` field, rendered inline |
| Permission error | Not distinct from generic errors — a 403 shows the backend's message text, not a dedicated `PermissionDeniedState` component |
| Network error | `apiFetch` catches JSON-parse failure and synthesizes `{error_code:"NETWORK_ERROR", detail: "HTTP {status}"}"` — never a raw unhandled exception |
| Session expired | Dedicated: `"Session expired. Please sign in again."` + `clearSession()` redirect |
| Rate-limit error | Falls through to the generic error display (no dedicated 429 UI) |
| Not-found state | Case-by-case per page (some show "not found", some — per FINAL-L5-01D/02B's documented finding — return HTTP 200 with an embedded not-found body instead of a real 404; a real, carried, low-severity, no-data-leak finding, not fixed this sprint, out of scope) |
| Conflict state | Falls through to generic error display |

## Real finding this sprint: 500 errors are indistinguishable from CORS failures in the browser
`GET /v1/provider/wallet` (before this sprint's fix routed callers away from it) returned a genuine unhandled `500 INTERNAL_ERROR` with **no `Access-Control-Allow-Origin` header** on the error response. The browser reported this to the frontend as a CORS failure (`Access to fetch ... has been blocked by CORS policy`), not as a 500 — meaning `apiFetch`'s error-handling code never even ran (the browser blocks CORS-failed requests before the response body is readable by JS at all). This is a real, serious "hidden error" class (rule 11) at the browser layer: **any unhandled backend 500 anywhere in the app looks like a CORS misconfiguration to a developer debugging it**, not the real failure. Root-caused to backend middleware ordering (`CORSMiddleware` is not the outermost ASGI layer — see Backend Shared Helper Report for why this wasn't blind-fixed this sprint) and separately to the specific endpoint's own bug (querying the dormant `tenant_wallets` table, raising an uncaught `ValueError`). The specific *consumer* of this broken endpoint was migrated away from it this sprint (see Performance Code Cleanup Report), which removes the symptom for the one call site that was firing on every page load; the underlying CORS-header-on-error gap remains and is logged in Remaining Blockers.

## Recommended components (mission's list) — not built this sprint
`ApiErrorAlert`, `PageErrorState`, `PermissionDeniedState`, `NotFoundState`, `SessionExpiredDialog` as literal shared components don't exist; the *behavior* they'd encapsulate already exists, just duplicated inline per-page. Extracting them is real, valuable, low-risk future work (pure UI refactor, no logic change) — recommended in the Deprecated Pattern Guide rather than attempted here, since it would touch dozens of files for a cosmetic consolidation with no functional bug behind it (unlike the fixes this sprint prioritized, which all had a real, demonstrable defect).

## Result
No page found showing raw JSON as its primary error UI (checked directly in this sprint's browser regression). `request_id` preserved everywhere except the 5 super-admin pages (now fixed).
