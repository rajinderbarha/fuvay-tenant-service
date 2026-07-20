# Customer / Address Contact Pattern

Built and wired into the real `JobDetailScreen` this pass (`CustomerContactCard` + `AddressCard`, both consuming
`CustomerContactView` built inline from the already-fetched `BookingSummary` -- no extra API call).

## Minimal-necessary-data enforcement
- `CustomerContactView` never carries a phone number -- confirmed no field for one exists on either `Job` or the
  safe `BookingSummary` view (MODULE-L5-36 evidence, re-checked this pass). `callSupported` is therefore always
  `false` and `CustomerContactCard` renders "Call unavailable" instead of a working button, rather than fabricating
  a dead action.
- `messageSupported` is typed `true` (real staff chat exists) but wired `false` in `JobDetailScreen` this pass --
  no code path resolves "the chat thread for this specific job" yet, so the button intentionally isn't shown
  rather than linking to a guessed thread id. Documented as a real gap, not silently hidden.
- `AddressCard`'s Navigate/Copy actions currently show an `Alert` placeholder rather than opening a real map
  intent or clipboard write -- the address text itself (`city`/`zipcode`, the only fields the safe view carries)
  is real, the action wiring is a design fixture pending a decision on which map-deeplink scheme to use.

## Location privacy
No continuous location tracking is implied or built here. `useLocation.ts` (pre-existing) is untouched by this
pass.
