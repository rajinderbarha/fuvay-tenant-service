/**
 * Deliberately its own dark colour system, not the app's light theme --
 * matching the reference bot UI on explicit request ("don't like current
 * app bot style, I need better like AI bot"). Scoped to this screen only;
 * every other screen in the app keeps the shared light theme untouched.
 */
export const BOT = {
  bg: "#0B0E12",
  bgComposer: "#0D1116",
  surface: "#14181F",
  surfaceRaised: "#1B212A",
  surfaceSunken: "#10141A",
  surfaceActive: "#111A24",
  border: "#262D38",
  borderSubtle: "#232B36",
  borderActive: "#1F3A57",
  textPrimary: "#F4F6F9",
  textSecondary: "#C8CEDA",
  textTertiary: "#98A2B3",
  textMuted: "#8B94A0",
  textDim: "#5C6675",
  textFaint: "#4A5262",
  stepDone: "#4A5262",
  brand: "#2F8FFF",
  brandLight: "#5FA8FF",
  brandTint: "#2F8FFF1F",
  success: "#34D399",
  successBg: "#0F1E17",
  successBorder: "#1E3A2E",
  successTint: "#34D39922",
  warning: "#FFB020",
  danger: "#F85149",
};

/** Font families approximate the reference's Sora/Inter/JetBrains Mono --
 * no custom fonts are bundled in this app, so weight + system font is the
 * honest substitute rather than pulling in new font assets for one screen. */
export const BOT_FONT = {
  display: undefined, // system font, bold weights below approximate Sora
  body: undefined,
  mono: "monospace" as const,
};
