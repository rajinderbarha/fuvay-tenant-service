# Unclaimed Asset Authority

Final policy per principal for a `chat_attachment` MediaAsset with no
`chat_thread_id` claim (traced against both the attach path,
`chat_service._validate_attachments`, and the retrieval path,
`MediaAssetService._assert_chat_thread_authority`):

| Principal | Metadata read | View | Download | Attach/use (first-claim) | Intended-recipient authority |
|---|---|---|---|---|---|
| Uploader/owner | ALLOWED (`assert_can_view`'s uploader fallback) | ALLOWED | ALLOWED | ALLOWED (proven by `uploaded_by_user_id` match) | n/a (their own asset) |
| Asset customer (`asset.customer_id == actor.user_id`) | ALLOWED | ALLOWED | ALLOWED | ALLOWED (2F-18B customer-context branch) | Thread `customer_id` match required (2F-18B) |
| Tenant owner | ALLOWED (tenant-wide, existing policy) | ALLOWED | ALLOWED | ALLOWED (tenant + thread-customer match) | Thread membership is tenant-wide by ratified office policy |
| Canonical staff | ALLOWED (tenant-wide, existing policy) | ALLOWED | ALLOWED | ALLOWED (same as tenant owner) | same |
| Assigned technician (assigned to the target thread's Job) | **DENIED unless also the uploader (THIS SLICE)** | **DENIED unless uploader** | **DENIED unless uploader** | **DENIED unless uploader** | n/a — access denied entirely unless uploader |
| Same-tenant UNASSIGNED technician | DENIED (fails `validate_thread_access` before this question is even reached) | DENIED | DENIED | DENIED | n/a |
| Active thread participant (non-technician, e.g. a customer who is a listed participant) | Governed by their own role's rule above | — | — | — | — |
| Removed participant | DENIED (fails `validate_thread_access`) | DENIED | DENIED | DENIED | n/a |
| Foreign customer | DENIED (`assert_can_view`'s customer_id mismatch) | DENIED | DENIED | DENIED | n/a |
| Cross-tenant user | DENIED (`assert_can_view`'s tenant mismatch) | DENIED | DENIED | DENIED | n/a |
| Super admin | ALLOWED (bypasses everything) | ALLOWED | ALLOWED | ALLOWED | n/a |
| Unknown role | DENIED (role-map lookup returns `None`, or `assert_can_view` denies first) | DENIED | DENIED | DENIED | n/a |

## Corrected classification from 2F-18B/2F-18C
Both prior slices classified "technician tenant-wide unclaimed-asset
access" as accepted, existing, unmodified `MediaAccessService` behavior.
This slice's mission explicitly requires closing it: "Unclaimed assets
must not inherit broad tenant-wide technician access" and "A technician
must not receive unclaimed-asset access merely because the technician
belongs to the asset tenant." **Corrected**: a technician now needs
uploader-level evidence for BOTH attach and retrieval of an unclaimed
asset — tenant membership and even valid Job assignment are no longer
sufficient by themselves.

## Office access intentionally left tenant-wide
Per the ratified policy's own text ("Tenant owner/staff access is
explicit and least privilege" is satisfied by the EXISTING tenant+customer
match requirement, not by uploader-restriction) and consistent with every
prior slice's established office-persona precedent, `tenant_owner`/`staff`
retain their existing tenant-wide oversight — this is a deliberate,
documented design choice, not an oversight.
