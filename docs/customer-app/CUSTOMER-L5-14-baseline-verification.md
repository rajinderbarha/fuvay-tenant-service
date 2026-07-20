# CUSTOMER-L5-14 — Baseline Verification

Per this sprint's own instruction ("Do not trust prior reports without
repository and runtime proof"), every claim below was re-verified against
current repository state in this session — not copied from memory of
earlier sprints.

## 1. Authentication

Unchanged since CUSTOMER-L5-13. `get_current_user` dependency confirmed
still present and used by every router touched this sprint
(`app/dependencies/auth.py`, referenced in
`app/engines/quote_checklist/customer_router.py` lines 4, 23, 32, 42, 55,
68, 81).

## 2. Current customer / canonical booking / canonical service job

Unchanged since CUSTOMER-L5-11/12/13: `ServiceBooking` and `ServiceJob`
(`app/engines/final_records/models.py`) remain the real, canonical
records. Re-confirmed this sprint that `ServiceJob.customer_id` is the
same identity `quote_checklist`'s `ServiceJobQuote.customer_id` is copied
from at creation time (`quote_service.py` line 142:
`customer_id=job.customer_id`), and that every customer-facing
`quote_checklist` endpoint checks `str(quote.customer_id) == str(user.user_id)`
— the same ownership-check shape used by every previous sprint's
customer-scoped endpoints.

## 3. Baseline repository state re-confirmed this session

- `npx tsc --noEmit`: 31 pre-existing errors (unchanged baseline, matches
  CUSTOMER-L5-13's own closing number).
- `npx jest`: 93 suites / 617 tests passing (unchanged baseline).
- `npx eslint src`: 0 errors, 36 pre-existing warnings (unchanged
  baseline).
- `npx prettier --check`: clean.

## 4. Central Finding — two separate, unrelated backend systems both look like "the parts/additional-cost feature"; only one is real for customers

This sprint's spec describes "Parts Approval, Additional Cost and Customer
Decision" in language that maps naturally onto
`app/engines/execution/models.py`'s `PartsRequest` model (table
`service_job_parts_requests`, HS8B, referenced constants
`PARTS_STATUS_*`/`ERR_PARTS_*` in `execution/constants.py` lines 143–169).
Direct source verification (own reads, cross-checked by an independent
background research pass reaching the same conclusions) found:

- `PartsRequest` is real, has a complete data model (part name, quantity,
  estimated cost, reason, photos, business/customer-approval flags,
  approve/reject audit fields) and complete **staff** (create/list) and
  **provider/business** (list/approve/reject/install) endpoints
  (`execution/home_service_router.py` lines 234–334).
- **It has zero customer-facing endpoints anywhere in the repository.**
  `customer_router` in that same file (prefix
  `/v1/customer/service-jobs`) only exposes `GET /{job_id}/tracking`
  (CUSTOMER-L5-13) — it never calls `list_parts_requests` or any
  parts-related service method.
- Worse: the model's own `customer_approval_required` flag and
  `PARTS_STATUS_CUSTOMER_APPROVAL_PENDING`/`_CUSTOMER_APPROVED`/
  `_CUSTOMER_REJECTED` statuses are real and reachable (a provider can
  set `customer_approval_required=true` on creation, and the provider's
  own `approve` endpoint correctly moves the record to
  `customer_approval_pending`) — but **no code path anywhere sets
  `PARTS_STATUS_CUSTOMER_APPROVED` or `PARTS_STATUS_CUSTOMER_REJECTED`.**
  A parts request routed for customer approval becomes permanently stuck.
  Job completion (`complete_job`, lines 496–617) does not even gate on
  this — it only blocks on the earlier `PARTS_STATUS_REQUESTED` status —
  so the stuck record isn't just unreachable, it's also silently ignored
  by the rest of the system.

This is a genuinely orphaned, unfinished half of a state machine — real
schema, real constants, zero reachable customer action. Building a
"parts approval" client feature against it would mean shipping a screen
with literally nothing to call.

A second, entirely separate system — `app/engines/quote_checklist/`
(Sprint 22's own "Quote Approval + Checklist Engine", already documented
in memory as complete) — **is** the real, live, fully-wired
customer-facing "additional cost / customer decision" system: a
`ServiceJobQuote` + `ServiceJobQuoteItem` + `ServiceJobQuoteEvent` model
(`quote_checklist/models.py`) with a complete lifecycle
(`draft → submitted_to_provider → provider_approved → sent_to_customer →
customer_approved / customer_rejected / revision_requested → revised →
…`, `constants.py` lines 19–32) and a real, mounted `customer_router`
(prefix `/customer/quotes`, confirmed mounted in `app/main.py` lines
512–529) exposing:

- `GET /customer/quotes/jobs/{job_id}` — list this customer's quotes for a job
- `GET /customer/quotes/{quote_id}` — quote detail + line items
- `POST /customer/quotes/{quote_id}/approve` (requires `Idempotency-Key` header)
- `POST /customer/quotes/{quote_id}/reject` (body: `{reason}`)
- `POST /customer/quotes/{quote_id}/request-revision` (body: `{reason}`)
- `GET /customer/quotes/{quote_id}/events` — audit trail

This sprint builds the real customer feature against `quote_checklist`,
not `execution`'s `PartsRequest` — see `contract-matrix.md` for the full,
verified contract, and `known-gaps.md` for why the spec's literal "parts
approval" framing does not map onto a buildable real endpoint.

## 5. Real, disclosed backend defects found and worked around client-side

1. **No `/v1` prefix on this engine's customer router.** Every other
   engine's customer router in this codebase hardcodes `/v1/...` in its
   own `APIRouter(prefix=...)` string (confirmed by comparison with
   `invoice_payment/customer_router.py` line 13:
   `prefix="/v1/customer/service-invoices"` and `execution`'s own
   `/v1/customer/service-jobs`). `quote_checklist/customer_router.py`
   line 13 uses `prefix="/customer/quotes"` — no `/v1`. `app/main.py`'s
   `_mount_routers` applies no additional prefix to this or any other
   engine router (only the engine-registry router gets an explicit
   `prefix=` argument, line 148) — each engine owns its full path. This
   client therefore hits the real mounted path exactly as written:
   `/customer/quotes/...`, not `/v1/customer/quotes/...`.
2. **Every quote-service business-rule rejection is an opaque 500, not a
   4xx.** All of `quote_service.py`'s guard checks (wrong customer,
   invalid status transition, missing rejection/revision reason,
   idempotency conflict, quote/job not found) `raise ValueError(...)`
   rather than the app's own `ServiceOSException`. `app/exceptions.py`
   registers a handler for `ServiceOSException` (line 113) and a
   catch-all `Exception` handler (line 177) but **no handler for
   `ValueError`** — so every one of these business-rule violations falls
   through to the generic 500 `INTERNAL_ERROR` response, with the actual
   reason (`QUOTE_ACCESS_DENIED`, `QUOTE_REJECTION_REASON_REQUIRED`,
   etc.) only ever reaching the server log, never the response body. This
   client cannot distinguish "you tried to reject someone else's quote"
   from "the database is down" — both look identical: a generic
   `server_error`. Mitigated by proactively enforcing every one of these
   rules client-side before ever calling the endpoint (disable
   approve/reject/revision unless `status === "sent_to_customer"`;
   require non-empty reason before enabling submit) so the opaque-500
   path is only ever hit on a genuine race condition, not routine use —
   see `financial-security-review.md`.
3. **The customer-facing `GET /customer/quotes/{quote_id}` does not
   filter by `is_customer_visible`.** `quote_service.py`'s `get_quote`
   (lines 452–460) returns every `ServiceJobQuoteItem` row for the quote
   unfiltered, even though the item model has a real
   `is_customer_visible` column meant to hide internal-only line items.
   Also returns `provider_internal_notes` (an explicitly
   internal-labeled field) as part of the same envelope. Mitigated
   client-side: the parser drops any item with `is_customer_visible !==
   true`, and `provider_internal_notes`/`created_by_user_id`/
   `created_by_staff_member_id`/`idempotency_key`/`locked_at` are excluded
   structurally (never included in the parse schema at all) — the same
   `z.object()` key-stripping technique used since CUSTOMER-L5-08.
4. **No expiry enforcement despite a real `expires_at` column.**
   `ServiceJobQuote.expires_at` exists and `QS_EXPIRED` is a defined
   status, but no service method ever sets `expires_at`, and no
   scheduler/cron in the repo enforces it (confirmed by an independent
   background grep pass). A quote can sit in `sent_to_customer`
   indefinitely with no real deadline — this client does not fabricate
   one.
