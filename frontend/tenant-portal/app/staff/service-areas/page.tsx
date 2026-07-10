"use client";
import React, { useCallback } from "react";
import { StaffLayout } from "../../../components/layout/StaffLayout";
import { Card, StatCard, Badge, Skeleton, EmptyState } from "../../../components/shared/ui";
import { useApi } from "../../../hooks/useApi";
import { staffSelfApi } from "../../../lib/api";
import { MapPin } from "lucide-react";

export default function StaffServiceAreasPage() {
  const areas = useApi(useCallback(() => staffSelfApi.getServiceAreas(), []));
  const list = areas.data?.areas ?? [];

  return (
    <StaffLayout activeNav="service-areas">
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>Service Areas</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
          Areas your provider business is configured to serve. View only — contact your tenant admin to change coverage.
        </p>
      </div>

      <div style={{ marginBottom: 20 }}>
        {areas.loading ? <Skeleton height={92}/> : <StatCard label="Total Service Areas" value={areas.data?.total ?? 0} icon={<MapPin/>}/>}
      </div>

      <Card padding={0}>
        {areas.loading ? <Skeleton height={140}/> : areas.error ? (
          <div style={{ padding: 20 }}>
            <p style={{ color: "var(--danger-text)", fontSize: 13 }}>{areas.error}{areas.requestId && ` — Request ID: ${areas.requestId}`}</p>
          </div>
        ) : list.length === 0 ? (
          <EmptyState icon={<MapPin/>} title="No service areas configured yet."
            description="Your tenant admin configures which cities/zipcodes your business serves."/>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["City", "Zipcode", "Coverage Type", "Status"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {list.map((a, i) => (
                <tr key={i} style={{ borderBottom: "1px solid var(--border-subtle, var(--border))" }}>
                  <td style={{ padding: "10px 16px" }}>{String(a.city ?? "—")}</td>
                  <td style={{ padding: "10px 16px" }}>{String(a.zipcode ?? "—")}</td>
                  <td style={{ padding: "10px 16px" }}>{String(a.coverage_type ?? "—")}</td>
                  <td style={{ padding: "10px 16px" }}><Badge variant={a.is_active ? "success" : "muted"} size="sm">{a.is_active ? "Active" : "Inactive"}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </StaffLayout>
  );
}
