"use client";
/** Availability & Capacity — KPI strip. Dedicated component, not the generic
 * @serviceos/design-system Card -- matches the Dispatch Board's icon-circle
 * KPI style so the two Home Services planning pages look like one system. */
import React from "react";
import { CheckCircle2, UserX, Briefcase, ClipboardList, RefreshCcw, AlertTriangle } from "lucide-react";
import { Card } from "../shared/ui";

export interface AvailabilityKpiValues {
  availableToday: number;
  onLeave: number;
  totalCapacity: number;
  assigned: number;
  remaining: number;
  conflicts: number;
}

function KpiCard({ label, value, icon, variant }: {
  label: string; value: number; icon: React.ReactNode;
  variant: "success" | "default" | "info" | "indigo" | "warning" | "danger";
}) {
  const colors: Record<string, { fg: string; bg: string }> = {
    success: { fg: "var(--success-text)", bg: "var(--success-bg)" },
    default: { fg: "var(--text-secondary)", bg: "var(--surface-sunken)" },
    info:    { fg: "var(--info-text)", bg: "var(--info-bg)" },
    indigo:  { fg: "var(--accent)", bg: "var(--accent-muted)" },
    warning: { fg: "var(--warning-text)", bg: "var(--warning-bg)" },
    danger:  { fg: "var(--danger-text)", bg: "var(--danger-bg)" },
  };
  const c = colors[variant];
  return (
    <Card style={{ flex: "1 1 150px", minWidth: 140 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
        <span style={{ width: 30, height: 30, borderRadius: "50%", background: c.bg, color: c.fg,
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
          {icon}
        </span>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0, fontWeight: 600 }}>{label}</p>
      </div>
      <p style={{ fontSize: 24, fontWeight: 800, color: c.fg, margin: 0 }}>{value}</p>
    </Card>
  );
}

export function AvailabilityKpis({ values }: { values: AvailabilityKpiValues }) {
  return (
    <div style={{ display: "flex", gap: 14, flexWrap: "wrap", margin: "20px 0" }}>
      <KpiCard label="Available today" value={values.availableToday} icon={<CheckCircle2 size={16}/>} variant="success" />
      <KpiCard label="On leave" value={values.onLeave} icon={<UserX size={16}/>} variant="default" />
      <KpiCard label="Total capacity" value={values.totalCapacity} icon={<Briefcase size={16}/>} variant="info" />
      <KpiCard label="Assigned" value={values.assigned} icon={<ClipboardList size={16}/>} variant="indigo" />
      <KpiCard label="Remaining" value={values.remaining} icon={<RefreshCcw size={16}/>} variant="success" />
      <KpiCard label="Conflicts" value={values.conflicts} icon={<AlertTriangle size={16}/>} variant={values.conflicts > 0 ? "danger" : "default"} />
    </div>
  );
}
