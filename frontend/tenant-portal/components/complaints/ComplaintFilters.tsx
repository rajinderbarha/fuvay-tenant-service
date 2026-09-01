"use client";
import { Card } from "../shared/ui";
import EnterpriseFilterBar from "../enterprise/EnterpriseFilterBar";

export function ComplaintFilters({
  search, onSearch, status, onStatus, severity, onSeverity, slaState, onSlaState,
  statusOptions,
}: {
  search: string; onSearch: (v: string) => void;
  status: string; onStatus: (v: string) => void;
  severity: string; onSeverity: (v: string) => void;
  slaState: string; onSlaState: (v: string) => void;
  statusOptions: string[];
}) {
  return (
    <Card style={{ marginBottom: 16 }}>
      <EnterpriseFilterBar
        searchValue={search}
        onSearch={onSearch}
        filters={[
          { key: "status", label: "Status", type: "select", options: statusOptions.map(value => ({ value, label: value.replace(/_/g, " ") })) },
          { key: "severity", label: "Severity", type: "select", options: ["low", "medium", "high", "critical"].map(value => ({ value, label: value[0].toUpperCase() + value.slice(1) })) },
          { key: "slaState", label: "SLA", type: "select", options: [{ value: "on_time", label: "On time" }, { value: "at_risk", label: "At risk" }, { value: "breached", label: "Breached" }, { value: "escalated", label: "Escalated" }] },
        ]}
        values={{ status, severity, slaState }}
        onChange={(key, value) => key === "status" ? onStatus(value) : key === "severity" ? onSeverity(value) : onSlaState(value)}
        onReset={() => { onSearch(""); onStatus(""); onSeverity(""); onSlaState(""); }}
      />
    </Card>
  );
}
