"use client";

import React from "react";
import { Loader2 } from "lucide-react";

export type ButtonVariant = "primary" | "secondary" | "tertiary" | "ghost" | "destructive" | "link" | "icon";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  /** Required for variant="icon" so screen readers get a label. */
  "aria-label"?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const base: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  gap: "0.5rem",
  fontFamily: "var(--font-family-base)",
  fontWeight: 600,
  border: "1px solid transparent",
  borderRadius: "var(--radius-md)",
  cursor: "pointer",
  transition: "background var(--motion-fast) var(--motion-easing), border-color var(--motion-fast), color var(--motion-fast), opacity var(--motion-fast)",
  whiteSpace: "nowrap",
};

const sizes: Record<ButtonSize, React.CSSProperties> = {
  sm: { fontSize: "0.8125rem", padding: "0.375rem 0.75rem", minHeight: "2rem" },
  md: { fontSize: "0.875rem", padding: "0.5rem 1rem", minHeight: "2.25rem" },
  lg: { fontSize: "0.9375rem", padding: "0.625rem 1.25rem", minHeight: "2.75rem" },
};

function variantStyle(variant: ButtonVariant): React.CSSProperties {
  switch (variant) {
    case "primary":
      return { background: "var(--brand)", color: "var(--text-on-brand)", borderColor: "var(--brand)" };
    case "secondary":
      return { background: "var(--surface)", color: "var(--text-primary)", borderColor: "var(--border-strong)" };
    case "tertiary":
      return { background: "var(--bg-muted)", color: "var(--text-primary)", borderColor: "transparent" };
    case "ghost":
      return { background: "transparent", color: "var(--text-secondary)", borderColor: "transparent" };
    case "destructive":
      return { background: "var(--danger)", color: "#fff", borderColor: "var(--danger)" };
    case "link":
      return { background: "transparent", color: "var(--text-link)", borderColor: "transparent", padding: 0, minHeight: "auto", textDecoration: "underline" };
    case "icon":
      return { background: "transparent", color: "var(--text-secondary)", borderColor: "transparent", padding: "0.5rem", minHeight: "2.25rem", minWidth: "2.25rem" };
    default:
      return {};
  }
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading, disabled, children, leftIcon, rightIcon, style, className, ...rest },
  ref
) {
  const isIconOnly = variant === "icon";
  if (isIconOnly && !rest["aria-label"]) {
    // eslint-disable-next-line no-console
    console.warn("Button: variant='icon' requires an aria-label for accessibility.");
  }
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={["ds-focus-visible", className].filter(Boolean).join(" ")}
      style={{
        ...base,
        ...(variant !== "link" && variant !== "icon" ? sizes[size] : {}),
        ...variantStyle(variant),
        opacity: disabled ? 0.5 : 1,
        cursor: disabled || loading ? "not-allowed" : "pointer",
        ...style,
      }}
      {...rest}
    >
      {loading ? <Loader2 size={16} className="ds-spin" aria-hidden="true" /> : leftIcon}
      {!isIconOnly && children}
      {isIconOnly && !loading ? children : null}
      {!loading && !isIconOnly ? rightIcon : null}
    </button>
  );
});
