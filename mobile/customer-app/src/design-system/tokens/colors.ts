/**
 * Semantic color tokens only. No screen or component may use a literal hex
 * value -- every color a screen needs must resolve through these tokens (or
 * the theme built from them in ../theme).
 *
 * ── Fuvay v2 ──────────────────────────────────────────────────────────────
 * Every value below now resolves to the Fuvay v2 design language defined in
 * ./fuvay.ts (the "Fuvay App Screens" canvas). This file is the bridge: it
 * keeps the semantic names ~200 files already import, while the actual
 * colours come from the v2 palette. That is what makes the redesign reach
 * all 57 screens rather than only the four the canvas draws -- a screen that
 * asks for `surfaceDefault` gets the v2 card colour without being touched.
 *
 * Two consequences worth knowing:
 *
 * 1. `brandPrimary` is v2's **a2 (teal)**. The canvas uses a2 for every
 *    primary action -- the active nav pill, "Send code", "Ask AI" -- so it
 *    is the honest mapping for the single-brand-colour token. The other
 *    three accents (a1 amber / a3 green / a4 violet) are exposed through
 *    `accentAmber` / `accentMint` / `accentViolet`, and directly via
 *    ./fuvay.ts for screens that rotate accents per card.
 *
 * 2. `brandOnPrimary` is theme-dependent. The dark-mode teal is light enough
 *    that WCAG-correct foreground on it is near-black rather than white.
 *    This is `ink()` in ./fuvay.ts doing its job; a filled button in
 *    dark mode legitimately gets dark text. Hardcoding white there would
 *    fail contrast.
 */
import {
  darkAccents,
  darkSurfaces,
  ink,
  lightAccents,
  lightSurfaces,
  softAccent,
} from "./fuvay";

export interface ColorTokens {
  brandPrimary: string;
  brandPrimaryPressed: string;
  brandPrimaryMuted: string;
  brandOnPrimary: string;
  /**
   * The brand colour for TEXT and ICONS sitting on a normal page surface.
   *
   * Needed because one hex cannot do both jobs: v2's dark-mode teal is a
   * light tint that fills a shape well but is used as-is for text on dark
   * surfaces, while the light theme needs a darker teal to stay legible
   * on pale ones.
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

  /** Campaign / promo banner surfaces. v2 draws these as photography with a
   *  scrim plus an amber hex badge, so the accent is a1 and the badge
   *  foreground is computed from it. */
  campaignBackground: string;
  campaignGradientStart: string;
  campaignGradientEnd: string;
  campaignAccent: string;
  campaignBadgeForeground: string;
  campaignBadgeSurface: string;
  campaignScrim: string;
  campaignBadgeScrim: string;

  /** Content placed on photography. This deliberately does not invert in
   * dark mode: campaign artwork always needs a stable white foreground and
   * a predictable scrim, regardless of the page theme or image palette. */
  mediaForeground: string;
  mediaForegroundMuted: string;
  mediaScrim: string;
  mediaScrimStrong: string;

  /** Product accents are intentionally plural -- in v2 they are the a1-a4
   * rotation itself. The permanent shell stays neutral while service glyphs,
   * campaigns and editorial modules carry their own colour. */
  accentCyan: string;
  accentMint: string;
  accentCoral: string;
  accentAmber: string;
  accentViolet: string;
  accentVioletSurface: string;

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

const L = lightAccents;
const LS = lightSurfaces;
const D = darkAccents;
const DS = darkSurfaces;

/**
 * Danger has no accent in the v2 canvas -- a1-a4 are amber/teal/green/violet
 * and none of them may signal destruction. These are the one addition, hue-
 * matched to the palette's saturation and verified for AA in the tests.
 */
const LIGHT_DANGER = "#b3261e";
const DARK_DANGER = "#f2827a";

export const lightColors: ColorTokens = {
  brandPrimary: L.a2,
  brandPrimaryPressed: "#0b574e",
  brandPrimaryMuted: softAccent(L.a2, false),
  brandOnPrimary: ink(L.a2),
  brandPrimaryStrong: L.a2,

  // The v2 shell is the page ground; panel and card stack above it. Keeping
  // three distinct steps matters -- a previous regression made chat bubbles
  // invisible when surface and background were within ~1.5% luminance.
  backgroundPrimary: LS.shell,
  backgroundSecondary: LS.panel,
  backgroundElevated: LS.panel,
  backgroundSunken: "#f6f4f0",
  backgroundOverlay: "rgba(20, 20, 26, 0.45)",

  // v2 has two card-ish surfaces with distinct jobs: `panel` is the raised
  // content card (booking card, recommendation row), `card` is the RECESSED
  // input surface (search field, AI prompt rows). surfaceDefault is the
  // former -- mapping it to `card` put dark-mode bubbles only 3.07 luminance
  // from the background and tripped the chat-legibility guard below.
  surfaceDefault: LS.panel,
  surfaceSecondary: LS.card,
  surfaceRaised: LS.card,
  surfaceInteractive: softAccent(L.a2, false),
  surfaceSelected: softAccent(L.a2, false),
  surfaceDisabled: "#f0eee9",

  textPrimary: LS.text,
  textSecondary: LS.sub,
  textTertiary: LS.faint,
  textDisabled: "rgba(60,52,44,0.38)",
  textInverse: "#ffffff",
  textLink: L.a2,

  borderSubtle: LS.edge,
  borderDefault: LS.rule,
  borderStrong: "#ddd8d0",
  borderFocus: L.a2,
  borderDisabled: LS.edge,
  divider: LS.rule,

  iconDefault: LS.faint,
  bottomNavigation: LS.card,

  campaignBackground: softAccent(L.a1, false),
  campaignGradientStart: softAccent(L.a1, false),
  campaignGradientEnd: LS.panel,
  // The hex "₹500 OFF" badge is fixed amber in both themes in the canvas.
  campaignAccent: LS.hexFill,
  campaignBadgeForeground: ink(LS.hexFill),
  campaignBadgeSurface: "rgba(20,20,26,0.12)",
  campaignScrim: "rgba(10, 8, 14, 0.55)",
  campaignBadgeScrim: "rgba(10, 8, 14, 0.92)",

  mediaForeground: "#ffffff",
  mediaForegroundMuted: "rgba(255,255,255,0.72)",
  mediaScrim: "rgba(10, 8, 14, 0.30)",
  mediaScrimStrong: "rgba(10, 8, 14, 0.66)",

  accentCyan: L.a2,
  accentMint: L.a3,
  accentCoral: LIGHT_DANGER,
  accentAmber: L.a1,
  accentViolet: L.a4,
  accentVioletSurface: softAccent(L.a4, false),

  statusSuccess: L.a3,
  statusSuccessSurface: softAccent(L.a3, false),
  statusWarning: L.a1,
  statusWarningSurface: softAccent(L.a1, false),
  statusDanger: LIGHT_DANGER,
  statusDangerSurface: softAccent(LIGHT_DANGER, false),
  statusInfo: L.a2,
  statusInfoSurface: softAccent(L.a2, false),
  statusNeutral: LS.faint,
  statusNeutralSurface: "#f0eee9",

  statusBarStyle: "dark",
};

export const darkColors: ColorTokens = {
  brandPrimary: D.a2,
  brandPrimaryPressed: "#267f73",
  brandPrimaryMuted: softAccent(D.a2, true),
  // The brighter dark-theme teal needs near-black foreground for contrast.
  brandOnPrimary: ink(D.a2),
  brandPrimaryStrong: D.a2,

  backgroundPrimary: DS.shell,
  backgroundSecondary: DS.panel,
  backgroundElevated: DS.panel,
  backgroundSunken: "#141413",
  backgroundOverlay: "rgba(0, 0, 0, 0.6)",

  // See the light-theme note: `panel` is the raised card, `card` the
  // recessed input surface.
  surfaceDefault: DS.panel,
  surfaceSecondary: DS.card,
  surfaceRaised: DS.hexPanel,
  surfaceInteractive: softAccent(D.a2, true),
  surfaceSelected: softAccent(D.a2, true),
  surfaceDisabled: "#262622",

  textPrimary: DS.text,
  textSecondary: DS.sub,
  textTertiary: DS.faint,
  textDisabled: "rgba(255,255,255,0.38)",
  textInverse: "#14141a",
  textLink: D.a2,

  borderSubtle: DS.edge,
  borderDefault: DS.rule,
  borderStrong: "#33322c",
  borderFocus: D.a2,
  borderDisabled: DS.edge,
  divider: DS.rule,

  iconDefault: DS.faint,
  bottomNavigation: DS.card,

  campaignBackground: softAccent(D.a1, true),
  campaignGradientStart: softAccent(D.a1, true),
  campaignGradientEnd: DS.panel,
  campaignAccent: DS.hexFill,
  campaignBadgeForeground: ink(DS.hexFill),
  campaignBadgeSurface: "rgba(20,20,26,0.12)",
  campaignScrim: "rgba(10, 8, 14, 0.55)",
  campaignBadgeScrim: "rgba(10, 8, 14, 0.92)",

  mediaForeground: "#ffffff",
  mediaForegroundMuted: "rgba(255,255,255,0.72)",
  mediaScrim: "rgba(10, 8, 14, 0.34)",
  mediaScrimStrong: "rgba(10, 8, 14, 0.70)",

  accentCyan: D.a2,
  accentMint: D.a3,
  accentCoral: DARK_DANGER,
  accentAmber: D.a1,
  accentViolet: D.a4,
  accentVioletSurface: softAccent(D.a4, true),

  statusSuccess: D.a3,
  statusSuccessSurface: softAccent(D.a3, true),
  statusWarning: D.a1,
  statusWarningSurface: softAccent(D.a1, true),
  statusDanger: DARK_DANGER,
  statusDangerSurface: softAccent(DARK_DANGER, true),
  statusInfo: D.a2,
  statusInfoSurface: softAccent(D.a2, true),
  statusNeutral: DS.faint,
  statusNeutralSurface: "#262622",

  statusBarStyle: "light",
};
