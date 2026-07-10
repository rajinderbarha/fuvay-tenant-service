"use client";
import React, { useCallback } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { catalogApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import { ChevronRight, RefreshCw, XCircle, Copy, MapPin } from "lucide-react";

function copyText(t: string) { if (typeof navigator !== "undefined") navigator.clipboard?.writeText(t).catch(() => {}); }

function SectionError({ title, error, requestId, onRetry }: { title: string; error: string; requestId?: string | null; onRetry: () => void }) {
  return (
    <div style={{ padding: "16px 20px", background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--danger-text)", margin: "0 0 4px", display: "flex", alignItems: "center", gap: 6 }}><XCircle size={14}/> {title}</p>
          <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0, opacity: 0.85 }}>{error}</p>
          {requestId && <button onClick={() => copyText(requestId)} style={{ fontSize: 11, color: "var(--danger-text)", background: "none", border: "none", cursor: "pointer", padding: "4px 0 0" }}><Copy size={10} style={{ display: "inline", marginRight: 4 }}/>Request ID: {requestId}</button>}
        </div>
        <button onClick={onRetry} style={{ padding: "6px 12px", fontSize: 12, borderRadius: 8, border: "1px solid var(--danger-border)", background: "transparent", color: "var(--danger-text)", cursor: "pointer", display: "flex", alignItems: "center", gap: 5 }}><RefreshCw size={11}/> Retry</button>
      </div>
    </div>
  );
}

export default function AdminHomeServicesServiceAreasPage() {
  const tiersApi = useApi(useCallback(() => catalogApi.listTiers(true), []), []);
  const tiers = tiersApi.data?.tiers ?? [];

  return (
    <AdminLayout activeNav="hs-service-areas">
      <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}`}</style>
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 16, fontSize: 12, color: "var(--text-tertiary)" }}>
        <span>Admin</span><ChevronRight size={12}/><span>Home Services</span><ChevronRight size={12}/>
        <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>Service Areas / Zones</span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12, marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 4px" }}>Service Areas / Zones</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            Platform city tiers (Tier 1/2/3) used to scope Home Services pricing rules by zone. Tenant-level service areas are managed per-tenant.
          </p>
        </div>
        <button onClick={tiersApi.refetch} style={{ padding: "8px 14px", fontSize: 12, fontWeight: 600, borderRadius: 9, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-secondary)", cursor: "pointer", display: "flex", alignItems: "center", gap: 5 }}><RefreshCw size={12}/> Refresh</button>
      </div>

      {tiersApi.error ? (
        <SectionError title="We couldn't load service areas / zones" error={tiersApi.error} requestId={tiersApi.requestId} onRetry={tiersApi.refetch}/>
      ) : tiersApi.loading ? (
        <div style={{ height: 160, background: "var(--surface-sunken)", borderRadius: 12, animation: "pulse 1.5s ease-in-out infinite" }}/>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 12 }}>
          {tiers.map(t => (
            <div key={t.tier_id} style={{ padding: "14px 16px", borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <MapPin size={14} style={{ color: "var(--brand)" }}/>
                <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>{t.name}</span>
              </div>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 6px" }}>{t.tier_type}</p>
              <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: 0 }}>
                {t.linked_counts?.cities ?? 0} cities · {t.linked_counts?.zipcodes ?? 0} zipcodes · {t.linked_counts?.rules_active ?? 0} active pricing rules
              </p>
            </div>
          ))}
          {tiers.length === 0 && <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>No tiers configured yet.</p>}
        </div>
      )}

      <div style={{ marginTop: 20 }}>
        <a href="/admin/pricing-tiers" style={{ fontSize: 12, color: "var(--brand)", textDecoration: "none" }}>Manage tier definitions and city/zipcode mapping →</a>
      </div>
    </AdminLayout>
  );
}
