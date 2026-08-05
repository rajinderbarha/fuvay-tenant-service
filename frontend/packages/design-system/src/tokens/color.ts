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
  light: ["#3B6FED", "#5B8DEF", "#16A34A", "#0891B2", "#DC2626", "#7C3AED", "#DB2777", "#65A30D"],
  dark: ["#3B6FED", "#5B8DEF", "#4ADE80", "#22D3EE", "#F87171", "#A78BFA", "#F472B6", "#A3E635"],
} as const;

export type ThemeMode = "light" | "dark";
