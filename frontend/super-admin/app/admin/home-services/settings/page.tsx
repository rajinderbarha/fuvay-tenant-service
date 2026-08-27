"use client";
import React, { useCallback } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { autoPriceOptionsApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import { ChevronRight, RefreshCw, XCircle, Copy, CheckCircle2 } from "lucide-react";
import { Btn, SectionHeader } from "../../../../components/shared/ui";

function copyText(t: string) { if (typeof navigator !== "undefined") navigator.clipboard?.writeText(t).catch(() => {}); }

function SectionError({ title, error, requestId, onRetry }: { title: string; error: string; requestId?: string | null; onRetry: () => void }) {
  return (
    <div style={{ padding: "16px 20px", background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius:"var(--radius-lg)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--danger-text)", margin: "0 0 4px", display: "flex", alignItems: "center", gap: 6 }}><XCircle size={14}/> {title}</p>
          <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0, opacity: 0.85 }}>{error}</p>
          {requestId && <button onClick={() => copyText(requestId)} style={{ fontSize: 11, color: "var(--danger-text)", background: "none", border: "none", cursor: "pointer", padding: "4px 0 0" }}><Copy size={10} style={{ display: "inline", marginRight: 4 }}/>Request ID: {requestId}</button>}
        </div>
        <button onClick={onRetry} style={{ padding: "6px 12px", fontSize: 12, borderRadius:"var(--radius-md)", border: "1px solid var(--danger-border)", background: "transparent", color: "var(--danger-text)", cursor: "pointer", display: "flex", alignItems: "center", gap: 5 }}><RefreshCw size={11}/> Retry</button>
      </div>
    </div>
  );
}

function FlagRow({ label, on, description }: { label: string; on: boolean; description: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface)" }}>
      <div>
        <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 2px" }}>{label}</p>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{description}</p>
      </div>
      <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 999, display: "flex", alignItems: "center", gap: 5,
        background: on ? "var(--success-bg)" : "var(--surface-sunken)", color: on ? "var(--success-text)" : "var(--text-tertiary)",
        border: `1px solid ${on ? "var(--success-border)" : "var(--border)"}` }}>
        {on && <CheckCircle2 size={11}/>} {on ? "Enabled" : "Disabled"}
      </span>
    </div>
  );
}

export default function AdminHomeServicesSettingsPage() {
  const configApi = useApi(useCallback(() => autoPriceOptionsApi.getConfig(), []), []);
  const cfg = configApi.data;

  return (
    <AdminLayout activeNav="hs-settings">
      <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}`}</style>
      <div style={{ marginBottom: "var(--layout-page-gap)" }}>
        <SectionHeader eyebrow="Platform controls" context="Home Services" title="Home Services Settings"
          description="Platform-level feature flags controlling how pricing and matching work for the Home Services vertical."
          actions={<Btn variant="secondary" onClick={configApi.refetch}><RefreshCw size={12}/> Refresh</Btn>} />
      </div>

      {configApi.error ? (
        <SectionError title="We couldn't load Home Services settings" error={configApi.error} requestId={configApi.requestId} onRetry={configApi.refetch}/>
      ) : configApi.loading || !cfg ? (
        <div style={{ height: 160, background: "var(--surface-sunken)", borderRadius:"var(--radius-lg)", animation: "pulse 1.5s ease-in-out infinite" }}/>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <FlagRow label="Matching Engine Diagnostics" on={cfg.auto_price_options_enabled}
            description="System diagnostics are enabled for provider eligibility, scoring, and readiness. Tier-based customer price options are retired."/>
          <FlagRow label="Manual Bargain Rules" on={cfg.manual_bargain_rules_enabled}
            description="Legacy manual bargain-rule authoring. Disabled for the provider-owned pricing model."/>
          <FlagRow label="Provider-First Booking Engine" on={cfg.provider_first_matching_enabled}
            description="Customers are matched to the best-ranked provider before confirming the provider-owned price."/>
          <FlagRow label="Home Services Only" on={cfg.home_services_only}
            description="This pricing/matching flow is hard-scoped to the Home Services vertical and cannot affect other verticals."/>
        </div>
      )}
    </AdminLayout>
  );
}
