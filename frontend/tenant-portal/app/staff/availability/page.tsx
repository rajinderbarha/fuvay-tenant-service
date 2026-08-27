"use client";
import { TableSurface } from "@serviceos/design-system";
import React, { useCallback } from "react";
import { StaffLayout } from "../../../components/layout/StaffLayout";
import { Card, StatCard, Badge, Skeleton, EmptyState } from "../../../components/shared/ui";
import { useApi } from "../../../hooks/useApi";
import { providerAvailabilityApi } from "../../../lib/api";
import { Clock } from "lucide-react";

const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export default function StaffAvailabilityPage() {
  const rules = useApi(useCallback(() => providerAvailabilityApi.list(), []));
  const list = rules.data?.rules ?? [];

  return (
    <StaffLayout activeNav="availability">
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>My Availability</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
          Working hours configured for your business. View only — contact your tenant admin to request a schedule change.
        </p>
      </div>

      <div style={{ marginBottom: 20 }}>
        {rules.loading ? <Skeleton height={92}/> : <StatCard label="Configured Working-Hour Rules" value={list.length} icon={<Clock/>}/>}
      </div>

      <Card padding={0}>
        {rules.loading ? <Skeleton height={140}/> : rules.error ? (
          <div style={{ padding: 20 }}>
            <p style={{ color: "var(--danger-text)", fontSize: 13 }}>{rules.error}{rules.requestId && ` — Request ID: ${rules.requestId}`}</p>
          </div>
        ) : list.length === 0 ? (
          <EmptyState icon={<Clock/>} title="No availability configured yet."
            description="Your tenant admin sets your working hours."/>
        ) : (
          <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["Day", "Start Time", "End Time", "Status"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {list.map((r, i) => (
                <tr key={r.id ?? i} style={{ borderBottom: "1px solid var(--border-subtle, var(--border))" }}>
                  <td style={{ padding: "10px 16px" }}>{DAYS[r.day_of_week] ?? r.day_of_week}</td>
                  <td style={{ padding: "10px 16px" }}>{r.start_time}</td>
                  <td style={{ padding: "10px 16px" }}>{r.end_time}</td>
                  <td style={{ padding: "10px 16px" }}><Badge variant={r.is_active ? "success" : "muted"} size="sm">{r.is_active ? "Active" : "Inactive"}</Badge></td>
                </tr>
              ))}
            </tbody>
          </TableSurface>
        )}
      </Card>
    </StaffLayout>
  );
}
