# Customer App — Design System

## 1. Visual Principles

Clean white surfaces in light mode, charcoal (not pure black) surfaces in
dark mode, generous whitespace, restrained borders, subtle elevation, clear
grouping, strong typographic hierarchy, calm interaction patterns. No
gradients, no glassmorphism, no permanent decorative animation, no
per-screen ad hoc colors, no duplicated style constants — everything routes
through the token layer in `src/design-system/`.

## 2. Token Model

```
tokens/colors.ts     — primitive scales (neutral, brand, blue, green, amber, red)
tokens/typography.ts — 17 named text styles, platform-safe font family
tokens/spacing.ts    — 0..64 numeric scale, keyed 0-12
tokens/radii.ts      — none..full
tokens/sizes.ts      — touch targets, button/input heights, icon/avatar sizes
tokens/shadows.ts    — buildShadows(color) → { none, sm, md, lg }, platform-aware
tokens/motion.ts     — duration + easing curves
tokens/breakpoints.ts— mobile-specific width classes (compact/regular/large/tablet)
tokens/z-index.ts    — layering scale
themes/light-theme.ts, themes/dark-theme.ts — semantic tokens built from primitives
```

Screens/components never import `tokens/colors.ts` directly for a color
value — always go through `theme.colors.<semanticKey>` via `useAppTheme()`.

## 3. Semantic Colors

All 52 keys required by CUSTOMER-L5-00 §8 are implemented identically in
both themes (verified by `design-system/__tests__/theme-tokens.test.ts`).
Status is always paired with a text label, not conveyed by color alone
(see `AppBadge`, `ErrorState`, `EmptyState`). Disabled text/icon colors
(`textDisabled`, `iconDisabled`) are deliberately lighter-but-still-legible
neutrals, not the background color.

## 4. Typography

17 variants (`displayLarge` → `caption`, plus `numericEmphasis` for
price/booking numbers). Every variant sets `lineHeight` ≥ 1.2× `fontSize` so
large accessibility text does not clip; no component sets a fixed height
around text. Font family falls back to the OS default (`System` /
`sans-serif`) — nothing depends on a custom font being loaded, so there is
no failure mode. `allowFontScaling` is never disabled.

## 5. Spacing, Radii, Sizes

Spacing is a 13-step scale (`0`–`64`, keyed `0`–`12`) consumed as
`theme.spacing[6]` etc. Radii range `none`→`full`. `sizes.touchTargetMin`
(44) is enforced by `AppPressable` by default; `sizes.maxContentWidth`
(640) centers content on tablets via `ScreenContainer`.

## 6. Motion

`duration.instant/fast/standard/slow` + 4 named easing curves. No
looping decorative animation exists anywhere. The one animated primitive
(`Skeleton`) checks `AccessibilityInfo.isReduceMotionEnabled()` and
switches to a static opacity when reduced motion is on.

## 7. Responsive Rules

`tokens/breakpoints.ts` classifies width into `compact/regular/large/tablet`
based on real device widths, not web breakpoints. `ScreenContainer` centers
content at `maxContentWidth` on wide screens and always respects safe areas
and keyboard avoidance.

## 8. Light and Dark Modes

Resolved via `ThemeProvider` (`design-system/themes/theme-provider.tsx`):
preference is `light | dark | system`, persisted through
`preferenceStorage`, defaults to `system`, falls back to `system` if a
corrupted value is read. Dark theme uses charcoal surfaces (`#0B0F16`
family) and a pure-black, low-opacity shadow color (not the light theme's
brand-tinted shadow) specifically to avoid the "glowing grey box" look
called out in the sprint spec.

## 9. Component Usage Examples

```tsx
<ScreenContainer>
  <Stack gap={6}>
    <AppText variant="headingLarge">Book a service</AppText>
    <AppCard variant="elevated">
      <AppText variant="bodyMedium" color="textSecondary">…</AppText>
    </AppCard>
    <AppButton label="Continue" variant="primary" onPress={onContinue} />
  </Stack>
</ScreenContainer>
```

See `design-system/showcase/DesignSystemShowcaseScreen.tsx` (dev-only, via
Settings → "🧪 Design System Showcase (dev)") for every primitive rendered
live in both themes.

## 10. Prohibited Practices

- No inline hex colors, no inline `padding: 16`, no inline `borderRadius: 12`
  in new code — use tokens.
- No second icon library — `AppIcon` wraps `@expo/vector-icons` exclusively.
- No second toast library — `toastService` is the only entry point.
- No screen reads `useColorScheme()` directly — always `useAppTheme()`.
