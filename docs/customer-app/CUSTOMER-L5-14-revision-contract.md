# CUSTOMER-L5-14 — Revision Request Contract

## Endpoint

`POST /customer/quotes/{quote_id}/request-revision`, body
`{ "reason": string }` (`customer_router.py` lines 65–75). Same shape and
same lack of idempotency support as rejection.

## Service logic (`quote_service.py` `customer_request_revision`, lines
398–423)

1. `reason` required, non-empty → `ERR_QUOTE_REVISION_REASON_REQUIRED`
   otherwise.
2. Ownership check.
3. `_assert_transition(q, revision_requested)` — only valid from
   `sent_to_customer`.
4. Sets `status=revision_requested`, `revision_reason=reason`.
5. `_sync_job_status(job_id, "quote_revision_requested")`.
6. Logs `quote_revision_requested`.

## What happens after — real, but entirely outside this client

`revision_requested → {revised, cancelled}` per `QUOTE_TRANSITIONS` — a
staff/provider action (`mark_revised`, `quote_service.py` lines 505–526)
is the only way forward, and it does not create a new quote row or
change any item — it simply flips the **same** quote's status back to
`revised`, from which staff can `submitted_to_provider`/`sent_to_customer`
again. This client has no way to know when or whether that happens except
by re-fetching (`staleTime: 0` + refetch-on-mount, the same pattern used
everywhere in this app — no polling loop is added). When the quote comes
back around to `sent_to_customer`, this client's existing
`isQuoteActionable` check makes it actionable again automatically — no
separate "revised" UI state is needed beyond the status label
(`quoteDecision.status.revised` is shown only in the narrow window where
the quote is `revised` but not yet re-sent).

## No true "revision" record exists

This is genuinely a **single quote row's status oscillating**, not a
parent/child or version-linked model — `revision_reason` is a single
field on `ServiceJobQuote`, overwritten each time (a second revision
request from a later `sent_to_customer` state would erase the first
`revision_reason`, since there's only one column). This client never
attempts to reconstruct a revision history; `GET
/customer/quotes/{quote_id}/events` (used implicitly by the audit trail
this client does not currently render — see `known-gaps.md`) is the only
real source of that history.
