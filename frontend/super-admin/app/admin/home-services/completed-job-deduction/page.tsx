"use client";
import React, { useCallback } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { homeServicesCatalogConsoleApi, catalogApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import { ChevronRight, RefreshCw, XCircle, Copy, Info } from "lucide-react";

const safeText = (v: unknown, fb = "Not configured"): string => (typeof v === "string" && v.trim()) ? v.trim() : fb;
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

export default function AdminHomeServicesCompletedJobDeductionPage() {
  const servicesApi = useApi(useCallback(() => homeServicesCatalogConsoleApi.listServices(), []), []);
  const rulesApi = useApi(useCallback(() => catalogApi.listPricingRules(undefined, { pageSize: 200 }), []), []);

  const services = servicesApi.data?.services ?? [];
  const homeServiceIds = new Set(services.map(s => s.service_id));
  const rules = (rulesApi.data?.items ?? []).filter(r => homeServiceIds.has(r.master_service_id));

  function serviceName(id: string): string { return services.find(s => s.service_id === id)?.service_name ?? "Not configured"; }

  return (
    <AdminLayout activeNav="hs-completed-job-deduction">
      <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}`}</style>
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 16, fontSize: 12, color: "var(--text-tertiary)" }}>
        <span>Admin</span><ChevronRight size={12}/><span>Home Services</span><ChevronRight size={12}/>
        <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>Completed Job Deduction</span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12, marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 4px" }}>Completed Job Deduction</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            Usage credits deducted from the provider's balance per completed job, configured per pricing rule.
          </p>
        </div>
        <button onClick={() => { servicesApi.refetch(); rulesApi.refetch(); }} style={{ padding: "8px 14px", fontSize: 12, fontWeight: 600, borderRadius: 9, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-secondary)", cursor: "pointer", display: "flex", alignItems: "center", gap: 5 }}><RefreshCw size={12}/> Refresh</button>
      </div>

      <div style={{ marginBottom: 16, padding: "11px 15px", borderRadius: 10, background: "var(--surface-sunken)", border: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)", display: "flex", gap: 8 }}>
        <Info size={13} style={{ flexShrink: 0, marginTop: 1 }}/>
        Since customers pay providers directly (no platform-collected payment), Usage Credits deducted per completed job are how the platform charges providers for bookings. Edit deduction credits from the Pricing Rules screen.
      </div>

      {(rulesApi.error || servicesApi.error) ? (
        <SectionError title="We couldn't load deduction data" error={rulesApi.error ?? servicesApi.error ?? ""} requestId={rulesApi.requestId ?? servicesApi.requestId} onRetry={() => { rulesApi.refetch(); servicesApi.refetch(); }}/>
      ) : rulesApi.loading || servicesApi.loading ? (
        <div style={{ height: 160, background: "var(--surface-sunken)", borderRadius:"var(--radius-lg)", animation: "pulse 1.5s ease-in-out infinite" }}/>
      ) : (
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                {["Service", "Scope", "Completed Job Deduction", "Status"].map(h => (
                  <th key={h} style={{ padding: "9px 12px", textAlign: "left", fontSize: 10, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rules.map(r => (
                <tr key={r.rule_id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "9px 12px", fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{serviceName(r.master_service_id)}</td>
                  <td style={{ padding: "9px 12px", fontSize: 12, color: "var(--text-secondary)" }}>{r.service_type_id ? "Type-scoped" : r.brand_id ? "Brand-scoped" : "All"}</td>
                  <td style={{ padding: "9px 12px", fontSize: 12 }}>{r.completed_job_deduction_credits ?? 0} usage credits</td>
                  <td style={{ padding: "9px 12px" }}>
                    <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 999, background: r.is_active ? "var(--success-bg)" : "var(--surface-sunken)", color: r.is_active ? "var(--success-text)" : "var(--text-tertiary)" }}>{r.is_active ? "Active" : "Inactive"}</span>
                  </td>
                </tr>
              ))}
              {rules.length === 0 && <tr><td colSpan={4} style={{ padding: 20, textAlign: "center", fontSize: 12, color: "var(--text-tertiary)" }}>No rules configured yet.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
          Deduction credits were configured via the now-retired Pricing Rules admin screen —
          existing values above are historical. There is no current admin path to edit them.
        </p>
      </div>
    </AdminLayout>
  );
}
