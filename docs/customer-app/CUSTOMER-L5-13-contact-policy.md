# CUSTOMER-L5-13 — Contact Policy

## No Real Masked-Call or In-App Contact System Exists

Exhaustively verified (own research + independent cross-check): zero
hits repo-wide for `masked_call`, `call_masking`, `proxy_number`,
`click_to_call`, `contact_technician`. `ProviderTeamMember.phone`/`.email`
exist as real DB columns, but no customer-facing endpoint ever exposes
them, and no proxy/masking layer exists to make direct exposure safe even
if it did.

## Consequence

This sprint renders a single, static, non-interactive "Contact"
informational row (`serviceTracking.contactTitle`/`contactNote`) on the
tracking screen — matching CUSTOMER-L5-12's established pattern for other
confirmed-absent action boundaries (cancel/reschedule/technician/parts/invoice).
No phone number, masked or otherwise, is ever requested, stored, rendered,
or logged anywhere in `features/service-tracking/` — verified by grep
(there is none to leak in the first place, since the real backend never
returns one).

## What Would Close This Gap (Not This Sprint's Scope)

A real backend change: a masked-call/proxy-number system (e.g., a
telephony provider integration) plus a customer-facing endpoint issuing
short-lived, scoped contact tokens. Neither exists today.
