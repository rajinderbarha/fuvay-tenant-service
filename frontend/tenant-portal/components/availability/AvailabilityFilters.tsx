"use client";
import React from "react";
import { Search, RotateCcw } from "lucide-react";
import { Card } from "../shared/ui";

const selectStyle: React.CSSProperties = {
  padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)",
  background: "var(--surface)", color: "var(--text-primary)", fontSize: 12.5,
};

export function AvailabilityFilters({
  search, onSearch, roleFilter, onRole, roles,
  availFilter, onAvail, capabilityFilter, onCapability, capabilities,
  timezone, onReset,
}: {
  search: string; onSearch: (v: string) => void;
  roleFilter: string; onRole: (v: string) => void; roles: string[];
  availFilter: "" | "available" | "unavailable"; onAvail: (v: "" | "available" | "unavailable") => void;
  capabilityFilter: string; onCapability: (v: string) => void; capabilities: string[];
  timezone: string | null; onReset: () => void;
}) {
  return (
    <Card style={{ marginBottom: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr 1fr 1fr auto", gap: 10, alignItems: "end" }}>
        <div>
          <label style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Search</label>
          <div style={{ position: "relative" }}>
            <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
            <input value={search} onChange={e => onSearch(e.target.value)} placeholder="Search technicians…"
              style={{ width: "100%", height: 36, padding: "0 12px 0 32px", fontSize: 12.5, background: "var(--surface-sunken)",
                border: "1px solid var(--border)", borderRadius: 8, color: "var(--text-primary)", outline: "none", boxSizing: "border-box" }}/>
          </div>
        </div>
        <div>
          <label htmlFor="availability-role" style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Role</label>
          <select id="availability-role" value={roleFilter} onChange={e => onRole(e.target.value)} style={{ ...selectStyle, width: "100%" }}>
            <option value="">All roles</option>
            {roles.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="availability-status" style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Availability</label>
          <select id="availability-status" value={availFilter} onChange={e => onAvail(e.target.value as "" | "available" | "unavailable")} style={{ ...selectStyle, width: "100%" }}>
            <option value="">All</option>
            <option value="available">Available</option>
            <option value="unavailable">Unavailable</option>
          </select>
        </div>
        <div>
          <label htmlFor="availability-capability" style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Capability</label>
          <select id="availability-capability" value={capabilityFilter} onChange={e => onCapability(e.target.value)} style={{ ...selectStyle, width: "100%" }}>
            <option value="">All</option>
            {capabilities.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="availability-timezone" style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Timezone</label>
          <select id="availability-timezone" value={timezone ?? ""} disabled style={{ ...selectStyle, width: "100%", opacity: 0.7 }}>
            <option value={timezone ?? ""}>{timezone ?? "—"}</option>
          </select>
        </div>
        <button onClick={onReset} style={{ display: "flex", alignItems: "center", gap: 6, height: 36, padding: "0 12px",
          borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-secondary)",
          fontSize: 12.5, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap" }}>
          <RotateCcw size={13}/> Reset
        </button>
      </div>
    </Card>
  );
}
