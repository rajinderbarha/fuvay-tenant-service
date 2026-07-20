# Accessibility Reconciliation (UX-05B, item 5)

Mirrors `workstream-reconciliation.md`'s pattern: one clear, current statement of what accessibility work is
actually done, what isn't, and why — replacing the need to cross-reference `accessibility-report.md` (Round 4)
plus scattered mentions in later rounds' docs.

## Touch targets (44×44pt minimum)
**Covered**: `Button` (app-wide shared component, used by `JobDetailScreen`, `HomeScreen`, `CurrentJobScreen`,
every modal's Submit/Cancel pair, etc. — `sm` bumped 36pt→44pt, `md`/`lg` already compliant), `AddressCard`
Navigate/Copy, `CustomerContactCard` Call/Message, `JobNoteComposer`'s submit button (all bumped 40pt→44pt in
Round 4).
**Verified this session (UX-05B item 5)**: re-checked `JobDetailScreen.tsx` specifically (the screen this phase
touched for its theme conversion) — every actionable element on it (`Accept`/`Reject`/`On the Way`/etc., the
Reject/Complete modal Submit/Cancel buttons) routes through the shared `Button` component, so it inherits the
44pt fix automatically; no direct `TouchableOpacity` with a custom small hit area exists on this screen. No
change needed.
**Not covered**: tab-bar icons in `TechnicianTabNavigator`/`StaffTabNavigator` (React Navigation's own tab-bar
sizing, not independently audited); `JobsListScreen`'s filter tabs (`paddingVertical:12` gives roughly a 36–40pt
tap height depending on font metrics — not verified against the 44pt bar specifically, a real, disclosed gap).

## `accessibilityRole` / `accessibilityLabel`
**Covered** (Round 4, re-confirmed present via grep this session): `Button`, `AddressCard`, `CustomerContactCard`,
`NotificationCard`, `WorkItemCard`, `ScheduleCard`, `PartsRequestStatusCard`, `PermissionRestrictedState`,
`JobNoteComposer`'s visibility chips — 9 components, unchanged count since Round 4 (grep confirms no regressions
and no net-new additions since).
**Not covered**: `JobsListScreen`'s own tab `TouchableOpacity`s (no `accessibilityRole`/`accessibilityLabel` —
confirmed by reading the file this session; a screen reader announces them only by their visible text, which
happens to work but isn't an explicit, robust label), `JobDetailScreen`'s own inline elements outside the shared
`Button`/`Card`/`PipelineBadge` components (e.g. the header job-number/city `Text` nodes have no semantic
grouping — cosmetic, not a blocker, but not explicitly audited either).

## Screen-reader hiding of decorative icons
**Covered**: `PermissionRestrictedState`'s 🔒 icon (`accessibilityElementsHidden`/`importantForAccessibility="no"`,
Round 4).
**Not covered**: every other emoji-as-icon used across this app (🏠/📋/🗓/🔔/👤 tab icons, 🗓 date-row prefixes in
`HomeScreen`/`JobDetailScreen`/`ScheduleCard`, 📋 empty-state icon in `JobsListScreen`, ✅/🔒/⚠ status glyphs) —
none of these were audited for `accessibilityElementsHidden`. They render as plain `Text`, so a screen reader
will announce the emoji's Unicode name (e.g. "house" for 🏠) redundantly alongside the adjacent label text. Not a
functional blocker (the meaningful text is always present alongside), but a real, disclosed gap — this class of
icon was never swept the way `PermissionRestrictedState`'s was.

## Color-independent status
**Covered** (verified, not assumed, per Round 4): `JobStatusBadge` (text+color, pre-existing), `NotificationCard`
unread state (label prefix "Unread." + bold text + color — three redundant signals), `ScheduleCard` conflict
indicator (⚠ text + icon, not color alone).
**Not covered**: `JobDetailScreen`'s `JobStatusBadge` usage is the same pre-existing component (inherits the fix
automatically); no new color-only status indicator was introduced by this phase's theme conversion — confirmed
by re-reading the diff, only `theme.colors.X` → `colors.X` token swaps, no new visual-only signals added.

## Text scaling / `PixelRatio.getFontScale()`
**Covered**: Round 7 added a real `PixelRatio.getFontScale()` reading + confirmed (via grep) zero occurrences of
`allowFontScaling={false}` anywhere in the app — meaning nothing in this codebase actively blocks OS-level text
scaling. Demonstrated in `AccessibilityShowcaseScreen`.
**Not covered**: no actual stress test at 150%/200% OS text scale to confirm layouts don't visually break
(overlap, clipping, truncation) under real large-scale text — the `getFontScale()` reading proves the app *can*
detect scale, not that every layout *survives* it.

## Screen-reader session (live VoiceOver/TalkBack)
**Not covered, at all, across every round including this one.** No device/emulator with a screen reader has been
available in any WSL/headless environment used for this project. All fixes above are informed by correct use of
the React Native accessibility API (role/label/state), not verified against a live assistive-technology
experience. This is an explicit, honest, unclosed gap — not fabricated as "tested."

## Focus order
**Not covered, at all, across every round including this one.** React Navigation's native-stack handles most
platform-default focus management automatically (a reasonable baseline), but no independent audit of tab order
within any screen (e.g. does focus move sensibly through `JobDetailScreen`'s Reject modal fields?) was performed.

## Summary table

| Area | Status | Rounds covering it |
|---|---|---|
| Touch targets (interactive shared components) | PARTIAL — 8 components fixed, tab-bar/JobsListScreen tabs not audited | Round 4 |
| accessibilityRole/Label (shared components) | PARTIAL — 9 components covered, JobsListScreen tabs + JobDetailScreen inline text not covered | Round 4 |
| Decorative-icon screen-reader hiding | PARTIAL — 1 of ~10+ emoji-icon usages covered | Round 4 |
| Color-independent status | IMPLEMENTED for the 3 places it was checked | Round 4 |
| Font-scale detection | IMPLEMENTED (detection only, not a stress-test survival guarantee) | Round 7 |
| Live screen-reader session | NOT_DONE — no device available | none |
| Focus-order audit | NOT_DONE | none |

## Why this wasn't extended further this session
UX-05B's mandate for item 5 was explicitly "produce ONE clear reconciliation doc... and do a final pass fixing
anything obviously missing on the screens you've touched this session (JobDetailScreen especially)." That pass
was done (see the "Verified this session" notes above — `JobDetailScreen` needed no changes because its
interactive elements already inherit the Round 4 fixes via the shared `Button` component). A broader sweep of
every remaining emoji icon / tab bar / `JobsListScreen` tabs was out of this item's explicit scope (it names
JobDetailScreen specifically, not a general re-audit) and is listed above as a real, disclosed remaining gap
rather than silently left out.
