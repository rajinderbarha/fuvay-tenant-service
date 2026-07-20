import type { TypographyStyle } from "../tokens/typography";
import type { ShadowScale } from "../tokens/shadows";
import type { sizes as appSizes } from "../tokens/sizes";

export type ThemeMode = "light" | "dark";
export type ThemePreference = "light" | "dark" | "system";

export interface SemanticColors {
  backgroundPrimary: string;
  backgroundSecondary: string;
  backgroundTertiary: string;
  backgroundElevated: string;
  backgroundInverse: string;
  backgroundDisabled: string;

  surfacePrimary: string;
  surfaceSecondary: string;
  surfaceSelected: string;
  surfacePressed: string;
  surfaceHover: string;
  surfaceOverlay: string;

  textPrimary: string;
  textSecondary: string;
  textTertiary: string;
  textInverse: string;
  textDisabled: string;
  textLink: string;
  textSuccess: string;
  textWarning: string;
  textDanger: string;

  borderSubtle: string;
  borderDefault: string;
  borderStrong: string;
  borderFocus: string;
  borderSuccess: string;
  borderWarning: string;
  borderDanger: string;

  iconPrimary: string;
  iconSecondary: string;
  iconInverse: string;
  iconDisabled: string;
  iconSuccess: string;
  iconWarning: string;
  iconDanger: string;

  actionPrimary: string;
  actionPrimaryPressed: string;
  actionPrimaryDisabled: string;
  actionSecondary: string;
  actionSecondaryPressed: string;
  actionDestructive: string;
  actionDestructivePressed: string;

  statusSuccessBackground: string;
  statusSuccessForeground: string;
  statusWarningBackground: string;
  statusWarningForeground: string;
  statusDangerBackground: string;
  statusDangerForeground: string;
  statusInfoBackground: string;
  statusInfoForeground: string;

  skeletonBase: string;
  skeletonHighlight: string;
  scrim: string;
  focusRing: string;
}

export interface AppTheme {
  mode: ThemeMode;
  colors: SemanticColors;
  typography: Record<string, TypographyStyle>;
  spacing: Record<number, number>;
  radii: Record<string, number>;
  sizes: typeof appSizes;
  shadows: ShadowScale;
}

export const REQUIRED_SEMANTIC_COLOR_KEYS: (keyof SemanticColors)[] = [
  "backgroundPrimary",
  "backgroundSecondary",
  "backgroundTertiary",
  "backgroundElevated",
  "backgroundInverse",
  "backgroundDisabled",
  "surfacePrimary",
  "surfaceSecondary",
  "surfaceSelected",
  "surfacePressed",
  "surfaceHover",
  "surfaceOverlay",
  "textPrimary",
  "textSecondary",
  "textTertiary",
  "textInverse",
  "textDisabled",
  "textLink",
  "textSuccess",
  "textWarning",
  "textDanger",
  "borderSubtle",
  "borderDefault",
  "borderStrong",
  "borderFocus",
  "borderSuccess",
  "borderWarning",
  "borderDanger",
  "iconPrimary",
  "iconSecondary",
  "iconInverse",
  "iconDisabled",
  "iconSuccess",
  "iconWarning",
  "iconDanger",
  "actionPrimary",
  "actionPrimaryPressed",
  "actionPrimaryDisabled",
  "actionSecondary",
  "actionSecondaryPressed",
  "actionDestructive",
  "actionDestructivePressed",
  "statusSuccessBackground",
  "statusSuccessForeground",
  "statusWarningBackground",
  "statusWarningForeground",
  "statusDangerBackground",
  "statusDangerForeground",
  "statusInfoBackground",
  "statusInfoForeground",
  "skeletonBase",
  "skeletonHighlight",
  "scrim",
  "focusRing",
];
