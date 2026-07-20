# CUSTOMER-L5-08 — Provider Preview Contract

## Screen: `ProviderPreviewScreen`

Renders exactly the five fields in `selected_provider` — no more, no
less — per `matched-provider-schema.ts`'s `matchedProviderSchema`:

| UI element | Source field | Fallback when absent/null |
|---|---|---|
| Provider name (title) | `provider_name` | N/A — required, non-empty per schema; parse fails closed if missing. |
| Rating line | `rating` | `providerMatch.ratingNotYet` ("Not yet rated") when `null`. |
| Badge chips | `public_badges[]` | Section omitted entirely when the array is empty (a real, valid response shape — see contract-matrix.md). |
| "Why this provider" | `customer_visible_reason` | N/A — always present per schema. |
| (not displayed) | `tenant_id` | Held only for internal use (log context, cache key material); never rendered as visible text. |

## No-Match State

When `match-and-price` fails (any error — see contract-matrix.md's Error
Contract for why the two real 422 reasons collapse to one generic state at
this client's current error-handling layer), the screen renders:

- `providerMatch.noMatchTitle` / `providerMatch.noMatchDescription` — generic copy, since the real backend detail message (`"No eligible providers available in {city}. Try a nearby city."`) is not reachable from this client's normalized `ApiError` (the body is never parsed on the failure path).
- A "Try again" action that re-runs the exact same mutation (real re-derivation, not a client-side retry-with-backoff — the endpoint has no rate-limit/idempotency concerns documented).
- A "Change address" action that returns to `AddressSelection`, mirroring `ServiceabilityScreen`'s not-serviceable state exactly.

## Continue Action

Only shown on a successful match. Navigates to the existing dev-only
`Pricing` placeholder (`PricingBoundaryPlaceholderScreen`, updated this
sprint to describe itself as the price-tier/bargain boundary rather than
the provider-matching/pricing boundary, since provider matching is now a
real, completed stage by the time this screen's Continue button is
reachable).

## Accessibility

- The provider name uses `headingMedium` (a real heading-weight variant),
  distinct from the section's `titleLarge` "Provider matched" label, so a
  screen reader distinguishes the status label from the actual provider
  identity.
- Badge chips are plain `AppText` inside a `View` (no custom touchable
  behavior, no `accessibilityRole="button"` misuse) — they are descriptive,
  non-interactive metadata, not tappable controls.
- The back chevron reuses the exact `AppPressable`/`AppIcon`
  `accessibilityLabel="Go back"` pattern from `ServiceabilityScreen`.

## Localization

`discovery.json`'s `providerMatch.*` keys (English, Hindi, Punjabi in
Gurmukhi) cover every customer-visible string on this screen except one:
`customer_visible_reason` itself, which is real backend-authored English
text with no localization key on the server side (same category of gap as
CUSTOMER-L5-07's `preferred_time_window` free text) — rendered verbatim,
documented as a known gap rather than silently mistranslated or hidden.
