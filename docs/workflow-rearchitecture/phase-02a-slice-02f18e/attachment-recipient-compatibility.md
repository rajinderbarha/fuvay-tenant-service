# Attachment Recipient Compatibility

## Re-affirmed from 2F-18C, with this slice's addition

2F-18C's `attachment-recipient-authority.md` established that per-recipient
verification is enforced at RETRIEVAL time (every reader re-runs
`validate_thread_access`), not exhaustively re-checked at send time, because
every legitimate recipient already passed the identical thread-authority
gate the sender needed. This remains the enforcement mechanism.

## What this slice adds: sender-side destination compatibility
The GAP this slice closes is not "can the recipient receive it" (already
covered) but "did the SENDER prove they picked the RIGHT audience to begin
with." For office senders, this is now enforced via the first-use
ambiguity rule (`office-first-use-matrix.csv`): an office actor sharing an
asset they did not upload into a customer-linked thread has NOT
demonstrated destination compatibility, regardless of tenant/customer
matching, because the asset could equally plausibly belong to any of that
customer's other threads.

## Per-audience-class verification (re-derived against this slice's fix)
| Audience class | Compatibility check |
|---|---|
| Customer | `thread.customer_id == asset.customer_id` (2F-18B) AND (for office senders) office is the uploader OR the destination has no customer party (this slice) |
| Owner/staff | Tenant match + `MediaAccessService` (2F-18B, unchanged) |
| Assigned technician | Live `ServiceJob.assigned_staff_id` check at retrieval (2F-18C), plus the technician's OWN first-use uploader rule if THEY are the sender (2F-18D) |
| Active participants (general) | `validate_thread_access` at every read (2F-18A, unchanged) |
| Provider-only recipients | `visibility` enum restriction to admin-only senders (2F-18) — office/technician/customer senders cannot mark a message provider-only in the first place |
| Technician-visible recipients | `is_visible_to("technician")` correctly excludes `provider_only`/`admin_only` content (2F-18A) |

## Sender's own view authority is not blanket recipient authority
Re-confirmed: `MediaAccessService.assert_can_view`'s tenant-wide-for-office
rule proves the SENDER may view/use an asset; it says nothing about
whether EVERY thread participant should receive it. This slice's office
first-use fix is exactly the closure of that gap for the one place it was
still open — everywhere else (recipient-side retrieval), the
independently-enforced retrieval-time check already handles this
correctly per 2F-18C.
