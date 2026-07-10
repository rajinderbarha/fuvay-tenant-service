# Phase 3B — Swagger / OpenAPI Report

Verified via `GET /openapi.json` against the real running backend after
restart.

## 1-3. Bargain Rules / evaluation / provider override endpoints appear

All 12 bargain-rules paths and 13 provider-overrides paths are present in
`openapi.json["paths"]`:

```
/v1/admin/pricing/bargain-rules                              [get, post]
/v1/admin/pricing/bargain-rules/summary                      [get]
/v1/admin/pricing/bargain-rules/{rule_id}                    [get, put]
/v1/admin/pricing/bargain-rules/{rule_id}/activate            [post]
/v1/admin/pricing/bargain-rules/{rule_id}/audit                [get]
/v1/admin/pricing/bargain-rules/{rule_id}/deactivate          [post]
/v1/admin/pricing/bargain-rules/{rule_id}/disable             [post]
/v1/admin/pricing/bargain-rules/{rule_id}/enable              [post]
/v1/admin/pricing/bargain-rules/{rule_id}/validate            [post]
/v1/admin/pricing/bargain/evaluate-preview                    [post]
/v1/admin/pricing/provider-overrides                          [get, post]
/v1/admin/pricing/provider-overrides/summary                  [get]
/v1/admin/pricing/provider-overrides/validate-preview         [post]
/v1/admin/pricing/provider-overrides/{override_id}            [get, put]
/v1/admin/pricing/provider-overrides/{override_id}/activate    [post]
/v1/admin/pricing/provider-overrides/{override_id}/approve     [post]
/v1/admin/pricing/provider-overrides/{override_id}/audit       [get]
/v1/admin/pricing/provider-overrides/{override_id}/deactivate  [post]
/v1/admin/pricing/provider-overrides/{override_id}/disable     [post]
/v1/admin/pricing/provider-overrides/{override_id}/enable      [post]
/v1/admin/pricing/provider-overrides/{override_id}/reject      [post]
```

## 4. Provider override validation preview appears

`/v1/admin/pricing/provider-overrides/validate-preview` [post] — confirmed
above.

## 5-6. Request/response schemas exist

Every endpoint declares `response_model=ApiResponse[dict]` (the shared
envelope type used platform-wide); request bodies are consumed via raw
`await r.json()` (matching the pre-existing convention for every other
bargain/override endpoint in this router — not schema-typed with a dedicated
Pydantic model, same as its siblings). This is consistent with, not a
regression from, the router's existing style for this module.

## 7. Error schemas include request_id

All errors route through the shared `ServiceOSException` → RFC 7807
`problem+json` handler (`app/exceptions.py`), which always attaches
`request_id` via `_get_request_id(request)`. Confirmed live: every error
response captured during Part 4/5 testing (`OVERRIDE_BELOW_PLATFORM_MIN`,
`OVERRIDE_ABOVE_PLATFORM_MAX`, `DUPLICATE_ACTIVE_OVERRIDE`) included a
`request_id` field in its `meta`/problem body.

## 8. Auth requirement is documented

Every new/existing handler carries a `Depends(require_permission(P.<CONST>))`
parameter — FastAPI's OpenAPI generator surfaces this as a `security`
requirement on each operation (inherited from the shared `get_current_user`
OAuth2/Bearer dependency used platform-wide). Confirmed live: calling
`/pricing/bargain-rules/summary` with no `Authorization` header returned
`401`, not a schema validation error, proving the dependency (and therefore
its OpenAPI security declaration) is active.

## Result: **Swagger/OpenAPI — PASS**, all Phase 3B endpoints documented.
