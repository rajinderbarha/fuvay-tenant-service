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

// Warm-light: off-white background, never pure white everywhere, warm-gray
// borders instead of cool grays.
export const lightColors: ColorTokens = {
  brandPrimary: "#D9642B",
  brandPrimaryPressed: "#B84F1F",
  brandPrimaryMuted: "#FBE7D8",
  brandOnPrimary: "#FFFFFF",

  backgroundPrimary: "#F7F6F3",
  backgroundSecondary: "#F1EFEA",
  backgroundElevated: "#FFFFFF",
  backgroundSunken: "#EDEBE5",
  backgroundOverlay: "rgba(30, 25, 20, 0.45)",

  surfaceDefault: "#FFFFFF",
  surfaceRaised: "#FFFFFF",
  surfaceInteractive: "#F1EFEA",
  surfaceSelected: "#FBE7D8",
  surfaceDisabled: "#EDEBE5",

  textPrimary: "#221C16",
  textSecondary: "#5C5348",
  textTertiary: "#8B8072",
  textDisabled: "#B8AFA2",
  textInverse: "#FFFFFF",
  textLink: "#B84F1F",

  borderSubtle: "#E6E1D8",
  borderDefault: "#D8D1C4",
  borderStrong: "#B8AFA2",
  borderFocus: "#D9642B",
  borderDisabled: "#E6E1D8",

  statusSuccess: "#1E8E5A",
  statusSuccessSurface: "#E6F5EC",
  statusWarning: "#B5750B",
  statusWarningSurface: "#FCF0DC",
  statusDanger: "#C4342A",
  statusDangerSurface: "#FBE8E6",
  statusInfo: "#1E6FB8",
  statusInfoSurface: "#E6F0FA",
  statusNeutral: "#5C5348",
  statusNeutralSurface: "#EDEBE5",

  workflowCompleted: "#1E8E5A",
  workflowCurrent: "#D9642B",
  workflowUpcoming: "#8B8072",
  workflowBlocked: "#C4342A",
  workflowCancelled: "#B8AFA2",

  statusBarStyle: "dark",
};

// Warm near-black: layered charcoal surfaces (never pure black everywhere),
// off-white (not pure-white) primary text, warm dark-gray borders.
export const darkColors: ColorTokens = {
  brandPrimary: "#F2994A",
  brandPrimaryPressed: "#D9642B",
  brandPrimaryMuted: "#3A2A1A",
  brandOnPrimary: "#1A1512",

  backgroundPrimary: "#15120F",
  backgroundSecondary: "#1B1713",
  backgroundElevated: "#221D18",
  backgroundSunken: "#0F0D0B",
  backgroundOverlay: "rgba(0, 0, 0, 0.6)",

  surfaceDefault: "#221D18",
  surfaceRaised: "#2A241D",
  surfaceInteractive: "#2A241D",
  surfaceSelected: "#3A2A1A",
  surfaceDisabled: "#1B1713",

  textPrimary: "#F1ECE4",
  textSecondary: "#B8AD9E",
  textTertiary: "#87796A",
  textDisabled: "#544A3E",
  textInverse: "#1A1512",
  textLink: "#F2994A",

  borderSubtle: "#2A241D",
  borderDefault: "#3A342B",
  borderStrong: "#544A3E",
  borderFocus: "#F2994A",
  borderDisabled: "#2A241D",

  statusSuccess: "#4ADE80",
  statusSuccessSurface: "#16301F",
  statusWarning: "#FBBF24",
  statusWarningSurface: "#3A2E0E",
  statusDanger: "#F87171",
  statusDangerSurface: "#3A1614",
  statusInfo: "#60A5E8",
  statusInfoSurface: "#122C3E",
  statusNeutral: "#B8AD9E",
  statusNeutralSurface: "#2A241D",

  workflowCompleted: "#4ADE80",
  workflowCurrent: "#F2994A",
  workflowUpcoming: "#87796A",
  workflowBlocked: "#F87171",
  workflowCancelled: "#544A3E",

  statusBarStyle: "light",
};
