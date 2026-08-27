"use client";
/** Home Services Customers -- KPI strip. Every value is a real field from
 * GET /v1/tenant/home-services/customers/summary. The reference design's
 * "Payment attention" KPI is NOT included -- the backend explicitly marks
 * payment-reliability review as NOT_IMPLEMENTED (no canonical payment-
 * confirmation-mismatch model exists), so it is never fabricated as a
 * number here. */
import { Users, UserCheck, RefreshCcw, Star, ShieldAlert } from "lucide-react";
import { KpiGrid, SummaryCard } from "../shared/ui";
import type { HsCustomerSummary } from "../../lib/api";

export function CustomerKpis({ summary }: { summary: HsCustomerSummary }) {
  return (
    <KpiGrid minCardWidth={150} style={{ margin: "20px 0" }}>
      <SummaryCard label="Total customers" value={summary.total_customers} icon={<Users size={16}/>}/>
      <SummaryCard label="Active" value={summary.active_customers} icon={<UserCheck size={16}/>} tone="success"/>
      <SummaryCard label="Repeat customers" value={summary.repeat_customers} icon={<RefreshCcw size={16}/>} tone="info"/>
      <SummaryCard label="New this month" value={summary.new_customers} icon={<Star size={16}/>} tone="info"/>
      <SummaryCard label="Open complaints" value={summary.open_complaints} icon={<ShieldAlert size={16}/>} tone={summary.open_complaints > 0 ? "danger" : undefined}/>
      <SummaryCard label="One-time customers" value={summary.one_time_customers} icon={<Users size={16}/>} tone="warning"/>
    </KpiGrid>
  );
}
