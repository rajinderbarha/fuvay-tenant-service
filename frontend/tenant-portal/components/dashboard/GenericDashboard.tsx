"use client";
import React, { useCallback } from "react";
import { Building2, AlertCircle, Layers } from "lucide-react";
import { Card, Badge } from "../shared/ui";
import { categoryDashboardApi } from "../../lib/api";
import { useApi } from "../../hooks/useApi";
import { BookabilityStatusWidget } from "./BookabilityStatusWidget";
import { MarketingLaunchWidget } from "./MarketingLaunchWidget";

export function GenericDashboard() {
  const runtime = useApi(useCallback(() => categoryDashboardApi.getRuntime(), []));
  const data = runtime.data;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* Bookability status widget */}
      <BookabilityStatusWidget />

      {/* Marketing launch widget */}
      <MarketingLaunchWidget />

      {/* Warning banner */}
      <div style={{
        display: "flex", alignItems: "flex-start", gap: 14,
        padding: "16px 20px", borderRadius: 12,
        background: "var(--warning-bg, rgba(250,170,0,0.08))",
        border: "1px solid var(--warning-border, rgba(250,170,0,0.25))",
      }}>
        <AlertCircle size={20} style={{ color: "var(--warning, #f0a000)", flexShrink: 0, marginTop: 1 }}/>
        <div>
          <p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
            Category Dashboard Not Configured
          </p>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--text-secondary)" }}>
            Your business category has not been fully configured yet.
            Contact your admin to assign a dashboard type.
          </p>
        </div>
      </div>

      {runtime.loading ? (
        <Card>
          <div style={{ padding: "24px", color: "var(--text-tertiary)", fontSize: 14 }}>Loading…</div>
        </Card>
      ) : data ? (
        <>
          {/* Category info */}
          <Card>
            <div style={{ padding: "20px 24px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
                <Building2 size={18} style={{ color: "var(--accent)" }}/>
                <span style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)" }}>
                  Business Profile
                </span>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <InfoRow label="Business Name"  value={data.tenant?.business_name ?? "—"}/>
                <InfoRow label="Category"       value={data.tenant?.category?.name ?? "Uncategorised"}/>
                <InfoRow label="Dashboard Type" value={data.dashboard_type ?? "generic_dashboard"}/>
                <InfoRow label="Primary Engine" value={data.primary_engine ?? "—"}/>
              </div>
            </div>
          </Card>

          {/* Enabled engines */}
          {data.enabled_engines && data.enabled_engines.length > 0 && (
            <Card>
              <div style={{ padding: "20px 24px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
                  <Layers size={18} style={{ color: "var(--accent)" }}/>
                  <span style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)" }}>
                    Enabled Engines ({data.enabled_engines.length})
                  </span>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {data.enabled_engines.map((key: string) => (
                    <Badge key={key} variant="info">{key}</Badge>
                  ))}
                </div>
              </div>
            </Card>
          )}
        </>
      ) : (
        <Card>
          <div style={{ padding: "32px 24px", textAlign: "center", color: "var(--text-tertiary)", fontSize: 14 }}>
            No dashboard data available.
          </div>
        </Card>
      )}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p style={{ margin: 0, fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
        {label}
      </p>
      <p style={{ margin: "3px 0 0", fontSize: 14, color: "var(--text-primary)", fontWeight: 500 }}>
        {value}
      </p>
    </div>
  );
}
