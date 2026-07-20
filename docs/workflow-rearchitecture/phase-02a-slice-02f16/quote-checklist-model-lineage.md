# Quote Checklist Model Lineage

## ServiceJobQuote (table `service_job_quotes`)
Classification: **PROVIDER_QUOTE_DRAFT** (mutable pre-send) / **CUSTOMER_VISIBLE_RECORD** (post-send).
- PK: `id`. Tenant key: `tenant_id`. Customer key: `customer_id`. Job key: `job_id` (→ `ServiceJob.id`). Booking key: `booking_id` (denormalized from `job.booking_id`, no FK relationship object).
- Status: `status` (see `quote-state-machine.csv`).
- Amount fields: `labour_amount`, `parts_amount`, `service_amount`, `discount_amount`, `tax_amount`, `total_amount`, `customer_payable_amount` — all server-recalculated from line items (`_recalculate`), never client-set directly.
- Currency: `currency` (always `"INR"`, hardcoded at creation — no multi-currency support, documented not built).
- Created-by actor: `created_by_user_id`/`created_by_staff_member_id`. Sent-by actor: implicit via `ServiceJobQuoteEvent` (`QEV_SENT_TO_CUSTOMER`, `actor_user_id`). Customer-decision actor: `ServiceJobQuoteEvent` rows with `actor_type="customer"`. Finalized-by actor: `approved_at`/`rejected_at` timestamps, no separate actor column (the decision event carries the actor).
- Approval/rejection reason: `rejection_reason`, `revision_reason`.
- Invoice/payment linkage: **none** — no FK, no reference anywhere in this model or its service (see `quote-financial-boundary.md`).
- Read consumers: provider/staff/admin/customer routers (scoped per persona this slice).
- Not a legacy/alternate model — this is the live, actively-called quote record.

## ServiceJobQuoteItem (table `service_job_quote_items`)
Classification: **QUOTE_LINE_ITEM**.
- PK: `id`. Parent key: `quote_id` (→ `ServiceJobQuote.id`). Tenant/job/booking denormalized for query convenience.
- Quantity/unit-price fields: `quantity` (Numeric 10,3), `unit_price` (Numeric 14,2), `line_total` (server-computed `quantity * unit_price`, never client-supplied directly).
- `item_type` drives which quote total bucket it contributes to (`labour`/`part`/`material`/`service`/`discount`/`tax`/`visit_charge`/`other`).
- `is_customer_visible` — internal-only line items can be hidden from the customer view (read-privacy mechanism, not separately enforced at the API layer currently — see `known-limitations.md`).

## ServiceJobQuoteEvent (table `service_job_quote_events`)
Classification: **QUOTE_HISTORY**.
- Append-only audit trail. `actor_type` (`"staff"`/`"customer"`), `actor_user_id` (server-derived from the caller in every write site), `old_status`/`new_status`, `reason`, `request_id`.

## SjChecklistTemplate / SjChecklistTemplateItem (tables `sj_checklist_templates`/`sj_checklist_template_items`)
Classification: **PROVIDER_INTERNAL_RECORD** (template catalog, platform-managed).
- Managed exclusively via `admin_router.py` (`require_super_admin`) — genuinely platform-scoped, `tenant_id` nullable (global templates) or set (tenant-specific).

## ServiceJobChecklist / ServiceJobChecklistItem (tables `service_job_checklists`/`service_job_checklist_items`)
Classification: **QUOTE_CHECKLIST** / **QUOTE_LINE_ITEM**-analogue (per-job checklist, not a quote — distinct capability from `ServiceJobQuote` despite living in the same module).
- PK: `id`. Job key: `job_id` (→ `ServiceJob.id`, now validated at creation — see `quote-job-item-ownership.md`). Tenant key: `tenant_id`.
- `completed_by_user_id`/`completed_at` — actor tracking for checklist completion.
- No amount fields — this is an inspection/quality checklist, not a priced quote.

## Models NOT present / not applicable here
- **Quote, JobQuote, QuoteResponse, QuoteApproval, QuoteStatusHistory, Inspection, Estimate, CustomerDecision** — none of these class names exist in `quote_checklist`. `JobQuote` DOES exist, but in `field_ops.models`, a distinct, unrelated model (see `field-ops-quote-alternate-audit.md`).
- **Invoice, Payment, Commission record** — no model reference anywhere in `quote_checklist` (see `quote-financial-boundary.md`).
- **PartsRequest** — no model reference anywhere in `quote_checklist` (see `parts-request-boundary.md`).
- **Media/evidence reference** — `ServiceJobChecklistItem.media_url` exists (a string URL field) but there is no dedicated media model relationship — out of scope to build (media infrastructure explicitly out of scope this slice).

No models were merged. `ServiceJobQuote`/`ServiceJobQuoteItem` remain entirely distinct from `field_ops.JobQuote`.
