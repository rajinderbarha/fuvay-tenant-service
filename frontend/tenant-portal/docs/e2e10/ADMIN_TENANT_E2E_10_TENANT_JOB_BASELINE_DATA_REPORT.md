# ADMIN-TENANT-E2E-10 — Tenant Job Baseline Data Report

## Static Analysis Only

## Job Data Model (from `lib/api.ts`)

### Core Job Fields
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | UUID |
| `job_number` | string | Human-readable job number |
| `status` | string | Current status in the job lifecycle |
| `job_type` | `"repair" \| "service" \| "consultation"` | Determines UI branch |
| `service_type` | string | Service name |
| `service_type_id` | string | Service type ID |
| `service_category` | string | Category |
| `customer_name` | string? | Customer display name |
| `customer_phone` | string? | Contact number |
| `customer_address` | string? | Job address |
| `assigned_staff` | string? | Technician name |
| `job_value` | number? | Final job value |
| `quoted_price` | number? | Price from quote |
| `customer_credit_applied` | number? | Credit used by customer |
| `payable_to_provider` | number? | Net amount technician collects |
| `amount_collected` | number? | Recorded collected amount |
| `payment_recorded` | boolean? | Whether collection is confirmed |
| `commission_amount` | number? | Usage credit deduction amount |
| `minutes_in_status` | number? | SLA timer |
| `allowed_transitions` | string[] | Server-resolved next statuses (job_type-aware) |
| `checklist` | JobChecklistItem[]? | Service checklist steps |
| `findings` | string? | Assessment findings text |
| `recommendation` | string? | Assessment recommendation |
| `parent_job_id` | string? | Set if spawned from consultation |
| `duration_estimate_minutes` | number? | Estimated duration |
| `notes` | string? | Internal notes |
| `created_at` | string | ISO timestamp |

### Payment Collection Model
- Payment mode: `"customer_pays_provider_directly"`
- Technician collects cash/UPI from customer on-site
- Platform never collects service payment for Home Services
- ServiceOS deducts usage credits (not cash) after job closes

## Data Source
All data fetched from `/v1/jobs` and `/v1/jobs/{id}` — no mock or hardcoded data detected.

## Status: PASS
