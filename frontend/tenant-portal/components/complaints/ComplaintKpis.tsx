"use client";
import React from "react";
import { MessageCircle, Clock3, AlertTriangle, ShieldAlert, TimerOff, CheckCircle2 } from "lucide-react";
import { KpiGrid, SummaryCard } from "../shared/ui";
import type { ComplaintQueueSummary } from "../../lib/api";

function KpiCard({ label, value, icon, variant }: {
  label: string; value: number; icon: React.ReactNode;
  variant: "default" | "warning" | "danger" | "success";
}) {
  return <SummaryCard label={label} value={value} icon={icon} tone={variant === "default" ? "info" : variant} />;
}

export function ComplaintKpis({ summary }: { summary: ComplaintQueueSummary }) {
  return (
    <KpiGrid minCardWidth={150} style={{ margin: "20px 0" }}>
      <KpiCard label="Open" value={summary.open} icon={<MessageCircle size={16}/>} variant="default"/>
      <KpiCard label="Awaiting response" value={summary.awaiting_response} icon={<Clock3 size={16}/>} variant="warning"/>
      <KpiCard label="At risk" value={summary.at_risk} icon={<AlertTriangle size={16}/>} variant={summary.at_risk > 0 ? "warning" : "default"}/>
      <KpiCard label="Escalated" value={summary.escalated} icon={<ShieldAlert size={16}/>} variant={summary.escalated > 0 ? "danger" : "default"}/>
      <KpiCard label="SLA breached" value={summary.breached} icon={<TimerOff size={16}/>} variant={summary.breached > 0 ? "danger" : "default"}/>
      <KpiCard label="Resolved this month" value={summary.resolved_this_month} icon={<CheckCircle2 size={16}/>} variant="success"/>
    </KpiGrid>
  );
}
