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

// Shared Fuvay reference palette: warm neutrals with teal interaction states.
export const lightColors: ColorTokens = {
  brandPrimary: "#0F6B60",
  brandPrimaryPressed: "#0B574E",
  brandPrimaryMuted: "#E8F2F0",
  brandOnPrimary: "#FFFFFF",

  backgroundPrimary: "#F7F5F1",
  backgroundSecondary: "#F6F4F0",
  backgroundElevated: "#FFFFFF",
  backgroundSunken: "#FBFAF8",
  backgroundOverlay: "rgba(27, 26, 24, 0.45)",

  surfaceDefault: "#FFFFFF",
  surfaceRaised: "#FFFFFF",
  surfaceInteractive: "#E8F2F0",
  surfaceSelected: "#E8F2F0",
  surfaceDisabled: "#F0EEE9",

  textPrimary: "#1B1A18",
  textSecondary: "#5F5B54",
  textTertiary: "#8A857C",
  textDisabled: "#A09A90",
  textInverse: "#FFFFFF",
  textLink: "#0F6B60",

  borderSubtle: "#F0ECE6",
  borderDefault: "#E9E5DF",
  borderStrong: "#DDD8D0",
  borderFocus: "#0F6B60",
  borderDisabled: "#F0ECE6",

  statusSuccess: "#0F6B60",
  statusSuccessSurface: "#E8F2F0",
  statusWarning: "#A9722F",
  statusWarningSurface: "#F6EFE4",
  statusDanger: "#C2703F",
  statusDangerSurface: "#FFF4ED",
  statusInfo: "#0F6B60",
  statusInfoSurface: "#E8F2F0",
  statusNeutral: "#7C776E",
  statusNeutralSurface: "#F0EEE9",

  workflowCompleted: "#0F6B60",
  workflowCurrent: "#0F6B60",
  workflowUpcoming: "#8A857C",
  workflowBlocked: "#C2703F",
  workflowCancelled: "#A09A90",

  statusBarStyle: "dark",
};

// Reference dark mode: warm charcoal layers with a brighter teal accent.
export const darkColors: ColorTokens = {
  brandPrimary: "#2F9E8F",
  brandPrimaryPressed: "#267F73",
  brandPrimaryMuted: "#15332F",
  brandOnPrimary: "#07211D",

  backgroundPrimary: "#111110",
  backgroundSecondary: "#161615",
  backgroundElevated: "#1F1F1C",
  backgroundSunken: "#141413",
  backgroundOverlay: "rgba(0, 0, 0, 0.6)",

  surfaceDefault: "#1A1A17",
  surfaceRaised: "#1F1F1C",
  surfaceInteractive: "#1F1F1C",
  surfaceSelected: "#15332F",
  surfaceDisabled: "#262622",

  textPrimary: "#F2EFE9",
  textSecondary: "#B6B0A6",
  textTertiary: "#918C83",
  textDisabled: "#6F6A62",
  textInverse: "#111110",
  textLink: "#7FD6C7",

  borderSubtle: "#242420",
  borderDefault: "#2C2C26",
  borderStrong: "#33322C",
  borderFocus: "#2F9E8F",
  borderDisabled: "#242420",

  statusSuccess: "#7FD6C7",
  statusSuccessSurface: "#15332F",
  statusWarning: "#E2BD7E",
  statusWarningSurface: "#33281A",
  statusDanger: "#E08A5A",
  statusDangerSurface: "#352219",
  statusInfo: "#7FD6C7",
  statusInfoSurface: "#15332F",
  statusNeutral: "#A09A90",
  statusNeutralSurface: "#262622",

  workflowCompleted: "#7FD6C7",
  workflowCurrent: "#2F9E8F",
  workflowUpcoming: "#918C83",
  workflowBlocked: "#E08A5A",
  workflowCancelled: "#6F6A62",

  statusBarStyle: "light",
};
