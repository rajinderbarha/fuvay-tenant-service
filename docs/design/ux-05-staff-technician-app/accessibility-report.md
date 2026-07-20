# Accessibility Report (Round 4 — real fixes, not just a plan)

A real pass across existing components, not a documentation-only plan. Fixes made and committed:

## Touch target sizing (44×44pt minimum)
- `Button` (app-wide, used by every screen): `sm` size was 36pt tall — bumped to 44pt.
- `AddressCard` Navigate/Copy buttons: 40pt → 44pt.
- `CustomerContactCard` Call/Message buttons: 40pt → 44pt.
- `JobNoteComposer`'s Add Note submit button: 40pt → 44pt.

## accessibilityRole / accessibilityLabel added
- `Button`: `accessibilityRole="button"`, `accessibilityLabel={label}`, `accessibilityState={{disabled, busy}}`
  (busy reflects the loading spinner state — a screen reader now knows a button is mid-action, not just disabled).
- `AddressCard`: Navigate/Copy buttons labeled with the actual address text spoken, not just the icon+word.
- `CustomerContactCard`: Call/Message labeled; the disabled "Call unavailable" state uses
  `accessibilityRole="text"` with a full-sentence label instead of relying on visual graying-out alone.
- `NotificationCard`: `accessibilityRole="button"`, label prefixes "Unread." for unread items —
  status-beyond-color (see below).
- `WorkItemCard` / `ScheduleCard`: labeled with job number, city, status (and conflict, for schedule) as one
  spoken sentence instead of relying on visually-scanning the card.
- `PartsRequestStatusCard`: `accessibilityRole="summary"` with part name/quantity/status spoken together.
- `PermissionRestrictedState`: `accessibilityRole="alert"` (announces on appear) with the full reason spoken;
  the 🔒 icon is now `accessibilityElementsHidden`/`importantForAccessibility="no"` (decorative — the label
  text already carries the meaning, so the icon isn't announced as a separate, meaningless glyph).
- `JobNoteComposer`: visibility-picker chips now have `accessibilityLabel`/`accessibilityState={{selected}}`.

## Status-beyond-color (verified, not just assumed)
- `JobStatusBadge` (pre-existing): already text + color, not color alone — verified, no change needed.
- `NotificationCard`'s unread indicator: previously color-only (a colored dot). Now also conveyed via the
  accessibility label ("Unread. ...") and the existing bold-text visual treatment — three redundant signals,
  not one.
- `ScheduleCard`'s conflict indicator: already text ("⚠ Conflict") + icon, not color alone.

## Screen titles
All navigable screens (both production and dev-only showcases) already had explicit `title` options set in
`AppNavigator`/tab navigators from Rounds 2–3 — verified present, no gaps found this pass.

## Not done this round (real, disclosed gaps)
- No systematic focus-order audit was performed (React Navigation's native-stack handles most focus management
  automatically on iOS/Android; this wasn't independently verified).
- No text-scaling (Dynamic Type / Android font scale) testing was performed — no `allowFontScaling={false}` was
  found anywhere in the app (good — nothing is blocking OS text scaling), but no explicit maximum-scale-factor
  testing was done to confirm layouts don't break at 200% text size.
- No screen-reader (VoiceOver/TalkBack) manual pass was performed — the fixes above are informed by RN
  accessibility API correctness, not a live assistive-technology session (no device/emulator available in this
  environment).
- The remaining ~10 unfixed components (Skeleton, StatCard, JobStatusBadge details, Card, all screen-level
  containers) were not individually audited this round — this was a targeted pass on interactive elements most
  likely to be missed, not an exhaustive one.
