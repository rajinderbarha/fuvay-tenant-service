# FINAL-L5-03 — Logging and Observability Standard

## Backend
`structlog` used pervasively (267 files per FINAL-L5-00). `StructuredLoggingMiddleware` + `RequestIDMiddleware` provide `request_id`, endpoint/action, status, duration on every request — confirmed present in every response's `meta.request_id` field checked across this sprint's live API calls.

## Forbidden-in-logs check
No passwords/tokens/API keys/full payment credentials found logged in any backend file touched or read this sprint. `app/dependencies/auth.py`'s blacklist-check failure path logs only `error=str(e)` on Redis unavailability — no token value included.

## Frontend
`lib/authTimeline.ts` (tenant-portal only) is the sole dedicated frontend logging utility — explicitly opt-in (query param or localStorage flag) and explicitly documented as event-name-only, never logging token/header/payload values (established FINAL-L5-01E, unchanged this sprint).

## Real fix this sprint relevant to this Part
Removing `MOCK_MODE` also removed a latent risk: the mock login path stored a **hardcoded fake token string** (`"mock_admin_token_dev"`, `"mock_tenant_token"`) directly into `localStorage` under the same key real tokens use — while not a "logged secret" in the traditional sense, it's a real, live artifact that could have been confused for a real token in debugging/support contexts. Its removal is a small, genuine observability-hygiene improvement.

## No new production frontend logging was added this sprint
No `console.log`/`console.error` calls were added to any of the fixed files beyond what already existed — the `apiFetchPaginatedRaw` migration and `TenantLayout` wallet fix are pure data-flow changes, not new logging.

## Result
No secrets found exposed in logs, console, or error text in this sprint's scope; one real (if minor) hygiene improvement made via the MOCK_MODE removal.
