import React from "react";
import type { LucideIcon } from "lucide-react";
import { SummaryCard } from "./PortalKit";

export interface StatCardProps {
  icon: LucideIcon;
  label: string;
  value: React.ReactNode;
  change?: { value: string; direction: "up" | "down" | "flat" };
  tone?: "brand" | "success" | "warning" | "danger" | "info";
}

export function StatCard({ icon: Icon, label, value, change, tone = "brand" }: StatCardProps) {
  const trend = change?.direction === "flat" ? "neutral" : change?.direction;
  const changeLabel = change
    ? `${change.direction === "up" ? "+" : change.direction === "down" ? "-" : ""}${change.value}`
    : undefined;
  return <SummaryCard
    label={label}
    value={value}
    icon={<Icon size={20} strokeWidth={2} />}
    tone={tone === "brand" ? undefined : tone}
    accent={tone === "brand"}
    change={changeLabel}
    trend={trend}
  />;
}
