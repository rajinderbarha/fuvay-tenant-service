"use client";
import React, { useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, SectionHeader, Badge, Btn, Skeleton } from "../../../../components/shared/ui";
import { categoryRuntimeApi, monetizationApi, adminOnboardingTemplatesApi, adminCustomerFlowApi, type CategoryRuntime, type CategoryEngineRuntime, type CategoryDashboardModule, type MonetizationConfig, type OnboardingChecklistTemplate, type CustomerFlowConfig } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import {
  Layers, ArrowLeft, Zap, LayoutDashboard, Users, Globe,
  Monitor, Activity, FileText, ToggleLeft, ToggleRight, Star, Settings2, DollarSign,
  ClipboardList, Plus, Pencil, Check, X,
} from "lucide-react";

const TABS = [
  { key: "overview",      label: "Overview",             icon: <Layers size={14}/> },
  { key: "engines",       label: "Running Engines",      icon: <Zap size={14}/> },
  { key: "modules",       label: "Dashboard Modules",    icon: <LayoutDashboard size={14}/> },
  { key: "monetization",  label: "Monetization",         icon: <DollarSign size={14}/> },
  { key: "onboarding",    label: "Onboarding Checklist", icon: <ClipboardList size={14}/> },
  { key: "providers",     label: "Providers",            icon: <Users size={14}/> },
  { key: "customer",      label: "Customer Flow",        icon: <Globe size={14}/> },
  { key: "provider_ui",   label: "Provider Dashboard",   icon: <Monitor size={14}/> },
  { key: "health",        label: "Engine Health",        icon: <Activity size={14}/> },
  { key: "audit",         label: "Audit Logs",           icon: <FileText size={14}/> },
] as const;
type TabKey = typeof TABS[number]["key"];

const FLOW_LABEL: Record<string, string> = {
  service_booking: "Service Booking", appointment_booking: "Appointment Booking",
  lead_capture: "Lead Capture", order_flow: "Order Flow", inquiry_flow: "Inquiry Flow",
};
const DASHBOARD_LABEL: Record<string, string> = {
  home_service_dashboard: "Home Services Dashboard",
  coaching_dashboard: "Coaching Dashboard",
  real_estate_dashboard: "Real Estate Dashboard",
  restaurant_dashboard: "Restaurant Dashboard",
  generic_dashboard: "Generic Dashboard",
};
const MODULE_TYPE_COLOR: Record<string, string> = {
  metric_card: "var(--brand)", chart: "var(--accent)", table: "var(--success)",
  quick_action: "var(--warning)", navigation: "#475569",
};
const HEALTH_COLOR: Record<string, string> = {
  healthy: "var(--success)", degraded: "var(--warning)", down: "var(--danger)", unknown: "#94a3b8",
};

function InfoRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display:"flex", gap:12, padding:"10px 0", borderBottom:"1px solid var(--border)" }}>
      <span style={{ fontSize:12, color:"var(--text-tertiary)", minWidth:160, fontWeight:500 }}>{label}</span>
      <div style={{ fontSize:13, color:"var(--text-primary)", flex:1 }}>{children}</div>
    </div>
  );
}

const MODEL_COLOR: Record<string, string> = {
  credit_wallet_commission: "var(--brand)",
  subscription: "var(--accent)",
  freemium: "var(--success)",
  fixed_billing: "var(--warning)",
};
const MODEL_LABEL: Record<string, string> = {
  credit_wallet_commission: "Credit Wallet + Commission",
  subscription: "Subscription",
  freemium: "Freemium",
  fixed_billing: "Fixed Billing",
};

function MonetizationTab({ catId }: { catId: string }) {
  const cfg = useApi(useCallback(() => monetizationApi.getCategoryConfig(catId), [catId]));
  const [form, setForm] = React.useState<Partial<MonetizationConfig>>({});
  const [editing, setEditing] = React.useState(false);
  const [saved, setSaved] = React.useState(false);

  const saveAction = useAction(async (data: Partial<MonetizationConfig>) => {
    await monetizationApi.upsertCategoryConfig(catId, data);
    cfg.refetch();
    setEditing(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  });

  const c = cfg.data;

  React.useEffect(() => {
    if (c && !editing) {
      setForm({
        monetization_model: c.monetization_model,
        commission_rate: c.commission_rate,
        credit_minimum_balance: c.credit_minimum_balance,
        subscription_plan_type: c.subscription_plan_type ?? undefined,
        subscription_billing_cycle: c.subscription_billing_cycle ?? undefined,
        subscription_amount_inr: c.subscription_amount_inr ?? undefined,
        trial_days: c.trial_days,
        leads_per_billing_cycle: c.leads_per_billing_cycle ?? undefined,
        notes: c.notes ?? undefined,
        is_active: c.is_active,
      });
    }
  }, [c, editing]);

  if (cfg.loading) return <div style={{ padding:24 }}><Skeleton height={300}/></div>;

  const isSubscription = (form.monetization_model ?? c?.monetization_model) === "subscription";
  const isCredit = (form.monetization_model ?? c?.monetization_model) === "credit_wallet_commission";

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
      {saved && (
        <div style={{ padding:"12px 16px", borderRadius:10, background:"rgba(5,150,105,0.08)",
          border:"1px solid rgba(5,150,105,0.25)", fontSize:13, color:"var(--success)", fontWeight:600 }}>
          Monetization config saved.
        </div>
      )}
      {saveAction.error && (
        <div style={{ padding:"12px 16px", borderRadius:10, background:"rgba(220,38,38,0.08)",
          border:"1px solid rgba(220,38,38,0.25)", fontSize:13, color:"var(--danger)" }}>
          {saveAction.error}
        </div>
      )}
      <Card>
        <div style={{ padding:"20px 24px" }}>
          <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:20 }}>
            <div style={{ display:"flex", alignItems:"center", gap:10 }}>
              <DollarSign size={18} style={{ color:"var(--accent)" }}/>
              <span style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)" }}>Monetization Config</span>
              {c && (
                <span style={{ fontSize:11, fontWeight:700, padding:"2px 10px", borderRadius:20,
                  background: `${MODEL_COLOR[c.monetization_model] ?? "#64748b"}18`,
                  color: MODEL_COLOR[c.monetization_model] ?? "var(--text-tertiary)" }}>
                  {MODEL_LABEL[c.monetization_model] ?? c.monetization_model}
                </span>
              )}
            </div>
            {!editing ? (
              <Btn size="sm" variant="secondary" onClick={() => setEditing(true)}>Edit</Btn>
            ) : (
              <div style={{ display:"flex", gap:8 }}>
                <Btn size="sm" variant="secondary" onClick={() => setEditing(false)}>Cancel</Btn>
                <Btn size="sm" variant="primary" loading={saveAction.loading}
                  onClick={() => saveAction.execute(form)}>
                  Save
                </Btn>
              </div>
            )}
          </div>

          {!c && !editing ? (
            <div style={{ textAlign:"center", padding:"32px 0", color:"var(--text-tertiary)", fontSize:13 }}>
              No monetization config set for this category.
              <br/>
              <Btn size="sm" variant="primary" style={{ marginTop:16 }} onClick={() => setEditing(true)}>
                Create Config
              </Btn>
            </div>
          ) : (
            <div style={{ display:"flex", flexDirection:"column", gap:0 }}>
              <InfoRow label="Monetization Model">
                {editing ? (
                  <select value={form.monetization_model ?? ""} onChange={e => setForm(f => ({ ...f, monetization_model: e.target.value }))}
                    style={{ fontSize:13, padding:"4px 8px", borderRadius:6, border:"1px solid var(--border)", background:"var(--surface)" }}>
                    <option value="">Select model…</option>
                    <option value="credit_wallet_commission">Credit Wallet + Commission</option>
                    <option value="subscription">Subscription</option>
                    <option value="freemium">Freemium</option>
                    <option value="fixed_billing">Fixed Billing</option>
                  </select>
                ) : (
                  <span style={{ fontWeight:600, color: MODEL_COLOR[c?.monetization_model ?? ""] ?? "var(--text-primary)" }}>
                    {MODEL_LABEL[c?.monetization_model ?? ""] ?? c?.monetization_model ?? "—"}
                  </span>
                )}
              </InfoRow>

              {(isCredit || (!editing && c?.monetization_model === "credit_wallet_commission")) && (
                <>
                  <InfoRow label="Commission Rate">
                    {editing ? (
                      <input type="number" step="0.01" min="0" max="1"
                        value={form.commission_rate ?? 0}
                        onChange={e => setForm(f => ({ ...f, commission_rate: parseFloat(e.target.value) }))}
                        style={{ fontSize:13, padding:"4px 8px", width:120, borderRadius:6, border:"1px solid var(--border)", background:"var(--surface)" }}/>
                    ) : (
                      `${((c?.commission_rate ?? 0) * 100).toFixed(1)}%`
                    )}
                  </InfoRow>
                  <InfoRow label="Credit Minimum Balance">
                    {editing ? (
                      <input type="number" step="100" min="0"
                        value={form.credit_minimum_balance ?? 0}
                        onChange={e => setForm(f => ({ ...f, credit_minimum_balance: parseFloat(e.target.value) }))}
                        style={{ fontSize:13, padding:"4px 8px", width:140, borderRadius:6, border:"1px solid var(--border)", background:"var(--surface)" }}/>
                    ) : (
                      `₹${c?.credit_minimum_balance?.toFixed(2) ?? "0.00"}`
                    )}
                  </InfoRow>
                </>
              )}

              {(isSubscription || (!editing && c?.monetization_model === "subscription")) && (
                <>
                  <InfoRow label="Plan Type">
                    {editing ? (
                      <input type="text" value={form.subscription_plan_type ?? ""}
                        onChange={e => setForm(f => ({ ...f, subscription_plan_type: e.target.value }))}
                        style={{ fontSize:13, padding:"4px 8px", width:140, borderRadius:6, border:"1px solid var(--border)", background:"var(--surface)" }}/>
                    ) : (c?.subscription_plan_type ?? "—")}
                  </InfoRow>
                  <InfoRow label="Billing Cycle">
                    {editing ? (
                      <select value={form.subscription_billing_cycle ?? ""}
                        onChange={e => setForm(f => ({ ...f, subscription_billing_cycle: e.target.value }))}
                        style={{ fontSize:13, padding:"4px 8px", borderRadius:6, border:"1px solid var(--border)", background:"var(--surface)" }}>
                        <option value="">—</option>
                        <option value="monthly">Monthly</option>
                        <option value="annual">Annual</option>
                      </select>
                    ) : (c?.subscription_billing_cycle ?? "—")}
                  </InfoRow>
                  <InfoRow label="Amount (INR)">
                    {editing ? (
                      <input type="number" step="1" min="0"
                        value={form.subscription_amount_inr ?? ""}
                        onChange={e => setForm(f => ({ ...f, subscription_amount_inr: parseFloat(e.target.value) }))}
                        style={{ fontSize:13, padding:"4px 8px", width:140, borderRadius:6, border:"1px solid var(--border)", background:"var(--surface)" }}/>
                    ) : (c?.subscription_amount_inr ? `₹${c.subscription_amount_inr.toFixed(2)}` : "—")}
                  </InfoRow>
                  <InfoRow label="Trial Days">
                    {editing ? (
                      <input type="number" step="1" min="0"
                        value={form.trial_days ?? 0}
                        onChange={e => setForm(f => ({ ...f, trial_days: parseInt(e.target.value) }))}
                        style={{ fontSize:13, padding:"4px 8px", width:100, borderRadius:6, border:"1px solid var(--border)", background:"var(--surface)" }}/>
                    ) : `${c?.trial_days ?? 0} days`}
                  </InfoRow>
                  <InfoRow label="Leads / Billing Cycle">
                    {editing ? (
                      <input type="number" step="1" min="0"
                        value={form.leads_per_billing_cycle ?? ""}
                        onChange={e => setForm(f => ({ ...f, leads_per_billing_cycle: parseInt(e.target.value) }))}
                        style={{ fontSize:13, padding:"4px 8px", width:100, borderRadius:6, border:"1px solid var(--border)", background:"var(--surface)" }}/>
                    ) : (c?.leads_per_billing_cycle ?? "—")}
                  </InfoRow>
                </>
              )}

              <InfoRow label="Notes">
                {editing ? (
                  <textarea value={form.notes ?? ""}
                    onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                    rows={2}
                    style={{ fontSize:13, padding:"4px 8px", width:"100%", borderRadius:6, border:"1px solid var(--border)", background:"var(--surface)", resize:"vertical" }}/>
                ) : (c?.notes ?? "—")}
              </InfoRow>

              <InfoRow label="Status">
                {editing ? (
                  <label style={{ display:"flex", alignItems:"center", gap:8, cursor:"pointer" }}>
                    <input type="checkbox" checked={form.is_active ?? true}
                      onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}/>
                    Active
                  </label>
                ) : (
                  <Badge variant={c?.is_active ? "success" : "muted"} size="sm">
                    {c?.is_active ? "Active" : "Inactive"}
                  </Badge>
                )}
              </InfoRow>

              <InfoRow label="Last Updated">
                <span style={{ color:"var(--text-tertiary)" }}>
                  {c?.updated_at ? new Date(c.updated_at).toLocaleString() : "—"}
                </span>
              </InfoRow>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

// ── Customer Flow Tab ─────────────────────────────────────────────────────────

const FLOW_TYPES = ["service_booking","appointment_booking","lead_capture","order_flow","inquiry_flow","product_inquiry","unsupported"] as const;
const COMPONENT_KEYS = ["ServiceBookingFlow","AppointmentBookingFlow","LeadCaptureFlow","OrderFlow","InquiryFlow","ProductInquiryFlow","UnsupportedFlow"] as const;
const ENGINE_KEYS = ["booking_engine","appointment_engine","lead_engine","order_engine","inquiry_engine","none"] as const;

function CustomerFlowTab({ catId }: { catId: string }) {
  const cfg = useApi(useCallback(() => adminCustomerFlowApi.getFlowConfig(catId), [catId]));
  const [editing, setEditing] = React.useState(false);
  const [saved, setSaved] = React.useState(false);
  const [form, setForm] = React.useState<Partial<CustomerFlowConfig>>({});

  React.useEffect(() => {
    const c = cfg.data;
    if (c && !editing) {
      setForm({
        customer_flow_type: c.customer_flow_type,
        frontend_component_key: c.frontend_component_key,
        primary_engine_key: c.primary_engine_key,
        required_steps: c.required_steps,
        optional_steps: c.optional_steps,
        is_active: c.is_active,
      });
    }
  }, [cfg.data, editing]);

  const saveAction = useAction(async (data: Partial<CustomerFlowConfig>) => {
    await adminCustomerFlowApi.upsertFlowConfig(catId, data);
    cfg.refetch();
    setEditing(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  });

  const toggleAction = useAction(async (activate: boolean) => {
    if (activate) await adminCustomerFlowApi.activateFlowConfig(catId);
    else await adminCustomerFlowApi.deactivateFlowConfig(catId);
    cfg.refetch();
  });

  const c = cfg.data;

  const inp = (style?: React.CSSProperties): React.CSSProperties => ({
    width: "100%", padding: "8px 10px", borderRadius:"var(--radius-md)",
    border: "1px solid var(--border)", background: "var(--surface)",
    color: "var(--text-primary)", fontSize: 13, boxSizing: "border-box", ...style,
  });

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
      {saved && (
        <div style={{ padding:"12px 16px", borderRadius:10, background:"rgba(5,150,105,0.08)",
          border:"1px solid rgba(5,150,105,0.25)", fontSize:13, color:"var(--success)", fontWeight:600 }}>
          Customer flow config saved.
        </div>
      )}
      {saveAction.error && (
        <div style={{ padding:"12px 16px", borderRadius:10, background:"rgba(220,38,38,0.08)",
          border:"1px solid rgba(220,38,38,0.25)", fontSize:13, color:"var(--danger)" }}>
          {saveAction.error}
        </div>
      )}
      <Card>
        <div style={{ padding:"20px 24px" }}>
          <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:20 }}>
            <div style={{ display:"flex", alignItems:"center", gap:10 }}>
              <Globe size={18} style={{ color:"var(--accent)" }}/>
              <span style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)" }}>Customer Flow Config</span>
              {c && (
                <span style={{ fontSize:11, fontWeight:700, padding:"2px 10px", borderRadius:20,
                  background: c.is_active ? "rgba(5,150,105,0.1)" : "rgba(148,163,184,0.15)",
                  color: c.is_active ? "var(--success)" : "#64748b" }}>
                  {c.is_active ? "Active" : "Inactive"}
                </span>
              )}
            </div>
            <div style={{ display:"flex", gap:8 }}>
              {c && !editing && (
                <>
                  <Btn size="sm" variant="ghost" onClick={() => toggleAction.execute(!c.is_active)}>
                    {c.is_active ? <ToggleRight size={14}/> : <ToggleLeft size={14}/>}
                    {c.is_active ? " Deactivate" : " Activate"}
                  </Btn>
                  <Btn size="sm" variant="secondary" onClick={() => setEditing(true)}>
                    <Pencil size={12}/> Edit
                  </Btn>
                </>
              )}
              {editing && (
                <>
                  <Btn size="sm" variant="ghost" onClick={() => setEditing(false)}><X size={12}/> Cancel</Btn>
                  <Btn size="sm" variant="primary" loading={saveAction.loading}
                    onClick={() => saveAction.execute(form)}>
                    <Check size={12}/> Save
                  </Btn>
                </>
              )}
            </div>
          </div>

          {cfg.loading && <Skeleton height={200}/>}

          {!cfg.loading && !c && !editing && (
            <div style={{ padding:"20px 0", textAlign:"center" }}>
              <p style={{ fontSize:13, color:"var(--text-secondary)", marginBottom:14 }}>
                No customer flow config for this category yet.
              </p>
              <Btn size="sm" variant="primary" onClick={() => {
                setForm({ customer_flow_type:"service_booking", frontend_component_key:"ServiceBookingFlow", primary_engine_key:"booking_engine", required_steps:[], optional_steps:[], is_active:true });
                setEditing(true);
              }}>Configure Customer Flow</Btn>
            </div>
          )}

          {!cfg.loading && (c || editing) && (
            <div style={{ display:"flex", flexDirection:"column", gap:0 }}>
              <InfoRow label="Flow Type">
                {editing ? (
                  <select value={form.customer_flow_type ?? ""} onChange={e => setForm(f => ({ ...f, customer_flow_type: e.target.value }))} style={inp()}>
                    {FLOW_TYPES.map(ft => <option key={ft} value={ft}>{FLOW_LABEL[ft] ?? ft}</option>)}
                  </select>
                ) : (
                  <span style={{ fontWeight:600 }}>{c ? (FLOW_LABEL[c.customer_flow_type] ?? c.customer_flow_type) : "—"}</span>
                )}
              </InfoRow>
              <InfoRow label="Frontend Component">
                {editing ? (
                  <select value={form.frontend_component_key ?? ""} onChange={e => setForm(f => ({ ...f, frontend_component_key: e.target.value }))} style={inp()}>
                    {COMPONENT_KEYS.map(k => <option key={k} value={k}>{k}</option>)}
                  </select>
                ) : (
                  <code style={{ fontSize:12, background:"var(--surface-sunken)", padding:"2px 6px", borderRadius:4 }}>
                    {c?.frontend_component_key ?? "—"}
                  </code>
                )}
              </InfoRow>
              <InfoRow label="Primary Engine">
                {editing ? (
                  <select value={form.primary_engine_key ?? ""} onChange={e => setForm(f => ({ ...f, primary_engine_key: e.target.value }))} style={inp()}>
                    {ENGINE_KEYS.map(k => <option key={k} value={k}>{k}</option>)}
                  </select>
                ) : (
                  <code style={{ fontSize:12, background:"var(--surface-sunken)", padding:"2px 6px", borderRadius:4 }}>
                    {c?.primary_engine_key ?? "—"}
                  </code>
                )}
              </InfoRow>
              <InfoRow label="Required Steps">
                {editing ? (
                  <textarea
                    value={(form.required_steps ?? []).join(", ")}
                    onChange={e => setForm(f => ({ ...f, required_steps: e.target.value.split(",").map(s => s.trim()).filter(Boolean) }))}
                    rows={3} style={inp()}
                    placeholder="select_offering, address, confirmation"
                  />
                ) : (
                  <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
                    {(c?.required_steps ?? []).map((s, i) => (
                      <span key={i} style={{ fontSize:11, padding:"2px 8px", borderRadius:20,
                        background:"rgba(37,99,235,0.08)", color:"var(--brand)", fontWeight:600 }}>
                        {i+1}. {s}
                      </span>
                    ))}
                    {!c?.required_steps?.length && <span style={{ color:"var(--text-tertiary)", fontSize:12 }}>None</span>}
                  </div>
                )}
              </InfoRow>
              <InfoRow label="Optional Steps">
                {editing ? (
                  <textarea
                    value={(form.optional_steps ?? []).join(", ")}
                    onChange={e => setForm(f => ({ ...f, optional_steps: e.target.value.split(",").map(s => s.trim()).filter(Boolean) }))}
                    rows={2} style={inp()}
                    placeholder="photo_upload, customer_notes"
                  />
                ) : (
                  <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
                    {(c?.optional_steps ?? []).map((s, i) => (
                      <span key={i} style={{ fontSize:11, padding:"2px 8px", borderRadius:20,
                        background:"rgba(124,58,237,0.08)", color:"var(--accent)", fontWeight:600 }}>
                        {s}
                      </span>
                    ))}
                    {!c?.optional_steps?.length && <span style={{ color:"var(--text-tertiary)", fontSize:12 }}>None</span>}
                  </div>
                )}
              </InfoRow>
            </div>
          )}
        </div>
      </Card>

      <Card>
        <div style={{ padding:"16px 20px" }}>
          <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"0 0 6px", fontWeight:600 }}>
            Customer-facing API endpoint
          </p>
          <code style={{ fontSize:12, color:"var(--text-secondary)", background:"var(--surface-sunken)",
            padding:"8px 12px", borderRadius:"var(--radius-md)", display:"block" }}>
            GET /v1/customer/categories/{"{slug}"}/runtime
          </code>
          <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"10px 0 0" }}>
            This config is served to customer apps to determine which flow shell component to render
            (e.g. ServiceBookingFlow, AppointmentBookingFlow). Changes take effect immediately.
          </p>
        </div>
      </Card>
    </div>
  );
}

// ── Onboarding Checklist Tab ──────────────────────────────────────────────────

type TemplateForm = Partial<OnboardingChecklistTemplate> & { completion_rule_raw?: string };

function OnboardingChecklistTab({ catId }: { catId: string }) {
  const templates = useApi(useCallback(() => adminOnboardingTemplatesApi.list(catId), [catId]));
  const [showForm, setShowForm] = React.useState(false);
  const [editId, setEditId] = React.useState<string | null>(null);
  const [form, setForm] = React.useState<TemplateForm>({});
  const [formError, setFormError] = React.useState<string | null>(null);
  const [toast, setToast] = React.useState<string | null>(null);

  function flash(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  function openCreate() {
    setForm({ is_required: true, is_blocking: true, allows_admin_override: false, is_active: true, display_order: 0 });
    setEditId(null);
    setFormError(null);
    setShowForm(true);
  }

  function openEdit(t: OnboardingChecklistTemplate) {
    setForm({ ...t, completion_rule_raw: t.completion_rule ? JSON.stringify(t.completion_rule, null, 2) : "" });
    setEditId(t.id);
    setFormError(null);
    setShowForm(true);
  }

  const saveAction = useAction(async () => {
    if (!form.checklist_key?.trim()) { setFormError("Checklist key is required"); return; }
    if (!form.title?.trim())         { setFormError("Title is required"); return; }
    if (!form.item_type?.trim())     { setFormError("Item type is required"); return; }
    if (!form.completion_source?.trim()) { setFormError("Completion source is required"); return; }
    let completion_rule: Record<string, unknown> | null = null;
    if (form.completion_rule_raw?.trim()) {
      try { completion_rule = JSON.parse(form.completion_rule_raw); }
      catch { setFormError("Completion Rule must be valid JSON"); return; }
    }
    const payload: Partial<OnboardingChecklistTemplate> = {
      checklist_key: form.checklist_key, title: form.title,
      description: form.description, item_type: form.item_type,
      completion_source: form.completion_source,
      required_engine_key: form.required_engine_key,
      required_permission: form.required_permission,
      is_required: form.is_required ?? true,
      is_blocking: form.is_blocking ?? true,
      allows_admin_override: form.allows_admin_override ?? false,
      provider_action_label: form.provider_action_label,
      provider_action_route: form.provider_action_route,
      admin_action_label: form.admin_action_label,
      admin_action_route: form.admin_action_route,
      completion_rule, display_order: form.display_order ?? 0,
      is_active: form.is_active ?? true,
    };
    if (editId) {
      await adminOnboardingTemplatesApi.update(editId, payload);
    } else {
      await adminOnboardingTemplatesApi.create(catId, payload);
    }
    templates.refetch();
    setShowForm(false);
    flash(editId ? "Template updated." : "Template created.");
  });

  const activateAction = useAction(async (id: string) => {
    await adminOnboardingTemplatesApi.activate(id); templates.refetch(); flash("Template activated.");
  });
  const deactivateAction = useAction(async (id: string) => {
    if (!confirm("Deactivate this checklist item?")) return;
    await adminOnboardingTemplatesApi.deactivate(id); templates.refetch(); flash("Template deactivated.");
  });

  const list: OnboardingChecklistTemplate[] = templates.data?.templates ?? [];

  function FieldRow({ label, children }: { label: string; children: React.ReactNode }) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", textTransform: "uppercase",
          letterSpacing: "0.06em" }}>{label}</label>
        {children}
      </div>
    );
  }

  const inputStyle: React.CSSProperties = {
    fontSize: 13, padding: "6px 10px", borderRadius: 7,
    border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", width: "100%",
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* MODULE-L5-44: investigated whether /v1/admin/onboarding/templates*
          could be repointed to a real endpoint (same audit that found
          L5-39..43). Confirmed the backing feature (OnboardingChecklistTemplate
          model/table -- checklist_key/item_type/completion_source/
          required_engine_key) no longer exists anywhere in the codebase or
          database; the only adjacent real table (master_checklist_items) is a
          different concept (generic workflow-step checklist items, not
          onboarding-approval gates with evaluators) and would misrepresent
          the feature if silently substituted. Rather than fabricate a fix,
          this tab now says so honestly instead of letting every action
          404 silently. */}
      <div style={{ padding: "10px 16px", borderRadius: 10, background: "rgba(217,119,6,0.08)",
        border: "1px solid rgba(217,119,6,0.25)", fontSize: 13, color: "#b45309" }}>
        Onboarding checklist template management is not available in this build.
        The backing feature was removed from the backend (no matching table or
        endpoints remain); this tab cannot list, create, or edit templates
        until it is rebuilt. Contact engineering before relying on it.
      </div>

      {toast && (
        <div style={{ padding: "10px 16px", borderRadius: 10, background: "rgba(5,150,105,0.08)",
          border: "1px solid rgba(5,150,105,0.25)", fontSize: 13, color: "var(--success)" }}>{toast}</div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
          {templates.data?.count ?? 0} template{templates.data?.count !== 1 ? "s" : ""} in this category
        </p>
        <Btn size="sm" variant="primary" onClick={openCreate} disabled>
          <Plus size={13}/> Add Item
        </Btn>
      </div>

      {/* Add/Edit form */}
      {showForm && (
        <Card>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
              {editId ? "Edit Template" : "New Checklist Item"}
            </span>
            <button onClick={() => setShowForm(false)}
              style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)" }}>
              <X size={16}/>
            </button>
          </div>
          {formError && (
            <div style={{ padding: "8px 12px", borderRadius:"var(--radius-md)", background: "rgba(220,38,38,0.08)",
              border: "1px solid rgba(220,38,38,0.25)", fontSize: 12, color: "var(--danger)", marginBottom: 12 }}>
              {formError}
            </div>
          )}
          {saveAction.error && (
            <div style={{ padding: "8px 12px", borderRadius:"var(--radius-md)", background: "rgba(220,38,38,0.08)",
              border: "1px solid rgba(220,38,38,0.25)", fontSize: 12, color: "var(--danger)", marginBottom: 12 }}>
              {saveAction.error}
            </div>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <FieldRow label="Checklist Key *">
              <input style={inputStyle} value={form.checklist_key ?? ""}
                onChange={e => setForm(f => ({ ...f, checklist_key: e.target.value }))}
                placeholder="e.g. business_profile"/>
            </FieldRow>
            <FieldRow label="Title *">
              <input style={inputStyle} value={form.title ?? ""}
                onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                placeholder="Complete Business Profile"/>
            </FieldRow>
            <FieldRow label="Item Type *">
              <select style={inputStyle} value={form.item_type ?? ""}
                onChange={e => setForm(f => ({ ...f, item_type: e.target.value }))}>
                <option value="">Select…</option>
                {["profile","verification","monetization","package","offering","service_area",
                  "staff","appointment_slots","agent","property","media","marketing","compliance","custom"
                ].map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
              </select>
            </FieldRow>
            <FieldRow label="Completion Source *">
              <select style={inputStyle} value={form.completion_source ?? ""}
                onChange={e => setForm(f => ({ ...f, completion_source: e.target.value }))}>
                <option value="">Select…</option>
                {["provider_profile","provider_verification","provider_monetization","provider_package",
                  "provider_enabled_offerings","provider_service_areas","provider_staff",
                  "provider_appointment_slots","provider_agents","provider_properties",
                  "provider_media","marketing_assets","admin_override","custom_rule"
                ].map(s => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
              </select>
            </FieldRow>
            <FieldRow label="Description">
              <input style={inputStyle} value={form.description ?? ""}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))}/>
            </FieldRow>
            <FieldRow label="Required Engine Key">
              <input style={inputStyle} value={form.required_engine_key ?? ""}
                onChange={e => setForm(f => ({ ...f, required_engine_key: e.target.value || undefined }))}/>
            </FieldRow>
            <FieldRow label="Provider Action Label">
              <input style={inputStyle} value={form.provider_action_label ?? ""}
                onChange={e => setForm(f => ({ ...f, provider_action_label: e.target.value || undefined }))}/>
            </FieldRow>
            <FieldRow label="Provider Action Route">
              <input style={inputStyle} value={form.provider_action_route ?? ""}
                onChange={e => setForm(f => ({ ...f, provider_action_route: e.target.value || undefined }))}
                placeholder="/onboarding-status"/>
            </FieldRow>
            <FieldRow label="Admin Action Label">
              <input style={inputStyle} value={form.admin_action_label ?? ""}
                onChange={e => setForm(f => ({ ...f, admin_action_label: e.target.value || undefined }))}/>
            </FieldRow>
            <FieldRow label="Admin Action Route">
              <input style={inputStyle} value={form.admin_action_route ?? ""}
                onChange={e => setForm(f => ({ ...f, admin_action_route: e.target.value || undefined }))}/>
            </FieldRow>
            <FieldRow label="Display Order">
              <input type="number" style={inputStyle} value={form.display_order ?? 0}
                onChange={e => setForm(f => ({ ...f, display_order: parseInt(e.target.value) || 0 }))}/>
            </FieldRow>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, alignItems: "flex-start",
              paddingTop: 18 }}>
              {[
                { key: "is_required",          label: "Required" },
                { key: "is_blocking",          label: "Blocking" },
                { key: "allows_admin_override", label: "Allows Admin Override" },
                { key: "is_active",             label: "Active" },
              ].map(({ key, label }) => (
                <label key={key} style={{ display: "flex", alignItems: "center", gap: 8,
                  fontSize: 12, cursor: "pointer", color: "var(--text-primary)" }}>
                  <input type="checkbox"
                    checked={(form as Record<string, unknown>)[key] as boolean ?? false}
                    onChange={e => setForm(f => ({ ...f, [key]: e.target.checked }))}/>
                  {label}
                </label>
              ))}
            </div>
          </div>
          <FieldRow label="Completion Rule (JSON)">
            <textarea style={{ ...inputStyle, resize: "vertical", fontFamily: "monospace", fontSize: 12 }}
              rows={3} value={form.completion_rule_raw ?? ""}
              onChange={e => setForm(f => ({ ...f, completion_rule_raw: e.target.value }))}
              placeholder='{"type":"field_check","field":"is_verified","value":true}'/>
          </FieldRow>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 16 }}>
            <Btn size="sm" variant="secondary" onClick={() => setShowForm(false)}>Cancel</Btn>
            <Btn size="sm" variant="primary" loading={saveAction.loading}
              onClick={() => saveAction.execute()}>
              {editId ? "Save Changes" : "Create Item"}
            </Btn>
          </div>
        </Card>
      )}

      {/* Templates table */}
      {templates.loading ? (
        <Skeleton height={200}/>
      ) : list.length === 0 ? (
        <Card>
          <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-tertiary)" }}>
            <ClipboardList size={28} style={{ display: "block", margin: "0 auto 10px" }}/>
            <p style={{ fontSize: 13, margin: 0 }}>No checklist templates yet. Add the first one.</p>
          </div>
        </Card>
      ) : (
        <Card padding={0}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                  {["Key","Title","Type","Source","Req","Block","Override","Engine","Route","Order","Active","Actions"].map(h => (
                    <th key={h} style={{ padding: "9px 12px", textAlign: "left", fontSize: 10, fontWeight: 700,
                      color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em",
                      whiteSpace: "nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {list.map((t, i) => (
                  <tr key={t.id}
                    style={{ borderBottom: i < list.length - 1 ? "1px solid var(--border)" : "none" }}>
                    <td style={{ padding: "9px 12px" }}>
                      <span style={{ fontSize: 11, fontFamily: "monospace", background: "var(--surface-sunken)",
                        padding: "2px 6px", borderRadius: 5, border: "1px solid var(--border)" }}>
                        {t.checklist_key}
                      </span>
                    </td>
                    <td style={{ padding: "9px 12px", fontSize: 12, fontWeight: 600,
                      color: "var(--text-primary)", maxWidth: 180 }}>{t.title}</td>
                    <td style={{ padding: "9px 12px" }}>
                      <Badge variant="info" size="sm">{t.item_type}</Badge>
                    </td>
                    <td style={{ padding: "9px 12px", fontSize: 11, color: "var(--text-secondary)" }}>
                      {t.completion_source.replace(/_/g, " ")}
                    </td>
                    <td style={{ padding: "9px 12px" }}>
                      <Badge variant={t.is_required ? "danger" : "muted"} size="sm">
                        {t.is_required ? "Yes" : "No"}
                      </Badge>
                    </td>
                    <td style={{ padding: "9px 12px" }}>
                      <Badge variant={t.is_blocking ? "danger" : "muted"} size="sm">
                        {t.is_blocking ? "Yes" : "No"}
                      </Badge>
                    </td>
                    <td style={{ padding: "9px 12px" }}>
                      <Badge variant={t.allows_admin_override ? "success" : "muted"} size="sm">
                        {t.allows_admin_override ? "Yes" : "No"}
                      </Badge>
                    </td>
                    <td style={{ padding: "9px 12px", fontSize: 11, fontFamily: "monospace",
                      color: "var(--text-secondary)" }}>
                      {t.required_engine_key ?? "—"}
                    </td>
                    <td style={{ padding: "9px 12px", fontSize: 11, fontFamily: "monospace",
                      color: "var(--text-secondary)" }}>
                      {t.provider_action_route ?? "—"}
                    </td>
                    <td style={{ padding: "9px 12px", fontSize: 12, color: "var(--text-secondary)" }}>
                      {t.display_order}
                    </td>
                    <td style={{ padding: "9px 12px" }}>
                      <Badge variant={t.is_active ? "success" : "muted"} size="sm">
                        {t.is_active ? "Active" : "Off"}
                      </Badge>
                    </td>
                    <td style={{ padding: "9px 12px" }}>
                      <div style={{ display: "flex", gap: 4 }}>
                        <Btn size="xs" variant="ghost" onClick={() => openEdit(t)}>
                          <Pencil size={11}/>
                        </Btn>
                        {t.is_active ? (
                          <Btn size="xs" variant="ghost"
                            loading={deactivateAction.loading}
                            onClick={() => deactivateAction.execute(t.id)}>
                            <X size={11}/>
                          </Btn>
                        ) : (
                          <Btn size="xs" variant="primary"
                            loading={activateAction.loading}
                            onClick={() => activateAction.execute(t.id)}>
                            <Check size={11}/>
                          </Btn>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

function EnginesTab({ catId }: { catId: string }) {
  const engines = useApi(useCallback(() => categoryRuntimeApi.listCategoryEngines(catId), [catId]));
  const enableAction = useAction(async ({ cid, eid }: { cid: string; eid: string }) => {
    await categoryRuntimeApi.enableCategoryEngine(cid, eid); engines.refetch();
  });
  const disableAction = useAction(async ({ cid, eid }: { cid: string; eid: string }) => {
    await categoryRuntimeApi.disableCategoryEngine(cid, eid); engines.refetch();
  });
  const setPrimaryAction = useAction(async ({ cid, eid }: { cid: string; eid: string }) => {
    await categoryRuntimeApi.setPrimaryEngine(cid, eid); engines.refetch();
  });

  if (engines.loading) return <div style={{ padding:24 }}><Skeleton height={200}/></div>;
  const list: CategoryEngineRuntime[] = engines.data?.engines ?? [];

  return (
    <div>
      {engines.data && (
        <div style={{ display:"flex", gap:12, padding:"16px 0 20px", flexWrap:"wrap" }}>
          {[
            { label:"Total", value: engines.data.total },
            { label:"Required", value: engines.data.required_count },
            { label:"Optional", value: engines.data.optional_count },
            { label:"Primary", value: engines.data.primary_engine?.engine_key ?? "—" },
          ].map(s => (
            <div key={s.label} style={{ background:"var(--surface-sunken)", borderRadius:10,
              padding:"12px 20px", border:"1px solid var(--border)", minWidth:100 }}>
              <p style={{ fontSize:22, fontWeight:700, color:"var(--text-primary)", margin:0 }}>{s.value}</p>
              <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0, marginTop:2 }}>{s.label}</p>
            </div>
          ))}
        </div>
      )}
      <Card padding={0}>
        <table style={{ width:"100%", borderCollapse:"collapse" }}>
          <thead>
            <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
              {["Engine","Key","Required","Primary","Health","Status","Actions"].map(h => (
                <th key={h} style={{ padding:"10px 14px", textAlign:"left", fontSize:11, fontWeight:700,
                  color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {list.map((eng, i) => (
              <tr key={eng.category_engine_id}
                style={{ borderBottom: i < list.length-1 ? "1px solid var(--border)" : "none" }}>
                <td style={{ padding:"10px 14px" }}>
                  <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0 }}>{eng.name}</p>
                  <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0 }}>{eng.engine_id.slice(0,8)}…</p>
                </td>
                <td style={{ padding:"10px 14px" }}>
                  <span style={{ fontSize:11, fontFamily:"monospace", background:"var(--surface-sunken)",
                    padding:"2px 6px", borderRadius:5, border:"1px solid var(--border)" }}>
                    {eng.engine_key}
                  </span>
                </td>
                <td style={{ padding:"10px 14px" }}>
                  <Badge variant={eng.is_required ? "danger" : "muted"} size="sm">
                    {eng.is_required ? "Required" : "Optional"}
                  </Badge>
                </td>
                <td style={{ padding:"10px 14px" }}>
                  {eng.is_primary ? (
                    <span style={{ display:"flex", alignItems:"center", gap:4, fontSize:12, color:"var(--warning)" }}>
                      <Star size={12}/> Primary
                    </span>
                  ) : (
                    <Btn size="xs" variant="ghost"
                      loading={setPrimaryAction.loading}
                      onClick={() => setPrimaryAction.execute({ cid: catId, eid: eng.engine_id })}>
                      Set Primary
                    </Btn>
                  )}
                </td>
                <td style={{ padding:"10px 14px" }}>
                  <span style={{ fontSize:12, fontWeight:500,
                    color: HEALTH_COLOR[eng.health_status] ?? "var(--text-tertiary)" }}>
                    {eng.health_status}
                  </span>
                </td>
                <td style={{ padding:"10px 14px" }}>
                  <Badge variant={eng.is_enabled ? "success" : "muted"} size="sm">
                    {eng.is_enabled ? "Enabled" : "Disabled"}
                  </Badge>
                </td>
                <td style={{ padding:"10px 14px" }}>
                  {eng.is_enabled ? (
                    <Btn size="xs" variant="ghost"
                      disabled={eng.is_required}
                      loading={disableAction.loading}
                      onClick={() => disableAction.execute({ cid: catId, eid: eng.engine_id })}>
                      <ToggleLeft size={12}/> Disable
                    </Btn>
                  ) : (
                    <Btn size="xs" variant="primary"
                      loading={enableAction.loading}
                      onClick={() => enableAction.execute({ cid: catId, eid: eng.engine_id })}>
                      <ToggleRight size={12}/> Enable
                    </Btn>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

function ModulesTab({ catId }: { catId: string }) {
  const modules = useApi(useCallback(() => categoryRuntimeApi.listDashboardModules(catId), [catId]));
  const enableAction = useAction(async ({ cid, mid }: { cid: string; mid: string }) => {
    await categoryRuntimeApi.enableModule(cid, mid); modules.refetch();
  });
  const disableAction = useAction(async ({ cid, mid }: { cid: string; mid: string }) => {
    await categoryRuntimeApi.disableModule(cid, mid); modules.refetch();
  });

  if (modules.loading) return <div style={{ padding:24 }}><Skeleton height={200}/></div>;
  const list: CategoryDashboardModule[] = modules.data?.modules ?? [];

  return (
    <div>
      {modules.data && (
        <div style={{ display:"flex", gap:12, padding:"16px 0 20px" }}>
          {[
            { label:"Total", value: modules.data.total },
            { label:"Enabled", value: modules.data.enabled_count },
          ].map(s => (
            <div key={s.label} style={{ background:"var(--surface-sunken)", borderRadius:10,
              padding:"12px 20px", border:"1px solid var(--border)" }}>
              <p style={{ fontSize:22, fontWeight:700, color:"var(--text-primary)", margin:0 }}>{s.value}</p>
              <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0, marginTop:2 }}>{s.label}</p>
            </div>
          ))}
        </div>
      )}
      <Card padding={0}>
        <table style={{ width:"100%", borderCollapse:"collapse" }}>
          <thead>
            <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
              {["Module","Key","Area","Type","Engine","Route","Order","Status","Actions"].map(h => (
                <th key={h} style={{ padding:"10px 14px", textAlign:"left", fontSize:11, fontWeight:700,
                  color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {list.map((mod, i) => {
              const typeColor = MODULE_TYPE_COLOR[mod.module_type] ?? "var(--text-tertiary)";
              const areaColor: Record<string, string> = {
                sidebar: "#6366f1", overview: "var(--success)", analytics: "var(--warning)",
                quick_actions: "#ec4899", finance: "#0ea5e9", marketing: "#8b5cf6",
              };
              const areaClr = areaColor[mod.dashboard_area ?? ""] ?? "var(--text-tertiary)";
              return (
                <tr key={mod.module_id}
                  style={{ borderBottom: i < list.length-1 ? "1px solid var(--border)" : "none" }}>
                  <td style={{ padding:"10px 14px" }}>
                    <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                      <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0 }}>{mod.module_name}</p>
                      {mod.is_required && (
                        <span style={{ fontSize:10, fontWeight:700, padding:"2px 6px", borderRadius:20,
                          background:"rgba(239,68,68,0.12)", color:"#ef4444", flexShrink:0 }}>
                          REQUIRED
                        </span>
                      )}
                    </div>
                  </td>
                  <td style={{ padding:"10px 14px" }}>
                    <span style={{ fontSize:11, fontFamily:"monospace", background:"var(--surface-sunken)",
                      padding:"2px 6px", borderRadius:5, border:"1px solid var(--border)" }}>
                      {mod.module_key}
                    </span>
                  </td>
                  <td style={{ padding:"10px 14px" }}>
                    {mod.dashboard_area ? (
                      <span style={{ fontSize:11, fontWeight:600, padding:"3px 8px", borderRadius:20,
                        background: areaClr + "18", color: areaClr }}>
                        {mod.dashboard_area}
                      </span>
                    ) : <span style={{ color:"var(--text-tertiary)", fontSize:12 }}>—</span>}
                  </td>
                  <td style={{ padding:"10px 14px" }}>
                    <span style={{ fontSize:11, fontWeight:600, padding:"3px 8px", borderRadius:20,
                      background: typeColor + "18", color: typeColor }}>
                      {mod.module_type}
                    </span>
                  </td>
                  <td style={{ padding:"10px 14px", fontSize:12, color:"var(--text-secondary)" }}>
                    {mod.engine_key ?? "—"}
                  </td>
                  <td style={{ padding:"10px 14px", fontSize:12, fontFamily:"monospace", color:"var(--text-secondary)" }}>
                    {mod.route_path ?? "—"}
                  </td>
                  <td style={{ padding:"10px 14px", fontSize:12, color:"var(--text-secondary)" }}>
                    {mod.display_order}
                  </td>
                  <td style={{ padding:"10px 14px" }}>
                    <Badge variant={mod.is_enabled ? "success" : "muted"} size="sm">
                      {mod.is_enabled ? "Enabled" : "Disabled"}
                    </Badge>
                  </td>
                  <td style={{ padding:"10px 14px" }}>
                    {mod.is_required ? (
                      <span style={{ fontSize:11, color:"var(--text-tertiary)" }}>Locked</span>
                    ) : mod.is_enabled ? (
                      <Btn size="xs" variant="ghost"
                        loading={disableAction.loading}
                        onClick={() => disableAction.execute({ cid: catId, mid: mod.module_id })}>
                        <ToggleLeft size={12}/> Disable
                      </Btn>
                    ) : (
                      <Btn size="xs" variant="primary"
                        loading={enableAction.loading}
                        onClick={() => enableAction.execute({ cid: catId, mid: mod.module_id })}>
                        <ToggleRight size={12}/> Enable
                      </Btn>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

export default function CategoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabKey>("overview");

  const runtime = useApi(useCallback(
    () => categoryRuntimeApi.getCategoryRuntime(id),
    [id]
  ));

  const activateAction = useAction(async () => {
    await categoryRuntimeApi.activateCategory(id); runtime.refetch();
  });
  const deactivateAction = useAction(async () => {
    await categoryRuntimeApi.deactivateCategory(id); runtime.refetch();
  });

  const r: CategoryRuntime | null = runtime.data ?? null;
  const cat = r?.category ?? null;

  return (
    <AdminLayout activeNav="categories">
      <div style={{ marginBottom:16 }}>
        <Btn variant="ghost" size="sm" onClick={() => router.push("/admin/categories")}>
          <ArrowLeft size={13}/> Back to Categories
        </Btn>
      </div>

      {runtime.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          <Skeleton height={80}/>
          <Skeleton height={400}/>
        </div>
      ) : !cat ? (
        <Card>
          <p style={{ fontSize:14, color:"var(--text-secondary)", textAlign:"center", margin:0 }}>
            {runtime.error ?? "Category not found."}
          </p>
        </Card>
      ) : (
        <>
          {/* Header */}
          <SectionHeader
            title={cat.name}
            subtitle={cat.description ?? "Category Runtime Configuration"}
            icon={<Layers/>}
            actions={
              <div style={{ display:"flex", gap:8, alignItems:"center" }}>
                <Badge variant={cat.is_active ? "success" : "muted"}>
                  {cat.is_active ? "Active" : "Inactive"}
                </Badge>
                {cat.is_active ? (
                  <Btn size="sm" variant="ghost"
                    loading={deactivateAction.loading}
                    onClick={() => deactivateAction.execute()}>
                    Deactivate
                  </Btn>
                ) : (
                  <Btn size="sm" variant="primary"
                    loading={activateAction.loading}
                    onClick={() => activateAction.execute()}>
                    Activate
                  </Btn>
                )}
              </div>
            }
          />

          {/* Summary stats */}
          <div style={{ display:"flex", gap:12, marginBottom:24, flexWrap:"wrap" }}>
            {[
              { label:"Running Engines", value: r!.engine_summary.total },
              { label:"Required Engines", value: r!.engine_summary.required },
              { label:"Dashboard Modules", value: r!.dashboard_modules.length },
              { label:"Total Tenants", value: r!.tenant_count },
              { label:"Active Tenants", value: r!.active_tenant_count },
            ].map(s => (
              <div key={s.label} style={{ background:"var(--surface-sunken)", borderRadius:"var(--radius-lg)",
                padding:"14px 20px", border:"1px solid var(--border)", flex:"1 1 140px" }}>
                <p style={{ fontSize:26, fontWeight:700, color:"var(--text-primary)", margin:0 }}>{s.value}</p>
                <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0, marginTop:3 }}>{s.label}</p>
              </div>
            ))}
          </div>

          {/* Tabs */}
          <div style={{ display:"flex", gap:2, marginBottom:20, borderBottom:"1px solid var(--border)",
            overflowX:"auto" }}>
            {TABS.map(tab => (
              <button key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                style={{
                  display:"flex", alignItems:"center", gap:6,
                  padding:"10px 16px", background:"none", border:"none", cursor:"pointer",
                  fontSize:13, fontWeight:activeTab === tab.key ? 600 : 400,
                  color: activeTab === tab.key ? "var(--text-primary)" : "var(--text-secondary)",
                  borderBottom: activeTab === tab.key ? "2px solid var(--brand-primary)" : "2px solid transparent",
                  marginBottom:-1, whiteSpace:"nowrap",
                }}>
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          {activeTab === "overview" && (
            <Card>
              <div style={{ padding:"4px 0" }}>
                <InfoRow label="Category ID">
                  <span style={{ fontFamily:"monospace", fontSize:12 }}>{cat.category_id}</span>
                </InfoRow>
                <InfoRow label="Slug">
                  <span style={{ fontFamily:"monospace", background:"var(--surface-sunken)",
                    padding:"2px 8px", borderRadius:6, border:"1px solid var(--border)", fontSize:12 }}>
                    {cat.slug}
                  </span>
                </InfoRow>
                <InfoRow label="Category Type">
                  {cat.category_type ? (
                    <Badge variant="info">{cat.category_type}</Badge>
                  ) : <span style={{ color:"var(--text-tertiary)" }}>Not configured</span>}
                </InfoRow>
                <InfoRow label="Customer Flow">
                  {cat.customer_flow_type
                    ? FLOW_LABEL[cat.customer_flow_type] ?? cat.customer_flow_type
                    : <span style={{ color:"var(--text-tertiary)" }}>Not configured</span>}
                </InfoRow>
                <InfoRow label="Provider Dashboard">
                  {cat.provider_dashboard_type
                    ? DASHBOARD_LABEL[cat.provider_dashboard_type] ?? cat.provider_dashboard_type
                    : <span style={{ color:"var(--text-tertiary)" }}>Not configured</span>}
                </InfoRow>
                <InfoRow label="Provider Registerable">
                  <Badge variant={cat.is_provider_registerable ? "success" : "muted"}>
                    {cat.is_provider_registerable ? "Yes" : "No"}
                  </Badge>
                </InfoRow>
                <InfoRow label="Primary Engine">
                  {r!.engine_summary.primary ? (
                    <span style={{ display:"flex", alignItems:"center", gap:6 }}>
                      <Star size={12} style={{ color:"var(--warning)" }}/>
                      <strong>{r!.engine_summary.primary.name}</strong>
                      <span style={{ fontSize:11, fontFamily:"monospace", color:"var(--text-tertiary)" }}>
                        {r!.engine_summary.primary.engine_key}
                      </span>
                    </span>
                  ) : <span style={{ color:"var(--text-tertiary)" }}>Not set</span>}
                </InfoRow>
                <InfoRow label="Status">
                  <Badge variant={cat.is_active ? "success" : "muted"}>
                    {cat.is_active ? "Active" : "Inactive"}
                  </Badge>
                </InfoRow>
                <InfoRow label="Description">
                  <span style={{ color:"var(--text-secondary)" }}>{cat.description ?? "—"}</span>
                </InfoRow>
                <InfoRow label="Created">
                  <span style={{ fontSize:12, color:"var(--text-secondary)" }}>
                    {cat.created_at ? new Date(cat.created_at).toLocaleString() : "—"}
                  </span>
                </InfoRow>
                <InfoRow label="Updated">
                  <span style={{ fontSize:12, color:"var(--text-secondary)" }}>
                    {cat.updated_at ? new Date(cat.updated_at).toLocaleString() : "—"}
                  </span>
                </InfoRow>
              </div>
            </Card>
          )}

          {activeTab === "engines" && <EnginesTab catId={id}/>}
          {activeTab === "modules" && <ModulesTab catId={id}/>}
          {activeTab === "onboarding" && <OnboardingChecklistTab catId={id}/>}

          {activeTab === "providers" && (
            <Card>
              <div style={{ padding:32, textAlign:"center" }}>
                <Users size={32} style={{ color:"var(--text-tertiary)", margin:"0 auto 12px", display:"block" }}/>
                <p style={{ fontSize:14, color:"var(--text-secondary)", margin:0 }}>
                  {r!.tenant_count} total tenants · {r!.active_tenant_count} active
                </p>
                <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"8px 0 0" }}>
                  Provider roster view will be added in Sprint 5.
                </p>
              </div>
            </Card>
          )}

          {activeTab === "customer" && (
            <CustomerFlowTab catId={cat.category_id}/>
          )}

          {activeTab === "provider_ui" && (
            <Card>
              <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
                <div style={{ padding:"16px 20px", background:"var(--surface-sunken)",
                  borderRadius:10, border:"1px solid var(--border)" }}>
                  <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"0 0 4px", fontWeight:500 }}>
                    Provider Dashboard Type
                  </p>
                  <p style={{ fontSize:16, fontWeight:700, color:"var(--text-primary)", margin:0 }}>
                    {cat.provider_dashboard_type
                      ? DASHBOARD_LABEL[cat.provider_dashboard_type] ?? cat.provider_dashboard_type
                      : "Not configured"}
                  </p>
                </div>
                <div>
                  <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:"0 0 10px" }}>
                    Enabled Dashboard Modules ({r!.dashboard_modules.filter(m => m.is_enabled).length})
                  </p>
                  <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(200px,1fr))", gap:10 }}>
                    {r!.dashboard_modules.filter(m => m.is_enabled).map(mod => {
                      const c = MODULE_TYPE_COLOR[mod.module_type] ?? "var(--text-tertiary)";
                      return (
                        <div key={mod.module_id} style={{ padding:"12px 14px", borderRadius:10,
                          background: c + "10", border:`1px solid ${c}30` }}>
                          <p style={{ fontSize:12, fontWeight:600, color:"var(--text-primary)", margin:"0 0 2px" }}>
                            {mod.module_name}
                          </p>
                          <p style={{ fontSize:11, color: c, margin:0 }}>{mod.module_type}</p>
                          {mod.route_path && (
                            <p style={{ fontSize:10, fontFamily:"monospace", color:"var(--text-tertiary)", margin:"4px 0 0" }}>
                              {mod.route_path}
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </Card>
          )}

          {activeTab === "health" && (
            <Card>
              <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                {r!.running_engines.map(eng => (
                  <div key={eng.engine_id} style={{ display:"flex", alignItems:"center", gap:14,
                    padding:"12px 16px", borderRadius:10, background:"var(--surface-sunken)",
                    border:"1px solid var(--border)" }}>
                    <div style={{ width:8, height:8, borderRadius:"50%",
                      background: HEALTH_COLOR[eng.health_status] ?? "#94a3b8", flexShrink:0 }}/>
                    <div style={{ flex:1 }}>
                      <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0 }}>{eng.name}</p>
                      <p style={{ fontSize:11, fontFamily:"monospace", color:"var(--text-tertiary)", margin:0 }}>{eng.engine_key}</p>
                    </div>
                    <span style={{ fontSize:12, fontWeight:500,
                      color: HEALTH_COLOR[eng.health_status] ?? "var(--text-tertiary)" }}>
                      {eng.health_status}
                    </span>
                    {eng.is_primary && (
                      <Star size={12} style={{ color:"var(--warning)", flexShrink:0 }}/>
                    )}
                    <Badge variant={eng.is_enabled ? "success" : "muted"} size="sm">
                      {eng.is_enabled ? "on" : "off"}
                    </Badge>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {activeTab === "monetization" && id && (
            <MonetizationTab catId={id}/>
          )}

          {activeTab === "audit" && (
            <Card>
              <div style={{ padding:32, textAlign:"center" }}>
                <FileText size={32} style={{ color:"var(--text-tertiary)", margin:"0 auto 12px", display:"block" }}/>
                <p style={{ fontSize:14, color:"var(--text-secondary)", margin:0 }}>
                  Category audit log will be displayed here.
                </p>
              </div>
            </Card>
          )}
        </>
      )}
    </AdminLayout>
  );
}
