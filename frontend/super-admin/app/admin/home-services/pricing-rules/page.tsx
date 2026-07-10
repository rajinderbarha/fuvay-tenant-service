"use client";
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import {
  homeServicesCatalogConsoleApi, catalogApi, masterDataApi,
  type PricingRule, type HsConsoleService,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import {
  ChevronRight, RefreshCw, Plus, XCircle, CheckCircle2, Copy, X, Save,
} from "lucide-react";

const safeText = (v: unknown, fb = "Not configured"): string =>
  (typeof v === "string" && v.trim()) ? v.trim() : fb;
const safeCurrency = (v: unknown): string =>
  (typeof v === "number" && isFinite(v)) ? `₹${v.toLocaleString("en-IN")}` : "Not configured";
const safePercent = (v: unknown): string =>
  (typeof v === "number" && isFinite(v)) ? `${v}%` : "Not configured";
function copyText(t: string) { if (typeof navigator !== "undefined") navigator.clipboard?.writeText(t).catch(() => {}); }

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
          <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0, opacity: 0.85 }}>{error} Retry or contact support with the request ID below.</p>
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

interface FormState {
  master_service_id: string; service_type_id: string; brand_id: string;
  min_price: string; max_price: string; platform_fee_percent: string;
  completed_job_deduction_credits: string; is_active: boolean; rule_name: string;
}
const BLANK: FormState = {
  master_service_id: "", service_type_id: "", brand_id: "",
  min_price: "", max_price: "", platform_fee_percent: "10",
  completed_job_deduction_credits: "0", is_active: true, rule_name: "",
};

export default function AdminHomeServicesPricingRulesPage() {
  const servicesApi = useApi(useCallback(() => homeServicesCatalogConsoleApi.listServices(), []), []);
  const rulesApi = useApi(useCallback(() => catalogApi.listPricingRules(undefined, { pageSize: 200 }), []), []);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<PricingRule | null>(null);
  const [form, setForm] = useState<FormState>(BLANK);
  const [formError, setFormError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null);
  function notify(msg: string, type: "success" | "error" = "success") { setToast({ msg, type }); setTimeout(() => setToast(null), 3500); }

  const services = servicesApi.data?.services ?? [];
  const homeServiceIds = new Set(services.map(s => s.service_id));
  // Hard scope: only ever show pricing rules for services in the real Home Services category.
  const rules = (rulesApi.data?.items ?? []).filter(r => homeServiceIds.has(r.master_service_id));

  const typesApi = useApi(
    useCallback(() => form.master_service_id ? catalogApi.listServiceTypeMappings(form.master_service_id) : Promise.resolve({ types: [] }), [form.master_service_id]),
    [form.master_service_id],
  );
  const brandsApi = useApi(
    useCallback(() => form.master_service_id ? catalogApi.listBrandMappings(form.master_service_id) : Promise.resolve({ brands: [] }), [form.master_service_id]),
    [form.master_service_id],
  );

  function serviceName(id: string): string { return services.find(s => s.service_id === id)?.service_name ?? "Not configured"; }

  function openCreate() { setEditingRule(null); setForm(BLANK); setFormError(null); setModalOpen(true); }
  function openEdit(r: PricingRule) {
    setEditingRule(r);
    setForm({
      master_service_id: r.master_service_id, service_type_id: r.service_type_id ?? "", brand_id: r.brand_id ?? "",
      min_price: r.min_price != null ? String(r.min_price) : "", max_price: r.max_price != null ? String(r.max_price) : "",
      platform_fee_percent: String(r.platform_fee_percent ?? 10),
      completed_job_deduction_credits: String(r.completed_job_deduction_credits ?? 0),
      is_active: r.is_active, rule_name: r.rule_name ?? "",
    });
    setFormError(null);
    setModalOpen(true);
  }

  const saveAction = useAction(useCallback(async (f: FormState, ruleId: string | null) => {
    const min = Number(f.min_price), max = Number(f.max_price);
    const fee = Number(f.platform_fee_percent), deduction = Number(f.completed_job_deduction_credits);
    if (!f.master_service_id) throw new Error("Service is required.");
    if (!isFinite(min) || min <= 0) throw new Error("Admin Minimum Price must be greater than 0.");
    if (!isFinite(max) || max < min) throw new Error("Admin Maximum Price must be greater than or equal to Admin Minimum Price.");
    if (!isFinite(fee) || fee < 0) throw new Error("Platform Fee must be greater than or equal to 0.");
    if (!isFinite(deduction) || deduction < 0) throw new Error("Completed Job Deduction must be greater than or equal to 0.");

    const pricingModel = services.find(s => s.service_id === f.master_service_id)?.pricing_model ?? "range";
    // HS3 — Type-Dependent Brand Pricing: a brand override on a type-based
    // service must be scoped to a type, otherwise the price is wrongly
    // global across every type. Mirrors the backend's
    // SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING check as fast client-side
    // feedback (the backend still enforces this regardless).
    if (f.brand_id && pricingModel === "range" && !f.service_type_id) {
      throw new Error("Service type is required when adding brand pricing for a type-based service.");
    }

    const payload = {
      master_service_id: f.master_service_id,
      service_type_id: f.service_type_id || undefined,
      brand_id: f.brand_id || undefined,
      job_type: services.find(s => s.service_id === f.master_service_id)?.job_type ?? "repair",
      pricing_model: pricingModel,
      base_price: min,
      min_price: min, max_price: max,
      platform_fee_percent: fee,
      completed_job_deduction_credits: deduction,
      is_active: f.is_active,
      rule_name: f.rule_name || undefined,
    };
    if (ruleId) await catalogApi.updatePricingRule(ruleId, payload);
    else await catalogApi.createPricingRule(payload);
  }, [services]));

  async function handleSave() {
    setFormError(null);
    try {
      await saveAction.execute(form, editingRule?.rule_id ?? null);
      setModalOpen(false);
      rulesApi.refetch();
      notify(editingRule ? "Pricing rule updated." : "Pricing rule created.");
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Price range could not be saved.");
    }
  }

  return (
    <AdminLayout activeNav="hs-pricing-rules">
      <style>{`@keyframes fadeIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}} @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}`}</style>

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
        <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>Pricing Rules</span>
      </div>

      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12, marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 4px" }}>Home Services Pricing Rules</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            Set platform-controlled price boundaries by service, type, brand, and tier. Providers can only set prices inside these ranges.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={() => { rulesApi.refetch(); servicesApi.refetch(); }}
            style={{ padding: "8px 14px", fontSize: 12, fontWeight: 600, borderRadius: 9, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-secondary)", cursor: "pointer", display: "flex", alignItems: "center", gap: 5 }}>
            <RefreshCw size={12}/> Refresh
          </button>
          <button onClick={openCreate}
            style={{ padding: "8px 16px", fontSize: 13, fontWeight: 600, borderRadius: 9, border: "none", background: "linear-gradient(135deg,#2563eb,#1d4ed8)", color: "white", cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
            <Plus size={13}/> Add Rule
          </button>
        </div>
      </div>

      {(rulesApi.error || servicesApi.error) ? (
        <SectionError title="Price range could not be loaded" error={rulesApi.error ?? servicesApi.error ?? ""} requestId={rulesApi.requestId ?? servicesApi.requestId} onRetry={() => { rulesApi.refetch(); servicesApi.refetch(); }}/>
      ) : rulesApi.loading || servicesApi.loading ? (
        <div style={{ height: 200, background: "var(--surface-sunken)", borderRadius: 12, animation: "pulse 1.5s ease-in-out infinite" }}/>
      ) : (
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                  {["Service", "Type", "Brand", "Zone/Tier", "Admin Min", "Admin Max", "Platform Fee", "Completed Job Deduction", "Status", "Actions"].map(h => (
                    <th key={h} style={{ padding: "9px 12px", textAlign: "left", fontSize: 10, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", whiteSpace: "nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rules.map(r => (
                  <tr key={r.rule_id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "9px 12px", fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{serviceName(r.master_service_id)}</td>
                    <td style={{ padding: "9px 12px", fontSize: 12, color: "var(--text-secondary)" }}>{r.service_type_id ? "Type-scoped" : "All Types"}</td>
                    <td style={{ padding: "9px 12px", fontSize: 12, color: "var(--text-secondary)" }}>{r.brand_id ? "Brand-scoped" : "All Brands"}</td>
                    <td style={{ padding: "9px 12px", fontSize: 12, color: "var(--text-secondary)" }}>{safeText(r.zone ?? r.city, "All Zones")}</td>
                    <td style={{ padding: "9px 12px", fontSize: 12 }}>{safeCurrency(r.min_price)}</td>
                    <td style={{ padding: "9px 12px", fontSize: 12 }}>{safeCurrency(r.max_price)}</td>
                    <td style={{ padding: "9px 12px", fontSize: 12 }}>{safePercent(r.platform_fee_percent)}</td>
                    <td style={{ padding: "9px 12px", fontSize: 12 }}>{r.completed_job_deduction_credits ?? 0} usage credits</td>
                    <td style={{ padding: "9px 12px" }}>
                      <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 999, background: r.is_active ? "var(--success-bg)" : "var(--surface-sunken)", color: r.is_active ? "var(--success-text)" : "var(--text-tertiary)" }}>
                        {r.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td style={{ padding: "9px 12px" }}>
                      <button onClick={() => openEdit(r)} style={{ fontSize: 11, fontWeight: 600, padding: "5px 10px", borderRadius: 7, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", cursor: "pointer" }}>Edit</button>
                    </td>
                  </tr>
                ))}
                {rules.length === 0 && (
                  <tr><td colSpan={10} style={{ padding: 20, textAlign: "center", fontSize: 12, color: "var(--text-tertiary)" }}>No Home Services pricing rules configured yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {modalOpen && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
          <div style={{ background: "var(--surface)", borderRadius: 14, maxWidth: 520, width: "100%", maxHeight: "90vh", overflowY: "auto", border: "1px solid var(--border)" }}>
            <div style={{ padding: "18px 24px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>{editingRule ? "Edit Pricing Rule" : "Add Pricing Rule"}</h2>
              <button onClick={() => setModalOpen(false)} style={{ width: 28, height: 28, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface-sunken)", cursor: "pointer" }}><X size={13}/></button>
            </div>
            <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 14 }}>
              <Field label="Service">
                <select value={form.master_service_id} onChange={e => setForm({ ...form, master_service_id: e.target.value, service_type_id: "", brand_id: "" })}
                  style={selectStyle}>
                  <option value="">Select a service…</option>
                  {services.map(s => <option key={s.service_id} value={s.service_id}>{s.service_name}</option>)}
                </select>
              </Field>
              <Field label="Type (optional)">
                <select value={form.service_type_id} onChange={e => setForm({ ...form, service_type_id: e.target.value })} style={selectStyle} disabled={!form.master_service_id}>
                  <option value="">All Types</option>
                  {(typesApi.data?.types ?? []).map(t => <option key={t.service_type_id} value={t.service_type_id}>{t.name}</option>)}
                </select>
              </Field>
              <Field label="Brand (optional)">
                <select value={form.brand_id} onChange={e => setForm({ ...form, brand_id: e.target.value })} style={selectStyle} disabled={!form.master_service_id}>
                  <option value="">All Brands</option>
                  {(brandsApi.data?.brands ?? []).map(b => <option key={b.brand_id} value={b.brand_id}>{b.name}</option>)}
                </select>
              </Field>
              <div style={{ display: "flex", gap: 12 }}>
                <Field label="Admin Minimum Price"><input value={form.min_price} onChange={e => setForm({ ...form, min_price: e.target.value })} style={inputStyle}/></Field>
                <Field label="Admin Maximum Price"><input value={form.max_price} onChange={e => setForm({ ...form, max_price: e.target.value })} style={inputStyle}/></Field>
              </div>
              <div style={{ display: "flex", gap: 12 }}>
                <Field label="Platform Fee %"><input value={form.platform_fee_percent} onChange={e => setForm({ ...form, platform_fee_percent: e.target.value })} style={inputStyle}/></Field>
                <Field label="Completed Job Deduction Credits"><input value={form.completed_job_deduction_credits} onChange={e => setForm({ ...form, completed_job_deduction_credits: e.target.value })} style={inputStyle}/></Field>
              </div>
              <Field label="Internal Notes (rule name)"><input value={form.rule_name} onChange={e => setForm({ ...form, rule_name: e.target.value })} style={inputStyle} placeholder="Optional"/></Field>
              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-primary)", cursor: "pointer" }}>
                <input type="checkbox" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })}/> Active
              </label>

              {formError && (
                <div style={{ padding: "10px 14px", background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius: 9, fontSize: 12, color: "var(--danger-text)" }}>
                  {formError}
                  {saveAction.requestId && (
                    <button onClick={() => copyText(saveAction.requestId!)} style={{ display: "block", marginTop: 4, fontSize: 11, color: "var(--danger-text)", background: "none", border: "none", cursor: "pointer", padding: 0 }}>
                      <Copy size={10} style={{ display: "inline", marginRight: 4 }}/> Request ID: {saveAction.requestId}
                    </button>
                  )}
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 6 }}>
                <button onClick={() => setModalOpen(false)} style={{ padding: "9px 16px", fontSize: 13, borderRadius: 9, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", cursor: "pointer" }}>Cancel</button>
                <button onClick={handleSave} disabled={saveAction.loading}
                  style={{ padding: "9px 18px", fontSize: 13, fontWeight: 600, borderRadius: 9, border: "none", background: "var(--brand)", color: "white", cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
                  <Save size={13}/> {saveAction.loading ? "Saving…" : "Save"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </AdminLayout>
  );
}

const selectStyle: React.CSSProperties = { width: "100%", padding: "8px 10px", fontSize: 13, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit" };
const inputStyle: React.CSSProperties = { width: "100%", padding: "8px 10px", fontSize: 13, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit" };

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ flex: 1 }}>
      <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>{label}</label>
      {children}
    </div>
  );
}
