# Product Decisions Required — Slice 2F-9 (not resolved this slice)

## 1. Final-state protection for `respond_to_complaint`/`offer_resolution`
No check exists preventing a provider from replying to or proposing a
resolution on a `closed`/`cancelled`/`rejected` complaint. Plausible gap,
not conclusively proven exploitable (no demonstrated state-corruption or
financial consequence). A future slice should decide the correct
behavior (reject with a specific error code, or intentionally allow
late replies for record-keeping).

## 2. `complaints.customer_router`'s own authorization posture
Shows the same surface-level pattern (`get_current_user` only, no
permission/role check) this slice found and fixed in the provider
router. Not audited or modified this slice — a distinct persona/module
boundary; investigating it would be starting a second module. Strongly
recommended as the next slice in this series.

## 3. Should canonical staff ever be delegated complaint-response capability?
`require_tenant_owner_mutation` is currently owner-only. Whether office
staff should be able to respond to complaints/offer resolutions without
owner involvement is an open product question — no permission or role
evidence currently supports it.

## 4. The `AddMessageIn.visibility` field is dead input
The schema accepts a `visibility` field for provider messages, but the
service always hardcodes `public_to_case`. Whether provider-internal
notes should become a real capability (and if so, with what backend
enforcement) is a product decision, not resolved here.

## 5. Rework creation and admin-approval ownership
Not reachable from this router; their own router/guard was not
identified or audited. A future slice should locate and verify them.

## 6. Refund admin-approval (`admin_approve_refund`) ownership
Same disposition as #5.

## Recommendation (non-binding)
Item #2 (`complaints.customer_router`) is the highest-priority follow-up
— it is the customer-facing counterpart to the exact vulnerability class
this slice just closed, and may carry the same or worse exposure (a
customer's own complaint data plus PII).
