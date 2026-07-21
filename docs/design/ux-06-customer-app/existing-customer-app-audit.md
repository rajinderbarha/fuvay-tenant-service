# UX-06 Round 1 — Existing `mobile/customer-app` Audit

Date: 2026-07-20. Baseline commit: `50840acc91622bad7729a02fc602a65a911f407b` (master).

## What actually exists on disk

`mobile/customer-app` already had a substantial scaffold: Expo app (expo ~56, RN 0.85,
React 19), `AuthProvider` + AsyncStorage session, React Navigation (native-stack +
bottom-tabs), a `lib/api.ts` API client with ~20 endpoint groups, a `lib/theme.ts`,
~18 screens, and `tests/test_customer_app.py` (a Python file — not a real RNTL test,
not evaluated further this round).

This does **not** match the task brief's description of the starting point (no
`src/design-system/tokens/breakpoints.ts`, no `src/localization/i18n-setup.ts`,
no zustand/react-query, no hi/pa locale files were found — `src/lib/i18n.ts` exists
but is a small, unrelated helper, not an i18n framework). The brief's description
appears to describe a different/aspirational baseline; this audit reports what is
actually in the repository.

## Critical finding: the API client pointed almost entirely at endpoints that do not exist

`src/lib/api.ts` was internally labelled "PROVEN LEVEL 5" but was verified against the
live backend's `openapi.json` (`curl http://localhost:8000/openapi.json`, 1,663,208
bytes, confirmed live and reachable) and found to be **almost entirely fictional**:

| Area | Scaffold called | Real backend has | Verdict |
|---|---|---|---|
| Auth | `/v1/auth/customer/otp-request`, `/v1/auth/customer/otp-verify`, `/v1/auth/customer/login` | `/v1/auth/login` (email+password, unified across all roles — same finding UX-05 made for staff) | FAKE — no customer OTP endpoint exists anywhere in the schema |
| Categories | `/v1/services/categories` | `/v1/customer/categories` | FAKE path, real feature exists under different path |
| Bookings | `/v1/bookings` (generic) | `/v1/customer/bookings*`, `/v1/customer/my-activity/bookings` | Partially real (`/v1/bookings` also exists as an internal/admin-facing shape) but customer app should use the `/v1/customer/*` scoped surface |
| Jobs | `/v1/jobs` (generic) | `/v1/customer/jobs*`, `/v1/customer/service-jobs/{id}/tracking` | Same pattern — customer-scoped surface exists and is the correct one |
| Reviews | `POST /v1/reviews` | `/v1/customer/reviews*` (canonical `customer_reviews` engine) | FAKE/legacy — confirms the memory-documented rule that `/v1/reviews` is a dead legacy route (410) |
| Chat | `/v1/chat/rooms*` | `/v1/customer/chat/threads*` (distinct from `/v1/staff/chat/threads`) | FAKE path |
| Addresses | `/v1/commerce/customers/{id}/addresses` | `/v1/customers/me/addresses` | FAKE path |
| Notifications | `/v1/notifications*` (generic) | `/v1/customer/notifications*` (role-scoped, mirrors staff/provider/admin pattern) | FAKE — generic path exists but is not customer-scoped |
| Settings/preferences | `/v1/settings/{id}/preferences` | not found anywhere in schema | FAKE, no real contract found |
| Help/FAQ | `/v1/help/faqs`, `/v1/help/tickets` | not found anywhere in schema | FAKE, no real contract found |
| Payment methods | `/v1/payments/customers/{id}/methods` | not found anywhere in schema | FAKE, no real contract found (consistent with the "on-site payment, no platform payment processing" rule — there may simply be no saved-payment-method feature) |
| Invoices | `/v1/payments/invoices*` | `/v1/customer/service-invoices*` | FAKE path, real one uses different naming and includes `apply-credit` (Service Credit, not cash) |
| Quotes | `/v1/jobs/{id}/quote*` | `/v1/customer/quotes/{id}`, `/v1/customer/quotes/jobs/{id}` | FAKE path |
| AI chat (session) | `/v1/customer/ai-chat/sessions*` | same path, confirmed real | REAL — this one was correct |
| AI chat (generic) | `/v1/ai/chat` | `/v1/ai/chat` + `/v1/ai/chat/meta` also exist | REAL but a different, non-session engine — not used (see deepseek-conversation-contract.md) |
| Service Credit | not present | `/v1/me/credits*` | Real contract found, not previously wired up at all |

**Root cause assessment**: this looks like the same class of issue documented
repeatedly in prior MODULE-L5 fixes (L5-35 through L5-50) — a plausible-looking
client built against assumed/legacy route shapes rather than the live schema. The
customer app's compile-time types were internally consistent, so nothing caught it
without an openapi diff.

## Correction made this round

`src/lib/api.ts` was rewritten in place, re-pointing every endpoint group at its real
verified path (see the file's own header comment for the full list). `AuthContext.tsx`
and `LoginScreen.tsx` were corrected to the real unified email/password
`/v1/auth/login` contract; the fake phone/OTP two-step flow was removed rather than
left as a dead UI control (matching the UX-06 brief's instruction to prefer removing
misleading controls over shipping something that silently fails).

## Not fixed this round (deferred — see deferred-items.md)

Several existing screens (`HomeScreen`, `JobTrackingScreen`, `ServiceHistoryScreen`,
`PaymentMethodsScreen`, `HelpSupportScreen`, `SettingsScreen`) still import the old,
now-removed API export names (`jobsApi.myJobs`, `paymentMethodsApi`, `helpApi`,
`settingsApi`, `StaffLocation`, etc.) and will fail typecheck until rewired to the
corrected `api.ts` exports (`serviceJobsApi`, `bookingsApi`, etc.) or, for the three
areas with **no real backend contract found at all** (payment methods, help/FAQ,
settings/preferences), rebuilt as honestly-labelled `MOCK_DESIGN_ONLY` screens or
removed from navigation. This round prioritized correcting the foundational API
contract and auth flow (used by every other screen) over chasing every downstream
screen; a fresh WSL typecheck pass to get an exact error count is deferred to the
next round (see known-limitations.md).
