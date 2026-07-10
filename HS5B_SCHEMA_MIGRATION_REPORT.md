# HS5B — Schema Migration Report

## Migration 121 (applied, live-verified)
`alembic/versions/121_hs5b_availability_exceptions_booking_window.py`

1. **`provider_availability_rules`** — added `break_start_time`,
   `break_end_time` (nullable varchar(8)), `max_jobs_per_day` (nullable
   int), `timezone` (`server_default='Asia/Kolkata'` — safe for existing
   rows), `emergency_available` (`server_default='false'`).
2. **New table `tenant_availability_exceptions`** — `date`, `reason`,
   `full_day_closed`, `start_time`/`end_time` (nullable),
   `affected_service_area_ids`/`affected_service_ids` (jsonb),
   `status`. Indexed on `(tenant_id, date)`.
3. **New table `tenant_booking_window_settings`** — one row per tenant
   (unique `tenant_id`), all 7 ticket fields with the ticket's exact
   suggested defaults (`minimum_notice_minutes=120`,
   `maximum_advance_booking_days=7`, `slot_duration_minutes=60`,
   `buffer_minutes_between_jobs=30`, `allow_same_day_booking=true`,
   `emergency_booking_allowed=false`, `timezone='Asia/Kolkata'`).
4. **`tenant_service_area_services`** — added `service_type_id`,
   `brand_id` (both nullable UUID). **Real finding**: this table already
   existed (service-level per-area coverage) but had **no router
   anywhere in the codebase using it** — it was dead infrastructure.
   This sprint both extended its schema (type/brand columns) and wired
   it to a real endpoint for the first time.

## Safety
- Idempotent-guarded (`inspector.get_columns()`/`get_table_names()`
  checks before every add), matching this repo's established migration
  convention.
- All new columns nullable or have safe `server_default`s — zero data
  migration needed, confirmed via live application (`alembic upgrade
  head` ran clean against the real dev DB with existing data).
- Forward-only with a real `downgrade()` provided (drops in reverse
  dependency order).
- No destructive changes — no existing column altered or dropped.

## Live verification
`alembic upgrade head` ran successfully against the real dev DB;
`psql \d` confirmed all new columns/tables present with correct types
and defaults immediately after.

## Verdict
Schema migration: **complete, safe, applied, and live-verified**.
