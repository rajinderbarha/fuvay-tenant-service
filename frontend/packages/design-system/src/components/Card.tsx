import React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  actions?: React.ReactNode;
  padding?: "none" | "sm" | "md" | "lg";
}

const paddingMap = { none: "0", sm: "0.75rem", md: "1.25rem", lg: "1.75rem" };

export function Card({ title, actions, padding = "md", children, style, ...rest }: CardProps) {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-xl, 1rem)",
        boxShadow: "var(--shadow-sm)",
        overflow: "hidden",
        ...style,
      }}
      {...rest}
    >
      {(title || actions) && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "1rem 1.25rem",
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
      <div style={{ padding: paddingMap[padding] }}>{children}</div>
    </div>
  );
}
