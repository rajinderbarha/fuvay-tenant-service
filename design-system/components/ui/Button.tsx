/**
 * Button — ServiceOS primary interactive element v2.
 * Variants: primary | secondary | outline | ghost | danger | success | warning | icon
 * Sizes: xs | sm | md | lg | icon-sm | icon-md | icon-lg
 * All colours from CSS variables — zero hardcoded hex.
 */
"use client";
import React from "react";

export type ButtonVariant = "primary" | "secondary" | "outline" | "ghost" | "danger" | "success" | "warning";
export type ButtonSize    = "xs" | "sm" | "md" | "lg" | "icon-sm" | "icon-md" | "icon-lg";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:   ButtonVariant;
  size?:      ButtonSize;
  loading?:   boolean;
  icon?:      React.ReactNode;
  iconRight?: React.ReactNode;
  fullWidth?: boolean;
}

const VARIANT_STYLES: Record<ButtonVariant, React.CSSProperties> = {
  primary: {
    background: "var(--color-brand-500)", color: "var(--color-text-on-brand)",
    border: "1px solid transparent",
  },
  secondary: {
    background: "var(--color-surface-base)", color: "var(--color-text-primary)",
    border: "1px solid var(--color-border)",
  },
  outline: {
    background: "transparent", color: "var(--color-brand-500)",
    border: "1px solid var(--color-brand-500)",
  },
  ghost: {
    background: "transparent", color: "var(--color-text-secondary)",
    border: "1px solid transparent",
  },
  danger: {
    background: "var(--color-danger-bg)", color: "var(--color-danger-text)",
    border: "1px solid var(--color-danger-border)",
  },
  success: {
    background: "var(--color-success-bg)", color: "var(--color-success-text)",
    border: "1px solid var(--color-success-border)",
  },
  warning: {
    background: "var(--color-warning-bg)", color: "var(--color-warning-text)",
    border: "1px solid var(--color-warning-border)",
  },
};

const SIZE_STYLES: Record<ButtonSize, React.CSSProperties> = {
  xs:       { padding: "4px 10px",  fontSize: "var(--text-xs)",   borderRadius: "var(--radius-sm)", height: "26px", minWidth: 0  },
  sm:       { padding: "6px 14px",  fontSize: "var(--text-sm)",   borderRadius: "var(--radius)",    height: "32px", minWidth: 0  },
  md:       { padding: "8px 18px",  fontSize: "var(--text-base)", borderRadius: "var(--radius-md)", height: "38px", minWidth: 0  },
  lg:       { padding: "10px 24px", fontSize: "var(--text-md)",   borderRadius: "var(--radius-lg)", height: "44px", minWidth: 0  },
  "icon-sm":{ padding: 0, width: "28px", height: "28px", borderRadius: "var(--radius-sm)", fontSize: "var(--text-sm)"  },
  "icon-md":{ padding: 0, width: "36px", height: "36px", borderRadius: "var(--radius-md)", fontSize: "var(--text-base)" },
  "icon-lg":{ padding: 0, width: "44px", height: "44px", borderRadius: "var(--radius-lg)", fontSize: "var(--text-lg)"  },
};

export function Button({
  variant = "primary", size = "md", loading, icon, iconRight,
  fullWidth, children, disabled, style, onMouseEnter, onMouseLeave, ...props
}: ButtonProps) {
  const [hovered, setHovered] = React.useState(false);

  const HOVER_BG: Partial<Record<ButtonVariant, string>> = {
    primary:   "var(--color-brand-600)",
    secondary: "var(--color-surface-sunken)",
    outline:   "var(--color-accent-muted)",
    ghost:     "var(--color-surface-sunken)",
    danger:    "var(--color-danger-border)",
    success:   "var(--color-success-border)",
    warning:   "var(--color-warning-border)",
  };

  const isIconOnly  = size.startsWith("icon");
  const base: React.CSSProperties = {
    display: "inline-flex", alignItems: "center", justifyContent: "center",
    gap: 6, fontWeight: "var(--font-semibold)" as unknown as number,
    fontFamily: "var(--font-sans)", cursor: "pointer",
    transition: "all 0.15s cubic-bezier(0.4, 0, 0.2, 1)",
    whiteSpace: "nowrap", userSelect: "none",
    width:   fullWidth ? "100%" : SIZE_STYLES[size].width,
    height:  SIZE_STYLES[size].height,
    opacity: disabled || loading ? 0.55 : 1,
    boxShadow: variant === "primary" && !disabled && !loading
      ? "0 1px 3px rgba(30,58,95,0.25), 0 1px 2px rgba(30,58,95,0.15)" : "none",
    ...VARIANT_STYLES[variant],
    ...SIZE_STYLES[size],
    background: hovered && !disabled && !loading
      ? (HOVER_BG[variant] ?? VARIANT_STYLES[variant].background)
      : VARIANT_STYLES[variant].background,
    transform: hovered && !disabled && !loading ? "translateY(-0.5px)" : "none",
    ...style,
  };

  return (
    <button
      {...props}
      disabled={disabled || loading}
      style={base}
      onMouseEnter={e => { setHovered(true); onMouseEnter?.(e); }}
      onMouseLeave={e => { setHovered(false); onMouseLeave?.(e); }}
    >
      {loading ? <BtnSpinner size={isIconOnly ? 16 : size === "xs" || size === "sm" ? 13 : 15} /> : icon}
      {!isIconOnly && children}
      {!loading && !isIconOnly && iconRight}
    </button>
  );
}

function BtnSpinner({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      style={{ animation: "spin 0.7s linear infinite", flexShrink: 0 }}>
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.25"/>
      <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
    </svg>
  );
}
