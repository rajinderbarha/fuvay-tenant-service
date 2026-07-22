import React from "react";
import type { LucideIcon } from "lucide-react";

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: LucideIcon;
  size?: number;
  variant?: "default" | "filled";
  "aria-label": string;
}

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { icon: Icon, size = 18, variant = "default", style, className, ...rest },
  ref
) {
  return (
    <button
      ref={ref}
      className={["ds-focus-visible", className].filter(Boolean).join(" ")}
      style={{
        width: "2.25rem",
        height: "2.25rem",
        borderRadius: "var(--radius-lg)",
        border: variant === "filled" ? "none" : "1px solid var(--border)",
        background: variant === "filled" ? "var(--accent-muted)" : "var(--surface)",
        color: variant === "filled" ? "var(--brand)" : "var(--text-secondary)",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
        transition: "background var(--motion-fast) var(--motion-easing), border-color var(--motion-fast)",
        flexShrink: 0,
        ...style,
      }}
      {...rest}
    >
      <Icon size={size} strokeWidth={2} />
    </button>
  );
});
