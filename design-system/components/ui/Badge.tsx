/**
 * Badge — status indicator. All colours from CSS vars.
 */
import React from "react";

export type BadgeVariant = "default" | "success" | "warning" | "danger" | "info" | "muted";
export type BadgeSize    = "sm" | "md" | "lg";

const VARIANT_STYLES: Record<BadgeVariant, React.CSSProperties> = {
  default: { background: "var(--color-accent-muted)", color: "var(--color-accent)", border: "1px solid transparent" },
  success: { background: "var(--color-success-bg)",   color: "var(--color-success-text)", border: "1px solid var(--color-success-border)" },
  warning: { background: "var(--color-warning-bg)",   color: "var(--color-warning-text)", border: "1px solid var(--color-warning-border)" },
  danger:  { background: "var(--color-danger-bg)",    color: "var(--color-danger-text)",  border: "1px solid var(--color-danger-border)"  },
  info:    { background: "var(--color-info-bg)",      color: "var(--color-info-text)",    border: "1px solid var(--color-info-border)"    },
  muted:   { background: "var(--color-surface-sunken)", color: "var(--color-text-tertiary)", border: "1px solid var(--color-border)" },
};

const SIZE_STYLES: Record<BadgeSize, React.CSSProperties> = {
  sm: { fontSize: "10px", padding: "2px 7px",  borderRadius: "999px", fontWeight: 600 },
  md: { fontSize: "11px", padding: "3px 9px",  borderRadius: "999px", fontWeight: 600 },
  lg: { fontSize: "12px", padding: "4px 12px", borderRadius: "999px", fontWeight: 600 },
};

export function Badge({ children, variant = "default", size = "md", style }: {
  children: React.ReactNode; variant?: BadgeVariant;
  size?: BadgeSize; style?: React.CSSProperties;
}) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: "4px",
      letterSpacing: "0.03em", whiteSpace: "nowrap",
      ...VARIANT_STYLES[variant], ...SIZE_STYLES[size], ...style,
    }}>
      {children}
    </span>
  );
}
