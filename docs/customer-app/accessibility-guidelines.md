# Customer App — Accessibility Guidelines

Applies to all new code under `mobile/customer-app/src`. Existing screens
predate these guidelines and are migrated incrementally (see
`known-gaps.md`), not rewritten wholesale in this sprint.

## Buttons

Use `AppButton`/`AppIconButton`, never a bare `Pressable`/`TouchableOpacity`
for an action. `accessibilityRole="button"` and
`accessibilityState={{ disabled, busy }}` are set automatically. Icon-only
buttons **require** an `accessibilityLabel` prop — there is no default.

## Form Fields

Use `AppTextField`/`AppTextArea`/`AppCheckbox`/`AppRadio`/`AppSwitch`. The
label is always a real rendered `AppText`, never only a `placeholder`.
Errors set `aria-invalid`/`accessibilityState` and are rendered via
`FieldMessage` immediately below the field so screen readers encounter them
in reading order.

## Validation Errors

Announce via `FieldMessage tone="error"` (sets
`accessibilityLiveRegion="polite"`). Do not show a red border alone — the
error text is the primary signal.

## Headings

Use the largest appropriate `AppText` variant (`headingLarge/Medium/Small`,
`titleLarge/Medium/Small`) for section headings so the visual hierarchy is
unambiguous even before considering `accessibilityRole="header"` (add that
role explicitly per-screen where a heading needs to be a landmark — not
default on `AppText`, since most `AppText` usage is body copy).

## Lists

Prefer `FlatList`/`SectionList` over mapping into a `ScrollView` for any
list that can grow — layout primitives (`Stack`) are for small, fixed
groups of children, not data lists (see Performance §38 in the sprint
spec: "list primitives prepared for virtualization").

## Cards

`AppCard` with `variant="interactive"` requires an `accessibilityLabel`
describing the destination/action, since the card's visible text is often
not phrased as an action ("AC Repair — ₹499" vs. the label "View AC Repair
service details").

## Bottom Sheets / Modals

Use `BottomSheet`/`ConfirmationModal`. Both set
`accessibilityViewIsModal`, handle the Android hardware back button, and
dismiss via scrim tap. Do not build a custom `Modal` per feature.

## Progress Indicators

Use `LoadingIndicator` (`accessibilityRole="progressbar"`). Never render a
bare `ActivityIndicator` in feature code.

## Booking Status / Price Changes / Live Updates (future sprints)

Any UI that changes value without direct user interaction (a live price,
a booking status transition, a technician ETA) must pair the visual change
with an `AccessibilityInfo.announceForAccessibility()` call or a live
region, exactly as `toastService.show()` already does for toasts. Do not
rely on a screen reader user noticing an unannounced visual change.

## Reduced Motion

Any new animation must check
`AccessibilityInfo.isReduceMotionEnabled()` (see `Skeleton` for the
reference pattern) and provide a static equivalent.

## Touch Targets

`AppPressable` enforces `sizes.touchTargetMin` (44dp) by default via
`enforceMinTouchTarget`. Only disable it (`enforceMinTouchTarget={false}`)
when the pressable is visually large enough on its own (e.g. a full-width
card) — never for a small icon-only control.

## Automated Checks in This Sprint

`design-system/__tests__` and `components/__tests__` assert
`accessibilityRole`, `accessibilityLabel`, and `accessibilityState` on every
primitive with interactive tests (AppButton, AppIconButton, AppCheckbox,
AppSwitch, AppTextField, AppCard, ErrorState). Full device-level TalkBack/
VoiceOver manual verification was **not** performed in this sprint (no
physical device/simulator was exercised — see `known-gaps.md`).
