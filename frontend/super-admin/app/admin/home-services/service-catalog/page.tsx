"use client";
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import {
  homeServicesCatalogConsoleApi, masterDataApi,
  type HsConsoleService, type HsConsoleServiceDetail, type HsConsoleType,
  type HsConsoleBrand,
} from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import { usePermissions } from "../../../../hooks/usePermissions";
import {
  ChevronRight, RefreshCw, Plus, XCircle, CheckCircle2, Copy,
  Layers, Activity, AlertTriangle, Lock,
} from "lucide-react";

// ── Formatters ───────────────────────────────────────────────────────────────
const safeText = (v: unknown, fb = "Not configured"): string =>
  (typeof v === "string" && v.trim()) ? v.trim() : fb;
const safeNum = (v: unknown): number => (typeof v === "number" && isFinite(v)) ? v : 0;
const safeCurrency = (v: unknown): string =>
  (typeof v === "number" && isFinite(v)) ? `₹${v.toLocaleString("en-IN")}` : "Not configured";
const safePercent = (v: unknown): string =>
  (typeof v === "number" && isFinite(v)) ? `${v}%` : "Not configured";
const safeDate = (v: unknown): string => {
  if (!v || typeof v !== "string") return "Not configured";
  try { return new Date(v).toLocaleDateString("en-IN", { dateStyle: "medium" }); } catch { return "Not configured"; }
};
function copyText(t: string) { if (typeof navigator !== "undefined") navigator.clipboard?.writeText(t).catch(() => {}); }

const PRICING_MODEL_LABELS: Record<string, string> = {
  fixed: "Fixed", range: "Type-based", post_assessment: "Consultation", hourly: "Hourly",
};

// ── Error section ────────────────────────────────────────────────────────────
function SectionError({ title, error, requestId, onRetry }: {
  title: string; error: string; requestId?: string | null; onRetry: () => void;
}) {
  return (
    <div style={{ padding: "16px 20px", background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
        <div>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--danger-text)", margin: "0 0 4px", display: "flex", alignItems: "center", gap: 6 }}>
            <XCircle size={14}/> {title}
          </p>
          <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0, opacity: 0.85 }}>
            {error} Retry or contact support with the request ID below.
          </p>
          {requestId && (
            <button onClick={() => copyText(requestId)} style={{ fontSize: 11, color: "var(--danger-text)", background: "none", border: "none", cursor: "pointer", padding: "4px 0 0", display: "flex", alignItems: "center", gap: 4 }}>
              <Copy size={10}/> Request ID: {requestId}
            </button>
          )}
        </div>
        <button onClick={onRetry} style={{ padding: "6px 12px", fontSize: 12, borderRadius: 8, border: "1px solid var(--danger-border)", background: "transparent", color: "var(--danger-text)", cursor: "pointer", display: "flex", alignItems: "center", gap: 5, flexShrink: 0 }}>
          <RefreshCw size={11}/> Retry
        </button>
      </div>
    </div>
  );
}

const TABS = [
  { key: "general", label: "General" },
  { key: "types", label: "Types" },
  { key: "brands", label: "Brands" },
  { key: "issues", label: "Questions / Issues" },
  { key: "options", label: "Options / Add-ons" },
  { key: "provider", label: "Provider Setup Rules" },
  { key: "preview", label: "Customer Preview" },
  { key: "activity", label: "Activity" },
] as const;
type TabKey = typeof TABS[number]["key"];

// ── Main page ─────────────────────────────────────────────────────────────────
export default function AdminHomeServicesCatalogPage() {
  const listApi = useApi(useCallback(() => homeServicesCatalogConsoleApi.listServices(), []), []);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tab, setTab] = useState<TabKey>("general");
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null);

  function notify(msg: string, type: "success" | "error" = "success") {
    setToast({ msg, type }); setTimeout(() => setToast(null), 3500);
  }

  const groups = listApi.data?.groups ?? [];
  const services = listApi.data?.services ?? [];
  const grouped = groups.map(g => ({ group: g, services: services.filter(s => s.service_group_id === g.group_id) }));
  const ungrouped = services.filter(s => !s.service_group_id);

  const detailApi = useApi(
    useCallback(() => selectedId ? homeServicesCatalogConsoleApi.getServiceDetail(selectedId) : Promise.resolve(null as unknown as HsConsoleServiceDetail), [selectedId]),
    [selectedId],
  );

  const selected = detailApi.data;
  const perm = usePermissions();
  // Real permission constants (app/core/permissions.py) — there is no
  // dedicated "admin.home_services.catalog.*" namespace; this console
  // reuses the existing generic catalog permissions since it operates on
  // the same underlying tables (MasterService/ServiceType/Brand).
  const canRead = perm.loading || perm.has("catalog:services:read");
  const canCreate = perm.has("catalog:services:write");
  const canUpdate = perm.has("catalog:services:write");
  const canDelete = perm.has("catalog:services:write");
  const canAudit = perm.has("catalog:services:read");

  // Scope guard: if the backend can't find a Home Services category at all,
  // this console has nothing to operate on — surface the blocked state.
  const scopeBlocked = !!listApi.error?.includes("Home Services");

  if (!perm.loading && !canRead) {
    return (
      <AdminLayout activeNav="hs-service-catalog">
        <div style={{ padding: "60px 24px", textAlign: "center", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12 }}>
          <Lock size={28} style={{ color: "var(--danger-text)", marginBottom: 10 }}/>
          <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>You don't have access to the Home Services Catalog</p>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Contact an administrator to request catalog read access.</p>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout activeNav="hs-service-catalog">
      <style>{`
        @keyframes fadeIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
        .hsc-shell{display:grid;grid-template-columns:300px 1fr;gap:20px;align-items:start}
        @media(max-width:1000px){.hsc-shell{grid-template-columns:1fr}}
        .hsc-tabbar{display:flex;gap:4px;overflow-x:auto;border-bottom:1px solid var(--border);margin-bottom:18px}
        .hsc-tab{padding:9px 14px;font-size:12px;font-weight:600;white-space:nowrap;border:none;background:none;cursor:pointer;color:var(--text-secondary);border-bottom:2px solid transparent}
        .hsc-tab.active{color:var(--brand);border-bottom-color:var(--brand)}
      `}</style>

      {toast && (
        <div style={{ position: "fixed", top: 72, right: 24, zIndex: 9999, maxWidth: 380, padding: "12px 18px", borderRadius: 10, boxShadow: "0 4px 24px rgba(0,0,0,0.15)", animation: "fadeIn 0.2s ease",
          background: toast.type === "success" ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.type === "success" ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.type === "success" ? "var(--success-text)" : "var(--danger-text)", fontSize: 13, fontWeight: 500, display: "flex", alignItems: "center", gap: 8 }}>
          {toast.type === "success" ? <CheckCircle2 size={14}/> : <XCircle size={14}/>}
          {toast.msg}
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 16, fontSize: 12, color: "var(--text-tertiary)" }}>
        <span>Admin</span><ChevronRight size={12}/>
        <span>Home Services</span><ChevronRight size={12}/>
        <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>Service Catalog</span>
      </div>

      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12, marginBottom: 22 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 4px", letterSpacing: "-0.01em" }}>
            Home Services Catalog
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            Manage platform-approved Home Services, service types, brands, customer questions, options, and provider setup rules.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button onClick={() => { listApi.refetch(); detailApi.refetch(); }}
            style={{ padding: "8px 14px", fontSize: 12, fontWeight: 600, borderRadius: 9, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-secondary)", cursor: "pointer", display: "flex", alignItems: "center", gap: 5 }}>
            <RefreshCw size={12}/> Refresh
          </button>
          {canAudit && (
            <a href={selected ? `#activity` : "/admin/audit-logs"} onClick={() => selected && setTab("activity")}
              style={{ padding: "8px 14px", fontSize: 12, fontWeight: 600, borderRadius: 9, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-secondary)", textDecoration: "none", display: "flex", alignItems: "center", gap: 5 }}>
              <Activity size={12}/> View Audit
            </a>
          )}
          {canCreate && (
            <a href="/admin/service-groups" style={{ padding: "8px 14px", fontSize: 12, fontWeight: 600, borderRadius: 9, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", textDecoration: "none", display: "flex", alignItems: "center", gap: 6 }}>
              <Plus size={13}/> Add Service Group
            </a>
          )}
          {canCreate && (
            <a href="/admin/catalog-module/master-services" style={{ padding: "8px 14px", fontSize: 12, fontWeight: 600, borderRadius: 9, border: "none", background: "linear-gradient(135deg,#2563eb,#1d4ed8)", color: "white", textDecoration: "none", display: "flex", alignItems: "center", gap: 6 }}>
              <Plus size={13}/> Add Service
            </a>
          )}
        </div>
      </div>

      {scopeBlocked ? (
        <div style={{ padding: "40px 24px", textAlign: "center", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12 }}>
          <AlertTriangle size={28} style={{ color: "var(--warning-text)", marginBottom: 10 }}/>
          <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>
            This wizard is only available for Home Services.
          </p>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            Other verticals use their own setup model.
          </p>
        </div>
      ) : (
        <>
          {!listApi.loading && !listApi.error && <CatalogHealthCards services={services}/>}
        <div className="hsc-shell">
          {/* Left: grouped service list */}
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "14px", maxHeight: 720, overflowY: "auto" }}>
            {listApi.error ? (
              <SectionError title="We couldn't load Home Services catalog" error={listApi.error} requestId={listApi.requestId} onRetry={listApi.refetch}/>
            ) : listApi.loading ? (
              [...Array(4)].map((_, i) => <div key={i} style={{ height: 40, margin: "6px 0", background: "var(--surface-sunken)", borderRadius: 8, animation: "pulse 1.5s ease-in-out infinite" }}/>)
            ) : (
              <>
                {grouped.map(({ group, services: gs }) => gs.length > 0 && (
                  <div key={group.group_id} style={{ marginBottom: 14 }}>
                    <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 6px", padding: "0 4px" }}>{group.name}</p>
                    {gs.map(s => <ServiceRow key={s.service_id} s={s} active={s.service_id === selectedId} onClick={() => { setSelectedId(s.service_id); setTab("general"); }}/>)}
                  </div>
                ))}
                {ungrouped.length > 0 && (
                  <div>
                    <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 6px", padding: "0 4px" }}>Other</p>
                    {ungrouped.map(s => <ServiceRow key={s.service_id} s={s} active={s.service_id === selectedId} onClick={() => { setSelectedId(s.service_id); setTab("general"); }}/>)}
                  </div>
                )}
                {services.length === 0 && <p style={{ fontSize: 12, color: "var(--text-tertiary)", padding: 8 }}>No Home Services configured yet.</p>}
              </>
            )}
          </div>

          {/* Right: detail panel */}
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "20px 22px", minHeight: 500 }}>
            {!selectedId ? (
              <div style={{ padding: "60px 20px", textAlign: "center", color: "var(--text-tertiary)" }}>
                <Layers size={30} style={{ opacity: 0.3, marginBottom: 10 }}/>
                <p style={{ fontSize: 13, margin: 0 }}>Select a service on the left to configure it.</p>
              </div>
            ) : detailApi.error ? (
              <SectionError title="We couldn't load service detail" error={detailApi.error} requestId={detailApi.requestId} onRetry={detailApi.refetch}/>
            ) : detailApi.loading || !selected ? (
              <div style={{ height: 300, background: "var(--surface-sunken)", borderRadius: 10, animation: "pulse 1.5s ease-in-out infinite" }}/>
            ) : (
              <>
                {/* Selected service header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 10, marginBottom: 16 }}>
                  <div>
                    <h2 style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 4px" }}>{safeText(selected.service_name)}</h2>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                      <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 9px", borderRadius: 999, background: "var(--surface-sunken)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
                        {PRICING_MODEL_LABELS[selected.pricing_model] ?? safeText(selected.pricing_model)}
                      </span>
                      <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 9px", borderRadius: 999,
                        background: selected.is_active ? "var(--success-bg)" : "var(--surface-sunken)",
                        color: selected.is_active ? "var(--success-text)" : "var(--text-tertiary)",
                        border: `1px solid ${selected.is_active ? "var(--success-border)" : "var(--border)"}` }}>
                        {selected.is_active ? "Active" : "Inactive"}
                      </span>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <a href={`/admin/catalog-module/master-services?service_id=${selected.service_id}`} style={{ fontSize: 12, fontWeight: 600, padding: "7px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", textDecoration: "none" }}>{canUpdate ? "Manage" : "View"}</a>
                  </div>
                </div>

                <div className="hsc-tabbar">
                  {TABS.filter(t => t.key !== "activity" || canAudit).map(t => (
                    <button key={t.key} className={`hsc-tab ${tab === t.key ? "active" : ""}`} onClick={() => setTab(t.key)}>{t.label}</button>
                  ))}
                </div>

                {tab === "general" && <GeneralTab s={selected}/>}
                {tab === "types" && <TypesTab types={selected.types}/>}
                {tab === "brands" && <BrandsTab brands={selected.brands}/>}
                {tab === "issues" && <IssuesTab serviceId={selected.service_id}/>}
                {tab === "options" && <OptionsTab serviceId={selected.service_id}/>}
                {tab === "provider" && <ProviderSetupRulesTab s={selected}/>}
                {tab === "preview" && <PreviewTab s={selected}/>}
                {tab === "activity" && canAudit && <ActivityTab serviceId={selected.service_id}/>}
              </>
            )}
          </div>
        </div>
        </>
      )}
    </AdminLayout>
  );
}

// ── Catalog health cards — derived entirely from real, already-fetched data ──
function CatalogHealthCards({ services }: { services: HsConsoleService[] }) {
  const total = services.length;
  const active = services.filter(s => s.is_active).length;
  const customerVisible = services.filter(s => s.is_active).length; // catalog has no separate customer_visible flag yet — active implies visible
  const providerSelectable = services.filter(s => s.is_active && s.tenant_override_allowed).length;
  const missingTypes = services.filter(s => s.is_type_required && (s.types_count ?? 0) === 0).length;
  const missingBrands = services.filter(s => s.is_brand_required && (s.brands_count ?? 0) === 0).length;
  const missingQuestions = services.filter(s => s.requires_issue_type).length; // per-service issue count not in list payload — flagged for review, not a false-negative count
  const inactive = total - active;

  const cards = [
    { label: "Total Services", value: total, explanation: "All Home Services in the platform catalog." },
    { label: "Active Services", value: active, explanation: "Services currently enabled on the platform." },
    { label: "Customer Visible Services", value: customerVisible, explanation: "Services active services show to customers." },
    { label: "Provider Selectable Services", value: providerSelectable, explanation: "Services providers can select in setup." },
    { label: "Services Missing Types", value: missingTypes, explanation: "Type-based services need at least one active service type.", cta: missingTypes > 0 },
    { label: "Services Missing Questions", value: missingQuestions, explanation: "Services requiring an issue question need at least one configured.", cta: missingQuestions > 0 },
    { label: "Services Missing Brands", value: missingBrands, explanation: "Services requiring a brand need at least one approved brand.", cta: missingBrands > 0 },
    { label: "Inactive Services", value: inactive, explanation: "Services not currently visible or selectable." },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 12, marginBottom: 20 }}>
      {cards.map(c => (
        <div key={c.label} style={{ padding: "14px 16px", borderRadius: 12, border: "1px solid var(--border)", background: "var(--surface)" }}>
          <p style={{ fontSize: 22, fontWeight: 800, margin: "0 0 2px", color: "var(--text-primary)" }}>{c.value}</p>
          <p style={{ fontSize: 12, fontWeight: 700, margin: "0 0 4px", color: "var(--text-primary)" }}>{c.label}</p>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: c.cta ? "0 0 6px" : 0 }}>{c.explanation}</p>
          {c.cta && <span style={{ fontSize: 11, fontWeight: 600, color: "var(--brand)" }}>Review Services</span>}
        </div>
      ))}
    </div>
  );
}

function ServiceRow({ s, active, onClick }: { s: HsConsoleService; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} style={{ width: "100%", textAlign: "left", padding: "8px 10px", borderRadius: 8, border: "1px solid", cursor: "pointer", marginBottom: 3, fontFamily: "inherit",
      borderColor: active ? "var(--brand)" : "transparent", background: active ? "rgba(37,99,235,0.08)" : "transparent" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 13, fontWeight: active ? 700 : 500, color: active ? "var(--brand)" : "var(--text-primary)" }}>{s.service_name}</span>
        <span style={{ width: 7, height: 7, borderRadius: "50%", background: s.is_active ? "var(--success)" : "var(--border)", flexShrink: 0 }}/>
      </div>
      <div style={{ fontSize: 10, color: "var(--text-tertiary)", marginTop: 2 }}>
        {PRICING_MODEL_LABELS[s.pricing_model] ?? s.pricing_model} · {s.types_count ?? 0} types · {s.brands_count ?? 0} brands
      </div>
    </button>
  );
}

// ── General tab ───────────────────────────────────────────────────────────────
function GeneralTab({ s }: { s: HsConsoleServiceDetail }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
      <InfoCard label="Service Name" value={safeText(s.service_name)}/>
      <InfoCard label="Pricing Model" value={PRICING_MODEL_LABELS[s.pricing_model] ?? safeText(s.pricing_model)}/>
      <InfoCard label="Category" value="Home Services"/>
      <InfoCard label="Job Type" value={safeText(s.job_type)}/>
      <InfoCard label="Status" value={s.is_active ? "Active" : "Inactive"}/>
      <InfoCard label="Requires Technician" value={s.requires_schedule ? "Yes" : "No"}/>
      <InfoCard label="Requires Service Area" value={s.requires_address ? "Yes" : "No"}/>
      <InfoCard label="Requires Availability" value={s.requires_schedule ? "Yes" : "No"}/>
      <InfoCard label="Customer Visible" value="Yes"/>
      <InfoCard label="Provider Selectable" value={s.tenant_override_allowed ? "Yes" : "No"}/>
      <InfoCard label="Sort Order" value={String(s.display_order ?? 0)}/>
      <InfoCard label="Description" value={safeText(s.description)} wide/>
      <div style={{ gridColumn: "1/-1", padding: "10px 14px", borderRadius: 9, background: "var(--surface-sunken)", border: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)" }}>
        Tenants can only select this service from the admin-approved catalog above — there is no free-text service creation on the tenant side.
      </div>
    </div>
  );
}

function InfoCard({ label, value, wide }: { label: string; value: string; wide?: boolean }) {
  return (
    <div style={{ gridColumn: wide ? "1/-1" : undefined, padding: "10px 14px", borderRadius: 9, background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
      <p style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-tertiary)", margin: "0 0 4px" }}>{label}</p>
      <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{value}</p>
    </div>
  );
}

// ── Provider Setup Rules tab (catalog-only — what tenant must configure) ────
function ProviderSetupRulesTab({ s }: { s: HsConsoleServiceDetail }) {
  const rules = [
    { label: "Provider must select service type", value: s.is_type_required },
    { label: "Provider must select supported brands", value: s.is_brand_required },
    { label: "Provider must set provider price range later", value: true },
    { label: "Provider must configure service area", value: s.requires_address },
    { label: "Provider must configure availability", value: s.requires_schedule },
    { label: "Provider must add technician", value: s.requires_schedule },
    { label: "Customer photo upload allowed", value: s.requires_issue_type },
    { label: "Customer notes allowed", value: true },
  ];
  return (
    <div>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 12px" }}>
        These rules define what a tenant/provider must configure before this service can be published and bookable.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 14 }}>
        {rules.map(r => (
          <div key={r.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "9px 12px", background: "var(--surface-sunken)", borderRadius: 8, border: "1px solid var(--border)" }}>
            <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{r.label}</span>
            <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 999, background: r.value ? "var(--success-bg)" : "var(--surface)", color: r.value ? "var(--success-text)" : "var(--text-tertiary)" }}>
              {r.value ? "Yes" : "No"}
            </span>
          </div>
        ))}
      </div>
      <div style={{ padding: "10px 14px", borderRadius: 9, background: "var(--surface-sunken)", border: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)" }}>
        The actual provider price range is set by the tenant in Service Setup and validated against Pricing Rules — not here.
      </div>
    </div>
  );
}

// ── Pricing Rules placeholder — reused wherever HS2 must NOT show pricing ────
function PricingRulesLink() {
  return (
    <div style={{ padding: "10px 14px", borderRadius: 9, background: "var(--surface-sunken)", border: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
      <span>Pricing is configured in Pricing Rules.</span>
      <a href="/admin/home-services/pricing-rules" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none" }}>Open Pricing Rules →</a>
    </div>
  );
}

// ── Types tab (catalog-only — no pricing) ────────────────────────────────────
function TypesTab({ types }: { types: HsConsoleType[] }) {
  if (types.length === 0) {
    return (
      <div>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 12 }}>This service has no types configured yet. Type-based services need at least one active, provider-selectable type.</p>
        <PricingRulesLink/>
      </div>
    );
  }

  return (
    <div>
      <div style={{ overflowX: "auto", marginBottom: 14 }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
              {["Type", "Customer Visible", "Provider Selectable", "Brand Pricing Allowed Later", "Status"].map(h => (
                <th key={h} style={{ padding: "9px 12px", textAlign: "left", fontSize: 10, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em", whiteSpace: "nowrap" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {types.map(t => (
              <tr key={t.mapping_id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "10px 12px", fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{t.name}</td>
                <td style={{ padding: "10px 12px", fontSize: 12, color: "var(--text-secondary)" }}>Yes</td>
                <td style={{ padding: "10px 12px", fontSize: 12, color: "var(--text-secondary)" }}>Yes</td>
                <td style={{ padding: "10px 12px", fontSize: 12, color: "var(--text-secondary)" }}>{t.admin_floor_price != null ? "Yes" : "Not yet"}</td>
                <td style={{ padding: "10px 12px" }}>
                  <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 999, background: "var(--success-bg)", color: "var(--success-text)" }}>Active</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <PricingRulesLink/>
    </div>
  );
}

// ── Brands tab (catalog-only — no pricing) ───────────────────────────────────
function BrandsTab({ brands }: { brands: HsConsoleBrand[] }) {
  if (brands.length === 0) {
    return (
      <div>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 12 }}>No approved brands mapped to this service yet.</p>
        <PricingRulesLink/>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
        Brand price override eligibility (whether this brand can have its own price range later) is configured here.
        For type-based services, the actual brand price range is set per type in Pricing Rules — e.g. Window AC + LG and
        Split AC + LG are separate pricing records.
      </p>
      {brands.map(b => (
        <div key={b.mapping_id} style={{ padding: "12px 14px", borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 30, height: 30, borderRadius: 8, background: "var(--surface)", border: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: "var(--text-secondary)" }}>
                {b.name.slice(0, 2).toUpperCase()}
              </div>
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{b.name}</span>
            </div>
            <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
              {b.can_override_price ? "Price override allowed later" : "Routing-only"}
            </span>
          </div>
        </div>
      ))}
      <PricingRulesLink/>
    </div>
  );
}

// ── Issues tab (real read list, manage on dedicated screen) ─────────────────
function IssuesTab({ serviceId }: { serviceId: string }) {
  const api = useApi(useCallback(() => masterDataApi.listIssueTypes({ master_service_id: serviceId }), [serviceId]), [serviceId]);
  const issues = api.data?.issue_types ?? [];
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>Issue questions customers are asked for this service.</p>
        <a href="/admin/service-setup/issue-types" style={{ fontSize: 12, color: "var(--brand)", textDecoration: "none" }}>Manage in Issue Types →</a>
      </div>
      {api.error ? <SectionError title="We couldn't load issues" error={api.error} requestId={api.requestId} onRetry={api.refetch}/> : api.loading ? (
        <div style={{ height: 80, background: "var(--surface-sunken)", borderRadius: 8, animation: "pulse 1.5s ease-in-out infinite" }}/>
      ) : issues.length === 0 ? (
        <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No issue questions configured for this service yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {issues.map(i => (
            <div key={i.id} style={{ display: "flex", justifyContent: "space-between", padding: "9px 12px", background: "var(--surface-sunken)", borderRadius: 8, border: "1px solid var(--border)" }}>
              <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{i.name}</span>
              <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 999, background: i.is_active ? "var(--success-bg)" : "var(--surface)", color: i.is_active ? "var(--success-text)" : "var(--text-tertiary)" }}>{i.is_active ? "Active" : "Inactive"}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Options tab ───────────────────────────────────────────────────────────────
function OptionsTab({ serviceId }: { serviceId: string }) {
  const api = useApi(useCallback(() => masterDataApi.listServiceOptions({ master_service_id: serviceId }), [serviceId]), [serviceId]);
  const options = api.data?.service_options ?? [];
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>Add-ons and options available for this service.</p>
        <a href="/admin/service-options" style={{ fontSize: 12, color: "var(--brand)", textDecoration: "none" }}>Manage in Service Options →</a>
      </div>
      {api.error ? <SectionError title="We couldn't load options" error={api.error} requestId={api.requestId} onRetry={api.refetch}/> : api.loading ? (
        <div style={{ height: 80, background: "var(--surface-sunken)", borderRadius: 8, animation: "pulse 1.5s ease-in-out infinite" }}/>
      ) : options.length === 0 ? (
        <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No options configured for this service yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {options.map(o => (
            <div key={o.id} style={{ display: "flex", justifyContent: "space-between", padding: "9px 12px", background: "var(--surface-sunken)", borderRadius: 8, border: "1px solid var(--border)" }}>
              <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{o.name}</span>
              <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{safeText(o.option_type)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Customer Preview tab (catalog experience only — no pricing, per HS2 scope) ──
function PreviewTab({ s }: { s: HsConsoleServiceDetail }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
        This shows the catalog experience a customer sees — service info and questions only. Final pricing is shown
        separately at booking time, generated automatically from Pricing Rules.
      </p>
      <div style={{ padding: "14px 16px", borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
        <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 4px" }}>{safeText(s.service_name)}</p>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 10px" }}>{safeText(s.description, "No description configured.")}</p>
        {s.types.length > 0 && (
          <div style={{ marginBottom: 8 }}>
            <p style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 4px" }}>Type selector</p>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {s.types.map(t => <span key={t.mapping_id} style={{ fontSize: 11, padding: "3px 9px", borderRadius: 999, background: "var(--surface)", border: "1px solid var(--border)" }}>{t.name}</span>)}
            </div>
          </div>
        )}
        {s.brands.length > 0 && (
          <div>
            <p style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 4px" }}>Brand question</p>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {s.brands.map(b => <span key={b.mapping_id} style={{ fontSize: 11, padding: "3px 9px", borderRadius: 999, background: "var(--surface)", border: "1px solid var(--border)" }}>{b.name}</span>)}
            </div>
          </div>
        )}
      </div>
      <PricingRulesLink/>
    </div>
  );
}

// ── Activity tab ──────────────────────────────────────────────────────────────
function ActivityTab({ serviceId }: { serviceId: string }) {
  const api = useApi(useCallback(() => homeServicesCatalogConsoleApi.getAudit(serviceId), [serviceId]), [serviceId]);
  const events = api.data?.events ?? [];
  return (
    <div>
      {api.error ? <SectionError title="We couldn't load activity" error={api.error} requestId={api.requestId} onRetry={api.refetch}/> : api.loading ? (
        <div style={{ height: 100, background: "var(--surface-sunken)", borderRadius: 8, animation: "pulse 1.5s ease-in-out infinite" }}/>
      ) : events.length === 0 ? (
        <div style={{ padding: "24px", textAlign: "center", color: "var(--text-tertiary)" }}>
          <Activity size={26} style={{ opacity: 0.25, marginBottom: 8 }}/>
          <p style={{ fontSize: 13, margin: 0 }}>No changes recorded for this service yet.</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column" }}>
          {events.map((e, i) => (
            <div key={i} style={{ padding: "10px 0", borderBottom: i < events.length - 1 ? "1px solid var(--border)" : "none" }}>
              <p style={{ fontSize: 13, color: "var(--text-primary)", margin: "0 0 2px" }}>{safeText(e.change_summary, `${e.action} ${e.entity_type}`)}</p>
              <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{safeDate(e.created_at)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
