import { neutral, brand, blue, green, amber, red } from "../tokens/colors";
import { typography } from "../tokens/typography";
import { spacing } from "../tokens/spacing";
import { radii } from "../tokens/radii";
import { sizes } from "../tokens/sizes";
import { buildShadows } from "../tokens/shadows";
import type { AppTheme, SemanticColors } from "./theme-types";

const colors: SemanticColors = {
  backgroundPrimary: neutral[0],
  backgroundSecondary: "#F8FAFF",
  backgroundTertiary: neutral[100],
  backgroundElevated: neutral[0],
  backgroundInverse: brand[600],
  backgroundDisabled: neutral[100],

  surfacePrimary: neutral[0],
  surfaceSecondary: neutral[50],
  surfaceSelected: brand[50],
  surfacePressed: neutral[100],
  surfaceHover: neutral[50],
  surfaceOverlay: "rgba(15, 23, 42, 0.5)",

  textPrimary: neutral[900],
  textSecondary: neutral[600],
  textTertiary: neutral[400],
  textInverse: neutral[0],
  textDisabled: neutral[300],
  textLink: blue[700],
  textSuccess: green[600],
  textWarning: amber[600],
  textDanger: red[600],

  borderSubtle: neutral[200],
  borderDefault: neutral[300],
  borderStrong: neutral[400],
  borderFocus: brand[400],
  borderSuccess: green[300],
  borderWarning: amber[300],
  borderDanger: red[300],

  iconPrimary: neutral[700],
  iconSecondary: neutral[500],
  iconInverse: neutral[0],
  iconDisabled: neutral[300],
  iconSuccess: green[600],
  iconWarning: amber[600],
  iconDanger: red[600],

  actionPrimary: brand[600],
  actionPrimaryPressed: brand[700],
  actionPrimaryDisabled: neutral[200],
  actionSecondary: neutral[0],
  actionSecondaryPressed: neutral[100],
  actionDestructive: red[500],
  actionDestructivePressed: red[600],

  statusSuccessBackground: green[50],
  statusSuccessForeground: green[700],
  statusWarningBackground: amber[50],
  statusWarningForeground: amber[700],
  statusDangerBackground: red[50],
  statusDangerForeground: red[700],
  statusInfoBackground: blue[50],
  statusInfoForeground: blue[700],

  skeletonBase: neutral[200],
  skeletonHighlight: neutral[100],
  scrim: "rgba(15, 23, 42, 0.5)",
  focusRing: brand[400],
};

export const lightTheme: AppTheme = {
  mode: "light",
  colors,
  typography,
  spacing,
  radii,
  sizes,
  shadows: buildShadows(brand[600]),
};
