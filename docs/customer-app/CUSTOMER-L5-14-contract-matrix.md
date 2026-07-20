# CUSTOMER-L5-14 — Real Backend Contract Matrix

All paths, fields, and rules below were read directly from
`app/engines/quote_checklist/{models.py,constants.py,quote_service.py,
customer_router.py}` and cross-checked by an independent background
research pass. See `baseline-verification.md` for why the
`execution` engine's `PartsRequest` model is NOT the system this sprint
builds against (real, but zero customer-facing surface, and a genuinely
stuck customer-decision status).

## Endpoints (real, mounted, `app/main.py` lines 512–529)

| Method | Path (no `/v1` — see baseline-verification.md #5.1) | Auth | Body | Notes |
|---|---|---|---|---|
| GET | `/customer/quotes/jobs/{job_id}` | Bearer | — | returns `ServiceJobQuote[]` for this customer + job, no items |
| GET | `/customer/quotes/{quote_id}` | Bearer | — | returns one quote + its `items[]` — **unfiltered by `is_customer_visible`, see gap #3** |
| POST | `/customer/quotes/{quote_id}/approve` | Bearer + `Idempotency-Key` header (required) | — | one-shot from `sent_to_customer` only |
| POST | `/customer/quotes/{quote_id}/reject` | Bearer | `{ "reason": string }` | reason required, non-empty |
| POST | `/customer/quotes/{quote_id}/request-revision` | Bearer | `{ "reason": string }` | reason required, non-empty |
| GET | `/customer/quotes/{quote_id}/events` | Bearer | — | audit trail, `event_type`/`old_status`/`new_status`/`reason`/`created_at` |

## Quote fields (`ServiceJobQuote.to_dict()`, `models.py` lines 49–79)

Rendered/used by this client: `id`, `quote_number`, `job_id`, `status`,
`quote_type`, `currency` (always `"INR"`, hardcoded server-side, line 30),
`labour_amount`, `parts_amount`, `service_amount`, `discount_amount`,
`tax_amount`, `total_amount`, `customer_payable_amount`,
`customer_visible_notes`, `rejection_reason`, `revision_reason`,
`created_at`.

**Deliberately excluded (never included in this client's parse schema —
structural stripping, gap #3):** `provider_internal_notes`,
`created_by_staff_member_id`, `created_by_user_id`, `idempotency_key`,
`locked_at`, `tenant_id`, `booking_id`, `customer_id`,
`approved_at`/`rejected_at`/`sent_to_customer_at` (timestamps not needed
by this client's UI — status label already conveys state; omitted rather
than parsed-and-unused).

## Quote item fields (`ServiceJobQuoteItem.to_dict()`, lines 103–117)

Rendered: `id`, `item_type`, `item_name`, `item_description`, `quantity`,
`unit_price`, `line_total`. `is_customer_visible` is parsed but used only
as a **client-side filter** (drop the item), never rendered.
`is_required`/`item_metadata` excluded (not needed by this screen).

## Status vocabulary + transitions (`constants.py` lines 4–32)

```
draft → {submitted_to_provider, sent_to_customer, cancelled}
submitted_to_provider → {provider_approved, provider_rejected, cancelled}
provider_approved → {sent_to_customer, cancelled}
provider_rejected → {revised, cancelled}
sent_to_customer → {customer_approved, customer_rejected, revision_requested, expired, cancelled}
customer_approved → (final)
customer_rejected → (final)
revision_requested → {revised, cancelled}
revised → {submitted_to_provider, sent_to_customer, cancelled}
expired → (final, never actually reached — see baseline-verification.md #5.4)
cancelled → (final)
```

**This client's actionable rule**: approve/reject/request-revision are
only ever offered when `status === "sent_to_customer"` — every other
status is read-only display. This mirrors the server's own
`QUOTE_TRANSITIONS` map exactly (only `sent_to_customer` allows any of
the three customer-initiated transitions), and proactively avoids the
opaque-500 failure mode (baseline-verification.md #5.2) for the
overwhelmingly common case.

## Job/booking status side-effects (`quote_service.py` `_sync_job_status` calls)

| Quote action | `ServiceJob.status` set to |
|---|---|
| `send_to_customer` (staff/provider-triggered, not this client) | `awaiting_customer_quote_approval` |
| `customer_approve` | `quote_approved` |
| `customer_reject` | `quote_rejected` |
| `customer_request_revision` | `quote_revision_requested` |

These four strings are a **separate vocabulary** from the `execution`
engine's own `JS_*` statuses already in `booking-status-registry.ts`
(`quote_required`, `service_started`, etc.) — both write to the same
`ServiceJob.status` column via different engines. Extended
`booking-status-registry.ts` this sprint with all four (see
`booking-job-effects.md`).

## Job ID resolution

No new lookup needed — reuses the exact same `useBookingDetail` (from
`features/booking-confirmation`, not `features/bookings`) established by
CUSTOMER-L5-13 to resolve `job.id`, since it remains the only real
customer endpoint returning a raw job ID.

## Money handling

`currency` is always `"INR"` (hardcoded, never customer- or
provider-selectable). All amounts are backend-computed
(`_recalculate`, lines 104–122) — this client never computes or displays
a client-derived total; it only renders `total_amount`/
`customer_payable_amount` exactly as returned, consistent with every
previous sprint's money-handling rule.
