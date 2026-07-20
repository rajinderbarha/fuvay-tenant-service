import { neutral, brand, blue, green, amber, red } from "../tokens/colors";
import { typography } from "../tokens/typography";
import { spacing } from "../tokens/spacing";
import { radii } from "../tokens/radii";
import { sizes } from "../tokens/sizes";
import { buildShadows } from "../tokens/shadows";
import type { AppTheme, SemanticColors } from "./theme-types";

// Charcoal surfaces, not pure black — avoids OLED smearing and keeps elevation readable.
const charcoal900 = "#0B0F16";
const charcoal800 = "#121826";
const charcoal700 = "#1B2333";
const charcoal600 = "#2A3346";

const colors: SemanticColors = {
  backgroundPrimary: charcoal900,
  backgroundSecondary: charcoal800,
  backgroundTertiary: charcoal700,
  backgroundElevated: charcoal700,
  backgroundInverse: neutral[0],
  backgroundDisabled: charcoal700,

  surfacePrimary: charcoal800,
  surfaceSecondary: charcoal700,
  surfaceSelected: "#1E3350",
  surfacePressed: charcoal600,
  surfaceHover: charcoal600,
  surfaceOverlay: "rgba(0, 0, 0, 0.6)",

  textPrimary: neutral[50],
  textSecondary: neutral[300],
  textTertiary: neutral[500],
  textInverse: neutral[900],
  textDisabled: neutral[600],
  textLink: blue[300],
  textSuccess: green[300],
  textWarning: amber[300],
  textDanger: red[300],

  borderSubtle: charcoal600,
  borderDefault: "#37415A",
  borderStrong: "#4C5977",
  borderFocus: brand[300],
  borderSuccess: green[600],
  borderWarning: amber[600],
  borderDanger: red[600],

  iconPrimary: neutral[200],
  iconSecondary: neutral[400],
  iconInverse: neutral[900],
  iconDisabled: neutral[600],
  iconSuccess: green[300],
  iconWarning: amber[300],
  iconDanger: red[300],

  actionPrimary: brand[400],
  actionPrimaryPressed: brand[300],
  actionPrimaryDisabled: charcoal600,
  actionSecondary: charcoal700,
  actionSecondaryPressed: charcoal600,
  actionDestructive: red[500],
  actionDestructivePressed: red[600],

  statusSuccessBackground: "#0F2A1B",
  statusSuccessForeground: green[300],
  statusWarningBackground: "#332209",
  statusWarningForeground: amber[300],
  statusDangerBackground: "#331313",
  statusDangerForeground: red[300],
  statusInfoBackground: "#0C2536",
  statusInfoForeground: blue[300],

  skeletonBase: charcoal700,
  skeletonHighlight: charcoal600,
  scrim: "rgba(0, 0, 0, 0.7)",
  focusRing: brand[300],
};

export const darkTheme: AppTheme = {
  mode: "dark",
  colors,
  typography,
  spacing,
  radii,
  sizes,
  // Pure black, low opacity — avoids the "glowing grey box" look of reusing
  // the brand-tinted light-theme shadow color on dark surfaces.
  shadows: buildShadows("#000000"),
};
