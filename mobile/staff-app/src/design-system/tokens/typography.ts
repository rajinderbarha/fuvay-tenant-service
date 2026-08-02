import { TextStyle } from "react-native";

/** Font weights as RN-valid string literals (not numbers) so TextStyle
 * accepts them directly. */
const weight = {
  regular: "400" as const,
  medium: "500" as const,
  semibold: "600" as const,
  bold: "700" as const,
  extrabold: "800" as const,
};

/** Semantic type scale. `fontVariant: ["tabular-nums"]` is applied to the
 * numeric styles so money/time/job-number columns align -- never apply a
 * decorative font to operational data (job numbers, amounts, timestamps). */
export const typography: Record<string, TextStyle> = {
  displayLarge:  { fontSize: 32, lineHeight: 40, fontWeight: weight.extrabold },
  displayMedium: { fontSize: 28, lineHeight: 36, fontWeight: weight.extrabold },
  headingLarge:  { fontSize: 24, lineHeight: 32, fontWeight: weight.bold },
  headingMedium: { fontSize: 20, lineHeight: 28, fontWeight: weight.bold },
  headingSmall:  { fontSize: 18, lineHeight: 24, fontWeight: weight.bold },
  title:         { fontSize: 16, lineHeight: 22, fontWeight: weight.semibold },
  body:          { fontSize: 15, lineHeight: 22, fontWeight: weight.regular },
  bodyStrong:    { fontSize: 15, lineHeight: 22, fontWeight: weight.semibold },
  bodySmall:     { fontSize: 13, lineHeight: 18, fontWeight: weight.regular },
  label:         { fontSize: 12, lineHeight: 16, fontWeight: weight.medium },
  labelStrong:   { fontSize: 12, lineHeight: 16, fontWeight: weight.bold },
  caption:       { fontSize: 11, lineHeight: 14, fontWeight: weight.regular },
  numericLarge:  { fontSize: 24, lineHeight: 30, fontWeight: weight.bold,     fontVariant: ["tabular-nums"] },
  numericMedium: { fontSize: 16, lineHeight: 22, fontWeight: weight.semibold, fontVariant: ["tabular-nums"] },
  button:        { fontSize: 15, lineHeight: 20, fontWeight: weight.semibold },
};

export type TypographyToken = keyof typeof typography;
export { weight as fontWeight };
