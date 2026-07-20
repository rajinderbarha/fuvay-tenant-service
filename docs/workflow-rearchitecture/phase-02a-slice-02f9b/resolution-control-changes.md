# Resolution Control Changes — Slice 2F-9B (Workstream 4)

File: `frontend/tenant-portal/app/(tenant)/provider/complaints/[complaint_id]/page.tsx`

## Header button
Before (Slice 2F-9A): `{canReplyOrOffer && (<Btn ...>Offer resolution</Btn>)}`
— `canReplyOrOffer = canMutate && !isFinalState` (3-state final check).

After (this slice): `{canOfferResolution && (<Btn ...>Offer resolution</Btn>)}`
— `canOfferResolution = canOfferProviderComplaintResolution(role, status)`
(exact 2-state legal-source check).

## Modal open condition (defense in depth)
`<Modal open={resOpen && canOfferResolution} ...>` — previously
`open={resOpen}` alone. `resOpen` is local component state only settable
via the now-correctly-gated button, so this is a second, redundant layer
against any stale-state edge case (e.g. a future code change that sets
`resOpen` some other way) rather than a currently-reachable bug.

## Auto-close on state change
```ts
React.useEffect(() => {
  if (resOpen && !canOfferResolution) setResOpen(false);
}, [resOpen, canOfferResolution]);
```
If the modal is open and a refetch (`refreshAll()`, triggered by any of
the page's other successful actions) causes the complaint's status to
leave the legal-source set, the modal closes itself rather than staying
open with a form that would now only fail server-side.

## Submit handler re-check
Before: `onClick={() => offerResolution.execute()}`, `disabled={!resDesc.trim() || offerResolution.loading}`.
After: `onClick={() => { if (canOfferResolution) offerResolution.execute(); }}`,
`disabled={!resDesc.trim() || offerResolution.loading || !canOfferResolution}`.
Eligibility is re-evaluated at click time (React re-renders on every
`complaint.data` change from `useApi`, so `canOfferResolution` is always
current at the moment of the click), not just at modal-open time.

## Unchanged
- "Propose settlement" button and modal: untouched (different service
  method, out of scope).
- Settlement accept/reject controls: untouched.
- Reply control (`canReplyOrOffer`): untouched — see
  `reply-control-regression.md`.
- Modal layout, form fields (`Select`/`Input`), confirmation/cancel
  buttons, and all styling: byte-for-byte unchanged except for the 2
  boolean-condition edits above.

## Verification
`npx tsc --noEmit` — clean, no errors (see `test-report.md`).
