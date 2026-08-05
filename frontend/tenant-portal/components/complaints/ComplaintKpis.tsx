"use client";
import React from "react";
import { MessageCircle, Clock3, AlertTriangle, ShieldAlert, TimerOff, CheckCircle2 } from "lucide-react";
import { Card } from "../shared/ui";
import type { ComplaintQueueSummary } from "../../lib/api";

function KpiCard({ label, value, icon, variant }: {
  label: string; value: number; icon: React.ReactNode;
  variant: "default" | "warning" | "danger" | "success";
}) {
  const colors: Record<string, { fg: string; bg: string }> = {
    default: { fg: "var(--info-text)", bg: "var(--info-bg)" },
    warning: { fg: "var(--warning-text)", bg: "var(--warning-bg)" },
    danger:  { fg: "var(--danger-text)", bg: "var(--danger-bg)" },
    success: { fg: "var(--success-text)", bg: "var(--success-bg)" },
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

export function ComplaintKpis({ summary }: { summary: ComplaintQueueSummary }) {
  return (
    <div style={{ display: "flex", gap: 14, flexWrap: "wrap", margin: "20px 0" }}>
      <KpiCard label="Open" value={summary.open} icon={<MessageCircle size={16}/>} variant="default"/>
      <KpiCard label="Awaiting response" value={summary.awaiting_response} icon={<Clock3 size={16}/>} variant="warning"/>
      <KpiCard label="At risk" value={summary.at_risk} icon={<AlertTriangle size={16}/>} variant={summary.at_risk > 0 ? "warning" : "default"}/>
      <KpiCard label="Escalated" value={summary.escalated} icon={<ShieldAlert size={16}/>} variant={summary.escalated > 0 ? "danger" : "default"}/>
      <KpiCard label="SLA breached" value={summary.sla_breached} icon={<TimerOff size={16}/>} variant={summary.sla_breached > 0 ? "danger" : "default"}/>
      <KpiCard label="Resolved this month" value={summary.resolved_this_month} icon={<CheckCircle2 size={16}/>} variant="success"/>
    </div>
  );
}
