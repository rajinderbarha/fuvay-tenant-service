# FINAL-L5-01D — Tenant Jobs Contract Verification

Real field-by-field comparison of frontend expectations (post-migration) against actual live `GET /v1/provider/my-records/jobs` response.

| Mission field | Present in canonical response? | Frontend handling |
|---|---|---|
| `job_id` (as `id`) | Yes | Used for navigation/keys |
| `booking_id` | Yes | Displayed in detail |
| `tenant_id` | Yes | Not displayed (implicit from auth) |
| `customer` (name) | **No** — only `customer_id` | Displayed as short ID, not fabricated |
| `service`/`service_type`/`brand`/`issue` | **No** — only `category_id`/`offering_id` (raw IDs) | Not displayed (would require additional resolution calls not built this sprint) |
| `zipcode` | Yes | Displayed |
| `selected_price` | **No** | Not displayed |
| `payment_mode` | **No** | Not displayed |
| `technician` (name) | **No** — only `assigned_staff_id` | Displayed as short ID |
| `status` | Yes | `JobStatusBadge`, graceful fallback |
| `scheduled_at` (as `scheduled_date`+`scheduled_time_window`) | Yes | Displayed |
| `completed_at` | Implicit via `completion_data.completed_at` | Displayed when present |
| `completion_proof` (as `completion_data`) | Yes | Displayed when present |
| `deduction` | **No** — lives in `usage_credit_ledger`, not on the job record | Not displayed (would require a separate ledger query) |
| `created_at`/`updated_at` | Yes | Displayed |

## List envelope
```
{ "items": ServiceJobRecord[], "total": number, "limit": number, "offset": number }
```
Matches the frontend's updated expectation exactly (`jobs.data?.items`, `jobs.data?.total`).

## Status enum — actual backend values (verified via seeded data)
`new`, `assigned`, `in_progress`, `completed`, `cancelled` — confirmed against the 5 real canonical seeded jobs, matches the frontend's updated status filter dropdown exactly.

## Honest assessment
Several mission-listed fields (`service`/`brand`/`issue` names, `selected_price`, `payment_mode`, `deduction`) are **not present** on the canonical `service_jobs` record — they either don't exist on this table at all, or require joining across `category_id`/`offering_id`/`usage_credit_ledger`. The frontend was migrated to show only real, available fields rather than fabricating or guessing these — a deliberate, honest choice consistent with the no-mock-data rule. Enriching the display with resolved names/pricing is real, valuable follow-up work, not done this sprint given time constraints.
