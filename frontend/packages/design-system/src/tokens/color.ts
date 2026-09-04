// Semantic color tokens. Values mirror the CSS custom properties emitted in
// theme.css so TS logic (e.g. chart palettes) never hardcodes hex.
export const colorVar = {
  bg: "var(--bg)",
  bgSoft: "var(--bg-soft)",
  bgMuted: "var(--bg-muted)",
  surface: "var(--surface)",
  surfaceElevated: "var(--surface-elevated)",
  surfaceSunken: "var(--surface-sunken)",
  border: "var(--border)",
  borderStrong: "var(--border-strong)",
  borderFocus: "var(--border-focus)",
  textPrimary: "var(--text-primary)",
  textSecondary: "var(--text-secondary)",
  textTertiary: "var(--text-tertiary)",
  textOnBrand: "var(--text-on-brand)",
  brand: "var(--brand)",
  brandHover: "var(--brand-hover)",
  brandSubtle: "var(--accent-muted)",
  success: "var(--success)",
  successBg: "var(--success-bg)",
  successBorder: "var(--success-border)",
  successText: "var(--success-text)",
  warning: "var(--warning)",
  warningBg: "var(--warning-bg)",
  warningBorder: "var(--warning-border)",
  warningText: "var(--warning-text)",
  danger: "var(--danger)",
  dangerBg: "var(--danger-bg)",
  dangerBorder: "var(--danger-border)",
  dangerText: "var(--danger-text)",
  info: "var(--info)",
  infoBg: "var(--info-bg)",
  infoBorder: "var(--info-border)",
  infoText: "var(--info-text)",
  neutral: "var(--neutral)",
  neutralBg: "var(--neutral-bg)",
  neutralBorder: "var(--neutral-border)",
  neutralText: "var(--neutral-text)",
  focusRing: "var(--focus-ring)",
  overlay: "var(--overlay)",
  skeleton: "var(--skeleton)",
} as const;

// Chart series colors — literal hex needed for canvas/SVG libs that can't read
// CSS vars per-datapoint reliably. Kept in one place, distinct light/dark sets.
export const chartPalette = {
  light: ["#0F6B60", "#2F9E8F", "#A9722F", "#7C776E", "#C2703F", "#6C5D88", "#A35F78", "#667A42"],
  dark: ["#2F9E8F", "#7FD6C7", "#E2BD7E", "#A09A90", "#E08A5A", "#A99BC2", "#D39AAF", "#AFC77B"],
} as const;

export type ThemeMode = "light" | "dark";
