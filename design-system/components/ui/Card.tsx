/** Card — content container with optional hover lift. */
import React from "react";

export function Card({ children, style, hover = false, padding = 24, ...props }:{
  children: React.ReactNode; style?: React.CSSProperties;
  hover?: boolean; padding?: number; onClick?: () => void;
}) {
  const [hovered, setHovered] = React.useState(false);
  return (
    <div
      {...props}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: "var(--color-surface-base)",
        border: "1px solid var(--color-border)",
        borderRadius: "14px",
        padding: `${padding}px`,
        boxShadow: hovered && hover ? "var(--shadow-md)" : "var(--shadow-sm)",
        transform: hovered && hover ? "translateY(-2px)" : "none",
        transition: "box-shadow 0.2s ease, transform 0.2s ease, border-color 0.2s ease",
        borderColor: hovered && hover ? "var(--color-border-strong)" : "var(--color-border)",
        cursor: props.onClick ? "pointer" : undefined,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
