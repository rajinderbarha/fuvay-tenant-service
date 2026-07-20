# Frontend State Alignment — Slice 2F-9A

## [CORRECTED IN SLICE 2F-9B]
This document's conclusion that the coarser 3-state gate was an
acceptable, intentionally conservative simplification for
`offer_resolution` has been superseded. Slice 2F-9B implemented the
exact 2-state legal-source gate
(`canOfferProviderComplaintResolution` in `lib/api.ts`), so the
`offer_resolution` button now renders only in
`awaiting_provider_response`/`under_admin_review`, matching the backend
precisely. See `phase-02a-slice-02f9b/resolution-control-changes.md` and
`phase-02a-slice-02f9b/approval-gate.md` for the corrected, final
`FRONTEND_STATE_POLICY_ALIGNED: YES` result. The reasoning below is kept
for historical record of what Slice 2F-9A actually shipped, not as the
current state of the code.


## Backend remains authoritative
Both target routes continue to independently and correctly reject
illegal-state requests server-side, regardless of any frontend change.
This slice's frontend edit is a UX improvement only (don't show a control
that will always fail), not a security or correctness boundary.

## Change made
`frontend/tenant-portal/app/(tenant)/provider/complaints/[complaint_id]/page.tsx`:
- Added `isFinalState = ["closed", "cancelled", "rejected"].includes(status)`
  and `canReplyOrOffer = canMutate && !isFinalState`.
- The "Reply to customer" input + "Send reply" button (respond_to_complaint)
  and the "Offer resolution" button (offer_resolution) are now gated on
  `canReplyOrOffer` instead of `canMutate` alone.
- "Propose settlement" and the settlement accept/reject controls are
  **unchanged** — different service methods
  (`create_settlement_proposal`/`respond_to_settlement`), out of this
  slice's scope; no state-based gating was added or removed for them.

## Why `["closed", "cancelled", "rejected"]` and not the broader `resolved`/`settled`
This matches `respond_to_complaint`'s actual backend policy
(`FINAL_STATUSES`, not `FINAL_STATUSES_EXT`) — since the reply control's
gate must reflect `provider_add_response`'s real behavior, which still
allows a reply on `resolved`/`settled` complaints. The `offer_resolution`
button uses the same flag as a simplification: strictly, `offer_resolution`
is illegal from every state except 2 (`awaiting_provider_response`,
`under_admin_review`), which is a narrower set than "not final." Hiding it
only on the 3 base-final states is intentionally conservative — it still
allows the button to render (and then correctly fail server-side) in
states like `resolved`/`resolution_proposed` where it is also illegal,
because building a full 13-state frontend gate for one button was judged
out of proportion to a narrow follow-up slice and would risk silently
encoding wrong domain assumptions in the UI ahead of any product decision.
This is flagged, not silently resolved — see `product-decisions-required.md`.

## Verification
`npx tsc --noEmit` in `frontend/tenant-portal` — clean, no errors.
`next lint` — not verified (pre-existing environment/tooling gap,
documented in prior slices; no ESLint v9 config exists in this
environment).
