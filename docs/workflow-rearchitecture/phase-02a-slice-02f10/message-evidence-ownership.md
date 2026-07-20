# Message and Evidence Ownership — Slice 2F-10 (Workstream 8)

## Author type is server-derived, not client-supplied
`add_customer_message` (unmodified) hardcodes `sender_type = ACTOR_CUSTOMER`
on the created `ComplaintMessage` — `AddMessageIn` has no `sender_type` or
`visibility` field at all. A customer cannot submit a provider author
type or mark their own message provider-internal/platform-only; there is
no such input to manipulate.

## Customer cannot edit or delete provider-authored messages
No `customer_router` route accepts a `message_id` for edit/delete at
all — the only customer message mutation is `add_customer_message`
(create-only, append). Confirmed absent by the full route inventory
(`customer-complaints-final-route-inventory.csv`).

## No evidence-upload route exists in customer_router
`ComplaintService.upload_complaint_media` exists in the shared service
file but **customer_router.py has no route that calls it** — confirmed
by grep across the file. The only media-related capability visible to a
customer is the (also absent) ability to view provider-visible evidence
via `list_media`, which is likewise not routed from `customer_router`.
This is reported as an absent capability, not silently assumed working —
see `known-limitations.md`.

## Visibility flag is dead input where it would matter
Where `visibility` fields exist elsewhere in the complaint schema set
(e.g. `upload_complaint_media`'s `visibility` parameter), the customer
route surface simply doesn't expose a path to set it — consistent with
the same "dead input" finding already documented for the provider side in
Slice 2F-9's `known-limitations.md` item 3 (`AddMessageIn.visibility`).

## Final-state restriction
`add_customer_message` blocks on `FINAL_STATUSES`
(`closed`/`cancelled`/`rejected`) — unmodified, pre-existing, identical
to the pattern Slice 2F-9A mirrored for the provider side. Confirmed via
the pre-existing test suite (unchanged) and re-verified in this slice's
regression run.

## Audit/history
Every message creation logs `EVT_CUSTOMER_MESSAGE_ADDED` via
`_log_event` — unmodified, pre-existing.
