"use client";
import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  RefreshCw, ChevronRight, CheckCircle2, XCircle, AlertTriangle,
  Search, MoreVertical, MapPin, Tag, Zap, Info, Shield,
  ArrowRight, ExternalLink, HelpCircle, Package, Wrench,
} from "lucide-react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import {
  homeServicesSetupApi, offeringCoverageApi, providerBrandApi,
  providerStatusApi, myStatusApi,
  type TenantEnabledService, type AdminMasterServiceRow, type HsSetupType, type HsSetupBrand,
  type CoverageServiceOption, type ProviderServiceArea,
  type ProviderAvailableBrand, type TenantStatusAuditLogEntry,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";

// ── helpers ───────────────────────────────────────────────────────────────────
function safeArr<T>(v: T[] | null | undefined): T[] { return Array.isArray(v) ? v : []; }
function safeText(v: unknown, fb = "—"): string { return v != null && String(v).trim() ? String(v) : fb; }
function safeDate(v: unknown): string {
  if (!v) return "—";
  try { return new Date(String(v)).toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }); }
  catch { return "—"; }
}
function svcLabel(s: TenantEnabledService, nameMap?: Record<string, string>): string {
  if (safeText(s.tenant_display_name) !== "—") return String(s.tenant_display_name);
  if (nameMap && nameMap[s.master_service_id]) return nameMap[s.master_service_id];
  return `Service #${s.master_service_id.slice(0, 8)}`;
}

const SERVICE_COLORS = ["#3b82f6","#22c55e","#f59e0b","#ef4444","#8b5cf6","#06b6d4","#f97316","#10b981"];
function svcColor(id: string) { let h=0; for (const c of id) h=(h*31+c.charCodeAt(0))>>>0; return SERVICE_COLORS[h % SERVICE_COLORS.length]; }

const TABS = ["Types & Brands", "Service Options", "Service Areas", "Readiness"] as const;
type Tab = typeof TABS[number];

// ── page ──────────────────────────────────────────────────────────────────────
export default function ServiceCoveragePage() {
  const [search, setSearch]       = useState("");
  const [filterStatus, setFilter] = useState("All Status");
  const [expanded, setExpanded]   = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [configTab, setConfigTab] = useState<Tab>("Types & Brands");
  const [showConfig, setShowConfig] = useState(false);

  const enabledApi   = useApi(useCallback(() => homeServicesSetupApi.listEnabled(), []));
  const availableApi = useApi(useCallback(() => homeServicesSetupApi.listAvailable(), []));
  const areasApi     = useApi(useCallback(() => myStatusApi.getServiceAreas(), []));
  const statusApi    = useApi(useCallback(() => providerStatusApi.get(), []));
  const activityApi  = useApi(useCallback(() => myStatusApi.getAuditLog(10), []));

  const services = safeArr(enabledApi.data?.services);

  // master_service_id → service_name lookup so cards show real names
  const nameMap: Record<string, string> = {};
  safeArr(availableApi.data?.services).forEach((r: AdminMasterServiceRow) => {
    nameMap[r.service_id] = r.service_name;
  });
  const areas    = safeArr((areasApi.data as { areas?: ProviderServiceArea[] } | null)?.areas);
  const status   = statusApi.data;
  const logs     = safeArr((activityApi.data as { logs?: TenantStatusAuditLogEntry[] } | null)?.logs);

  const selected = services.find(s => s.tenant_service_id === selectedId) ?? null;

  const refreshAll = useCallback(() => {
    enabledApi.refetch(); availableApi.refetch(); areasApi.refetch(); statusApi.refetch(); activityApi.refetch();
  }, [enabledApi, availableApi, areasApi, statusApi, activityApi]);

  // KPI counts
  const totalSvcs    = services.length;
  const published    = services.filter(s => s.setup_status === "published").length;
  const draft        = services.filter(s => s.setup_status !== "published").length;
  const needsAttn    = services.filter(s => s.setup_status !== "published" && !s.is_active).length;
  const bookable     = status?.is_bookable ?? false;
  const activeAreas  = areas.filter(a => a.is_active).length;

  // filter
  const filtered = services.filter(s => {
    const lbl = svcLabel(s, nameMap).toLowerCase();
    if (search && !lbl.includes(search.toLowerCase())) return false;
    if (filterStatus === "Published" && s.setup_status !== "published") return false;
    if (filterStatus === "Draft"     && s.setup_status === "published") return false;
    return true;
  });
  const visible = expanded ? filtered : filtered.slice(0, 8);

  function openConfig(id: string) {
    setSelectedId(id);
    setConfigTab("Types & Brands");
    setShowConfig(true);
  }

  return (
    <TenantLayout activeNav="provider-service-coverage">
      <style>{`
        .sc-card{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:20px}
        .sc-card-sm{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px}
        .sc-title{font-size:13px;font-weight:700;color:var(--text-primary);margin:0 0 14px;letter-spacing:0.02em}
        .sc-tbl{width:100%;border-collapse:collapse}
        .sc-tbl th{font-size:11px;font-weight:600;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:0.05em;padding:9px 14px;text-align:left;border-bottom:1px solid var(--border)}
        .sc-tbl td{font-size:13px;color:var(--text-primary);padding:11px 14px;border-bottom:1px solid var(--border)}
        .sc-tbl tr:last-child td{border-bottom:none}
        .sc-tbl tr:hover td{background:var(--surface-sunken,rgba(0,0,0,0.06))}
        .pill-green{display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;font-size:11px;font-weight:600;background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.25);color:#22c55e;white-space:nowrap}
        .pill-red{display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;font-size:11px;font-weight:600;background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.25);color:#ef4444;white-space:nowrap}
        .pill-amber{display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;font-size:11px;font-weight:600;background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.22);color:#f59e0b;white-space:nowrap}
        .pill-blue{display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;font-size:11px;font-weight:600;background:rgba(59,130,246,0.12);border:1px solid rgba(59,130,246,0.25);color:var(--brand,#3b82f6);white-space:nowrap}
        .pill-muted{display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;font-size:11px;font-weight:600;background:var(--surface-sunken,rgba(0,0,0,0.12));border:1px solid var(--border);color:var(--text-secondary);white-space:nowrap}
        .tag{display:inline-flex;align-items:center;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:500;background:var(--surface-sunken,rgba(0,0,0,0.15));border:1px solid var(--border);color:var(--text-secondary)}
        .btn-sec{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border-radius:9px;font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;border:1px solid var(--border);background:transparent;color:var(--text-primary);white-space:nowrap}
        .btn-sec:hover{border-color:rgba(255,255,255,0.2)}
        .btn-pri{display:inline-flex;align-items:center;gap:6px;padding:8px 18px;border-radius:9px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;border:none;background:var(--brand,#3b82f6);color:#fff;white-space:nowrap}
        .btn-pri:hover{opacity:0.9}
        .btn-ghost{display:inline-flex;align-items:center;gap:5px;padding:6px 12px;border-radius:8px;font-size:12px;font-weight:500;cursor:pointer;font-family:inherit;border:1px solid var(--border);background:transparent;color:var(--text-secondary);white-space:nowrap}
        .svc-card{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:16px;display:flex;flex-direction:column;gap:10px;transition:box-shadow .15s,border-color .15s;cursor:default}
        .svc-card:hover{border-color:rgba(255,255,255,0.15);box-shadow:0 4px 20px rgba(0,0,0,0.2)}
        .sc-tab{padding:8px 14px;border:none;background:transparent;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;color:var(--text-secondary);border-bottom:2px solid transparent;margin-bottom:-1px;transition:color .15s}
        .sc-tab.active{color:var(--brand,#3b82f6);border-bottom-color:var(--brand,#3b82f6)}
        .sc-check-row{display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid var(--border)}
        .sc-brand-lbl{display:inline-flex;align-items:center;gap:5px;padding:4px 9px;border-radius:6px;cursor:pointer;font-size:12px;border:1px solid var(--border);color:var(--text-secondary);background:var(--surface-sunken,rgba(0,0,0,0.1));transition:all .12s}
        .sc-brand-lbl.on{background:rgba(59,130,246,0.1);border-color:rgba(59,130,246,0.35);color:var(--brand,#3b82f6)}
        .sc-opt-row{display:flex;align-items:center;gap:12px;padding:9px 12px;border-radius:8px;cursor:pointer;border:1px solid var(--border);background:var(--surface-sunken,rgba(0,0,0,0.08));transition:all .12s}
        .sc-opt-row.on{background:rgba(59,130,246,0.07);border-color:rgba(59,130,246,0.28)}
        .sc-area-row{display:flex;align-items:center;gap:12px;padding:9px 12px;border-radius:8px;background:rgba(34,197,94,0.07);border:1px solid rgba(34,197,94,0.18)}
        .banner-info{padding:10px 16px;border-radius:10px;background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.2);color:var(--brand,#3b82f6);font-size:12px;display:flex;align-items:center;gap:10px}
        .banner-green{padding:10px 12px;border-radius:8px;background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.22);color:#22c55e;font-size:12px;display:flex;align-items:center;gap:8px}
        .banner-amber{padding:10px 12px;border-radius:8px;background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.22);color:#f59e0b;font-size:12px;display:flex;align-items:center;gap:8px}
        .banner-red{padding:10px 12px;border-radius:8px;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.22);color:#ef4444;font-size:12px;display:flex;align-items:center;gap:8px}
        .sc-empty{text-align:center;padding:28px 16px;color:var(--text-tertiary)}
        @keyframes spin-sc{to{transform:rotate(360deg)}}
        .sc-spin{animation:spin-sc 1s linear infinite}
        .modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:100;display:flex;align-items:flex-start;justify-content:flex-end}
        .modal-panel{width:560px;max-width:95vw;height:100vh;background:var(--surface);border-left:1px solid var(--border);overflow-y:auto;display:flex;flex-direction:column}
      `}</style>

      <div style={{ display: "flex", flexDirection: "column", gap: 20, minHeight: "100%", color: "var(--text-primary)" }}>

        {/* breadcrumb */}
        <div style={{ fontSize: 12, color: "var(--text-tertiary)", display: "flex", alignItems: "center", gap: 5 }}>
          <Link href="/dashboard" style={{ color: "var(--text-tertiary)", textDecoration: "none" }}>Tenant Portal</Link>
          <ChevronRight size={12} />
          <span>Setup</span>
          <ChevronRight size={12} />
          <span style={{ color: "var(--text-secondary)" }}>Service Coverage</span>
        </div>

        {/* page header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 800, margin: "0 0 4px", letterSpacing: "-0.01em" }}>Service Coverage</h1>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
              Configure supported types, brands and service areas for each enabled service.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button className="btn-sec" onClick={refreshAll}>
              <RefreshCw size={13} /> Refresh
            </button>
            {selected && <SaveDraftBtn service={selected} onDone={refreshAll} />}
            {selected && <PublishBtn   service={selected} onDone={refreshAll} />}
          </div>
        </div>

        {/* info banner */}
        <div className="banner-info">
          <Info size={15} style={{ flexShrink: 0 }} />
          <span>
            Published services with complete type, brand, and area coverage become available for customer matching.
          </span>
          <button style={{ marginLeft: "auto", fontSize: 12, color: "var(--brand)", background: "none", border: "none", cursor: "pointer", fontWeight: 600, whiteSpace: "nowrap" }}>
            Learn more
          </button>
        </div>

        {/* search + filter + action row */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          {/* search */}
          <div style={{ position: "relative", flex: 1, minWidth: 200, maxWidth: 340 }}>
            <Search size={13} style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)", pointerEvents: "none" }} />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search services…"
              style={{ width: "100%", height: 36, padding: "0 12px 0 32px", fontSize: 13,
                background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 9,
                color: "var(--text-primary)", outline: "none", fontFamily: "inherit", boxSizing: "border-box" as const }} />
          </div>
          {/* status filter */}
          <select value={filterStatus} onChange={e => setFilter(e.target.value)}
            style={{ height: 36, padding: "0 10px", fontSize: 13, borderRadius: 9,
              border: "1px solid var(--border)", background: "var(--surface)",
              color: "var(--text-primary)", cursor: "pointer", fontFamily: "inherit", outline: "none" }}>
            {["All Status","Published","Draft"].map(o => <option key={o}>{o}</option>)}
          </select>
          {(search || filterStatus !== "All Status") && (
            <button className="btn-ghost" onClick={() => { setSearch(""); setFilter("All Status"); }}>
              Clear filters
            </button>
          )}
          <div style={{ marginLeft: "auto" }}>
            <Link href="/catalog">
              <button className="btn-pri"><Tag size={14} /> Setup New Service</button>
            </Link>
          </div>
        </div>

        {/* KPI stat cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
          {[
            { icon:<Package size={22}/>, label:"Available Services", val:totalSvcs, sub:"Admin approved", color:"var(--brand,#3b82f6)", bg:"rgba(59,130,246,0.1)", border:"rgba(59,130,246,0.2)", arrow:true },
            { icon:<CheckCircle2 size={22}/>, label:"Published",     val:published,  sub:"Live and available", color:"#22c55e", bg:"rgba(34,197,94,0.1)", border:"rgba(34,197,94,0.2)", arrow:false },
            { icon:<Tag size={22}/>, label:"Draft / Setup Pending",  val:draft,      sub:"In progress",   color:"#f59e0b", bg:"rgba(245,158,11,0.1)", border:"rgba(245,158,11,0.2)", arrow:true },
            { icon:<AlertTriangle size={22}/>, label:"Needs Attention", val:needsAttn, sub:"Missing required steps", color:"#ef4444", bg:"rgba(239,68,68,0.1)", border:"rgba(239,68,68,0.2)", arrow:true },
          ].map(k => (
            <div key={k.label} style={{ background: "var(--surface)", border: `1px solid var(--border)`,
              borderRadius: 14, padding: "16px 20px", display: "flex", alignItems: "center", gap: 14,
              cursor: "pointer" }}>
              <div style={{ width: 48, height: 48, borderRadius: 12, background: k.bg, border: `1px solid ${k.border}`,
                display: "flex", alignItems: "center", justifyContent: "center", color: k.color, flexShrink: 0 }}>
                {k.icon}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600, marginBottom: 2 }}>{k.label}</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: k.color, lineHeight: 1.1 }}>{k.val}</div>
                <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>{k.sub}</div>
              </div>
              {k.arrow && <ChevronRight size={16} color="var(--text-tertiary)" style={{ flexShrink: 0 }} />}
            </div>
          ))}
        </div>

        {/* main 2-col layout */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 20, alignItems: "start" }}>

          {/* LEFT — service grid + active services table */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

            {/* service cards grid */}
            {enabledApi.loading ? (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
                {[...Array(4)].map((_, i) => (
                  <div key={i} style={{ height: 200, borderRadius: 14, background: "var(--surface)", border: "1px solid var(--border)", animation: "pulse 2s infinite" }} />
                ))}
              </div>
            ) : filtered.length === 0 ? (
              <div className="sc-empty">
                <Package size={28} style={{ marginBottom: 10, opacity: 0.4 }} />
                <p style={{ fontSize: 14, margin: "0 0 6px" }}>
                  {services.length === 0 ? "No services enabled yet." : "No services match your filter."}
                </p>
                <p style={{ fontSize: 12, margin: "0 0 14px" }}>
                  {services.length === 0 ? "Enable services from the Catalog first." : "Try clearing your filters."}
                </p>
                {services.length === 0 && (
                  <Link href="/catalog" style={{ fontSize: 13, color: "var(--brand)", fontWeight: 600, textDecoration: "none" }}>
                    Go to Catalog →
                  </Link>
                )}
              </div>
            ) : (
              <div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
                  {visible.map(s => (
                    <SvcCard key={s.tenant_service_id} service={s} label={svcLabel(s, nameMap)} onConfigure={() => openConfig(s.tenant_service_id)} />
                  ))}
                </div>
                {filtered.length > 8 && (
                  <div style={{ textAlign: "center", marginTop: 14 }}>
                    <button className="btn-ghost" onClick={() => setExpanded(e => !e)} style={{ gap: 6 }}>
                      {expanded ? `Show less` : `View all services (${filtered.length})`}
                      <ChevronRight size={13} style={{ transform: expanded ? "rotate(270deg)" : "rotate(90deg)", transition: "transform .2s" }} />
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Active services table */}
            {services.length > 0 && (
              <div className="sc-card" style={{ padding: 0, overflow: "hidden" }}>
                <div style={{ padding: "16px 20px 12px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>Your Active Services</span>
                  <span style={{ fontSize: 12, fontWeight: 600, padding: "2px 8px", borderRadius: 999,
                    background: "var(--brand,rgba(59,130,246,0.15))", color: "var(--brand,#3b82f6)" }}>
                    {services.length}
                  </span>
                </div>
                <table className="sc-tbl">
                  <thead>
                    <tr>
                      <th>Service</th>
                      <th>Status</th>
                      <th>Setup Status</th>
                      <th>Job Type</th>
                      <th>Last Updated</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {services.map(s => {
                      const pub = s.setup_status === "published";
                      return (
                        <tr key={s.tenant_service_id}>
                          <td style={{ fontWeight: 500 }}>{svcLabel(s, nameMap)}</td>
                          <td>
                            {s.is_active
                              ? <span className="pill-green">Active</span>
                              : <span className="pill-muted">Inactive</span>}
                          </td>
                          <td>
                            {pub
                              ? <span className="pill-green">Published</span>
                              : <span className="pill-amber">Draft</span>}
                          </td>
                          <td style={{ color: "var(--text-secondary)", fontSize: 12 }}>{s.job_type}</td>
                          <td style={{ color: "var(--text-tertiary)", fontSize: 12 }}>—</td>
                          <td>
                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                              <button className="btn-ghost" style={{ fontSize: 12, padding: "4px 10px" }}
                                onClick={() => openConfig(s.tenant_service_id)}>
                                Manage
                              </button>
                              <SaveDraftBtn service={s} onDone={refreshAll} compact />
                              <PublishBtn   service={s} onDone={refreshAll} compact />
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {services.length > 5 && (
                  <div style={{ padding: "12px 20px", borderTop: "1px solid var(--border)", textAlign: "center" }}>
                    <button className="btn-ghost" style={{ fontSize: 12 }}>View all active services →</button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* RIGHT sidebar */}
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

            {/* Setup Rules */}
            <div className="sc-card-sm">
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
                <Shield size={16} color="var(--brand,#3b82f6)" />
                <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>Coverage Rules</span>
              </div>
              {[
                "Types and brands require service-specific configuration.",
                "Brand coverage is tracked per service type separately.",
                "Published services are matched to customer bookings.",
                "Service areas define geographic coverage for matching.",
              ].map((r, i) => (
                <div key={i} style={{ display: "flex", gap: 10, padding: "8px 0", borderBottom: i < 3 ? "1px solid var(--border)" : "none" }}>
                  <CheckCircle2 size={14} color="#22c55e" style={{ flexShrink: 0, marginTop: 1 }} />
                  <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{r}</span>
                </div>
              ))}
              <button style={{ marginTop: 12, fontSize: 12, color: "var(--brand)", background: "none", border: "none",
                cursor: "pointer", fontWeight: 600, padding: 0, display: "flex", alignItems: "center", gap: 4 }}>
                View detailed guidelines <ArrowRight size={12} />
              </button>
            </div>

            {/* Needs Attention */}
            {draft > 0 && (
              <div className="sc-card-sm">
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <AlertTriangle size={16} color="#f59e0b" />
                    <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>Needs Attention</span>
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 999,
                    background: "rgba(239,68,68,0.15)", color: "#ef4444" }}>{draft}</span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {services.filter(s => s.setup_status !== "published").slice(0, 3).map(s => (
                    <div key={s.tenant_service_id} style={{ display: "flex", alignItems: "center", gap: 10,
                      padding: "8px 10px", borderRadius: 8, background: "var(--surface-sunken,rgba(0,0,0,0.1))", border: "1px solid var(--border)" }}>
                      <div style={{ width: 6, height: 6, borderRadius: 999, background: "#ef4444", flexShrink: 0 }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {svcLabel(s, nameMap)}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Setup pending</div>
                      </div>
                    </div>
                  ))}
                </div>
                <button className="btn-sec" onClick={() => setFilter("Draft")}
                  style={{ marginTop: 12, width: "100%", justifyContent: "center", fontSize: 12 }}>
                  Resolve Now
                </button>
              </div>
            )}

            {/* Bookability status */}
            <div className="sc-card-sm">
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <Zap size={16} color={bookable ? "#22c55e" : "#f59e0b"} />
                <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>Bookability</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                {[
                  { label: "Services Published",    done: published > 0  },
                  { label: "Service Areas Active",  done: activeAreas > 0 },
                  { label: "System Bookable",       done: bookable       },
                ].map((c, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {c.done
                      ? <CheckCircle2 size={13} color="#22c55e" style={{ flexShrink: 0 }} />
                      : <XCircle size={13} color="#ef4444" style={{ flexShrink: 0 }} />}
                    <span style={{ fontSize: 12, color: c.done ? "var(--text-secondary)" : "var(--text-primary)" }}>{c.label}</span>
                  </div>
                ))}
              </div>
              <Link href="/provider/status">
                <button className="btn-sec" style={{ marginTop: 12, width: "100%", justifyContent: "center", fontSize: 12 }}>
                  View Full Status <ExternalLink size={12} />
                </button>
              </Link>
            </div>

            {/* Need Help */}
            <div className="sc-card-sm">
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <HelpCircle size={16} color="var(--text-secondary)" />
                <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>Need Help?</span>
              </div>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 12px" }}>
                Get assistance with service coverage or type and brand configuration.
              </p>
              {[
                { label: "Help Center", icon: <ExternalLink size={12} /> },
                { label: "Contact Support", icon: <ExternalLink size={12} /> },
              ].map(h => (
                <button key={h.label} className="btn-sec"
                  style={{ width: "100%", justifyContent: "space-between", fontSize: 12, marginBottom: 6 }}>
                  {h.label} {h.icon}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* CONFIG SLIDE-OVER PANEL */}
      {showConfig && selected && (
        <div className="modal-overlay" onClick={() => setShowConfig(false)}>
          <div className="modal-panel" onClick={e => e.stopPropagation()}>
            <ConfigPanel
              service={selected}
              label={svcLabel(selected, nameMap)}
              areas={areas}
              tab={configTab}
              onTab={setConfigTab}
              onSaved={refreshAll}
              onClose={() => setShowConfig(false)}
            />
          </div>
        </div>
      )}
    </TenantLayout>
  );
}

// ── service grid card ──────────────────────────────────────────────────────────
function SvcCard({ service, label, onConfigure }: { service: TenantEnabledService; label: string; onConfigure: () => void }) {
  const pub   = service.setup_status === "published";
  const color = svcColor(service.tenant_service_id);

  // rough completion %
  const checks = [service.is_enabled, !!service.tenant_display_name, pub];
  const pct = Math.round((checks.filter(Boolean).length / checks.length) * 100);
  const barColor = pct === 100 ? "#22c55e" : pct >= 50 ? "#3b82f6" : "#f59e0b";

  return (
    <div className="svc-card">
      {/* icon + menu */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div style={{ width: 44, height: 44, borderRadius: 12, background: `${color}20`, border: `1px solid ${color}40`,
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, color }}>
          <Wrench size={20} />
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {pub
            ? <span className="pill-green" style={{ fontSize: 10, padding: "2px 8px" }}>Published</span>
            : <span className="pill-amber" style={{ fontSize: 10, padding: "2px 8px" }}>Draft</span>}
          <button style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", padding: 2 }}>
            <MoreVertical size={14} />
          </button>
        </div>
      </div>

      {/* name + type */}
      <div>
        <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginBottom: 2, lineHeight: 1.3 }}>{label}</div>
        <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
          {service.requires_type ? "Type-based" : "Fixed"} · {service.job_type}
        </div>
      </div>

      {/* tags */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
        {service.requires_brand && <span className="tag">Brand pricing</span>}
        {service.requires_type  && <span className="tag">Types required</span>}
      </div>

      {/* progress */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
          <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Setup progress</span>
          <span style={{ fontSize: 11, fontWeight: 700, color: barColor }}>{pct}%</span>
        </div>
        <div style={{ height: 4, borderRadius: 999, background: "var(--border)", overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${pct}%`, borderRadius: 999, background: barColor, transition: "width .4s" }} />
        </div>
      </div>

      {/* CTA */}
      <button onClick={onConfigure}
        style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
          padding: "8px 0", borderRadius: 9, border: "1px solid var(--border)", background: "transparent",
          color: "var(--text-primary)", fontSize: 13, fontWeight: 500, cursor: "pointer", fontFamily: "inherit" }}>
        {pub ? "Manage" : "Continue Setup"} <ChevronRight size={13} />
      </button>
    </div>
  );
}

// ── slide-over config panel ───────────────────────────────────────────────────
function ConfigPanel({ service, label, areas, tab, onTab, onSaved, onClose }:
  { service: TenantEnabledService; label: string; areas: ProviderServiceArea[]; tab: Tab;
    onTab: (t: Tab) => void; onSaved: () => void; onClose: () => void }) {

  const typesApi   = useApi(useCallback(() => homeServicesSetupApi.getTypes(service.tenant_service_id),        [service.tenant_service_id]));
  const brandsApi  = useApi(useCallback(() => homeServicesSetupApi.getBrands(service.tenant_service_id),       [service.tenant_service_id]));
  const optionsApi = useApi(useCallback(() => offeringCoverageApi.getOptions(service.master_service_id),       [service.master_service_id]));
  const availBrApi = useApi(useCallback(() => providerBrandApi.getAvailableForService(service.master_service_id), [service.master_service_id]));

  const types       = safeArr(typesApi.data?.types);
  const brands      = safeArr(brandsApi.data?.brands);
  const options     = safeArr(optionsApi.data?.service_options);
  const availBrands = safeArr(availBrApi.data?.brands);
  const color = svcColor(service.tenant_service_id);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* header */}
      <div style={{ padding: "20px 24px 0", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: `${color}20`, border: `1px solid ${color}40`,
              display: "flex", alignItems: "center", justifyContent: "center", color }}>
              <Wrench size={18} />
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>{label}</div>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{service.job_type} · Coverage Configuration</div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {service.setup_status === "published"
              ? <span className="pill-green">Published</span>
              : <span className="pill-amber">Draft</span>}
            <button onClick={onClose}
              style={{ width: 30, height: 30, borderRadius: 8, border: "1px solid var(--border)",
                background: "transparent", cursor: "pointer", color: "var(--text-secondary)",
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>
              ✕
            </button>
          </div>
        </div>
        {/* tabs */}
        <div style={{ display: "flex", gap: 0 }}>
          {TABS.map(t => (
            <button key={t} onClick={() => onTab(t)} className={`sc-tab${tab === t ? " active" : ""}`}>{t}</button>
          ))}
        </div>
      </div>

      {/* tab content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
        {tab === "Types & Brands"  && <TypesBrandsTab  service={service} types={types} brands={brands} availBrands={availBrands} loading={typesApi.loading || brandsApi.loading} onSaved={onSaved} />}
        {tab === "Service Options" && <ServiceOptionsTab options={options} loading={optionsApi.loading} />}
        {tab === "Service Areas"   && <ServiceAreasTab  areas={areas} />}
        {tab === "Readiness"       && <ReadinessTab     service={service} types={types} brands={brands} options={options} areas={areas} />}
      </div>

      {/* footer actions */}
      <div style={{ padding: "16px 24px", borderTop: "1px solid var(--border)", display: "flex", gap: 10, flexShrink: 0 }}>
        <SaveDraftBtn service={service} onDone={() => { onSaved(); }} />
        <PublishBtn   service={service} onDone={() => { onSaved(); }} />
      </div>
    </div>
  );
}

// ── types & brands tab ────────────────────────────────────────────────────────
// HS-fix: this tab previously let you check brands *per type*
// (Record<typeId, Set<brandId>>), implying type-scoped brand coverage.
// The backend explicitly does not support that — brand *enablement* is
// type-independent by design (TenantCatalogService.get_tenant_service_brands:
// "Brand enablement is type-independent... restricted to the
// service_type_id IS NULL marker row"). The old save handler silently
// flattened every type's checked brands into one set and called the
// global setBrands endpoint — the per-type structure the UI implied was
// never actually persisted. Fixed: this tab now only collects/saves
// service-level brand coverage (matching what the backend actually
// stores). Type-specific brand *pricing* (which is real and type-scoped)
// belongs in the Service Setup wizard at /tenant/setup/services.
function TypesBrandsTab({ service, types, brands, availBrands, loading, onSaved }:
  { service: TenantEnabledService; types: HsSetupType[]; brands: HsSetupBrand[];
    availBrands: ProviderAvailableBrand[]; loading: boolean; onSaved: () => void }) {

  const [selTypeIds,  setSelTypeIds]  = useState<Set<string>>(new Set());
  const [globalBrIds, setGlobalBrIds] = useState<Set<string>>(new Set());
  const [msg, setMsg] = useState("");

  useEffect(() => { setSelTypeIds(new Set(types.map(t => t.service_type_id))); }, [types]);
  useEffect(() => { setGlobalBrIds(new Set(brands.filter(b => b.is_enabled).map(b => b.brand_id))); }, [brands]);

  const saveAction = useAction(useCallback(async () => {
    await homeServicesSetupApi.setTypes(service.tenant_service_id, Array.from(selTypeIds));
    await homeServicesSetupApi.setBrands(service.tenant_service_id, Array.from(globalBrIds));
    setMsg("Saved successfully."); onSaved();
  }, [service.tenant_service_id, selTypeIds, globalBrIds, onSaved]));

  const toggleType = (id: string) => setSelTypeIds(prev => { const n = new Set(prev); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const toggleGlobalBrand = (id: string) => setGlobalBrIds(prev => { const n = new Set(prev); if (n.has(id)) n.delete(id); else n.add(id); return n; });

  if (loading) return <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Loading…</p>;
  const hasTypes = types.length > 0;
  const hasBrands = availBrands.length > 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {msg && <div className="banner-green"><CheckCircle2 size={13} />{msg}</div>}

      {/* types */}
      <div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.07em" }}>Service Types</span>
          <button className="btn-pri" style={{ fontSize: 12, padding: "6px 14px" }} onClick={() => saveAction.execute()} disabled={saveAction.loading}>
            {saveAction.loading ? "Saving…" : "Save Changes"}
          </button>
        </div>
        {!hasTypes && <div className="sc-empty"><Tag size={18} style={{ marginBottom: 8, opacity: 0.4 }} /><p style={{ fontSize: 12, margin: 0 }}>No service types available.</p></div>}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {types.map(tp => {
            const on = selTypeIds.has(tp.service_type_id);
            return (
              <div key={tp.service_type_id} style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 14,
                background: on ? "rgba(59,130,246,0.04)" : "var(--surface-sunken,rgba(0,0,0,0.08))" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <input type="checkbox" checked={on} onChange={() => toggleType(tp.service_type_id)}
                    style={{ width: 15, height: 15, accentColor: "var(--brand,#3b82f6)", cursor: "pointer", flexShrink: 0 }} />
                  <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", flex: 1 }}>{tp.name}</span>
                  {tp.is_required && <span className="pill-red">Required</span>}
                  {tp.is_default  && <span className="pill-blue">Default</span>}
                </div>
              </div>
            );
          })}
        </div>
        {hasTypes && (
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 10 }}>
            Need different brand pricing per type (e.g. Split AC vs. Window AC)? Configure that in{" "}
            <Link href="/tenant/setup/services" style={{ color: "var(--brand)" }}>Service Setup</Link>.
          </p>
        )}
      </div>

      {/* brand coverage — service-level only, matches the real backend model */}
      {hasBrands ? (
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 10 }}>
            Brand Coverage <span style={{ fontWeight: 400, textTransform: "none" }}>(applies to this service overall, not per type)</span>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 7, marginBottom: 14 }}>
            {availBrands.map(br => {
              const on = globalBrIds.has(br.brand_id);
              return (
                <label key={br.brand_id} className={`sc-brand-lbl${on ? " on" : ""}`}>
                  <input type="checkbox" checked={on} onChange={() => toggleGlobalBrand(br.brand_id)}
                    style={{ width: 13, height: 13, accentColor: "var(--brand,#3b82f6)" }} />
                  {br.display_name || br.name}
                  {br.is_required && <span style={{ color: "#ef4444", fontSize: 9, marginLeft: 1 }}>*</span>}
                </label>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="sc-empty"><Tag size={18} style={{ marginBottom: 8, opacity: 0.4 }} /><p style={{ fontSize: 12, margin: 0 }}>No brands available for this service.</p></div>
      )}
    </div>
  );
}

// ── service options tab ───────────────────────────────────────────────────────
function ServiceOptionsTab({ options, loading }: { options: CoverageServiceOption[]; loading: boolean }) {
  const [sel, setSel] = useState<Set<string>>(new Set());
  useEffect(() => { setSel(new Set(options.filter(o => o.is_active).map(o => o.id))); }, [options]);
  const toggle = (id: string) => setSel(prev => { const n = new Set(prev); if (n.has(id)) n.delete(id); else n.add(id); return n; });

  if (loading) return <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Loading…</p>;
  if (options.length === 0) return <div className="sc-empty"><Shield size={20} style={{ marginBottom: 8, opacity: 0.4 }} /><p style={{ fontSize: 12, margin: 0 }}>No service options for this service.</p></div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>Select the job options your team can handle.</p>
      {sel.size === 0 && <div className="banner-amber"><AlertTriangle size={13} /> No service options selected — select at least one.</div>}
      {options.map(o => {
        const on = sel.has(o.id);
        return (
          <div key={o.id} className={`sc-opt-row${on ? " on" : ""}`} onClick={() => toggle(o.id)}>
            <input type="checkbox" checked={on} readOnly style={{ width: 14, height: 14, accentColor: "var(--brand,#3b82f6)", flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: on ? "var(--brand,#3b82f6)" : "var(--text-primary)" }}>{o.name}</div>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{o.code} · {o.option_type}</div>
            </div>
            {o.is_customer_selectable ? <span className="pill-blue">Customer Selectable</span> : <span className="pill-muted">Internal</span>}
          </div>
        );
      })}
    </div>
  );
}

// ── service areas tab ─────────────────────────────────────────────────────────
function ServiceAreasTab({ areas }: { areas: ProviderServiceArea[] }) {
  const active = areas.filter(a => a.is_active);
  if (active.length === 0) return (
    <div className="sc-empty">
      <MapPin size={20} style={{ marginBottom: 8, opacity: 0.4 }} />
      <p style={{ fontSize: 13, margin: "0 0 10px" }}>No active service areas.</p>
      <Link href="/service-areas" style={{ fontSize: 12, color: "var(--brand)", fontWeight: 600, textDecoration: "none" }}>Add Service Area →</Link>
    </div>
  );
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>Active coverage areas for this service.</p>
      {active.map(a => (
        <div key={a.id} className="sc-area-row">
          <CheckCircle2 size={14} color="#22c55e" style={{ flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
              {safeText(a.zone_name ?? a.city ?? a.district ?? a.state)}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
              {a.coverage_type}{a.zipcode ? ` · ${a.zipcode}` : ""}{a.city ? ` · ${a.city}` : ""}
            </div>
          </div>
          <span className="pill-green">Covered</span>
        </div>
      ))}
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 4 }}>
        Manage in <Link href="/service-areas" style={{ color: "var(--brand)" }}>Service Areas</Link>.
      </p>
    </div>
  );
}

// ── readiness tab ─────────────────────────────────────────────────────────────
function ReadinessTab({ service, types, brands, options, areas }:
  { service: TenantEnabledService; types: HsSetupType[]; brands: HsSetupBrand[];
    options: CoverageServiceOption[]; areas: ProviderServiceArea[] }) {
  const checks = [
    { label: "Service enabled",               done: service.is_enabled,                                        href: "/catalog"      },
    { label: "At least one type selected",    done: !service.requires_type  || types.length > 0,               href: "#"             },
    { label: "At least one brand selected",   done: !service.requires_brand || brands.some(b => b.is_enabled), href: "#"             },
    { label: "Service option available",      done: options.some(o => o.is_active),                            href: "#"             },
    { label: "Active service area mapped",    done: areas.some(a => a.is_active),                              href: "/service-areas" },
    { label: "Coverage published",            done: service.setup_status === "published",                       href: "#"             },
  ];
  const all = checks.every(c => c.done);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <div className={all ? "banner-green" : "banner-amber"} style={{ marginBottom: 10 }}>
        {all ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}
        {all ? "All readiness checks passed." : "Complete the missing steps below."}
      </div>
      {checks.map((c, i) => (
        <div key={i} className="sc-check-row">
          {c.done ? <CheckCircle2 size={14} color="#22c55e" style={{ flexShrink: 0 }} />
                  : <XCircle size={14} color="#ef4444" style={{ flexShrink: 0 }} />}
          <span style={{ flex: 1, fontSize: 12, color: c.done ? "var(--text-secondary)" : "var(--text-primary)" }}>{c.label}</span>
          {!c.done && c.href !== "#" && <Link href={c.href} style={{ fontSize: 11, color: "var(--brand)", fontWeight: 600, textDecoration: "none" }}>Fix</Link>}
        </div>
      ))}
    </div>
  );
}

// ── save draft btn ────────────────────────────────────────────────────────────
function SaveDraftBtn({ service, onDone, compact }: { service: TenantEnabledService; onDone: () => void; compact?: boolean }) {
  const a = useAction(useCallback(async () => {
    await homeServicesSetupApi.saveDraft(service.tenant_service_id); onDone();
  }, [service.tenant_service_id, onDone]));

  if (compact) return (
    <button className="btn-ghost" style={{ fontSize: 12, padding: "4px 10px" }}
      onClick={e => { e.stopPropagation(); a.execute(); }} disabled={a.loading}>
      {a.loading ? "…" : "Draft"}
    </button>
  );
  return (
    <button className="btn-sec" onClick={() => a.execute()} disabled={a.loading}>
      {a.loading ? "Saving…" : "Save Draft"}
    </button>
  );
}

// ── publish btn ───────────────────────────────────────────────────────────────
function PublishBtn({ service, onDone, compact }: { service: TenantEnabledService; onDone: () => void; compact?: boolean }) {
  const [err, setErr] = useState("");
  const a = useAction(useCallback(async () => {
    setErr(""); await homeServicesSetupApi.publish(service.tenant_service_id); onDone();
  }, [service.tenant_service_id, onDone]), {
    onError: (e: unknown) => setErr(e instanceof Error ? e.message : "Publish failed."),
  });

  if (compact) return (
    <button className="btn-pri" style={{ fontSize: 12, padding: "4px 12px" }}
      onClick={e => { e.stopPropagation(); a.execute(); }} disabled={a.loading}>
      {a.loading ? "…" : "Publish"}
    </button>
  );
  return (
    <div>
      <button className="btn-pri" onClick={() => a.execute()} disabled={a.loading}>
        {a.loading ? "Publishing…" : "Publish Coverage"}
      </button>
      {err && <div style={{ marginTop: 5, fontSize: 11, color: "#ef4444" }}>{err}</div>}
    </div>
  );
}
