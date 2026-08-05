/**
 * Semantic color tokens only. No screen or component may use a literal hex
 * value -- every color a screen needs must resolve through these tokens (or
 * the theme built from them in ../theme).
 *
 * CONFLICT NOTE (Home-screen redesign phase): these values were replaced
 * with a new "approved brand tokens" spec for the Home screen redesign
 * (#FF641A primary, new surface/campaign tokens) that DIFFERS from the
 * palette mirrored from mobile/staff-app in earlier phases (#D9642B
 * primary). This is a real, reportable divergence from the "identical
 * visual DNA as Staff App" instruction established in Phase A-C/E -- see
 * the delivery report. The new tokens are applied here because this
 * phase's brief explicitly labels them "APPROVED," superseding the
 * earlier mirrored value for this app; Staff App itself was NOT touched
 * and still uses #D9642B, so the two apps are now visually divergent
 * pending an explicit design-system reconciliation decision.
 */
export interface ColorTokens {
  brandPrimary: string;
  brandPrimaryPressed: string;
  brandPrimaryMuted: string;
  brandOnPrimary: string;
  /**
   * The brand colour for TEXT and ICONS sitting on a normal page surface.
   *
   * Needed because one hex cannot do both jobs in light mode: the warm
   * yellow brand fill (#F2994A) only reaches 2.06:1 against the light
   * background, so using it for a label or icon would be unreadable. This
   * is the same hue (28deg) darkened until it passes WCAG AA for body
   * text, so the brand still reads as warm yellow without sacrificing
   * legibility. In dark mode the fill colour is already legible against
   * dark surfaces, so both tokens are the same value there.
   *
   * Rule of thumb: `brandPrimary` fills a shape, `brandPrimaryStrong`
   * draws on top of the page, `brandOnPrimary` draws on top of a fill.
   */
  brandPrimaryStrong: string;

  backgroundPrimary: string;
  backgroundSecondary: string;
  backgroundElevated: string;
  backgroundSunken: string;
  backgroundOverlay: string;

  surfaceDefault: string;
  surfaceSecondary: string;
  surfaceRaised: string;
  surfaceInteractive: string;
  surfaceSelected: string;
  surfaceDisabled: string;

  textPrimary: string;
  textSecondary: string;
  textTertiary: string;
  textDisabled: string;
  textInverse: string;
  textLink: string;

  borderSubtle: string;
  borderDefault: string;
  borderStrong: string;
  borderFocus: string;
  borderDisabled: string;
  divider: string;

  iconDefault: string;
  bottomNavigation: string;

  /** Solid campaign-banner background (light theme uses a single flat
   * tint per the approved design; dark theme uses campaignGradientStart/
   * End instead -- see buildTheme.ts campaignGradient helper). */
  campaignBackground: string;
  campaignGradientStart: string;
  campaignGradientEnd: string;

  statusSuccess: string;
  statusSuccessSurface: string;
  statusWarning: string;
  statusWarningSurface: string;
  statusDanger: string;
  statusDangerSurface: string;
  statusInfo: string;
  statusInfoSurface: string;
  statusNeutral: string;
  statusNeutralSurface: string;

  statusBarStyle: "dark" | "light";
}

// Aligned to the Staff app's palette (mobile/staff-app/src/design-system/
// tokens/colors.ts) so both apps read as one product family. This also
// fixed a real, user-visible chat defect: the customer app's
// `surfaceInteractive` was #FBFAF8 against a #F7F6F4 background -- a ~1.5%
// luminance step, so assistant chat bubbles were effectively invisible
// against the conversation background. The staff ramp has a genuine,
// legible step between background/surface/border at every level.
// Blue palette — per the 2026-08-04 project rebrand (warm orange -> blue),
// matching frontend/customer-app, frontend/super-admin and
// frontend/tenant-portal's globals.css exactly. `brandOnPrimary` stays
// white -- blue has enough luminance contrast for white text/icons on a
// filled button, unlike the previous yellow which needed dark ink.
export const lightColors: ColorTokens = {
  brandPrimary: "#3868E0",
  brandPrimaryPressed: "#2F5BD1",
  brandPrimaryMuted: "#EEF3FF",
  brandOnPrimary: "#FFFFFF",
  brandPrimaryStrong: "#2F5BD1",

  // Deliberately NOT pure white -- surfaceDefault (cards, chat bubbles) IS
  // pure white, so it must sit on something else or it's invisible (the
  // exact chat-legibility regression this token set already fixed once).
  backgroundPrimary: "#F5F8FD",
  backgroundSecondary: "#F1F5FB",
  backgroundElevated: "#FFFFFF",
  backgroundSunken: "#EAEFF8",
  backgroundOverlay: "rgba(15, 23, 42, 0.45)",

  surfaceDefault: "#FFFFFF",
  surfaceSecondary: "#F1F5FB",
  surfaceRaised: "#FFFFFF",
  surfaceInteractive: "#EEF3FF",
  surfaceSelected: "#EEF3FF",
  surfaceDisabled: "#EAEFF8",

  textPrimary: "#0F172A",
  textSecondary: "#475569",
  textTertiary: "#94A3B8",
  textDisabled: "#CBD3E1",
  textInverse: "#FFFFFF",
  textLink: "#2F5BD1",

  borderSubtle: "#E7EBF3",
  borderDefault: "#CBD3E1",
  borderStrong: "#94A3B8",
  borderFocus: "#3B6FED",
  borderDisabled: "#E7EBF3",
  divider: "#E7EBF3",

  iconDefault: "#475569",
  bottomNavigation: "#FFFFFF",

  campaignBackground: "#EEF3FF",
  campaignGradientStart: "#EEF3FF",
  campaignGradientEnd: "#EEF3FF",

  statusSuccess: "#1E8E5A",
  statusSuccessSurface: "#E6F5EC",
  statusWarning: "#B5750B",
  statusWarningSurface: "#FCF0DC",
  statusDanger: "#C4342A",
  statusDangerSurface: "#FBE8E6",
  statusInfo: "#1E6FB8",
  statusInfoSurface: "#E6F0FA",
  statusNeutral: "#475569",
  statusNeutralSurface: "#EAEFF8",

  statusBarStyle: "dark",
};

// Tesla-app reference: neutral charcoal-black layered surfaces (never pure
// black everywhere), off-white (not pure-white) primary text, electric-blue
// brand accent.
export const darkColors: ColorTokens = {
  brandPrimary: "#1A6FE0",
  brandPrimaryPressed: "#1558B8",
  brandPrimaryMuted: "#1A3A5C",
  brandOnPrimary: "#FFFFFF",
  // On dark surfaces the fill colour is already legible as a foreground
  // (#2B8FFF on #1C1C1E is well over 4.5:1), so no separate shade is needed.
  brandPrimaryStrong: "#5AB0FF",

  backgroundPrimary: "#1C1C1E",
  backgroundSecondary: "#202024",
  backgroundElevated: "#232326",
  backgroundSunken: "#161618",
  backgroundOverlay: "rgba(0, 0, 0, 0.6)",

  surfaceDefault: "#232326",
  surfaceSecondary: "#202024",
  surfaceRaised: "#2C2C30",
  surfaceInteractive: "#2C2C30",
  surfaceSelected: "#1A3A5C",
  surfaceDisabled: "#202024",

  textPrimary: "#F5F5F7",
  textSecondary: "#9B9BA1",
  textTertiary: "#6E6E73",
  textDisabled: "#44444A",
  textInverse: "#1C1C1E",
  textLink: "#5AB0FF",

  borderSubtle: "#2C2C30",
  borderDefault: "#333338",
  borderStrong: "#44444A",
  borderFocus: "#2B8FFF",
  borderDisabled: "#2C2C30",
  divider: "#2C2C30",

  iconDefault: "#9B9BA1",
  bottomNavigation: "#232326",

  campaignBackground: "#1A3A5C",
  campaignGradientStart: "#1A3A5C",
  campaignGradientEnd: "#202024",

  statusSuccess: "#4ADE80",
  statusSuccessSurface: "#16301F",
  statusWarning: "#FBBF24",
  statusWarningSurface: "#3A2E0E",
  statusDanger: "#F87171",
  statusDangerSurface: "#3A1614",
  statusInfo: "#60A5E8",
  statusInfoSurface: "#122C3E",
  statusNeutral: "#9B9BA1",
  statusNeutralSurface: "#2C2C30",

  statusBarStyle: "light",
};
