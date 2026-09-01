"use client";
/** Availability & Capacity — KPI strip. Dedicated component, not the generic
 * @serviceos/design-system Card -- matches the Dispatch Board's icon-circle
 * KPI style so the two Home Services planning pages look like one system. */
import React from "react";
import { CheckCircle2, UserX, Briefcase, ClipboardList, RefreshCcw, AlertTriangle } from "lucide-react";
import { KpiGrid, SummaryCard } from "../shared/ui";

export interface AvailabilityKpiValues {
  availableToday: number;
  onLeave: number;
  totalCapacity: number;
  assigned: number;
  remaining: number;
  conflicts: number;
}

export function AvailabilityKpis({ values, dateLabel = "today" }: { values: AvailabilityKpiValues; dateLabel?: string }) {
  return (
    <KpiGrid minCardWidth={150} style={{ margin: "20px 0" }}>
      <SummaryCard label={`Available ${dateLabel}`} value={values.availableToday} icon={<CheckCircle2 size={16}/>} tone="success" />
      <SummaryCard label={`On leave ${dateLabel}`} value={values.onLeave} icon={<UserX size={16}/>} />
      <SummaryCard label="Total capacity" value={values.totalCapacity} icon={<Briefcase size={16}/>} tone="info" />
      <SummaryCard label="Assigned" value={values.assigned} icon={<ClipboardList size={16}/>} />
      <SummaryCard label="Remaining" value={values.remaining} icon={<RefreshCcw size={16}/>} tone="success" />
      <SummaryCard label="Conflicts" value={values.conflicts} icon={<AlertTriangle size={16}/>} tone={values.conflicts > 0 ? "danger" : undefined} />
    </KpiGrid>
  );
}
