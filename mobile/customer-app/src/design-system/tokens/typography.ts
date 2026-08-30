import { TextStyle } from "react-native";

import { fuvayFontFamily } from "./fonts";

/** Font weights as RN-valid string literals (not numbers) so TextStyle
 * accepts them directly.
 *
 * These stay for callers that set weight themselves, but note the caveat in
 * ./fonts.ts: with custom TTFs, WEIGHT COMES FROM THE FAMILY NAME, not from
 * fontWeight. The scale below therefore pairs each style with the correctly
 * weighted Barlow family rather than relying on synthetic bolding. */
const weight = {
  regular: "400" as const,
  medium: "500" as const,
  semibold: "600" as const,
  bold: "700" as const,
  extrabold: "800" as const,
};

/**
 * Semantic type scale — Fuvay v2.
 *
 * Sizes are taken from the v2 canvas, which runs noticeably tighter than the
 * previous scale: section headings are 17px, card titles 14.5px, metadata
 * 9-11px. Fractional sizes from the design are kept rather than rounded, as
 * RN accepts them and rounding visibly changes the density the design
 * depends on.
 *
 * v2 leans on SEMIBOLD (600), not bold/extrabold — the canvas uses 600 for
 * every heading and title. Weight arrives via the Barlow family name.
 *
 * `fontVariant: ["tabular-nums"]` is applied to the numeric styles so
 * money/time columns align.
 */
export const typography: Record<string, TextStyle> = {
  displayLarge: {
    fontSize: 36,
    lineHeight: 37,
    letterSpacing: -0.9,
    fontFamily: fuvayFontFamily.semibold,
    fontWeight: weight.semibold,
  },
  displayMedium: {
    fontSize: 26,
    lineHeight: 28,
    letterSpacing: -0.39,
    fontFamily: fuvayFontFamily.semibold,
    fontWeight: weight.semibold,
  },
  headingLarge: {
    fontSize: 24,
    lineHeight: 26,
    letterSpacing: -0.36,
    fontFamily: fuvayFontFamily.semibold,
    fontWeight: weight.semibold,
  },
  headingMedium: {
    fontSize: 20,
    lineHeight: 22,
    letterSpacing: -0.2,
    fontFamily: fuvayFontFamily.semibold,
    fontWeight: weight.semibold,
  },
  headingSmall: {
    fontSize: 17,
    lineHeight: 21,
    fontFamily: fuvayFontFamily.semibold,
    fontWeight: weight.semibold,
  },
  title: {
    fontSize: 14.5,
    lineHeight: 18,
    fontFamily: fuvayFontFamily.semibold,
    fontWeight: weight.semibold,
  },
  body: {
    fontSize: 13,
    lineHeight: 19,
    fontFamily: fuvayFontFamily.regular,
    fontWeight: weight.regular,
  },
  bodyStrong: {
    fontSize: 13,
    lineHeight: 19,
    fontFamily: fuvayFontFamily.semibold,
    fontWeight: weight.semibold,
  },
  bodySmall: {
    fontSize: 11.5,
    lineHeight: 17,
    fontFamily: fuvayFontFamily.regular,
    fontWeight: weight.regular,
  },
  label: {
    fontSize: 11,
    lineHeight: 15,
    fontFamily: fuvayFontFamily.medium,
    fontWeight: weight.medium,
  },
  labelStrong: {
    fontSize: 11,
    lineHeight: 15,
    fontFamily: fuvayFontFamily.semibold,
    fontWeight: weight.semibold,
  },
  caption: {
    fontSize: 10.5,
    lineHeight: 14,
    fontFamily: fuvayFontFamily.regular,
    fontWeight: weight.regular,
  },
  numericLarge: {
    fontSize: 22,
    lineHeight: 24,
    fontFamily: fuvayFontFamily.semibold,
    fontWeight: weight.semibold,
    fontVariant: ["tabular-nums"],
  },
  numericMedium: {
    fontSize: 14,
    lineHeight: 20,
    fontFamily: fuvayFontFamily.semibold,
    fontWeight: weight.semibold,
    fontVariant: ["tabular-nums"],
  },
  button: {
    fontSize: 12.5,
    lineHeight: 17,
    fontFamily: fuvayFontFamily.semibold,
    fontWeight: weight.semibold,
  },

  /**
   * v2's signature metadata style: uppercase JetBrains Mono with wide
   * tracking ("NEXT VISIT", "LIMITED OFFER", "STEP 1 OF 5").
   *
   * Reserved for short uppercase labels — never body copy. Callers should
   * pass already-uppercased text rather than relying on textTransform, so
   * screen readers announce the words normally.
   */
  metaLabel: {
    fontSize: 9.5,
    lineHeight: 13,
    letterSpacing: 1.4,
    fontFamily: fuvayFontFamily.mono,
    fontWeight: weight.regular,
  },
  metaLabelWide: {
    fontSize: 9,
    lineHeight: 12,
    letterSpacing: 2.0,
    fontFamily: fuvayFontFamily.mono,
    fontWeight: weight.regular,
  },
};

export type TypographyToken = keyof typeof typography;
export { weight as fontWeight };
