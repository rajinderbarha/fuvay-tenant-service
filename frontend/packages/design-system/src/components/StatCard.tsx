import React from "react";
import type { LucideIcon } from "lucide-react";

export interface StatCardProps {
  icon: LucideIcon;
  label: string;
  value: React.ReactNode;
  change?: { value: string; direction: "up" | "down" | "flat" };
  tone?: "brand" | "success" | "warning" | "danger" | "info";
}

const toneBg: Record<NonNullable<StatCardProps["tone"]>, string> = {
  brand: "var(--accent-muted)",
  success: "var(--success-bg)",
  warning: "var(--warning-bg)",
  danger: "var(--danger-bg)",
  info: "var(--info-bg)",
};

const toneColor: Record<NonNullable<StatCardProps["tone"]>, string> = {
  brand: "var(--brand)",
  success: "var(--success)",
  warning: "var(--warning)",
  danger: "var(--danger)",
  info: "var(--info)",
};

export function StatCard({ icon: Icon, label, value, change, tone = "brand" }: StatCardProps) {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-xl, 1rem)",
        boxShadow: "var(--shadow-sm)",
        padding: "1.25rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.75rem",
        minWidth: 0,
      }}
    >
      <div
        style={{
          width: "2.5rem",
          height: "2.5rem",
          borderRadius: "var(--radius-lg)",
          background: toneBg[tone],
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        <Icon size={20} color={toneColor[tone]} strokeWidth={2} />
      </div>
      <div>
        <div className="ds-text-helper" style={{ color: "var(--text-secondary)", marginBottom: "0.25rem" }}>
          {label}
        </div>
        <div className="ds-text-page-title" style={{ color: "var(--text-primary)", lineHeight: 1.2 }}>
          {value}
        </div>
      </div>
      {change && (
        <div
          className="ds-text-caption"
          style={{
            color:
              change.direction === "up" ? "var(--success-text)" : change.direction === "down" ? "var(--danger-text)" : "var(--text-tertiary)",
          }}
        >
          {change.direction === "up" ? "+" : change.direction === "down" ? "-" : ""}
          {change.value}
        </div>
      )}
    </div>
  );
}
