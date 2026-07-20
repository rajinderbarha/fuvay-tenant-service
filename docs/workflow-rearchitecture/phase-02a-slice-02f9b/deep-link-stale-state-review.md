# Deep-Link and Stale-State Safety Review — Slice 2F-9B (Workstream 6)

## Modal-opening mechanism (source review)
`resOpen` is a plain `useState<boolean>(false)` local to
`ProviderComplaintDetailPage`. The component reads no query parameters,
no URL hash, and no router state to control `resOpen` — it is settable
only via the "Offer resolution" `Btn`'s `onClick`. There is no
`useSearchParams`/`router.query` usage anywhere in this file (confirmed
by source read of the full component). Therefore:

- **Direct URL to complaint detail in an illegal resolution state**:
  the page always mounts with `resOpen = false`; the "Offer resolution"
  button itself only renders when `canOfferResolution` is true, so there
  is no path by which loading the page directly, in any state, could
  show an active-looking control.
- **Query parameter attempting to open the resolution modal**: not
  possible — no code path reads any query parameter to set `resOpen`.
  This is a structural (not merely tested) guarantee; there is nothing to
  bypass.
- **Browser history restoring an open modal**: `useState` does not persist
  across a hard navigation/reload (React remounts the component with its
  initial state), and Next.js client-side back/forward navigation within
  the same mounted component instance does not exist for this page (it
  has no nested routes) — so there is no realistic path for browser
  history to resurrect `resOpen = true`. If in the future this ever did
  reoccur (e.g. via a state-restoration library), the `Modal open={resOpen
  && canOfferResolution}` gate would still prevent it from rendering.

## Complaint status changing after page load (tested behavior)
Implemented via:
```ts
React.useEffect(() => {
  if (resOpen && !canOfferResolution) setResOpen(false);
}, [resOpen, canOfferResolution]);
```
Every successful action on the page (`respond`, `offerResolution`,
`createProposal`, `respondProposal`, `submitAiAnswers`) calls
`refreshAll()`, which re-fetches `complaint` via `useApi`. When the new
`complaint.data.status` causes `canOfferResolution` to flip to `false`
while the modal happens to be open, this effect closes it on the next
render.

## Mutation attempted after a state changes on the server (race)
- The submit button's `disabled` includes `!canOfferResolution`, and the
  `onClick` handler itself re-checks `if (canOfferResolution)` before
  calling `offerResolution.execute()` — both evaluated at click time
  against the latest fetched `complaint.data`.
- If a genuine race occurs regardless (another actor changes the
  complaint's state between the last client fetch and the server
  processing the request), the backend's own `_transition` check remains
  the final, authoritative boundary — it will reject with
  `COMPLAINT_INVALID_STATUS_TRANSITION`, and `offerResolution.error` (the
  existing `useAction` error state, unchanged) surfaces it in the modal.
  No success UI is shown in this case, because `onSuccess` (which closes
  the modal and clears the form) only fires on a non-error response —
  this is `useAction`'s existing, unmodified behavior, not something this
  slice added.

## Cached complaint detail / unknown or missing API status
- `status = s(c.status)` (`s()` coerces `null`/`undefined` to `""`).
  `canOfferProviderComplaintResolution` explicitly returns `false` for a
  falsy status (`if (!status) return false;`), so a missing status in a
  cached or malformed API response cannot show the control.
- An unrecognized status string (e.g. a future backend status not yet
  known to the frontend) also correctly returns `false`, since it's not
  in `PROVIDER_RESOLUTION_LEGAL_SOURCE_STATES` — proven directly in
  `lib/api.persona.test.ts`'s "unknown/unrecognized status fails closed"
  test.

## Cross-tenant complaint detail
Unchanged from Slice 2F-9: `GET /v1/provider/complaints/{id}` 403/404s
server-side for a cross-tenant complaint id (via `provider_get_complaint`'s
tenant check), and the page's `complaint.error` branch renders an error
card and returns before any action button is reached — so no control,
resolution or otherwise, can ever render for a complaint outside the
caller's tenant, regardless of any frontend state.
