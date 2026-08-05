"use client";
import React from "react";
import { Search } from "lucide-react";
import { Card } from "../shared/ui";

const selectStyle: React.CSSProperties = {
  padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)",
  background: "var(--surface)", color: "var(--text-primary)", fontSize: 12.5,
};

export function CustomerFilters({
  search, onSearch, activity, onActivity, repeatStatus, onRepeatStatus,
}: {
  search: string; onSearch: (v: string) => void;
  activity: "" | "active" | "inactive"; onActivity: (v: "" | "active" | "inactive") => void;
  repeatStatus: "" | "repeat" | "one_time" | "none"; onRepeatStatus: (v: "" | "repeat" | "one_time" | "none") => void;
}) {
  return (
    <Card style={{ marginBottom: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr 1fr", gap: 10, alignItems: "end" }}>
        <div>
          <label style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Search</label>
          <div style={{ position: "relative" }}>
            <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
            <input value={search} onChange={e => onSearch(e.target.value)} placeholder="Search by customer alias…"
              style={{ width: "100%", height: 36, padding: "0 12px 0 32px", fontSize: 12.5, background: "var(--surface-sunken)",
                border: "1px solid var(--border)", borderRadius: 8, color: "var(--text-primary)", outline: "none", boxSizing: "border-box" }}/>
          </div>
        </div>
        <div>
          <label style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Activity</label>
          <select value={activity} onChange={e => onActivity(e.target.value as typeof activity)} style={{ ...selectStyle, width: "100%" }}>
            <option value="">All</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
        <div>
          <label style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Customer type</label>
          <select value={repeatStatus} onChange={e => onRepeatStatus(e.target.value as typeof repeatStatus)} style={{ ...selectStyle, width: "100%" }}>
            <option value="">All</option>
            <option value="repeat">Repeat</option>
            <option value="one_time">One-time</option>
            <option value="none">No completed jobs yet</option>
          </select>
        </div>
      </div>
    </Card>
  );
}
