import React from "react";
import type { LucideIcon } from "lucide-react";

export interface QuickAction {
  key: string;
  icon: LucideIcon;
  label: string;
  onClick?: () => void;
  href?: string;
}

export interface QuickActionGridProps {
  actions: QuickAction[];
  columns?: number;
}

export function QuickActionGrid({ actions, columns = 3 }: QuickActionGridProps) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${columns}, 1fr)`,
        gap: "0.75rem",
      }}
    >
      {actions.map((action) => {
        const Icon = action.icon;
        const Tag = action.href ? "a" : "button";
        return (
          <Tag
            key={action.key}
            href={action.href}
            onClick={action.onClick}
            className="ds-focus-visible"
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "0.5rem",
              padding: "1rem 0.5rem",
              borderRadius: "var(--radius-lg)",
              border: "1px solid var(--border)",
              background: "var(--surface-sunken)",
              cursor: "pointer",
              textDecoration: "none",
            }}
          >
            <div
              style={{
                width: "2.25rem",
                height: "2.25rem",
                borderRadius: "var(--radius-md)",
                background: "var(--accent-muted)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Icon size={18} color="var(--brand)" strokeWidth={2} />
            </div>
            <span className="ds-text-helper" style={{ color: "var(--text-secondary)", textAlign: "center" }}>
              {action.label}
            </span>
          </Tag>
        );
      })}
    </div>
  );
}
