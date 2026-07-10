# Phase 3C — Frontend/Backend Integration Report

Checklist from the ticket, each verified against real code + a live curl/render check:

| # | Check | Status |
|---|---|---|
| 1 | Bargain Rules page uses GET /summary | ✅ `bargainRulesApi.summary()` |
| 2 | Bargain Rules page uses GET list endpoint | ✅ `bargainRulesApi.list()` |
| 3 | Bargain detail uses GET detail endpoint | ✅ `bargainRulesApi.get(id)` |
| 4 | Bargain audit uses GET audit endpoint | ✅ `bargainRulesApi.audit(id)` |
| 5 | Bargain wizard uses POST/PUT endpoints | ✅ `create`/`update` |
| 6 | Bargain validate uses validate endpoint | ✅ `bargainRulesApi.validate(id)` |
| 7 | Evaluate Offer uses real backend evaluation endpoint | ✅ `evaluatePreview()` → `/pricing/bargain/evaluate-preview`, live-confirmed ₹500/₹650/₹700 |
| 8 | Provider Overrides page uses GET /summary | ✅ `providerOverridesApi.summary()` |
| 9 | Provider Overrides page uses GET list endpoint | ✅ `providerOverridesApi.list()` |
| 10 | Provider override detail uses GET detail endpoint | ✅ `providerOverridesApi.get(id)` |
| 11 | Provider override audit uses GET audit endpoint | ✅ `providerOverridesApi.audit(id)` |
| 12 | Provider override wizard uses POST/PUT endpoints | ✅ `create`/`update` |
| 13 | Provider override validate-preview uses backend endpoint | ✅ `providerOverridesApi.validatePreview()`, live-confirmed ₹500/₹1300 error shapes |
| 14 | Approve/reject actions call backend endpoints | ✅ `approve(id)`/`reject(id, reason)` |
| 15 | Activate/deactivate actions call backend endpoints | ✅ `activate(id)`/`deactivate(id)` for both pages |
| 16 | Frontend displays backend request_id on errors | ✅ fixed a real pre-existing bug this sprint (see below) |
| 17 | Frontend displays backend error_code on validation errors | ✅ `errorCode` now surfaced from `useAction`, rendered in `ErrorBlock` and per-error in `ValidationPreviewBlock` |
| 18 | Frontend displays tenant_name, not raw tenant ID only | ✅ verified live |
| 19 | Frontend displays service context | ✅ verified live |
| 20 | Frontend displays platform base/min/max/floor | ✅ verified live |
| 21 | Frontend does not use mock runtime data | ✅ grep-confirmed — zero `mockData`/`fakeApi` references in either page |

## Bug found and fixed this sprint: `request_id` was never actually reaching the UI

`lib/api.ts`'s `ApiError` interface already declared a top-level `request_id`
field (matching the backend's real RFC 7807 `problem+json` shape, where
`request_id` is a sibling of `error_code`/`detail`, not nested inside
`context`). But `apiFetch`'s catch path only forwarded `err.context` into
`ServiceOSError`, and `useApi`'s error handler read `e.context?.request_id` —
which was always `undefined` since `request_id` was never inside `context`.
**Every prior page's "Request ID: req_xxx" error-state text was silently
rendering nothing** (the conditional `list.requestId && ...` just never fired).

Fixed in `lib/api.ts` (`ServiceOSError` now carries a `requestId` field,
`apiFetch` passes `err.request_id` into it) and `hooks/useApi.ts` (`useApi`
reads `e.requestId` directly; `useAction` extended with the same `requestId`/
`errorCode`/`context` fields it previously lacked entirely, since mutation
errors — creates, validates, evaluates — never exposed request_id at all).
This is shared infrastructure used by every page in the app, not just the two
pricing pages — the fix benefits the whole admin frontend's error states.

## No field/schema mismatches found

Every field referenced in both pages (`readiness`, `warning`, `tenant_name`,
`delta_from_base`, `decision`, `error_code`, etc.) was cross-checked against
the actual Phase 3B response payloads captured live via curl before being
used in JSX — no guessed field names.
