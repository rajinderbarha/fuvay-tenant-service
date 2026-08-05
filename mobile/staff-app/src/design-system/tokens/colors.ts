/**
 * Semantic color tokens only. No screen or component may use a literal hex
 * value -- every color a screen needs must resolve through these tokens (or
 * the theme built from them in ../themes). Two palettes share this exact
 * key set so ThemeProvider can switch between them without any consumer
 * caring which one is active.
 */
export interface ColorTokens {
  // Brand
  brandPrimary: string;
  brandPrimaryPressed: string;
  brandPrimaryMuted: string;
  brandOnPrimary: string;

  // Background
  backgroundPrimary: string;
  backgroundSecondary: string;
  backgroundElevated: string;
  backgroundSunken: string;
  backgroundOverlay: string;

  // Surface
  surfaceDefault: string;
  surfaceRaised: string;
  surfaceInteractive: string;
  surfaceSelected: string;
  surfaceDisabled: string;

  // Text
  textPrimary: string;
  textSecondary: string;
  textTertiary: string;
  textDisabled: string;
  textInverse: string;
  textLink: string;

  // Border
  borderSubtle: string;
  borderDefault: string;
  borderStrong: string;
  borderFocus: string;
  borderDisabled: string;

  // Status
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

  // Workflow
  workflowCompleted: string;
  workflowCurrent: string;
  workflowUpcoming: string;
  workflowBlocked: string;
  workflowCancelled: string;

  // Chrome
  statusBarStyle: "dark" | "light";
}

// Blue palette (2026-08-04 rebrand, matching frontend/super-admin,
// frontend/tenant-portal, frontend/customer-app and mobile/customer-app):
// off-white background, never pure white everywhere.
export const lightColors: ColorTokens = {
  brandPrimary: "#3868E0",
  brandPrimaryPressed: "#2F5BD1",
  brandPrimaryMuted: "#EEF3FF",
  brandOnPrimary: "#FFFFFF",

  backgroundPrimary: "#F5F8FD",
  backgroundSecondary: "#F1F5FB",
  backgroundElevated: "#FFFFFF",
  backgroundSunken: "#EAEFF8",
  backgroundOverlay: "rgba(15, 23, 42, 0.45)",

  surfaceDefault: "#FFFFFF",
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
  borderFocus: "#3868E0",
  borderDisabled: "#E7EBF3",

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

  workflowCompleted: "#1E8E5A",
  workflowCurrent: "#3868E0",
  workflowUpcoming: "#94A3B8",
  workflowBlocked: "#C4342A",
  workflowCancelled: "#CBD3E1",

  statusBarStyle: "dark",
};

// Tesla-app reference dark mode: neutral charcoal-black layered surfaces
// (never pure black everywhere), off-white (not pure-white) primary text,
// electric-blue brand accent.
export const darkColors: ColorTokens = {
  brandPrimary: "#1A6FE0",
  brandPrimaryPressed: "#1558B8",
  brandPrimaryMuted: "#1A3A5C",
  brandOnPrimary: "#FFFFFF",

  backgroundPrimary: "#1C1C1E",
  backgroundSecondary: "#202024",
  backgroundElevated: "#232326",
  backgroundSunken: "#161618",
  backgroundOverlay: "rgba(0, 0, 0, 0.6)",

  surfaceDefault: "#232326",
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
  borderFocus: "#1A6FE0",
  borderDisabled: "#2C2C30",

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

  workflowCompleted: "#4ADE80",
  workflowCurrent: "#5AB0FF",
  workflowUpcoming: "#6E6E73",
  workflowBlocked: "#F87171",
  workflowCancelled: "#44444A",

  statusBarStyle: "light",
};
