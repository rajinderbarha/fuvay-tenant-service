# Seed Idempotency Report — UX-06 Round 4

Real test performed: reran `POST /v1/tenant/service-areas/c50daa54-.../services`
with the identical body a second time.

Result: real `409 Conflict`, `error_code: "ERR_DUPLICATE_MAPPING"` (surfaced by
`app/engines/serviceability/service.py:643-646`'s pre-existing duplicate guard,
querying `(tenant_service_area_id, service_id, job_type, is_available=true)`).
No duplicate row was created — confirmed by re-listing
`GET /v1/tenant/service-areas/c50daa54-.../services` immediately after, which
still shows exactly 1 mapping for `ac_repair`.

This means the seed step is safe to include in an automated setup script and
rerun without a custom "check if exists" guard — the backend's own real
validation already provides it.
