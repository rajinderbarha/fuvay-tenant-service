# CUSTOMER-L5-08 — Security Review

## Ownership Enforcement

`match_and_price`'s draft lookup (`svc.get_booking_draft(draft_id=draft_id,
customer_id=customer_id)`, customer_router.py:175) enforces draft ownership
before any matching runs — unchanged pattern from every prior sprint's own
`_require_draft`-style check. This client never supplies a raw provider ID
anywhere in this flow (there is no such route param reachable from real
UI — see the `providerPreview` route-param correction in the Known Gaps'
"pre-reserved but wrong" note), so there is no client-constructible path to
probe another customer's or another tenant's data through this screen.

## No Internal Scoring/Health Data Ever Reaches the Client

Verified structurally, not just by convention: `provider-match-schema.ts`'s
`matchedProviderSchema` has no key for `internal_score`,
`internal_score_breakdown`, `health_score`, or `health_band` — even if a
future backend regression accidentally included these in the response
body, `z.object()`'s default unknown-key stripping means they would never
survive into this client's parsed type or reach any log line, UI element,
or analytics event.

## No Sensitive Logging

`provider_match_started`/`provider_match_completed`/`provider_match_failed`/
`provider_match_no_match`/`provider_badge_unmapped` log calls
(`provider-matching-queries.ts`, `badge-label-mapping.ts`) pass only
booleans, counts, and known enum-like badge strings — never the provider's
name, rating, or reason text. Verified by direct review of every
`logger.*` call site added this sprint.

## No Production Mocks

Grepped `features/provider-matching/` for `mock`, `fake`, `TODO`, `FIXME`
— none found. Every rendered field traces to a real, schema-validated
`match-and-price` response.

## Cross-Tenant/Cross-Customer Isolation

Relies entirely on the backend's own draft-ownership check (above) — this
sprint adds no new client-side authorization logic of its own to bypass or
get wrong. The existing unconditional `queryClient.clear()` on
logout/account-switch (CUSTOMER-L5-02) covers this sprint's cache
additions with no new clearing logic required (see cache-policy.md).

## Known Backend Data-Integrity Concern (disclosed, not a client vulnerability)

The `"Verified"` badge is hardcoded unconditionally by the backend
regardless of `Tenant.verification_status` (see provider-model.md). This
client renders it as an honest passthrough of what the backend actually
sends — it does not add extra trust signaling on top of it, and this
finding is documented prominently so it is not mistaken for a real,
checked verification guarantee by anyone reading this sprint's output.

## Error Body Discard (pre-existing, cross-cutting, unmodified)

`api-client.ts`'s failure path never calls `res.json()` — the real
backend's `error_code` is never available to this or any other feature.
This is a safety property in one sense (no server-authored free text is
ever surfaced verbatim to a customer, reducing injection/spoofing surface
from a compromised or buggy backend response) and a UX limitation in
another (this sprint cannot show the real, more specific reason for a
match failure) — documented in contract-matrix.md and known-gaps.md, not
modified this sprint since it is shared infrastructure well outside this
sprint's scope.
