/**
 * Shared dark auth-shell tokens for Tenant Portal signup + login — distinct
 * from the app's light-mode dashboard tokens in design-tokens.ts.
 */
export const T = {
  pageBg:        "#0b0c0d",
  surface:       "#151617",
  surface2:      "#1d1e1c",
  inputBg:       "#151617",
  border:        "#393934",
  divider:       "rgba(255,255,255,0.10)",
  textPrimary:   "#f7f7f4",
  textSecondary: "#aaa99f",
  textMuted:     "#77776f",
  orange:        "#ff9f43",
  orangeHover:   "#ffad5c",
  orangePressed: "#ed8b31",
  success:       "#2fc36b",
  error:         "#ef5b5b",
  warning:       "#e9a23b",
  focusRing:     "rgba(255,159,67,0.35)",
} as const;
