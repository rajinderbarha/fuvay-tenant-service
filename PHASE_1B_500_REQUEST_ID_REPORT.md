# Phase 1B — 500 Error Envelope / request_id Verification Report

## Approach

Option 1 from the ticket: a safe, dev-only test-only endpoint,
`GET /v1/admin/test/error-500`, added to `app/main.py::_mount_routers()`.

```python
if not _get_settings().is_production:
    _test_router = APIRouter(prefix="/v1/admin/test", tags=["Dev-Only Test Routes"])

    @_test_router.get("/error-500", ...)
    async def _trigger_500(u=Depends(require_super_admin)):
        raise RuntimeError("Phase 1B controlled test failure — verifying 500 error envelope.")

    app.include_router(_test_router)
```

Guarded two ways:
1. **Environment guard** — never mounted when `APP_ENV=production`
   (`Settings.is_production` check).
2. **Auth guard** — requires `super_admin`, confirmed live: unauthenticated
   request → 401 (never reaches the handler that would raise), restricted
   role would get 403 (not separately re-tested since `require_super_admin`
   behavior is already exhaustively confirmed elsewhere this session).

## Live verification

```
GET /v1/admin/test/error-500 (as super_admin) → 500
{
  "type": "https://serviceos.io/errors/INTERNAL_ERROR",
  "title": "Internal Server Error",
  "status": 500,
  "detail": "An unexpected error occurred. Our team has been notified.",
  "error_code": "INTERNAL_ERROR",
  "resolution": "If this persists, contact support with the request_id.",
  "request_id": "req_bd97909d9383",
  "context": {"request_id": "req_bd97909d9383"}
}
```

`request_id` present, `error_code` present, human-readable `detail`, no
stack trace leaked to the client (confirmed — the traceback is only logged
server-side via `logger.error(..., traceback=traceback.format_exc())` in
`app/exceptions.py::unhandled_exception_handler`, never included in the
response body).

```
GET /v1/admin/test/error-500 (unauthenticated) → 401 (auth guard fires first, confirms the route is not a bypass)
```

## Frontend

Not separately re-verified with a live click — the existing
`EmptyState`/`useApi` error-handling pattern (already confirmed for
401/403/404/422 in Phase 1) is generic and status-code-agnostic; it renders
`error.message` + `Request ID: {requestId}` + a Retry button regardless of
which HTTP status triggered it, so no separate 500-specific code path exists
to test.

**Hard gate: 500 error envelope verified safely, without touching
production behavior — PASS.**
