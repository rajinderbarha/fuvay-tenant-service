"use client";
import { useState, useCallback } from "react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { engineApi } from "../../../../lib/api";
import type { TenantEffectiveEngine } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import { CheckCircle2, XCircle, RefreshCw, Info } from "lucide-react";

const SOURCE_LABEL: Record<string, string> = {
  global:              "Platform Default",
  category:            "Your Category",
  package_entitlement: "Your Package",
  tenant_override:     "Admin Override",
};

const SOURCE_COLOR: Record<string, string> = {
  global:              "#64748b",
  category:            "#7c3aed",
  package_entitlement: "#0369a1",
  tenant_override:     "#b45309",
};

function HealthDot({ status }: { status: string }) {
  const color =
    status === "healthy"  ? "#22c55e" :
    status === "degraded" ? "#eab308" :
    status === "down"     ? "#ef4444" : "#9ca3af";
  return (
    <span style={{ display:"inline-block", width:8, height:8, borderRadius:"50%",
      background:color, marginRight:4, flexShrink:0 }} />
  );
}

export default function EnginesPage() {
  const { data, loading, error, refetch } = useApi(
    useCallback(() => engineApi.getEffectiveEngines(), [])
  );
  const [showDisabled, setShowDisabled] = useState(false);

  const allEngines   = data?.engines ?? [];
  const enabled      = allEngines.filter(e => e.effective_enabled);
  const disabled     = allEngines.filter(e => !e.effective_enabled);
  const withOverride = allEngines.filter(e => e.source === "tenant_override");

  return (
    <TenantLayout activeNav="settings">
      <div style={{ padding:"24px 28px", maxWidth:900 }}>
        {/* Header */}
        <div style={{ marginBottom:24 }}>
          <h1 style={{ fontSize:20, fontWeight:700, color:"var(--text-primary)", margin:"0 0 4px" }}>
            My Engine Access
          </h1>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
            Platform capabilities available to your account. Engine access is determined by your category,
            package, and platform configuration.
          </p>
        </div>

        {/* Info banner */}
        <div style={{ display:"flex", gap:10, padding:"10px 14px", background:"#eff6ff",
          border:"1px solid #bfdbfe", borderRadius:8, marginBottom:20 }}>
          <Info size={15} style={{ color:"#3b82f6", flexShrink:0, marginTop:1 }} />
          <p style={{ fontSize:12, color:"#1e40af", margin:0 }}>
            Engine access is managed by your platform administrator. Contact support if you need
            an engine enabled or have questions about your current access.
          </p>
        </div>

        {loading && (
          <div style={{ textAlign:"center", padding:"48px 0", color:"var(--text-tertiary)", fontSize:13 }}>
            Loading engine access…
          </div>
        )}

        {error && (
          <div style={{ padding:"12px 16px", background:"#fef2f2", border:"1px solid #fecaca",
            borderRadius:8, color:"#dc2626", fontSize:13, marginBottom:16 }}>
            {error}
          </div>
        )}

        {data && !loading && (
          <>
            {/* Summary cards */}
            <div style={{ display:"grid", gridTemplateColumns:"repeat(3, 1fr)", gap:12, marginBottom:24 }}>
              {[
                { label:"Total Engines",    value:data.summary.total,   color:"#1e40af" },
                { label:"Enabled for You",  value:data.summary.enabled, color:"#15803d" },
                { label:"Not Enabled",      value:data.summary.disabled,color:"#9ca3af" },
              ].map(s => (
                <div key={s.label} style={{ border:"1px solid var(--border)", borderRadius:8, padding:"14px 16px" }}>
                  <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"0 0 4px", textTransform:"uppercase", letterSpacing:"0.05em" }}>
                    {s.label}
                  </p>
                  <p style={{ fontSize:26, fontWeight:800, color:s.color, margin:0 }}>{s.value}</p>
                </div>
              ))}
            </div>

            {/* Category + Package context */}
            {(data.category || data.package) && (
              <div style={{ display:"flex", gap:10, flexWrap:"wrap", marginBottom:20 }}>
                {data.category && (
                  <div style={{ padding:"4px 12px", borderRadius:20, border:"1px solid #ddd6fe",
                    background:"#faf5ff", fontSize:12, color:"#6d28d9" }}>
                    Category: <strong>{data.category.name}</strong>
                  </div>
                )}
                {data.package && (
                  <div style={{ padding:"4px 12px", borderRadius:20, border:"1px solid #bae6fd",
                    background:"#f0f9ff", fontSize:12, color:"#0369a1" }}>
                    Package: <strong>{data.package.name}</strong>
                  </div>
                )}
              </div>
            )}

            {/* Admin overrides notice */}
            {withOverride.length > 0 && (
              <div style={{ padding:"10px 14px", background:"#fffbeb", border:"1px solid #fde68a",
                borderRadius:8, marginBottom:20, fontSize:12, color:"#92400e" }}>
                <strong>{withOverride.length} engine(s)</strong> have a custom admin override applied to your account.
              </div>
            )}

            {/* Enabled engines */}
            <div style={{ marginBottom:24 }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:12 }}>
                <h2 style={{ fontSize:14, fontWeight:600, color:"var(--text-primary)", margin:0 }}>
                  Enabled Engines ({enabled.length})
                </h2>
                <button onClick={refetch}
                  style={{ background:"none", border:"1px solid var(--border)", borderRadius:6,
                    padding:"4px 10px", fontSize:12, cursor:"pointer", color:"var(--text-secondary)",
                    display:"flex", alignItems:"center", gap:4 }}>
                  <RefreshCw size={12} /> Refresh
                </button>
              </div>

              <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(260px, 1fr))", gap:10 }}>
                {enabled.map((e: TenantEffectiveEngine) => (
                  <div key={e.engine_key}
                    style={{ border:"1px solid #d1fae5", borderRadius:8, padding:"12px 14px",
                      background:"#f0fdf4" }}>
                    <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:4 }}>
                      <CheckCircle2 size={14} style={{ color:"#16a34a", flexShrink:0 }} />
                      <span style={{ fontSize:13, fontWeight:600, color:"#15803d" }}>{e.name}</span>
                    </div>
                    <div style={{ display:"flex", alignItems:"center", gap:8, flexWrap:"wrap" }}>
                      <span style={{ fontSize:10, fontFamily:"monospace", color:"#64748b",
                        background:"#f1f5f9", padding:"1px 6px", borderRadius:4 }}>
                        {e.engine_key}
                      </span>
                      <span style={{ fontSize:10, color:SOURCE_COLOR[e.source] ?? "#64748b" }}>
                        {SOURCE_LABEL[e.source] ?? e.source}
                      </span>
                    </div>
                    {e.is_required && (
                      <span style={{ display:"inline-block", marginTop:4, fontSize:10,
                        color:"#92400e", background:"#fef3c7", padding:"1px 6px", borderRadius:4 }}>
                        Required
                      </span>
                    )}
                    <div style={{ display:"flex", alignItems:"center", gap:4, marginTop:6 }}>
                      <HealthDot status={e.health_status} />
                      <span style={{ fontSize:10, color:"var(--text-tertiary)" }}>{e.health_status}</span>
                    </div>
                    {!e.dependencies_met && (
                      <p style={{ fontSize:10, color:"#b45309", margin:"4px 0 0" }}>
                        Dependencies not fully met
                      </p>
                    )}
                    {e.reason && e.source === "tenant_override" && (
                      <p style={{ fontSize:10, color:"#b45309", margin:"4px 0 0",
                        fontStyle:"italic" }}>
                        Override: {e.reason.slice(0, 60)}
                      </p>
                    )}
                  </div>
                ))}
                {enabled.length === 0 && (
                  <p style={{ fontSize:13, color:"var(--text-tertiary)", gridColumn:"1/-1" }}>
                    No engines currently enabled for your account.
                  </p>
                )}
              </div>
            </div>

            {/* Disabled engines (collapsible) */}
            {disabled.length > 0 && (
              <div>
                <button
                  onClick={() => setShowDisabled(v => !v)}
                  style={{ background:"none", border:"none", cursor:"pointer", padding:0,
                    fontSize:14, fontWeight:600, color:"var(--text-secondary)",
                    display:"flex", alignItems:"center", gap:6, marginBottom:10 }}>
                  <span style={{ display:"inline-block", transition:"transform 0.15s",
                    transform:showDisabled ? "rotate(90deg)" : "rotate(0deg)" }}>▸</span>
                  Not Available ({disabled.length})
                </button>

                {showDisabled && (
                  <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(220px, 1fr))", gap:8 }}>
                    {disabled.map((e: TenantEffectiveEngine) => (
                      <div key={e.engine_key}
                        style={{ border:"1px solid #f1f5f9", borderRadius:8, padding:"10px 12px",
                          background:"#f8fafc", opacity:0.75 }}>
                        <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:4 }}>
                          <XCircle size={13} style={{ color:"#9ca3af", flexShrink:0 }} />
                          <span style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)" }}>{e.name}</span>
                        </div>
                        <span style={{ fontSize:10, fontFamily:"monospace", color:"#94a3b8" }}>
                          {e.engine_key}
                        </span>
                        {e.reason && (
                          <p style={{ fontSize:10, color:"#94a3b8", margin:"4px 0 0" }}>
                            {e.reason.slice(0, 50)}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </TenantLayout>
  );
}
