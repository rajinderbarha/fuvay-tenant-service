# Slice 2F-9B Implementation Summary

## Scope
Narrow frontend + documentation correction slice. Precisely align the
provider complaint frontend's "Offer resolution" control with the
already-verified backend legal-source-state policy for
`provider_offer_resolution`. No backend behavior changes.

## What was found
Slice 2F-9A's frontend fix used a coarse `isFinalState` check (hides the
button only on `closed`/`cancelled`/`rejected`) for both the Reply and
Offer Resolution controls. This was correct and sufficient for Reply
(matches `provider_add_response`'s actual `FINAL_STATUSES` policy
exactly), but only conservative — not exact — for Offer Resolution,
whose real backend policy (`ALLOWED_TRANSITIONS_EXT`) permits the action
from exactly 2 states: `awaiting_provider_response` and
`under_admin_review`. The button previously still rendered (and would
correctly, safely fail server-side) in intermediate states such as
`open`, `resolution_proposed`, `rework_approved`, `refund_*`, `resolved`,
and `settled`.

A frontend caller inventory (`Workstream 2`) found exactly one caller of
the target backend endpoint (`POST /v1/provider/complaints/{id}/offer-resolution`)
across the entire repository: the tenant-portal complaint detail page's
"Offer resolution" button. A superficially similar "Propose resolution"
control exists in `frontend/super-admin/app/admin/complaints/[id]/page.tsx`,
but it calls a structurally distinct endpoint
(`POST /v1/admin/complaints/{id}/propose-resolution`, `complaints.admin_router`)
— out of scope, untouched, and not a caller of the target method. The
customer-app only displays/accepts existing resolutions; it does not
create them.

## What changed
1. **`frontend/tenant-portal/lib/api.ts`** — added
   `PROVIDER_RESOLUTION_LEGAL_SOURCE_STATES` (the exact 2-state constant,
   derived directly from `ALLOWED_TRANSITIONS_EXT`) and
   `canOfferProviderComplaintResolution(role, status, accessScope)`,
   following the exact existing pattern of `canIssueProviderInvoice`
   (tenant-owner-only, mutation-capable scope, fails closed on any
   unknown/missing role, scope, or status).
2. **`frontend/tenant-portal/app/(tenant)/provider/complaints/[complaint_id]/page.tsx`**
   — the "Offer resolution" header button now renders only when
   `canOfferProviderComplaintResolution(role, status)` is true (replacing
   the coarser `canReplyOrOffer`). The resolution `Modal`'s `open` prop is
   additionally gated on the same check (defense in depth against stale
   local state), an effect closes the modal if it's open and the
   complaint's state becomes ineligible on refetch, and the submit
   handler re-checks eligibility immediately before invoking the mutation.
   The Reply control's behavior (`canReplyOrOffer`, `FINAL_STATUSES`-based)
   is **unchanged**.
3. **`frontend/tenant-portal/lib/api.persona.test.ts`** — added 21 new
   direct tests for the new helper (14 per-status matrix cases + 7
   persona/edge-case tests), using the same `node:test` pattern already
   established in this file for Slice 2F-6B's helpers (no new test
   dependency introduced).
4. **Slice 2F-9A documentation corrected** — `frontend-state-alignment.md`,
   `approval-gate.md`, and `product-decisions-required.md` updated to
   reflect the exact alignment now shipped, replacing the prior
   `YES, PARTIALLY` with a pointer to this slice's corrected `YES`.

## What did NOT change
No backend file was modified. `FINAL_STATUSES`, `ALLOWED_TRANSITIONS_EXT`,
`_transition`, `provider_add_response`, and `provider_offer_resolution`
are byte-for-byte unchanged from Slice 2F-9A. No permission was created.
No role was created. `complaints.customer_router`,
`complaints.admin_router`, and `execution.real_estate_router` were not
touched. The "Propose settlement" button and settlement accept/reject
controls are unchanged. No visual redesign occurred — same layout, same
styling, same form fields; only the boolean conditions gating 2 controls
changed.

## Outcome
`SECURITY_AND_DOMAIN_INTEGRITY_CLOSED_PRODUCT_POLICY_BLOCKED` — see
`approval-gate.md`. Global tenant-mutation coverage unchanged: **106/182**.
