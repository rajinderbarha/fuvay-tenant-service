# FINAL-L5-02B — Tenant Jobs List Migration Report

The main Jobs list page (`app/(tenant)/jobs/page.tsx`) was already migrated in FINAL-L5-01D and required no changes this sprint (re-verified: still calls `serviceJobsApi.list`, zero `/v1/jobs`). This sprint's list-level migration work was the **Tenant Dashboard's "Recent Jobs" widget** (`components/dashboard/HomeServiceDashboard.tsx`), which is also a jobs list surface.

## Preserved
| Requirement | Result |
|---|---|
| Pagination | `serviceJobsApi.list({ limit: 8 })` — same page-size semantics as before (legacy call also used `limit:"8"`) |
| Status filter | Jobs page: preserved (`status` param, unchanged). Dashboard widget: no filter UI, unchanged. |
| Loading state | Preserved (`Skeleton` placeholders, gated on `jobs.loading`) |
| Error state | Jobs page preserves its existing error banner (unchanged code path) |
| Empty state | Preserved — dashboard renders nothing extra when `items` is empty (existing behavior) |
| Row links | Jobs page: unchanged (`window.location.href=/jobs/${id}`) |
| Permission-aware actions | Unaffected — list/widget are read-only surfaces |

## Real fields verified against `ServiceJobRecord` (canonical response shape)
`job_id`(→`id`), `booking_id`, `customer_id` (raw, no resolved name — pre-existing, documented FINAL-L5-01D limitation), `category_id`/`offering_id` (raw, no resolved `service`/`service_type`/`brand` labels), `zipcode`, `status`, `assignment_status`, `assigned_staff_id` (raw), `scheduled_date`/`scheduled_time_window`, `created_at`/`updated_at`, `completion_data.collected_amount` (used in place of the legacy `job_value` field, which does not exist on the canonical shape).

**Not fabricated**: `reference`, `payment_mode`, `issue`, `selected_price` as literal top-level fields do not exist on `ServiceJobRecord` — the dashboard widget was rewritten to use only fields that are genuinely present (`job_number`, `zipcode`/`city`, `assigned_staff_id` as a short ID, `completion_data.collected_amount`), matching the same honest-ID pattern already established on the main Jobs page.
