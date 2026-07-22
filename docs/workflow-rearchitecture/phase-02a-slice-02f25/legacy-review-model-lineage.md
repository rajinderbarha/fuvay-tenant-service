# Legacy Review Model Lineage — Slice 2F-25

## Classification

**`DISTINCT_WRITE_ACTIVE_LEGACY`**

Not `DISCONNECTED` — live frontend callers exist and the write paths are
mounted and reachable. Not `DEPRECATED_BUT_MOUNTED` — only the *create* route
is retired (410); reply, flag, resolve and request-creation all still write.

## `Review` -> table `reviews`

| Aspect | Detail |
|---|---|
| Primary key | `id` (UUID) |
| Tenant key | `tenant_id` — real column (**DIRECT_TENANT_COLUMN**) |
| Customer key | `customer_id` |
| Job relationship | `job_id` (string) |
| Staff | `staff_id` (nullable) |
| Rating | five signal columns + `composite_score` |
| Content | `comment` |
| Status | `status` (ReviewStatus enum) |
| Reply | `tenant_reply`, `replied_at`, `replied_by` |
| Flag | `flagged_reason`, `flagged_by` |
| Resolution | `resolved_by` |
| Idempotency | `idempotency_key` |
| Uniqueness | `uq_review_customer_job` (customer_id, job_id) |
| Indexes | `ix_rv_tenant` on tenant_id |

## Companion models
`ReviewRequest` (review_requests), `ReviewAggregate` (review_aggregates),
`ReviewStatusHistory` (immutable status trail).

## How it differs from `CustomerReview`

| | legacy `Review` | canonical `CustomerReview` |
|---|---|---|
| table | `reviews` | `customer_reviews` |
| rating shape | 5 weighted signals -> composite | overall + 6 dimensions |
| reply | inline columns on the review | separate `ReviewReply` model |
| flag | inline columns on the review | separate `ReviewFlag` model |
| parent | `job_id` string | `record_type` + `record_id` |
| moderation | status history model | `moderation_reason` / `rejection_reason` |
| create route | **410 GONE** | live customer submit route |

They are genuinely different schemas for the same concept. **No merge, no
migration, no record movement** was performed — all explicitly out of scope.

## Writers and readers

- **Writers:** `submit_reply`, `flag_review`, `resolve_flag`,
  `create_review_request` (+ `create_review` on the service, no longer
  reachable from any mounted route).
- **Readers:** 10 GET routes.
- **Frontend:** `tenant-portal` (7 endpoints). `super-admin` defines a legacy
  `reviewApi` object that Phase 1A confirmed is **not imported** by its
  reviews page, which reads the canonical stack.
- **Background/internal consumers:** none found.

## Migration question — explicitly NOT decided
Whether to migrate legacy records into `customer_reviews` and retire this
engine is a product decision (`MIGRATION_REQUIRED_PRODUCT_DECISION`), recorded
in `product-decisions-required.md`. This slice secured the engine as it
stands.
