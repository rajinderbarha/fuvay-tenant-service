/**
 * Component geometry shared by the Fuvay customer experience.
 *
 * Screens consume semantic names from this file instead of carrying a second
 * set of anonymous pixel values.  The values are transcribed from the
 * supplied 390 x 844 reference canvas and scale naturally through flex layout.
 */
export const componentMetrics = {
  screen: {
    referenceWidth: 390,
    referenceHeight: 844,
    horizontalInset: 18,
    authHorizontalInset: 14,
    bottomContentInset: 128,
  },
  ambientGlow: {
    large: 320,
    medium: 260,
  },
  panel: {
    horizontalPadding: 20,
    verticalPadding: 22,
    sheetRadius: 30,
    handleWidth: 40,
    handleHeight: 4,
  },
  tile: {
    compact: 38,
    standard: 46,
    service: 58,
    specialist: 82,
    assistant: 62,
  },
  control: {
    compact: 40,
    standard: 44,
    input: 58,
    primary: 56,
  },
  media: {
    campaign: 176,
    spotlight: 150,
    editorialBanner: 236,
  },
  splash: {
    logoWidth: 216,
    logoAspectRatio: 3.25,
    brandRuleWidth: 46,
    loadingTrackWidth: 120,
    loadingTrackHeight: 2,
  },
} as const;

