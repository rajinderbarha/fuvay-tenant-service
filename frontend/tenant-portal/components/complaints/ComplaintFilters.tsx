"use client";
import React from "react";
import { Search } from "lucide-react";
import { Card } from "../shared/ui";

const selectStyle: React.CSSProperties = {
  padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)",
  background: "var(--surface)", color: "var(--text-primary)", fontSize: 12.5,
};

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
      <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr 1fr 1fr", gap: 10, alignItems: "end" }}>
        <div>
          <label style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Search</label>
          <div style={{ position: "relative" }}>
            <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
            <input value={search} onChange={e => onSearch(e.target.value)} placeholder="Search complaints…"
              style={{ width: "100%", height: 36, padding: "0 12px 0 32px", fontSize: 12.5, background: "var(--surface-sunken)",
                border: "1px solid var(--border)", borderRadius: 8, color: "var(--text-primary)", outline: "none", boxSizing: "border-box" }}/>
          </div>
        </div>
        <div>
          <label style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Status</label>
          <select value={status} onChange={e => onStatus(e.target.value)} style={{ ...selectStyle, width: "100%" }}>
            <option value="">All</option>
            {statusOptions.map(s => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
          </select>
        </div>
        <div>
          <label style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Severity</label>
          <select value={severity} onChange={e => onSeverity(e.target.value)} style={{ ...selectStyle, width: "100%" }}>
            <option value="">All</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>
        <div>
          <label style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>SLA</label>
          <select value={slaState} onChange={e => onSlaState(e.target.value)} style={{ ...selectStyle, width: "100%" }}>
            <option value="">All</option>
            <option value="on_time">On time</option>
            <option value="at_risk">At risk</option>
            <option value="breached">Breached</option>
            <option value="escalated">Escalated</option>
          </select>
        </div>
      </div>
    </Card>
  );
}
