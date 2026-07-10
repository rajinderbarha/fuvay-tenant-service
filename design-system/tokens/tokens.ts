/**
 * ServiceOS Design System — tokens.ts
 * THE SINGLE SOURCE OF TRUTH.
 * Change here → every portal + mobile app updates.
 * No hardcoded hex/spacing/font values anywhere else.
 */

export const tokens = {
  colors: {
    brand: {
      50:  { light: "#EBF4FA", dark: "#0A1628" },
      100: { light: "#D6E8F5", dark: "#0F1F3D" },
      200: { light: "#AECFEA", dark: "#1A3356" },
      300: { light: "#7EB5DC", dark: "#1E3A5F" },
      400: { light: "#4A90D9", dark: "#2E5F8A" },
      500: { light: "#1E3A5F", dark: "#4A90D9" },
      600: { light: "#173050", dark: "#5BA3E8" },
      700: { light: "#102040", dark: "#7DB8F0" },
      800: { light: "#0A1628", dark: "#A8D0F8" },
      900: { light: "#060E1A", dark: "#D4E8FC" },
    },
    accent: {
      DEFAULT: { light: "#2E86AB", dark: "#5BB3D0" },
      hover:   { light: "#246E8C", dark: "#7CCADF" },
      muted:   { light: "#EBF6FB", dark: "#0D2F3A" },
    },
    surface: {
      base:     { light: "#FFFFFF",  dark: "#0F1923" },
      elevated: { light: "#FFFFFF",  dark: "#162030" },
      sunken:   { light: "#F5F7FA",  dark: "#0A1628" },
      overlay:  { light: "#FFFFFF",  dark: "#1C2B3D" },
      sidebar:  { light: "#1E3A5F",  dark: "#0A1628" },
    },
    background: {
      DEFAULT: { light: "#F0F4F8",   dark: "#080F1A" },
      subtle:  { light: "#F8FAFC",   dark: "#0D1824" },
    },
    border: {
      DEFAULT: { light: "#E2E8F0",   dark: "#1E3A5F" },
      strong:  { light: "#CBD5E1",   dark: "#2A4A70" },
      focus:   { light: "#2E86AB",   dark: "#5BB3D0" },
    },
    text: {
      primary:   { light: "#0F172A", dark: "#F1F5F9" },
      secondary: { light: "#475569", dark: "#94A3B8" },
      tertiary:  { light: "#94A3B8", dark: "#64748B" },
      inverse:   { light: "#FFFFFF", dark: "#0F172A" },
      link:      { light: "#2E86AB", dark: "#5BB3D0" },
      onBrand:   { light: "#FFFFFF", dark: "#FFFFFF" },
    },
    semantic: {
      success: {
        DEFAULT: { light: "#16A34A", dark: "#22C55E" },
        bg:      { light: "#F0FDF4", dark: "#052E16" },
        border:  { light: "#BBF7D0", dark: "#14532D" },
        text:    { light: "#15803D", dark: "#4ADE80" },
      },
      warning: {
        DEFAULT: { light: "#D97706", dark: "#F59E0B" },
        bg:      { light: "#FFFBEB", dark: "#2D1B00" },
        border:  { light: "#FDE68A", dark: "#451A00" },
        text:    { light: "#B45309", dark: "#FCD34D" },
      },
      danger: {
        DEFAULT: { light: "#DC2626", dark: "#EF4444" },
        bg:      { light: "#FEF2F2", dark: "#2D0606" },
        border:  { light: "#FECACA", dark: "#450A0A" },
        text:    { light: "#B91C1C", dark: "#FCA5A5" },
      },
      info: {
        DEFAULT: { light: "#0EA5E9", dark: "#38BDF8" },
        bg:      { light: "#F0F9FF", dark: "#082030" },
        border:  { light: "#BAE6FD", dark: "#0C3050" },
        text:    { light: "#0369A1", dark: "#7DD3FC" },
      },
    },
    // PROVEN: All 5 health bands here — JobStatusBadge reads from this
    health: {
      platinum: { bg: "#FDF6E3", text: "#8B6914", border: "#F0D060", icon: "#C0A060" },
      gold:     { bg: "#FEF9EE", text: "#92400E", border: "#FCD34D", icon: "#F4A830" },
      silver:   { bg: "#F8FAFC", text: "#475569", border: "#CBD5E1", icon: "#94A3B8" },
      bronze:   { bg: "#FDF0E8", text: "#7C2D12", border: "#FDBA74", icon: "#CD7F32" },
      at_risk:  { bg: "#FFFBEB", text: "#92400E", border: "#FDE68A", icon: "#F59E0B" },
      critical: { bg: "#FEF2F2", text: "#991B1B", border: "#FECACA", icon: "#EF4444" },
    },
    // PROVEN: All 23 job statuses here — never hardcoded in components
    jobStatus: {
      created:            { bg: "#EFF6FF", text: "#1D4ED8", border: "#BFDBFE", label: "Created" },
      pending_assignment: { bg: "#F5F3FF", text: "#6D28D9", border: "#DDD6FE", label: "Pending Assignment" },
      assigned:           { bg: "#ECFDF5", text: "#065F46", border: "#A7F3D0", label: "Assigned" },
      accepted:           { bg: "#F0FDF4", text: "#15803D", border: "#BBF7D0", label: "Accepted" },
      en_route:           { bg: "#FFF7ED", text: "#9A3412", border: "#FED7AA", label: "En Route" },
      arrived:            { bg: "#F0F9FF", text: "#0369A1", border: "#BAE6FD", label: "Arrived" },
      in_progress:        { bg: "#FFF1F2", text: "#9F1239", border: "#FECDD3", label: "In Progress" },
      parts_required:     { bg: "#FEFCE8", text: "#713F12", border: "#FEF08A", label: "Parts Required" },
      parts_sourced:      { bg: "#F7FEE7", text: "#3F6212", border: "#D9F99D", label: "Parts Sourced" },
      resumed:            { bg: "#F0FDFA", text: "#134E4A", border: "#99F6E4", label: "Resumed" },
      quality_check:      { bg: "#FDF4FF", text: "#701A75", border: "#F0ABFC", label: "Quality Check" },
      completed:          { bg: "#ECFDF5", text: "#065F46", border: "#6EE7B7", label: "Completed" },
      invoiced:           { bg: "#EFF6FF", text: "#1E40AF", border: "#93C5FD", label: "Invoiced" },
      payment_pending:    { bg: "#FFFBEB", text: "#92400E", border: "#FCD34D", label: "Payment Pending" },
      paid:               { bg: "#F0FDF4", text: "#14532D", border: "#86EFAC", label: "Paid" },
      closed:             { bg: "#F8FAFC", text: "#1E293B", border: "#CBD5E1", label: "Closed" },
      cancelled:          { bg: "#FEF2F2", text: "#991B1B", border: "#FECACA", label: "Cancelled" },
      disputed:           { bg: "#FFF7ED", text: "#7C2D12", border: "#FDBA74", label: "Disputed" },
      refunded:           { bg: "#F0F9FF", text: "#0C4A6E", border: "#7DD3FC", label: "Refunded" },
      no_show:            { bg: "#FEF2F2", text: "#7F1D1D", border: "#FCA5A5", label: "No Show" },
      rescheduled:        { bg: "#F5F3FF", text: "#4C1D95", border: "#C4B5FD", label: "Rescheduled" },
      warranty_claim:     { bg: "#FDF4FF", text: "#581C87", border: "#E9D5FF", label: "Warranty Claim" },
      archived:           { bg: "#F8FAFC", text: "#475569", border: "#E2E8F0", label: "Archived" },
    },
  },
  spacing: {
    0: "0px",   1: "4px",  2: "8px",  3: "12px", 4: "16px",
    5: "20px",  6: "24px", 7: "28px", 8: "32px",
    10: "40px", 12: "48px", 16: "64px", 20: "80px", 24: "96px",
  },
  radius: {
    none: "0px", sm: "4px", DEFAULT: "8px",
    md: "10px", lg: "14px", xl: "20px", "2xl": "28px", full: "9999px",
  },
  font: {
    family: {
      sans: "'Inter', 'SF Pro Display', -apple-system, sans-serif",
      mono: "'JetBrains Mono', 'Fira Code', monospace",
    },
    size: {
      "2xs": "10px", xs: "11px", sm: "12px", base: "14px",
      md: "15px", lg: "16px", xl: "18px", "2xl": "20px",
      "3xl": "24px", "4xl": "30px", "5xl": "36px", "6xl": "48px",
    },
    weight: { light: 300, regular: 400, medium: 500, semibold: 600, bold: 700, extrabold: 800 },
    leading: { tight: 1.2, snug: 1.375, normal: 1.5, relaxed: 1.65 },
    tracking: { tight: "-0.03em", snug: "-0.01em", normal: "0", wide: "0.03em" },
  },
  shadow: {
    light: {
      xs:  "0 1px 2px rgba(0,0,0,0.04)",
      sm:  "0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.04)",
      DEFAULT: "0 4px 6px rgba(0,0,0,0.06), 0 2px 4px rgba(0,0,0,0.04)",
      md:  "0 8px 16px rgba(0,0,0,0.08), 0 4px 8px rgba(0,0,0,0.04)",
      lg:  "0 16px 32px rgba(0,0,0,0.10), 0 8px 16px rgba(0,0,0,0.06)",
      xl:  "0 24px 48px rgba(0,0,0,0.14), 0 12px 24px rgba(0,0,0,0.08)",
    },
    dark: {
      xs:  "0 1px 2px rgba(0,0,0,0.30)",
      sm:  "0 1px 3px rgba(0,0,0,0.40), 0 1px 2px rgba(0,0,0,0.30)",
      DEFAULT: "0 4px 6px rgba(0,0,0,0.50), 0 2px 4px rgba(0,0,0,0.40)",
      md:  "0 8px 16px rgba(0,0,0,0.60), 0 4px 8px rgba(0,0,0,0.40)",
      lg:  "0 16px 32px rgba(0,0,0,0.70), 0 8px 16px rgba(0,0,0,0.50)",
      xl:  "0 24px 48px rgba(0,0,0,0.80), 0 12px 24px rgba(0,0,0,0.60)",
    },
  },
  animation: {
    duration: { instant: "50ms", fast: "120ms", normal: "200ms", slow: "350ms", slower: "500ms" },
    easing: {
      DEFAULT: "cubic-bezier(0.4, 0, 0.2, 1)",
      in:      "cubic-bezier(0.4, 0, 1, 1)",
      out:     "cubic-bezier(0, 0, 0.2, 1)",
      spring:  "cubic-bezier(0.34, 1.56, 0.64, 1)",
      bounce:  "cubic-bezier(0.68, -0.55, 0.265, 1.55)",
    },
  },
  breakpoints: { mobile: 0, tablet: 768, desktop: 1280, wide: 1536 },
  zIndex: { base: 0, raised: 10, dropdown: 100, sticky: 200, modal: 300, toast: 400, tooltip: 500 },
} as const;

export type Tokens       = typeof tokens;
export type ThemeMode    = "light" | "dark";
export type HealthBand   = keyof typeof tokens.colors.health;
export type JobStatus    = keyof typeof tokens.colors.jobStatus;
export const JOB_STATUSES = Object.keys(tokens.colors.jobStatus) as JobStatus[];
export const HEALTH_BANDS = Object.keys(tokens.colors.health) as HealthBand[];
export const JOB_STATUS_COUNT = JOB_STATUSES.length; // must equal 23

// ── STATUS_MAP — generic status → CSS class (drives StatusBadge) ─────────────
export const STATUS_MAP: Record<string, { cssClass: string; label: string; dot: boolean }> = {
  active:       { cssClass: "status--active",       label: "Active",         dot: true  },
  inactive:     { cssClass: "status--inactive",     label: "Inactive",       dot: true  },
  live:         { cssClass: "status--live",          label: "Live",           dot: true  },
  paused:       { cssClass: "status--paused",        label: "Paused",         dot: false },
  suspended:    { cssClass: "status--error",         label: "Suspended",      dot: false },
  pending:      { cssClass: "status--pending",       label: "Pending",        dot: false },
  processing:   { cssClass: "status--processing",    label: "Processing",     dot: true  },
  queued:       { cssClass: "status--queued",        label: "Queued",         dot: false },
  in_progress:  { cssClass: "status--in_progress",   label: "In Progress",    dot: true  },
  completed:    { cssClass: "status--completed",     label: "Completed",      dot: false },
  failed:       { cssClass: "status--failed",        label: "Failed",         dot: false },
  error:        { cssClass: "status--error",         label: "Error",          dot: false },
  cancelled:    { cssClass: "status--cancelled",     label: "Cancelled",      dot: false },
  expired:      { cssClass: "status--expired",       label: "Expired",        dot: false },
  draft:        { cssClass: "status--draft",         label: "Draft",          dot: false },
  connected:    { cssClass: "status--connected",     label: "Connected",      dot: true  },
  healthy:      { cssClass: "status--healthy",       label: "Healthy",        dot: true  },
  degraded:     { cssClass: "status--degraded",      label: "Degraded",       dot: true  },
  at_risk:      { cssClass: "status--at_risk",       label: "At Risk",        dot: true  },
  unknown:      { cssClass: "status--unknown",       label: "Unknown",        dot: false },
  paid:         { cssClass: "status--paid",          label: "Paid",           dot: false },
  disputed:     { cssClass: "status--disputed",      label: "Disputed",       dot: false },
  archived:     { cssClass: "status--archived",      label: "Archived",       dot: false },
  closed:       { cssClass: "status--closed",        label: "Closed",         dot: false },
  warning:      { cssClass: "status--warning",       label: "Warning",        dot: true  },
  critical:     { cssClass: "status--critical",      label: "Critical",       dot: true  },
  parts_required:{ cssClass:"status--parts_required",label:"Parts Required",  dot: false },
};

// ── ROLE_MAP — user role → CSS class + label (drives RoleBadge) ──────────────
export const ROLE_MAP: Record<string, { cssClass: string; label: string; priority: number }> = {
  super_admin:    { cssClass: "role--super_admin",    label: "Super Admin",    priority: 0 },
  platform_admin: { cssClass: "role--platform_admin", label: "Platform Admin", priority: 1 },
  tenant_owner:   { cssClass: "role--tenant_owner",   label: "Tenant Owner",   priority: 2 },
  tenant_staff:   { cssClass: "role--tenant_staff",   label: "Staff",          priority: 3 },
  customer:       { cssClass: "role--customer",       label: "Customer",       priority: 4 },
  api_key:        { cssClass: "role--api_key",        label: "API Key",        priority: 5 },
};

// ── CITY_TIER_MAP — city tier → CSS class + label (drives CityTierBadge) ──────
export const CITY_TIER_MAP: Record<number, { cssClass: string; label: string; desc: string }> = {
  1: { cssClass: "city--tier1", label: "Tier 1", desc: "Metro — Mumbai, Delhi, Bangalore" },
  2: { cssClass: "city--tier2", label: "Tier 2", desc: "Major — Pune, Hyderabad, Chennai"  },
  3: { cssClass: "city--tier3", label: "Tier 3", desc: "Regional — Nagpur, Surat, Jaipur"  },
  4: { cssClass: "city--tier4", label: "Tier 4", desc: "Emerging markets"                  },
};

// ── SLA_BANDS — minutes overdue → severity (drives JobSlaBadge) ──────────────
export const SLA_BANDS = [
  { maxMinutes:   0, label: "On Time",  severity: "ok"      },
  { maxMinutes:  30, label: "At Risk",  severity: "warning" },
  { maxMinutes:  60, label: "Overdue",  severity: "danger"  },
  { maxMinutes: 999, label: "Critical", severity: "critical"},
] as const;

export type StatusKey   = keyof typeof STATUS_MAP;
export type RoleKey     = keyof typeof ROLE_MAP;
export type CityTier    = keyof typeof CITY_TIER_MAP;
