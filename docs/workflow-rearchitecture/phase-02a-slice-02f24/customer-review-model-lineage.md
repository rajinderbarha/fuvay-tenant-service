# Model and Table Lineage — Slice 2F-24

## Canonical model: `CustomerReview` -> `customer_reviews`

| Aspect | Detail |
|---|---|
| Primary key | `id` (UUID) |
| Tenant/provider key | `tenant_id` NOT NULL, indexed (tenant IS the provider) |
| Customer key | `customer_id` NOT NULL, indexed |
| Parent record | `record_type` + `record_id` NOT NULL; plus nullable `booking_id`, `job_id`, `appointment_id`, `lead_id` |
| Rating | `overall_rating` NOT NULL + 6 nullable dimension ratings |
| Body | `review_title`, `review_text`, `review_tags`, `media_urls` |
| Publication | `status` (default `pending`), `visibility` (default `private_until_approved`) |
| Moderation | `moderation_reason`, `rejection_reason` |
| Staff rated | `staff_member_id` (nullable) -- the staff member RATED, not an owner |
| Uniqueness | `uq_cr_customer_record` on (customer_id, record_type, record_id); `uq_cr_number` |

**No `provider_id`/`business_id` column exists** -- see
`customer-review-ownership-contract.md`.

## `ReviewReply` -> `review_replies`
`review_id`, `tenant_id`, `replied_by_user_id`, `reply_text`, `status`
(pending|approved|rejected), `submitted_at`, `approved_at`. One per review,
enforced in the service (`ERR_REPLY_ALREADY_EXISTS`).

## `ReviewFlag` -> `review_flags`
`review_id`, `tenant_id` (**nullable** -- which is how a client-supplied or
null value slipped in before this slice), `flagged_by_user_id`,
`flagged_by_type`, `reason_code`, `reason_text`, `status`
(open|reviewed|resolved). Now always written from `review.tenant_id`.

## `ReviewEvent`, `ReviewPolicy`, `TenantRatingSummary`, `StaffRatingSummary`
Audit trail; per-tenant moderation policy (`require_reply_moderation`,
`edit_window_hours`); and the two precomputed rating aggregates.

## Models that DO NOT participate -- reported, not assumed
`ReviewResponse`, `ReviewModeration`, `ReviewAudit`, `ReviewHistory` do not
exist in this engine. `Customer`, `User`, `Tenant`, `ServiceBooking`,
`ServiceJob`, `field_ops.Job`, `Booking` and order/purchase records are **not
joined** by any route in scope -- ownership needs no derivation because
`tenant_id` and `customer_id` are direct columns.

## DISTINCT MODEL -- the legacy review engine
`app.engines.review` operates on table **`reviews`** via its own `Review`
model, superseded by `customer_reviews` (MODULE-L5-13). `POST /v1/reviews` is
**410 GONE** and remains so. Its `flag_review`/`get_review` routes carry a
similar unguarded pattern, but on a different table -- therefore
`DISTINCT_MODEL`, not a same-record bypass, and outside the mission's
permitted change boundary. Recorded in `known-limitations.md`.

No identifier is adapted between the Booking and Job pipelines anywhere in
this slice.
