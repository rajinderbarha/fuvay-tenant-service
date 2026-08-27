"use client";

import React, { useState } from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  actions?: React.ReactNode;
  padding?: "none" | "sm" | "md" | "lg" | number;
  hover?: boolean;
}

const paddingMap = {
  none: "var(--space-0)",
  sm: "var(--space-3)",
  md: "var(--space-5)",
  lg: "calc(var(--space-6) + var(--space-1))",
};

export function Card({ title, actions, padding = "md", hover = false, children, style, onClick, className, onMouseEnter, onMouseLeave, role, tabIndex, onKeyDown, ...rest }: CardProps) {
  const [hovered, setHovered] = useState(false);
  const resolvedPadding = typeof padding === "number" ? padding : paddingMap[padding];
  const hasHeader = Boolean(title || actions);
  return (
    <div
      className={["ds-surface-card", className].filter(Boolean).join(" ")}
      onClick={onClick}
      role={onClick ? "button" : role}
      tabIndex={onClick ? (tabIndex ?? 0) : tabIndex}
      onKeyDown={event => {
        onKeyDown?.(event);
        if (onClick && !event.defaultPrevented && (event.key === "Enter" || event.key === " ")) {
          event.preventDefault();
          onClick(event as unknown as React.MouseEvent<HTMLDivElement>);
        }
      }}
      onMouseEnter={event => { setHovered(true); onMouseEnter?.(event); }}
      onMouseLeave={event => { setHovered(false); onMouseLeave?.(event); }}
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-card)",
        boxShadow: hovered && hover ? "var(--shadow-md)" : "var(--shadow-sm)",
        transform: hovered && hover ? "translateY(-1px)" : "none",
        borderColor: hovered && hover ? "var(--border-strong)" : "var(--border)",
        transition: "border-color var(--motion-fast) var(--motion-easing), box-shadow var(--motion-fast) var(--motion-easing), transform var(--motion-fast) var(--motion-easing)",
        cursor: onClick ? "pointer" : undefined,
        overflow: "hidden",
        padding: hasHeader ? 0 : resolvedPadding,
        ...style,
      }}
      {...rest}
    >
      {hasHeader && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "var(--space-4) var(--space-5)",
            borderBottom: "1px solid var(--border)",
          }}
        >
          {title && (
            <h3 className="ds-text-card-title" style={{ color: "var(--text-primary)", margin: 0 }}>
              {title}
            </h3>
          )}
          {actions}
        </div>
      )}
      {hasHeader ? <div style={{ padding: resolvedPadding }}>{children}</div> : children}
    </div>
  );
}
