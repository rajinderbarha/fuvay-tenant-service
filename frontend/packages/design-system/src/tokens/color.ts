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
  light: ["#2563EB", "#7C3AED", "#16A34A", "#D97706", "#DC2626", "#0891B2", "#DB2777", "#65A30D"],
  dark: ["#60A5FA", "#A78BFA", "#4ADE80", "#FCD34D", "#F87171", "#22D3EE", "#F472B6", "#A3E635"],
} as const;

export type ThemeMode = "light" | "dark";
