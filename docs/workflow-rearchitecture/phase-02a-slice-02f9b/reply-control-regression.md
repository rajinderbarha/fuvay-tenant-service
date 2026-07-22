# Reply Control Regression — Slice 2F-9B (Workstream 5)

## No change made to the Reply control
`canReplyOrOffer = canMutate && !isFinalState` (where
`isFinalState = ["closed", "cancelled", "rejected"].includes(status)`,
i.e. base `FINAL_STATUSES`) is **unmodified** from Slice 2F-9A. The
Reply input and "Send reply" button both still use `canReplyOrOffer`
exactly as before. No resolution-specific helper
(`canOfferProviderComplaintResolution`) was applied to the Reply control
— confirmed by direct source diff review of this slice's own change (the
diff touches only the "Offer resolution" button, the `Modal`'s `open`
prop, and the modal's submit handler/disabled condition).

## Verification against the mission's explicit checklist
- **Hidden/disabled in `FINAL_STATUSES`-blocked statuses**: yes —
  `isFinalState` covers exactly `closed`/`cancelled`/`rejected`, matching
  `provider_add_response`'s own `FINAL_STATUSES` guard precisely.
- **Available in non-final states allowed by the backend**: yes —
  `provider_add_response` has no other restriction, so every other status
  (including `resolved`/`settled`) correctly still shows the control.
- **Tenant-owner mutation scope required**: yes — via `canMutate`
  (`isTenantOwnerRole(role) && !isTenantReadOnly()`), unchanged.
- **Staff and technicians denied**: yes — `isTenantOwnerRole` returns
  `false` for both.
- **Unknown statuses fail closed**: `isFinalState` only matches the 3
  named strings; an unrecognized status is simply not final, so the Reply
  control remains visible — this is the correct, established behavior
  for Reply (not a resolution-style allowlist), since `provider_add_response`
  itself only *blocks* on a known deny-list (`FINAL_STATUSES`), it does
  not require an allow-list match. This is intentionally different from
  `canOfferProviderComplaintResolution`'s allow-list approach, because the
  two backend methods use genuinely different validation strategies
  (deny-list vs. `_transition`'s allow-list) — mirroring each one's real
  backend logic, not applying one pattern to both.

## Product decision preserved, not touched
Whether `provider_add_response` should also block on `resolved`/`settled`
remains an open, undecided product question (Slice 2F-9A
`product-decisions-required.md` item 1) — this slice did not change
`FINAL_STATUSES`, did not change `provider_add_response`, and did not
change the Reply control's frontend gate.
