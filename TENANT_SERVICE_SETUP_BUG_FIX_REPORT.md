# Tenant Service Setup — Bug Fix Report

## Discovery

The Service Setup wizard page (`/provider/service-setup`) already existed in the
codebase, fully built with a 10-step wizard matching this ticket's spec almost
exactly. Rather than rewrite it, this sprint verified it end-to-end against the
real backend and found 2 real, live-500ing bugs in the Issues and Options wizard
steps.

## Bug 1 — Provider service-option endpoints returned a list but declared `ApiResponse[dict]`

**Symptom:** `GET /v1/provider/setup/services/{id}/available-options` and
`GET /v1/provider/setup/services/{id}/supported-options` both returned a live
500 with a Pydantic validation error:
`"Input should be a valid dictionary"` — because
`ServiceOptionService.get_available_options_for_service()` /
`.get_provider_supported_options()` both return `list[dict]`, but the router
declared `response_model=ApiResponse[dict]`.

**Fix:** `app/engines/admin_catalog/service_option_provider_router.py` — both
GET endpoints changed to `response_model=ApiResponse[list]`.

**Verification:** Live re-test after backend restart:
`GET /v1/provider/setup/services/{AC Repair id}/available-options` → `200`,
returns `["Gas Refill", "Emergency Visit"]`.

## Bug 2 — Customer catalog endpoints had the same list/dict mismatch

**Symptom:** `GET /v1/customer/catalog/service-options` and
`GET /v1/customer/catalog/issue-types` both live-500'd identically —
`ServiceOptionService.get_customer_options()` / `.get_customer_issue_types()`
both return `list[dict]`, router declared `response_model=ApiResponse[dict]`.

**Fix:** `app/engines/admin_catalog/service_option_customer_router.py` — both
GET endpoints changed to `response_model=ApiResponse[list]`.

**Verification:** Live re-test:
`GET /v1/customer/catalog/issue-types?service_id={AC Repair id}` → `200`,
returns 8 real issue types (AC Not Cooling, Water Leakage, Noise Issue, Gas
Refill Needed, AC Not Starting, Bad Smell, Remote Not Working, Cooling Low).

## Impact

Before these fixes, the wizard's Issues step (step 4) and Options step
(step 5) — 2 of the 10 required steps — would have shown a generic error for
every tenant, for every service, platform-wide. Both are now fully functional
with real data.

## Frontend change

Added a Home Services vertical scope guard (defense-in-depth; the backend
catalog query is already vertical-scoped) — if `tenant.vertical !==
"home_services"`, the page shows a blocked-state card instead of the wizard,
consistent with the scope restriction established in the Provider Matching +
Bargain sprint.
