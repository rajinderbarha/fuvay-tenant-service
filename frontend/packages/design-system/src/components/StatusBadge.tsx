import React from "react";
import { CheckCircle2, Clock, XCircle, Circle, AlertTriangle, Info } from "lucide-react";
import { statusRegistry, type StatusKey, type Tone } from "../tokens/motion";

const toneStyle: Record<Tone, { bg: string; border: string; text: string; icon: React.ComponentType<{ size?: number }> }> = {
  success: { bg: "var(--success-bg)", border: "var(--success-border)", text: "var(--success-text)", icon: CheckCircle2 },
  warning: { bg: "var(--warning-bg)", border: "var(--warning-border)", text: "var(--warning-text)", icon: Clock },
  danger: { bg: "var(--danger-bg)", border: "var(--danger-border)", text: "var(--danger-text)", icon: XCircle },
  info: { bg: "var(--info-bg)", border: "var(--info-border)", text: "var(--info-text)", icon: Info },
  neutral: { bg: "var(--neutral-bg)", border: "var(--neutral-border)", text: "var(--neutral-text)", icon: Circle },
  brand: { bg: "var(--accent-muted)", border: "var(--brand)", text: "var(--brand)", icon: AlertTriangle },
};

export interface StatusBadgeProps {
  /** Any status string. Unrecognized values fall back to a safe neutral badge
   * showing the raw text, rather than throwing or rendering blank. */
  status: string;
  variant?: "badge" | "dot" | "tone-text";
  size?: "sm" | "md";
}

function humanize(status: string): string {
  return status
    .split(/[_-]/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function StatusBadge({ status, variant = "badge", size = "md" }: StatusBadgeProps) {
  const key = status?.toLowerCase().replace(/[\s-]/g, "_") as StatusKey;
  const entry = statusRegistry[key];
  const tone: Tone = entry?.tone ?? "neutral";
  const label = entry?.label ?? humanize(status || "Unknown");
  const s = toneStyle[tone];
  const Icon = s.icon;
  const fontSize = size === "sm" ? "0.625rem" : "0.6875rem";

  if (variant === "dot") {
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: "0.375rem", fontSize, color: s.text }}>
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: s.text }} aria-hidden="true" />
        {label}
      </span>
    );
  }
  if (variant === "tone-text") {
    return <span style={{ color: s.text, fontSize, fontWeight: 600 }}>{label}</span>;
  }
  return (
    <span
      className="ds-text-badge"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.25rem",
        padding: size === "sm" ? "0.125rem 0.5rem" : "0.1875rem 0.625rem",
        borderRadius: "var(--radius-full)",
        background: s.bg,
        border: `1px solid ${s.border}`,
        color: s.text,
        fontSize,
      }}
    >
      <Icon size={size === "sm" ? 10 : 12} />
      {label}
    </span>
  );
}
