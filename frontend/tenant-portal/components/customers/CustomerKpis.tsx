"use client";
/** Home Services Customers -- KPI strip. Every value is a real field from
 * GET /v1/tenant/home-services/customers/summary. The reference design's
 * "Payment attention" KPI is NOT included -- the backend explicitly marks
 * payment-reliability review as NOT_IMPLEMENTED (no canonical payment-
 * confirmation-mismatch model exists), so it is never fabricated as a
 * number here. */
import React from "react";
import { Users, UserCheck, RefreshCcw, Star, ShieldAlert } from "lucide-react";
import { Card } from "../shared/ui";
import type { HsCustomerSummary } from "../../lib/api";

function KpiCard({ label, value, icon, variant }: {
  label: string; value: number | string; icon: React.ReactNode;
  variant: "default" | "success" | "info" | "warning" | "danger";
}) {
  const colors: Record<string, { fg: string; bg: string }> = {
    default: { fg: "var(--text-secondary)", bg: "var(--surface-sunken)" },
    success: { fg: "var(--success-text)", bg: "var(--success-bg)" },
    info:    { fg: "var(--info-text)", bg: "var(--info-bg)" },
    warning: { fg: "var(--warning-text)", bg: "var(--warning-bg)" },
    danger:  { fg: "var(--danger-text)", bg: "var(--danger-bg)" },
  };
  const c = colors[variant];
  return (
    <Card style={{ flex: "1 1 150px", minWidth: 140 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
        <span style={{ width: 32, height: 32, borderRadius: "50%", background: c.bg, color: c.fg,
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
          {icon}
        </span>
        <p style={{ fontSize: 12.5, color: "var(--text-tertiary)", margin: 0, fontWeight: 600 }}>{label}</p>
      </div>
      <p style={{ fontSize: 26, fontWeight: 800, color: c.fg, margin: 0 }}>{value}</p>
    </Card>
  );
}

export function CustomerKpis({ summary }: { summary: HsCustomerSummary }) {
  return (
    <div style={{ display: "flex", gap: 14, flexWrap: "wrap", margin: "20px 0" }}>
      <KpiCard label="Total customers" value={summary.total_customers} icon={<Users size={16}/>} variant="default"/>
      <KpiCard label="Active" value={summary.active_customers} icon={<UserCheck size={16}/>} variant="success"/>
      <KpiCard label="Repeat customers" value={summary.repeat_customers} icon={<RefreshCcw size={16}/>} variant="info"/>
      <KpiCard label="New this month" value={summary.new_customers} icon={<Star size={16}/>} variant="info"/>
      <KpiCard label="Open complaints" value={summary.open_complaints} icon={<ShieldAlert size={16}/>} variant={summary.open_complaints > 0 ? "danger" : "default"}/>
      <KpiCard label="One-time customers" value={summary.one_time_customers} icon={<Users size={16}/>} variant="warning"/>
    </div>
  );
}
