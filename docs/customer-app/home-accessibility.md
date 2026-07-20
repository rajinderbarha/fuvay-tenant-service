# Customer App — Home Accessibility

## Implemented

- `HomeScreen`'s greeting is `accessibilityRole="header"`.
- `Section` (CUSTOMER-L5-00) exposes its title as a heading automatically.
- `CategoryCard` is an `AppCard variant="interactive"`, which sets
  `accessibilityRole="button"` and requires (via its own prop contract) an
  `accessibilityLabel` — `HomeScreen` passes one that includes the
  offering count when available (e.g. "AC Repair, 5 services available"),
  satisfying "card labels should include status where relevant".
- The profile-avatar press target has an explicit
  `accessibilityLabel`/`accessibilityHint`.
- Decorative category icon images are `accessibilityElementsHidden`.
- `Skeleton` (CUSTOMER-L5-00) already respects reduced motion.
- `OfflineBanner`/`ErrorState`/`EmptyState` (CUSTOMER-L5-00) already carry
  their own accessibility roles — reused as-is, not reimplemented.

## Not Verified This Sprint

- No device-level VoiceOver/TalkBack pass (same documented limitation as
  every previous sprint — no physical device/simulator in this
  environment).
- No large-text layout check beyond `numberOfLines={2}` on the category
  title (a Dynamic Type stress test was not performed).
- No landscape/tablet layout check beyond the design system's existing
  `ScreenContainer` max-width behavior (CUSTOMER-L5-00).

## Deliberately Not Implemented

Carousel accessibility rules (§40's "carousel controls must be accessible")
do not apply — this sprint has no carousel (no campaigns exist to carousel
through).
