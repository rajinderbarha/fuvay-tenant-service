# Message, Evidence, and Internal-Note Privacy — Workstream 11

## Finding: no internal-note capability actually exists via this router
`AddMessageIn` (the request schema for `respond_to_complaint`) accepts a
`visibility` field (default `"public_to_case"`), suggesting the
capability to post a provider-internal note. However,
`provider_add_response` (the service method actually called) **hardcodes
`visibility = VIS_PUBLIC`** and never reads the request's `visibility`
field at all — confirmed via direct source read. **Every message a
provider posts through this router is customer-visible; there is no way
to create a genuinely provider-internal note through this endpoint,
despite the schema suggesting otherwise.**

This is not classified as a security defect (nothing leaks that
shouldn't — the opposite: a field that looks like it controls privacy is
silently ignored, always defaulting to the *more* visible state) but is
a real, user-facing inconsistency between the API contract and its
implementation, logged in `known-limitations.md`.

## No media/evidence upload route exists in this router
No route in `provider_router.py` uploads or attaches `ComplaintMedia`.
Confirmed via full read of the file — the only evidence-adjacent
capability is the settlement proposal's free-text `description`/
`conditions` fields, not a file/media attachment.

## Requirements verification

| Requirement | Status |
|---|---|
| Customer cannot read provider-internal notes | Vacuously true — no provider-internal note can be created through this router at all |
| Technician cannot read unrelated complaint notes | N/A — technician has no access to any route in this router (denied at the authorization layer) |
| Provider cannot alter customer-authored evidence | N/A — no evidence-mutation route exists here |
| Cross-tenant media IDs are rejected | N/A — no media reference is accepted by any route in this router |
| Internal note visibility is enforced by backend queries, not only frontend filtering | Moot — since no internal note can be created via this router, there is nothing for a backend query to filter incorrectly |
| Attachment deletion cannot remove another actor's evidence | N/A — no attachment-deletion route exists here |

## Conclusion
No note/evidence privacy violation exists in this router, because the
capability that would need privacy enforcement (provider-internal notes,
evidence upload/deletion) does not actually exist here — despite the
request schema's `visibility` field suggesting otherwise. This
discrepancy is documented, not silently fixed by inventing new backend
behavior (which would be a scope expansion beyond "close directly
connected bypasses").
