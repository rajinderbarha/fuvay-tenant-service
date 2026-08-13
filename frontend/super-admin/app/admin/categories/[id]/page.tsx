"use client";

import React, { useCallback, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft, Check, CircleDollarSign, ExternalLink, Globe, Layers,
  Pencil, ShieldCheck, ToggleLeft, ToggleRight, X,
} from "lucide-react";

import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Badge, Btn, Card, SectionHeader, Skeleton } from "../../../../components/shared/ui";
import { useAction, useApi } from "../../../../hooks/useApi";
import {
  adminCustomerFlowApi, catalogApi, categoryRuntimeApi,
  type CategoryCommissionAuthority, type CategoryRuntime, type CustomerFlowConfig,
} from "../../../../lib/api";

const TABS = [
  { key: "overview", label: "Overview", icon: <Layers size={14} /> },
  { key: "customer", label: "Customer Flow", icon: <Globe size={14} /> },
  { key: "finance", label: "Finance Policy", icon: <CircleDollarSign size={14} /> },
] as const;
type TabKey = (typeof TABS)[number]["key"];

const FLOW_LABEL: Record<string, string> = {
  service_booking: "Service Booking",
  appointment_booking: "Appointment Booking",
  lead_capture: "Lead Capture",
  order_flow: "Order Flow",
  inquiry_flow: "Inquiry Flow",
  product_inquiry: "Product Inquiry",
  unsupported: "Unsupported",
};
const DASHBOARD_LABEL: Record<string, string> = {
  home_service_dashboard: "Home Services Dashboard",
  coaching_dashboard: "Coaching Dashboard",
  real_estate_dashboard: "Real Estate Dashboard",
  restaurant_dashboard: "Restaurant Dashboard",
  generic_dashboard: "Generic Dashboard",
};
const FLOW_TYPES = ["service_booking", "appointment_booking", "lead_capture", "order_flow", "inquiry_flow", "product_inquiry", "unsupported"] as const;
const COMPONENT_KEYS = ["ServiceBookingFlow", "AppointmentBookingFlow", "LeadCaptureFlow", "OrderFlow", "InquiryFlow", "ProductInquiryFlow", "UnsupportedFlow"] as const;
const ENGINE_KEYS = ["booking_engine", "appointment_engine", "lead_engine", "order_engine", "inquiry_engine", "none"] as const;

function InfoRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", gap: 16, padding: "11px 0", borderBottom: "1px solid var(--border)" }}>
      <span style={{ minWidth: 175, fontSize: 12, fontWeight: 600, color: "var(--text-tertiary)" }}>{label}</span>
      <div style={{ flex: 1, minWidth: 0, fontSize: 13, color: "var(--text-primary)" }}>{children}</div>
    </div>
  );
}

function CustomerFlowTab({ categoryId }: { categoryId: string }) {
  const flow = useApi(useCallback(() => adminCustomerFlowApi.getFlowConfig(categoryId), [categoryId]), [categoryId]);
  const [editing, setEditing] = useState(false);
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState<Partial<CustomerFlowConfig>>({});

  React.useEffect(() => {
    if (flow.data && !editing) {
      setForm({
        customer_flow_type: flow.data.customer_flow_type,
        frontend_component_key: flow.data.frontend_component_key,
        primary_engine_key: flow.data.primary_engine_key,
        required_steps: flow.data.required_steps,
        optional_steps: flow.data.optional_steps,
        is_active: flow.data.is_active,
      });
    }
  }, [flow.data, editing]);

  const save = useAction(async () => {
    await adminCustomerFlowApi.upsertFlowConfig(categoryId, form);
    flow.refetch();
    setEditing(false);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2500);
  });
  const toggle = useAction(async (activate: boolean) => {
    if (activate) await adminCustomerFlowApi.activateFlowConfig(categoryId);
    else await adminCustomerFlowApi.deactivateFlowConfig(categoryId);
    flow.refetch();
  });

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "8px 10px", borderRadius: "var(--radius-md)",
    border: "1px solid var(--border)", background: "var(--surface)",
    color: "var(--text-primary)", fontSize: 13, boxSizing: "border-box",
  };
  const c = flow.data;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      {saved && <Notice tone="success">Customer flow saved and available to the customer app.</Notice>}
      {(save.error || toggle.error) && <Notice tone="danger">{save.error || toggle.error}</Notice>}
      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "center", marginBottom: 14 }}>
          <div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <Globe size={17} style={{ color: "var(--brand)" }} />
              <strong style={{ fontSize: 15 }}>Customer flow runtime</strong>
              {c && <Badge variant={c.is_active ? "success" : "muted"}>{c.is_active ? "Active" : "Inactive"}</Badge>}
            </div>
            <p style={{ margin: "5px 0 0", fontSize: 12, color: "var(--text-tertiary)" }}>
              Persisted configuration consumed directly by the native customer booking flow.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {c && !editing && <>
              <Btn size="sm" variant="ghost" onClick={() => toggle.execute(!c.is_active)}>
                {c.is_active ? <ToggleRight size={14} /> : <ToggleLeft size={14} />} {c.is_active ? "Deactivate" : "Activate"}
              </Btn>
              <Btn size="sm" variant="secondary" onClick={() => setEditing(true)}><Pencil size={13} /> Edit</Btn>
            </>}
            {editing && <>
              <Btn size="sm" variant="ghost" onClick={() => setEditing(false)}><X size={13} /> Cancel</Btn>
              <Btn size="sm" variant="primary" loading={save.loading} onClick={() => save.execute()}><Check size={13} /> Save</Btn>
            </>}
          </div>
        </div>

        {flow.loading && <Skeleton height={180} />}
        {!flow.loading && !c && !editing && (
          <div style={{ padding: "28px 12px", textAlign: "center" }}>
            <p style={{ margin: "0 0 12px", color: "var(--text-secondary)", fontSize: 13 }}>
              No customer flow has been configured for this category.
            </p>
            <Btn size="sm" variant="primary" onClick={() => {
              setForm({ customer_flow_type: "service_booking", frontend_component_key: "ServiceBookingFlow", primary_engine_key: "booking_engine", required_steps: [], optional_steps: [], is_active: true });
              setEditing(true);
            }}>Configure customer flow</Btn>
          </div>
        )}
        {!flow.loading && (c || editing) && <>
          <InfoRow label="Flow type">{editing ? (
            <select style={inputStyle} value={form.customer_flow_type ?? ""} onChange={e => setForm(v => ({ ...v, customer_flow_type: e.target.value }))}>
              {FLOW_TYPES.map(v => <option key={v} value={v}>{FLOW_LABEL[v]}</option>)}
            </select>
          ) : <strong>{FLOW_LABEL[c?.customer_flow_type ?? ""] ?? c?.customer_flow_type}</strong>}</InfoRow>
          <InfoRow label="Native component">{editing ? (
            <select style={inputStyle} value={form.frontend_component_key ?? ""} onChange={e => setForm(v => ({ ...v, frontend_component_key: e.target.value }))}>
              {COMPONENT_KEYS.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          ) : <code>{c?.frontend_component_key}</code>}</InfoRow>
          <InfoRow label="Execution engine">{editing ? (
            <select style={inputStyle} value={form.primary_engine_key ?? ""} onChange={e => setForm(v => ({ ...v, primary_engine_key: e.target.value }))}>
              {ENGINE_KEYS.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          ) : <code>{c?.primary_engine_key}</code>}</InfoRow>
          <InfoRow label="Required steps">{editing ? (
            <textarea style={inputStyle} rows={3} value={(form.required_steps ?? []).join(", ")} onChange={e => setForm(v => ({ ...v, required_steps: e.target.value.split(",").map(s => s.trim()).filter(Boolean) }))} />
          ) : <StepList steps={c?.required_steps ?? []} />}</InfoRow>
          <InfoRow label="Optional steps">{editing ? (
            <textarea style={inputStyle} rows={2} value={(form.optional_steps ?? []).join(", ")} onChange={e => setForm(v => ({ ...v, optional_steps: e.target.value.split(",").map(s => s.trim()).filter(Boolean) }))} />
          ) : <StepList steps={c?.optional_steps ?? []} />}</InfoRow>
        </>}
      </Card>
    </div>
  );
}

function StepList({ steps }: { steps: string[] }) {
  if (!steps.length) return <span style={{ color: "var(--text-tertiary)" }}>None</span>;
  return <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>{steps.map((s, i) => (
    <span key={`${s}-${i}`} style={{ padding: "3px 8px", borderRadius: 999, background: "var(--surface-sunken)", border: "1px solid var(--border)", fontSize: 11 }}>{i + 1}. {s}</span>
  ))}</div>;
}

function FinancePolicyTab({ categoryId }: { categoryId: string }) {
  const router = useRouter();
  const authority = useApi(useCallback(() => catalogApi.getCategoryCommissionAuthority(categoryId), [categoryId]), [categoryId]);
  const a: CategoryCommissionAuthority | null = authority.data;
  const source = a?.effective_source === "category_override" ? "Category override"
    : a?.effective_source === "vertical_default" ? "Published vertical default"
    : a?.effective_source === "platform_legacy_default" ? "Legacy platform fallback"
    : "Not applicable";

  if (authority.loading) return <Skeleton height={280} />;
  if (!a) return <Notice tone="danger">{authority.error ?? "Finance authority could not be loaded."}</Notice>;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <Notice tone="info">
        Finance policy is intentionally read-only here. Home Services Finance owns the published monetization policy; Provider Charges owns the optional category override.
      </Notice>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 12 }}>
        <Metric label="Published model" value={(a.provider_model ?? "Not configured").replaceAll("_", " ")} />
        <Metric label="Policy version" value={a.policy_version == null ? "Not published" : `Version ${a.policy_version}`} />
        <Metric label="Category pricing" value={a.category_override_pct == null ? "Uses vertical policy" : "Override configured"} />
        <Metric label="Resolved charge source" value={source} good={a.is_percentage_commission_live} />
      </div>
      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>
          <div style={{ flex: "1 1 420px" }}>
            <h3 style={{ margin: "0 0 5px", fontSize: 15 }}>Effective policy resolution</h3>
            <p style={{ margin: "0 0 14px", color: "var(--text-secondary)", fontSize: 12 }}>
              Runtime resolves the optional category override first, then the published vertical default. The resulting percentage is charged only when the published model is Percentage Commission.
            </p>
            <InfoRow label="Source"><Badge variant={a.is_percentage_commission_live ? "success" : "muted"}>{source}</Badge></InfoRow>
            <InfoRow label="Policy version">{a.policy_version == null ? "No published policy" : `Version ${a.policy_version}`}</InfoRow>
            <InfoRow label="Published">{a.policy_published_at ? new Date(a.policy_published_at).toLocaleString() : "—"}</InfoRow>
            <InfoRow label="Vertical"><code>{a.vertical_key ?? "unassigned"}</code></InfoRow>
          </div>
          <div style={{ display: "grid", gap: 8, minWidth: 235 }}>
            <Btn variant="primary" onClick={() => router.push(a.default_editor_path)}>Edit vertical default <ExternalLink size={13} /></Btn>
            <Btn variant="secondary" onClick={() => router.push(a.override_editor_path)}>Manage category overrides <ExternalLink size={13} /></Btn>
          </div>
        </div>
      </Card>
    </div>
  );
}

function Metric({ label, value, good }: { label: string; value: string | number; good?: boolean }) {
  return <div style={{ padding: "15px 17px", background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)" }}>
    <div style={{ fontSize: 19, fontWeight: 750, textTransform: label === "Published model" ? "capitalize" : undefined, color: good ? "var(--success)" : "var(--text-primary)" }}>{value}</div>
    <div style={{ marginTop: 3, fontSize: 11, color: "var(--text-tertiary)" }}>{label}</div>
  </div>;
}

function Notice({ children, tone }: { children: React.ReactNode; tone: "success" | "danger" | "info" }) {
  const color = tone === "success" ? "var(--success)" : tone === "danger" ? "var(--danger)" : "var(--brand)";
  return <div style={{ padding: "12px 15px", borderRadius: "var(--radius-lg)", background: `color-mix(in srgb, ${color} 8%, transparent)`, border: `1px solid color-mix(in srgb, ${color} 26%, var(--border))`, color, fontSize: 13 }}>{children}</div>;
}

export default function CategoryDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = String(params.id);
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const runtime = useApi(useCallback(() => categoryRuntimeApi.getCategoryRuntime(id), [id]), [id]);
  const activate = useAction(async (value: boolean) => {
    if (value) await categoryRuntimeApi.activateCategory(id);
    else await categoryRuntimeApi.deactivateCategory(id);
    runtime.refetch();
  });
  const r: CategoryRuntime | null = runtime.data;
  const cat = r?.category;

  return <AdminLayout activeNav="categories">
    <div style={{ marginBottom: 16 }}><Btn variant="ghost" size="sm" onClick={() => router.push("/admin/categories")}><ArrowLeft size={13} /> Back to Categories</Btn></div>
    {runtime.loading ? <><Skeleton height={84} /><div style={{ height: 12 }} /><Skeleton height={380} /></>
      : !cat ? <Notice tone="danger">{runtime.error ?? "Category not found."}</Notice>
      : <>
        <SectionHeader title={cat.name} subtitle={cat.description ?? "Category runtime configuration"} icon={<Layers />} actions={<div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Badge variant={cat.is_active ? "success" : "muted"}>{cat.is_active ? "Active" : "Inactive"}</Badge>
          <Btn size="sm" variant={cat.is_active ? "ghost" : "primary"} loading={activate.loading} onClick={() => activate.execute(!cat.is_active)}>{cat.is_active ? "Deactivate" : "Activate"}</Btn>
        </div>} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, marginBottom: 20 }}>
          <Metric label="Total providers" value={r?.tenant_count ?? 0} />
          <Metric label="Active providers" value={r?.active_tenant_count ?? 0} />
          <Metric label="Customer flow" value={cat.customer_flow_type ? "Configured" : "Missing"} good={!!cat.customer_flow_type} />
          <Metric label="Finance model" value={(cat.finance_model ?? "Missing").replaceAll("_", " ")} good={!!cat.finance_model} />
        </div>
        <div style={{ display: "flex", gap: 2, borderBottom: "1px solid var(--border)", marginBottom: 20, overflowX: "auto" }}>
          {TABS.map(tab => <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ display: "flex", gap: 6, alignItems: "center", padding: "10px 16px", border: 0, borderBottom: activeTab === tab.key ? "2px solid var(--brand)" : "2px solid transparent", background: "transparent", color: activeTab === tab.key ? "var(--text-primary)" : "var(--text-secondary)", fontWeight: activeTab === tab.key ? 650 : 450, cursor: "pointer", whiteSpace: "nowrap" }}>{tab.icon}{tab.label}</button>)}
        </div>
        {activeTab === "overview" && <Card>
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}><ShieldCheck size={17} style={{ color: "var(--success)" }} /><strong>Persisted category configuration</strong></div>
          <InfoRow label="Category ID"><code>{cat.category_id}</code></InfoRow>
          <InfoRow label="Slug"><code>{cat.slug}</code></InfoRow>
          <InfoRow label="Vertical"><code>{cat.vertical_type ?? "Not assigned"}</code></InfoRow>
          <InfoRow label="Category type">{cat.category_type ?? "Not configured"}</InfoRow>
          <InfoRow label="Customer flow">{cat.customer_flow_type ? FLOW_LABEL[cat.customer_flow_type] ?? cat.customer_flow_type : "Not configured"}</InfoRow>
          <InfoRow label="Provider dashboard">{cat.provider_dashboard_type ? DASHBOARD_LABEL[cat.provider_dashboard_type] ?? cat.provider_dashboard_type : "Not configured"}</InfoRow>
          <InfoRow label="Provider registration"><Badge variant={cat.is_provider_registerable ? "success" : "muted"}>{cat.is_provider_registerable ? "Allowed" : "Disabled"}</Badge></InfoRow>
          <InfoRow label="Tenant selectable"><Badge variant={cat.tenant_selectable ? "success" : "muted"}>{cat.tenant_selectable ? "Yes" : "No"}</Badge></InfoRow>
          <InfoRow label="Pricing supported"><Badge variant={cat.pricing_supported ? "success" : "muted"}>{cat.pricing_supported ? "Yes" : "No"}</Badge></InfoRow>
          <InfoRow label="Last updated">{cat.updated_at ? new Date(cat.updated_at).toLocaleString() : "—"}</InfoRow>
        </Card>}
        {activeTab === "customer" && <CustomerFlowTab categoryId={cat.category_id} />}
        {activeTab === "finance" && <FinancePolicyTab categoryId={cat.category_id} />}
      </>}
  </AdminLayout>;
}
