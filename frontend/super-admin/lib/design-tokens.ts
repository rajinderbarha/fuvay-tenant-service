/**
 * Sprint 34B — Design Token Reference
 *
 * These constants mirror the CSS custom properties in styles/globals.css.
 * Use them in inline styles where a direct JS value is required
 * (e.g. recharts stroke colors, canvas drawing, dynamic style calculations).
 *
 * For everything else, use CSS variables: var(--token-name)
 */

// ── Radius ─────────────────────────────────────────────────────────────────────
export const radius = {
  sm:   "8px",
  md:   "12px",
  lg:   "16px",
  xl:   "24px",
  full: "999px",
} as const;

// ── Shadows ───────────────────────────────────────────────────────────────────
export const shadows = {
  sm:       "0 1px 2px rgba(15,23,42,0.04), 0 1px 4px rgba(15,23,42,0.03)",
  default:  "0 1px 3px rgba(15,23,42,0.05), 0 8px 24px rgba(15,23,42,0.06)",
  md:       "0 4px 16px rgba(15,23,42,0.07), 0 12px 32px rgba(15,23,42,0.05)",
  lg:       "0 8px 32px rgba(15,23,42,0.10), 0 24px 48px rgba(15,23,42,0.07)",
  focus:    "0 0 0 4px rgba(37, 99, 235, 0.14)",
} as const;

// ── Spacing ───────────────────────────────────────────────────────────────────
export const spacing = {
  xs:   "var(--space-1)",
  sm:   "var(--space-2)",
  md:   "var(--space-3)",
  lg:   "var(--space-4)",
  xl:   "var(--space-6)",
  "2xl":"var(--space-8)",
  "3xl":"var(--space-12)",
} as const;

// ── Typography ────────────────────────────────────────────────────────────────
export const typography = {
  pageTitle: {
    fontSize: "28px",
    lineHeight: "36px",
    fontWeight: 700,
  },
  sectionTitle: {
    fontSize: "18px",
    lineHeight: "28px",
    fontWeight: 650,
  },
  cardTitle: {
    fontSize: "15px",
    lineHeight: "22px",
    fontWeight: 600,
  },
  body: {
    fontSize: "14px",
    lineHeight: "22px",
    fontWeight: 400,
  },
  bodySmall: {
    fontSize: "13px",
    lineHeight: "20px",
    fontWeight: 400,
  },
  caption: {
    fontSize: "12px",
    lineHeight: "18px",
    fontWeight: 400,
  },
  label: {
    fontSize: "11px",
    lineHeight: "16px",
    fontWeight: 600,
    letterSpacing: "0.07em",
    textTransform: "uppercase" as const,
  },
} as const;

// ── Chart colors (concrete values for JS charting libraries) ──────────────────
export const chartColors = {
  primary:   "#2563EB",
  secondary: "#7C3AED",
  accent:    "#06B6D4",
  success:   "#16A34A",
  warning:   "#D97706",
  danger:    "#DC2626",
  muted:     "#94A3B8",
  // Dark mode equivalents
  primaryDark:   "#60A5FA",
  secondaryDark: "#A78BFA",
} as const;

// ── Component token presets (reference for new components) ────────────────────
export const componentTokens = {
  card: {
    background:   "var(--surface)",
    border:       "1px solid var(--border)",
    borderRadius: radius.lg,
    boxShadow:    "var(--shadow-sm)",
  },
  cardElevated: {
    background:   "var(--surface-elevated)",
    border:       "1px solid var(--border)",
    borderRadius: radius.lg,
    boxShadow:    "var(--shadow)",
  },
  input: {
    background:   "var(--surface)",
    border:       "1px solid var(--border)",
    borderRadius: radius.sm,
    color:        "var(--text-primary)",
    fontSize:     "14px",
    height:       "38px",
    padding:      "0 12px",
  },
  buttonPrimary: {
    background:   "var(--primary-gradient)",
    color:        "var(--text-on-brand)",
    border:       "none",
    borderRadius: radius.md,
    fontWeight:   600,
    boxShadow:    "var(--shadow-sm)",
  },
  buttonSecondary: {
    background:   "var(--surface)",
    color:        "var(--text-primary)",
    border:       "1px solid var(--border)",
    borderRadius: radius.md,
    fontWeight:   500,
  },
  buttonDanger: {
    background:   "var(--danger-bg)",
    color:        "var(--danger-text)",
    border:       "1px solid var(--danger-border)",
    borderRadius: radius.md,
    fontWeight:   500,
  },
  badge: {
    borderRadius: radius.full,
    fontWeight:   700,
    fontSize:     "11px",
    letterSpacing:"0.03em",
    padding:      "3px 9px",
  },
  modal: {
    background:   "var(--surface)",
    border:       "1px solid var(--border)",
    borderRadius: radius.xl,
    boxShadow:    "var(--shadow-lg)",
  },
  tableHeader: {
    background:   "var(--surface-sunken)",
    borderBottom: "1px solid var(--border)",
    fontSize:     "11px",
    fontWeight:   700,
    letterSpacing:"0.06em",
    textTransform:"uppercase" as const,
    color:        "var(--text-tertiary)",
    padding:      "10px 14px",
  },
  tableRow: {
    borderBottom: "1px solid var(--border)",
    padding:      "12px 14px",
    fontSize:     "13px",
    color:        "var(--text-primary)",
  },
  navSidebar: {
    background: "var(--sidebar-bg)",
    border:     "none",
    color:      "var(--sidebar-text)",
    fontSize:   "13px",
    fontWeight: 400,
    borderRadius: radius.sm,
    padding:    "8px 10px",
  },
  navSidebarActive: {
    background: "var(--sidebar-active)",
    color:      "var(--sidebar-text-active)",
    fontWeight: 600,
  },
} as const;

// ── Status style map (for StatusBadge + inline status displays) ───────────────
export interface StatusStyle {
  bg:     string;
  text:   string;
  border: string;
  dot?:   string;
  label:  string;
}

export const statusStyles: Record<string, StatusStyle> = {
  active:    { bg: "var(--success-bg)",  text: "var(--success-text)",  border: "var(--success-border)",  dot: "var(--success)", label: "Active"     },
  inactive:  { bg: "var(--surface-sunken)", text: "var(--text-tertiary)", border: "var(--border)",       label: "Inactive"   },
  pending:   { bg: "var(--warning-bg)",  text: "var(--warning-text)",  border: "var(--warning-border)",  dot: "var(--warning)", label: "Pending"    },
  verified:  { bg: "var(--info-bg)",     text: "var(--info-text)",     border: "var(--info-border)",     dot: "var(--info)",    label: "Verified"   },
  rejected:  { bg: "var(--danger-bg)",   text: "var(--danger-text)",   border: "var(--danger-border)",   dot: "var(--danger)",  label: "Rejected"   },
  locked:    { bg: "var(--danger-bg)",   text: "var(--danger-text)",   border: "var(--danger-border)",   label: "Locked"     },
  disabled:  { bg: "var(--surface-sunken)", text: "var(--text-tertiary)", border: "var(--border)",       label: "Disabled"   },
  suspended: { bg: "var(--warning-bg)",  text: "var(--warning-text)",  border: "var(--warning-border)",  label: "Suspended"  },
  draft:     { bg: "var(--surface-sunken)", text: "var(--text-secondary)", border: "var(--border)",      label: "Draft"      },
  published: { bg: "var(--success-bg)",  text: "var(--success-text)",  border: "var(--success-border)",  label: "Published"  },
  archived:  { bg: "var(--surface-sunken)", text: "var(--text-tertiary)", border: "var(--border)",       label: "Archived"   },
  completed: { bg: "var(--success-bg)",  text: "var(--success-text)",  border: "var(--success-border)",  label: "Completed"  },
  cancelled: { bg: "var(--surface-sunken)", text: "var(--text-tertiary)", border: "var(--border)",       label: "Cancelled"  },
  failed:    { bg: "var(--danger-bg)",   text: "var(--danger-text)",   border: "var(--danger-border)",   label: "Failed"     },
  success:   { bg: "var(--success-bg)",  text: "var(--success-text)",  border: "var(--success-border)",  label: "Success"    },
  warning:   { bg: "var(--warning-bg)",  text: "var(--warning-text)",  border: "var(--warning-border)",  label: "Warning"    },
  danger:    { bg: "var(--danger-bg)",   text: "var(--danger-text)",   border: "var(--danger-border)",   label: "Danger"     },
  info:      { bg: "var(--info-bg)",     text: "var(--info-text)",     border: "var(--info-border)",     label: "Info"       },
  // Auth-specific
  force_password_change: { bg: "var(--warning-bg)", text: "var(--warning-text)", border: "var(--warning-border)", label: "Password change required" },
  password_reset_required: { bg: "var(--warning-bg)", text: "var(--warning-text)", border: "var(--warning-border)", label: "Reset required" },
  reverification_required: { bg: "var(--danger-bg)",  text: "var(--danger-text)",  border: "var(--danger-border)",  label: "Re-verification required" },
  changes_pending_review:  { bg: "var(--info-bg)",    text: "var(--info-text)",    border: "var(--info-border)",    label: "Changes pending review" },
  pending_activation:      { bg: "var(--warning-bg)", text: "var(--warning-text)", border: "var(--warning-border)", label: "Pending activation" },
};

export function getStatusStyle(status: string): StatusStyle {
  return statusStyles[status] ?? {
    bg: "var(--surface-sunken)", text: "var(--text-tertiary)", border: "var(--border)",
    label: status.replace(/_/g, " "),
  };
}
