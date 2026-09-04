"use client";
import React from "react";
import { MessageCircle, Clock3, AlertTriangle, ShieldAlert, TimerOff, CheckCircle2 } from "lucide-react";
import { KpiGrid, SummaryCard } from "../shared/ui";
import type { ComplaintQueueSummary } from "../../lib/api";

export function ComplaintKpis({ summary }: { summary: ComplaintQueueSummary }) {
  return (
    <KpiGrid className="complaints-kpis" minCardWidth={160} style={{ margin: 0, gap: 10 }}>
      <SummaryCard label="Open" value={summary.open} icon={<MessageCircle size={16}/>} tone="info"/>
      <SummaryCard label="Awaiting response" value={summary.awaiting_response} icon={<Clock3 size={16}/>} tone="warning"/>
      <SummaryCard label="At risk" value={summary.at_risk} icon={<AlertTriangle size={16}/>} tone={summary.at_risk > 0 ? "warning" : "info"}/>
      <SummaryCard label="Escalated" value={summary.escalated} icon={<ShieldAlert size={16}/>} tone={summary.escalated > 0 ? "danger" : "info"}/>
      <SummaryCard label="SLA breached" value={summary.breached} icon={<TimerOff size={16}/>} tone={summary.breached > 0 ? "danger" : "info"}/>
      <SummaryCard label="Resolved this month" value={summary.resolved_this_month} icon={<CheckCircle2 size={16}/>} tone="success"/>
    </KpiGrid>
  );
}
