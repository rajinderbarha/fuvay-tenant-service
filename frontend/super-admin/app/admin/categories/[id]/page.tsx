"use client";
import { TableSurface } from "@serviceos/design-system";

import React, { useCallback, useState } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import {
  AlertCircle, ArrowLeft, Boxes, Check, CircleDollarSign, ExternalLink, Globe,
  Layers, ListChecks, Network, Pencil, Route, Search, ShieldCheck, ToggleLeft,
  ToggleRight, X, Plus, RotateCcw, Archive,
} from "lucide-react";

import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Badge, Btn, Card, SectionHeader, Skeleton, SummaryCard, Pagination } from "../../../../components/shared/ui";
import { useAction, useApi } from "../../../../hooks/useApi";
import {
  adminCustomerFlowApi, catalogApi, categoryRuntimeApi,
  type CategoryCommissionAuthority, type CategoryRuntime, type CustomerFlowConfig,
  type CategoryLinkedCounts, type CategoryReadinessItem, type CategorySkill,
  type ServiceGroupEnriched,
} from "../../../../lib/api";

const TABS = [
  { key: "overview", label: "Overview", icon: <Layers size={14} /> },
  { key: "readiness", label: "Readiness", icon: <ListChecks size={14} /> },
  { key: "customer", label: "Customer Flow", icon: <Globe size={14} /> },
  { key: "finance", label: "Finance Policy", icon: <CircleDollarSign size={14} /> },
  { key: "catalog", label: "Catalog Links", icon: <Boxes size={14} /> },
  { key: "skills", label: "Technician Skills", icon: <ShieldCheck size={14} /> },
  { key: "engines", label: "Engines", icon: <Network size={14} /> },
  { key: "modules", label: "Modules", icon: <Route size={14} /> },
] as const;
type TabKey = (typeof TABS)[number]["key"];

function isTabKey(value: string | null): value is TabKey {
  return TABS.some(tab => tab.key === value);
}

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
const FLOW_COMPONENT_MAP: Record<string, (typeof COMPONENT_KEYS)[number]> = {
  service_booking: "ServiceBookingFlow",
  appointment_booking: "AppointmentBookingFlow",
  lead_capture: "LeadCaptureFlow",
  order_flow: "OrderFlow",
  inquiry_flow: "InquiryFlow",
  product_inquiry: "ProductInquiryFlow",
  unsupported: "UnsupportedFlow",
};
const FLOW_ENGINE_MAP: Record<string, string> = {
  service_booking: "booking_engine",
  appointment_booking: "appointment_engine",
  lead_capture: "lead_engine",
  order_flow: "order_engine",
  inquiry_flow: "inquiry_engine",
  product_inquiry: "product_inquiry_engine",
  unsupported: "none",
};

function InfoRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", gap: 16, padding: "11px 0", borderBottom: "1px solid var(--border)" }}>
      <span style={{ minWidth: 175, fontSize: 12, fontWeight: 600, color: "var(--text-tertiary)" }}>{label}</span>
      <div style={{ flex: 1, minWidth: 0, fontSize: 13, color: "var(--text-primary)" }}>{children}</div>
    </div>
  );
}

function CustomerFlowTab({ category }: { category: CategoryRuntime["category"] }) {
  const categoryId = category.category_id;
  const isHomeServices = category.vertical_type === "home_services";
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
    const flowType = isHomeServices ? "service_booking" : (form.customer_flow_type ?? "unsupported");
    await adminCustomerFlowApi.upsertFlowConfig(categoryId, {
      ...form,
      customer_flow_type: flowType,
      frontend_component_key: FLOW_COMPONENT_MAP[flowType] ?? "UnsupportedFlow",
      primary_engine_key: FLOW_ENGINE_MAP[flowType] ?? "none",
    });
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
  const availableFlowTypes = isHomeServices ? ["service_booking"] : FLOW_TYPES;
  const applyFlowType = (flowType: string) => {
    setForm(v => ({
      ...v,
      customer_flow_type: flowType,
      frontend_component_key: FLOW_COMPONENT_MAP[flowType] ?? "UnsupportedFlow",
      primary_engine_key: FLOW_ENGINE_MAP[flowType] ?? "none",
    }));
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      {saved && <Notice tone="success">Customer flow saved and available to the customer app.</Notice>}
      {(save.error || toggle.error) && <Notice tone="danger">{save.error || toggle.error}</Notice>}
      {isHomeServices && (
        <Notice tone="info">
          Home Services is locked to the native service booking flow. Other flow types are for other verticals and would not run the Home Services catalog, provider matching, booking, and job-completion pipeline.
        </Notice>
      )}
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
            <select style={inputStyle} value={form.customer_flow_type ?? ""} disabled={isHomeServices} onChange={e => applyFlowType(e.target.value)}>
              {availableFlowTypes.map(v => <option key={v} value={v}>{FLOW_LABEL[v]}</option>)}
            </select>
          ) : <strong>{FLOW_LABEL[c?.customer_flow_type ?? ""] ?? c?.customer_flow_type}</strong>}</InfoRow>
          <InfoRow label="Native component">{editing ? (
            <code>{form.frontend_component_key ?? FLOW_COMPONENT_MAP[form.customer_flow_type ?? "unsupported"] ?? "UnsupportedFlow"}</code>
          ) : <code>{c?.frontend_component_key}</code>}</InfoRow>
          <InfoRow label="Execution engine">{editing ? (
            <code>{form.primary_engine_key ?? FLOW_ENGINE_MAP[form.customer_flow_type ?? "unsupported"] ?? "none"}</code>
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
  const singleAuthority = a?.vertical_key === "home_services";
  const source = a?.effective_source === "category_override" ? "Category override"
    : a?.effective_source === "vertical_default" ? "Published vertical default"
    : a?.effective_source === "platform_legacy_default" ? "Legacy platform fallback"
    : "Not applicable";

  if (authority.loading) return <Skeleton height={280} />;
  if (!a) return <Notice tone="danger">{authority.error ?? "Finance authority could not be loaded."}</Notice>;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <Notice tone="info">
        {singleAuthority
          ? "Finance policy is intentionally read-only here. Home Services Finance > Monetization is the only provider and customer charge configuration authority."
          : "Finance policy is intentionally read-only here. Use the business vertical's finance workspace to manage its policy."}
      </Notice>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 12 }}>
        <Metric label="Published model" value={(a.provider_model ?? "Not configured").replaceAll("_", " ")} />
        <Metric label="Policy version" value={a.policy_version == null ? "Not published" : `Version ${a.policy_version}`} />
        <Metric label="Category finance" value={singleAuthority ? "Vertical policy only" : a.category_override_pct == null ? "Uses vertical policy" : "Override configured"} />
        <Metric label="Resolved charge source" value={source} good={a.is_percentage_commission_live} />
      </div>
      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>
          <div style={{ flex: "1 1 420px" }}>
            <h3 style={{ margin: "0 0 5px", fontSize: 15 }}>Effective policy resolution</h3>
            <p style={{ margin: "0 0 14px", color: "var(--text-secondary)", fontSize: 12 }}>
              {singleAuthority
                ? "Runtime uses the published Home Services Monetization policy directly. This category cannot define a second provider or customer charge."
                : "Runtime resolves this category using its business vertical's published finance policy."}
            </p>
            <InfoRow label="Source"><Badge variant={a.is_percentage_commission_live ? "success" : "muted"}>{source}</Badge></InfoRow>
            <InfoRow label="Policy version">{a.policy_version == null ? "No published policy" : `Version ${a.policy_version}`}</InfoRow>
            <InfoRow label="Published">{a.policy_published_at ? new Date(a.policy_published_at).toLocaleString() : "—"}</InfoRow>
            <InfoRow label="Vertical"><code>{a.vertical_key ?? "unassigned"}</code></InfoRow>
          </div>
          <div style={{ display: "grid", gap: 8, minWidth: 235 }}>
            <Btn variant="primary" onClick={() => router.push(a.default_editor_path)}>Edit vertical default <ExternalLink size={13} /></Btn>
            {a.override_editor_path && (
              <Btn variant="secondary" onClick={() => router.push(a.override_editor_path)}>Manage category overrides <ExternalLink size={13} /></Btn>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}

function Metric({ label, value, good }: { label: string; value: string | number; good?: boolean }) {
  return <SummaryCard label={label} value={value} tone={good ? "success" : undefined} />;
}

function StatusDot({ ok }: { ok: boolean }) {
  return <span style={{ width: 8, height: 8, borderRadius: 999, background: ok ? "var(--success)" : "var(--warning)", display: "inline-block" }} />;
}

function ReadinessTab({ cat }: { cat: CategoryRuntime["category"] & { readiness_status?: string; readiness_items?: CategoryReadinessItem[]; linked_counts?: CategoryLinkedCounts } }) {
  const items = cat.readiness_items ?? [];
  const ready = items.length === 0 && cat.is_active;
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <Notice tone={ready ? "success" : "info"}>
        {ready ? "This category has the required runtime setup for customer and tenant use." : "These checks are calculated from the persisted category, catalog, finance, and tenant-selection state."}
      </Notice>
      <Card>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
          <Metric label="Readiness" value={(cat.readiness_status ?? "unknown").replaceAll("_", " ")} good={ready} />
          <Metric label="Customer flow" value={cat.customer_flow_type ? "Configured" : "Missing"} good={!!cat.customer_flow_type} />
          <Metric label="Finance model" value={cat.finance_model ? "Configured" : "Missing"} good={!!cat.finance_model} />
          <Metric label="Tenant selectable" value={cat.tenant_selectable ? "Enabled" : "Disabled"} good={cat.tenant_selectable} />
        </div>
      </Card>
      <Card>
        <h3 style={{ margin: "0 0 12px", fontSize: 15 }}>Readiness checks</h3>
        {items.length === 0 ? (
          <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--success)", fontSize: 13 }}>
            <Check size={16} /> No blocking readiness items.
          </div>
        ) : (
          <div style={{ display: "grid", gap: 10 }}>
            {items.map(item => (
              <div key={item.key} style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: 12, borderRadius: "var(--radius-lg)", border: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                <AlertCircle size={15} style={{ color: item.status === "missing" ? "var(--danger)" : "var(--warning)", marginTop: 1 }} />
                <div>
                  <div style={{ fontSize: 13, fontWeight: 650, textTransform: "capitalize" }}>{item.key.replaceAll("_", " ")}</div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>{item.message}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function CatalogLinksTab({ cat }: { cat: CategoryRuntime["category"] & { linked_counts?: CategoryLinkedCounts } }) {
  const linked = cat.linked_counts ?? { service_groups: 0, services: 0, pricing_rules: 0, brands: 0, packages: 0, providers: 0 };
  const links = [
    { label: "Service groups", value: linked.service_groups, href: `/admin/service-groups?category_id=${cat.category_id}`, note: "Service grouping under this business category" },
    { label: "Master services", value: linked.services, href: `/admin/master-services?category_id=${cat.category_id}`, note: "Customer-visible service definitions" },
    { label: "Blueprint workspace", value: "Open", href: `/admin/catalog-workspace?category_id=${cat.category_id}`, note: "Job types, workflow, questions, pricing blueprint" },
    { label: "Checklists", value: "Open", href: `/admin/checklists?category_id=${cat.category_id}`, note: "Native staff/customer evidence requirements" },
    { label: "Providers", value: linked.providers, href: `/admin/home-services/providers?category_id=${cat.category_id}`, note: "Tenants offering this category" },
    { label: "Finance", value: cat.vertical_type === "home_services" ? "Monetization" : "Policy", href: cat.vertical_type === "home_services" ? "/admin/home-services/finance?tab=monetization" : "/admin/verticals", note: "Single finance authority for this vertical" },
  ];
  return (
    <Card>
      <h3 style={{ margin: "0 0 6px", fontSize: 15 }}>Connected catalog surfaces</h3>
      <p style={{ margin: "0 0 16px", fontSize: 12, color: "var(--text-secondary)" }}>
        These links keep the category page connected to the actual catalog, setup, finance, and provider surfaces.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: 12 }}>
        {links.map(link => (
          <Link key={link.label} href={link.href} style={{ textDecoration: "none", color: "inherit" }}>
            <div style={{ minHeight: 112, padding: 16, border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", background: "var(--surface-sunken)", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
                  <strong style={{ fontSize: 14 }}>{link.label}</strong>
                  <ExternalLink size={13} style={{ color: "var(--text-tertiary)" }} />
                </div>
                <p style={{ margin: "7px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>{link.note}</p>
              </div>
              <div style={{ marginTop: 14, fontSize: 20, fontWeight: 750, color: "var(--brand)" }}>{link.value}</div>
            </div>
          </Link>
        ))}
      </div>
    </Card>
  );
}

function TechnicianSkillsTab({ categoryId }: { categoryId: string }) {
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<CategorySkill | null | undefined>(undefined);
  const [form, setForm] = useState({ name: "", code: "", description: "", service_group_id: "", requires_verification: false, display_order: 100 });

  const skills = useApi(useCallback(
    () => categoryRuntimeApi.listSkills(categoryId, { q: query, status, page, page_size: 20 }),
    [categoryId, query, status, page],
  ), [categoryId, query, status, page]);
  const groups = useApi(useCallback(
    () => catalogApi.listServiceGroups({ categoryId, status: "active", limit: 100 }),
    [categoryId],
  ), [categoryId]);

  const save = useAction(async () => {
    const payload = {
      name: form.name.trim(), code: form.code.trim() || undefined,
      description: form.description.trim() || null,
      service_group_id: form.service_group_id || null,
      requires_verification: form.requires_verification,
      display_order: Number(form.display_order) || 100,
    };
    if (editing) await categoryRuntimeApi.updateSkill(categoryId, editing.id, payload);
    else await categoryRuntimeApi.createSkill(categoryId, payload);
    setEditing(undefined);
    skills.refetch();
  });
  const lifecycle = useAction(async (skill: CategorySkill) => {
    if (skill.status === "active") await categoryRuntimeApi.retireSkill(categoryId, skill.id);
    else await categoryRuntimeApi.restoreSkill(categoryId, skill.id);
    skills.refetch();
  });

  const openCreate = () => {
    setForm({ name: "", code: "", description: "", service_group_id: "", requires_verification: false, display_order: 100 });
    setEditing(null);
  };
  const openEdit = (skill: CategorySkill) => {
    setForm({ name: skill.name, code: skill.code, description: skill.description ?? "", service_group_id: skill.service_group_id ?? "", requires_verification: skill.requires_verification, display_order: skill.display_order });
    setEditing(skill);
  };
  const inputStyle: React.CSSProperties = { width: "100%", padding: "9px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", boxSizing: "border-box" };
  const data = skills.data;
  const rows = data?.items ?? [];

  return <div style={{ display: "grid", gap: 16 }}>
    <Notice tone="info">This catalog is the only source providers can use when assigning technician skills. Retiring a skill prevents new selection without deleting historical assignments.</Notice>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
      <Metric label="Catalog skills" value={data?.total ?? 0} good={(data?.total ?? 0) > 0} />
      <Metric label="Active on this page" value={rows.filter(item => item.status === "active").length} />
      <Metric label="Verification controlled" value={rows.filter(item => item.requires_verification).length} />
      <Metric label="Assigned technicians" value={rows.reduce((sum, item) => sum + Number(item.assigned_count || 0), 0)} />
    </div>
    <Card>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", marginBottom: 14 }}>
        <div style={{ display: "flex", gap: 8, flex: "1 1 520px", flexWrap: "wrap" }}>
          <div style={{ position: "relative", flex: "1 1 260px" }}>
            <Search size={14} style={{ position: "absolute", left: 11, top: 11, color: "var(--text-tertiary)" }} />
            <input value={search} onChange={event => setSearch(event.target.value)} onKeyDown={event => { if (event.key === "Enter") { setPage(1); setQuery(search); } }} placeholder="Search skills by name, code or description..." style={{ ...inputStyle, paddingLeft: 34 }} />
          </div>
          <Btn variant="secondary" onClick={() => { setPage(1); setQuery(search); }}>Search</Btn>
          <select value={status} onChange={event => { setStatus(event.target.value); setPage(1); }} style={{ ...inputStyle, width: 150 }}>
            <option value="">All statuses</option><option value="active">Active</option><option value="retired">Retired</option>
          </select>
        </div>
        <Btn variant="primary" onClick={openCreate}><Plus size={14} /> Add skill</Btn>
      </div>
      {(save.error || lifecycle.error || skills.error) && <Notice tone="danger">{save.error || lifecycle.error || skills.error}</Notice>}
      {skills.loading ? <Skeleton height={260} /> : rows.length === 0 ? (
        <div style={{ padding: 36, textAlign: "center", color: "var(--text-secondary)", fontSize: 13 }}>No skills match these filters.</div>
      ) : <div style={{ overflowX: "auto" }}><TableSurface style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead><tr style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: ".05em" }}>
          {['Skill', 'Service group', 'Verification', 'Assignments', 'Status', 'Actions'].map((label, index) => <th key={label} style={{ padding: "9px 10px", textAlign: index > 2 ? "right" : "left", borderBottom: "1px solid var(--border)" }}>{label}</th>)}
        </tr></thead>
        <tbody>{rows.map(skill => <tr key={skill.id}>
          <td style={{ padding: "12px 10px", borderBottom: "1px solid var(--border)" }}><div style={{ fontWeight: 650, fontSize: 13 }}>{skill.name}</div><code style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{skill.code}</code>{skill.description && <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 3 }}>{skill.description}</div>}</td>
          <td style={{ padding: "12px 10px", borderBottom: "1px solid var(--border)", fontSize: 12 }}>{skill.service_group_name ?? "Category-wide"}</td>
          <td style={{ padding: "12px 10px", borderBottom: "1px solid var(--border)" }}><Badge variant={skill.requires_verification ? "warning" : "muted"}>{skill.requires_verification ? "Required" : "Not required"}</Badge></td>
          <td style={{ padding: "12px 10px", borderBottom: "1px solid var(--border)", textAlign: "right", fontSize: 13, fontWeight: 650 }}>{skill.assigned_count}</td>
          <td style={{ padding: "12px 10px", borderBottom: "1px solid var(--border)", textAlign: "right" }}><Badge variant={skill.status === "active" ? "success" : "muted"}>{skill.status}</Badge></td>
          <td style={{ padding: "12px 10px", borderBottom: "1px solid var(--border)", textAlign: "right", whiteSpace: "nowrap" }}><Btn size="xs" variant="ghost" onClick={() => openEdit(skill)}><Pencil size={12} /> Edit</Btn><Btn size="xs" variant="ghost" loading={lifecycle.loading} onClick={() => lifecycle.execute(skill)}>{skill.status === "active" ? <Archive size={12} /> : <RotateCcw size={12} />}{skill.status === "active" ? "Retire" : "Restore"}</Btn></td>
        </tr>)}</tbody>
      </TableSurface></div>}
      <Pagination page={data?.page ?? page} pageSize={20} total={data?.total ?? 0} pageCount={data?.pages}
        onPage={setPage} itemLabel="skills" alwaysShow />
    </Card>
    {editing !== undefined && <Card>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}><div><h3 style={{ margin: 0, fontSize: 15 }}>{editing ? "Edit technician skill" : "Add technician skill"}</h3><p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--text-tertiary)" }}>Provider choices update immediately after saving.</p></div><Btn variant="ghost" size="sm" onClick={() => setEditing(undefined)}><X size={13} /> Close</Btn></div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
        <label style={{ fontSize: 12 }}>Skill name *<input value={form.name} onChange={event => setForm(value => ({ ...value, name: event.target.value }))} style={{ ...inputStyle, display: "block", marginTop: 5 }} /></label>
        <label style={{ fontSize: 12 }}>Stable code<input value={form.code} onChange={event => setForm(value => ({ ...value, code: event.target.value }))} placeholder="Generated from name" style={{ ...inputStyle, display: "block", marginTop: 5 }} /></label>
        <label style={{ fontSize: 12 }}>Service group<select value={form.service_group_id} onChange={event => setForm(value => ({ ...value, service_group_id: event.target.value }))} style={{ ...inputStyle, display: "block", marginTop: 5 }}><option value="">Category-wide</option>{((groups.data?.groups ?? []) as ServiceGroupEnriched[]).map(group => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
        <label style={{ fontSize: 12 }}>Display order<input type="number" min={0} value={form.display_order} onChange={event => setForm(value => ({ ...value, display_order: Number(event.target.value) }))} style={{ ...inputStyle, display: "block", marginTop: 5 }} /></label>
      </div>
      <label style={{ display: "block", fontSize: 12, marginTop: 12 }}>Description<textarea value={form.description} onChange={event => setForm(value => ({ ...value, description: event.target.value }))} rows={3} style={{ ...inputStyle, display: "block", marginTop: 5, resize: "vertical" }} /></label>
      <label style={{ display: "flex", alignItems: "center", gap: 9, marginTop: 12, fontSize: 12 }}><input type="checkbox" checked={form.requires_verification} onChange={event => setForm(value => ({ ...value, requires_verification: event.target.checked }))} /> Require evidence verification before this skill is shown as verified</label>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}><Btn variant="secondary" onClick={() => setEditing(undefined)}>Cancel</Btn><Btn variant="primary" loading={save.loading} disabled={!form.name.trim()} onClick={() => save.execute()}><Check size={13} /> Save skill</Btn></div>
    </Card>}
  </div>;
}

function EnginesTab({ runtime }: { runtime: CategoryRuntime }) {
  const engines = runtime.running_engines ?? [];
  const [q, setQ] = useState("");
  const [source, setSource] = useState("");
  const [required, setRequired] = useState("");
  const sources = React.useMemo(() => Array.from(new Set(engines.map(e => e.source).filter(Boolean) as string[])).sort(), [engines]);
  const filtered = React.useMemo(() => engines.filter(engine => {
    const term = q.trim().toLowerCase();
    if (term && !`${engine.display_name ?? ""} ${engine.engine_key} ${engine.runtime_reason ?? ""}`.toLowerCase().includes(term)) return false;
    if (source && engine.source !== source) return false;
    if (required === "required" && !engine.is_required) return false;
    if (required === "optional" && engine.is_required) return false;
    return true;
  }), [engines, q, source, required]);
  const runtimeUsed = engines.filter(e => String(e.source ?? "").includes("runtime")).length;
  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(165px, 1fr))", gap: 12 }}>
        <Metric label="Total runtime engines" value={engines.length} good={engines.length > 0} />
        <Metric label="Required engines" value={engines.filter(e => e.is_required).length} />
        <Metric label="Runtime inferred" value={runtimeUsed} good={runtimeUsed > 0} />
        <Metric label="Primary engine" value={runtime.engine_summary?.primary?.engine_key ?? "None"} good={!!runtime.engine_summary?.primary} />
      </div>
      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", flexWrap: "wrap", marginBottom: 14 }}>
          <div>
            <h3 style={{ margin: "0 0 6px", fontSize: 15 }}>Runtime engines</h3>
            <p style={{ margin: 0, fontSize: 12, color: "var(--text-secondary)" }}>
              Shows vertical registry mappings plus engines proven by live Home Services runtime routes, finance, support, booking, app and governance flows.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search engines..." style={{ minWidth: 220, padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }} />
            <select value={source} onChange={e => setSource(e.target.value)} style={{ padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }}>
              <option value="">All sources</option>
              {sources.map(s => <option key={s} value={s}>{s.replaceAll("_", " ")}</option>)}
            </select>
            <select value={required} onChange={e => setRequired(e.target.value)} style={{ padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }}>
              <option value="">All criticality</option>
              <option value="required">Required</option>
              <option value="optional">Optional</option>
            </select>
          </div>
        </div>
        {engines.length === 0 ? <Notice tone="danger">No engine mapping is configured for this category vertical.</Notice> : filtered.length === 0 ? (
          <Notice tone="info">No engines match the current filters.</Notice>
        ) : (
        <div style={{ display: "grid", gap: 8 }}>
          {filtered.map(engine => (
            <div key={engine.engine_key} style={{ display: "grid", gridTemplateColumns: "minmax(220px, 1fr) minmax(180px, 1.4fr) auto", gap: 12, alignItems: "center", padding: 12, border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", background: "var(--surface-sunken)" }}>
              <div style={{ minWidth: 0 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <StatusDot ok={engine.is_enabled} />
                  <strong style={{ fontSize: 13 }}>{engine.display_name ?? engine.engine_key}</strong>
                </div>
                <code style={{ display: "block", marginTop: 4, fontSize: 11, color: "var(--text-tertiary)" }}>{engine.engine_key}</code>
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 4 }}>
                  <Badge variant={engine.is_required ? "warning" : "muted"}>{engine.is_required ? "Required" : "Optional"}</Badge>
                  <Badge variant={String(engine.source ?? "").includes("runtime") ? "success" : "muted"}>{(engine.source ?? "registry").replaceAll("_", " ")}</Badge>
                  {engine.is_primary && <Badge variant="success">Primary</Badge>}
                </div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{engine.runtime_reason ?? "Mapped to this vertical."}</div>
                {engine.dependencies?.length ? <div style={{ marginTop: 4, fontSize: 11, color: "var(--text-tertiary)" }}>Depends on: {engine.dependencies.join(", ")}</div> : null}
              </div>
              <Badge variant={engine.health_status === "attention" ? "warning" : "success"}>{engine.health_status.replaceAll("_", " ")}</Badge>
            </div>
          ))}
        </div>
      )}
      </Card>
    </div>
  );
}

function ModulesTab({ runtime }: { runtime: CategoryRuntime }) {
  const modules = runtime.dashboard_modules ?? [];
  const [q, setQ] = useState("");
  const [area, setArea] = useState("");
  const [source, setSource] = useState("");
  const areas = React.useMemo(() => Array.from(new Set(modules.map(m => m.dashboard_area).filter(Boolean) as string[])).sort(), [modules]);
  const sources = React.useMemo(() => Array.from(new Set(modules.map(m => m.source).filter(Boolean) as string[])).sort(), [modules]);
  const filtered = React.useMemo(() => modules.filter(module => {
    const term = q.trim().toLowerCase();
    if (term && !`${module.module_name ?? ""} ${module.module_key} ${module.description ?? ""} ${module.engine_key ?? ""}`.toLowerCase().includes(term)) return false;
    if (area && module.dashboard_area !== area) return false;
    if (source && module.source !== source) return false;
    return true;
  }), [modules, q, area, source]);
  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(165px, 1fr))", gap: 12 }}>
        <Metric label="Visible modules" value={modules.length} good={modules.length > 0} />
        <Metric label="Required modules" value={modules.filter(m => m.is_required).length} />
        <Metric label="Runtime routes" value={modules.filter(m => String(m.source ?? "").includes("runtime")).length} good />
        <Metric label="Module groups" value={areas.length} />
      </div>
      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", flexWrap: "wrap", marginBottom: 14 }}>
          <div>
            <h3 style={{ margin: "0 0 6px", fontSize: 15 }}>Admin modules</h3>
            <p style={{ margin: 0, fontSize: 12, color: "var(--text-secondary)" }}>
              Shows registry modules plus live Home Services admin routes. Retired destinations stay hidden; current replacement routes are visible.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search modules..." style={{ minWidth: 220, padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }} />
            <select value={area} onChange={e => setArea(e.target.value)} style={{ padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }}>
              <option value="">All groups</option>
              {areas.map(a => <option key={a} value={a}>{a.replaceAll("_", " ")}</option>)}
            </select>
            <select value={source} onChange={e => setSource(e.target.value)} style={{ padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }}>
              <option value="">All sources</option>
              {sources.map(s => <option key={s} value={s}>{s.replaceAll("_", " ")}</option>)}
            </select>
          </div>
        </div>
      {modules.length === 0 ? <Notice tone="danger">No available modules are assigned to this category vertical.</Notice> : filtered.length === 0 ? (
        <Notice tone="info">No modules match the current filters.</Notice>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <TableSurface style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ color: "var(--text-tertiary)", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                <th style={{ textAlign: "left", padding: "9px 10px", borderBottom: "1px solid var(--border)" }}>Module</th>
                <th style={{ textAlign: "left", padding: "9px 10px", borderBottom: "1px solid var(--border)" }}>Group</th>
                <th style={{ textAlign: "left", padding: "9px 10px", borderBottom: "1px solid var(--border)" }}>Engine</th>
                <th style={{ textAlign: "left", padding: "9px 10px", borderBottom: "1px solid var(--border)" }}>Status</th>
                <th style={{ textAlign: "left", padding: "9px 10px", borderBottom: "1px solid var(--border)" }}>Source</th>
                <th style={{ textAlign: "right", padding: "9px 10px", borderBottom: "1px solid var(--border)" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(module => (
                <tr key={module.module_key}>
                  <td style={{ padding: "12px 10px", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ fontWeight: 650, fontSize: 13 }}>{module.module_name ?? module.display_name ?? module.module_key}</div>
                    <div style={{ marginTop: 3, fontSize: 11, color: "var(--text-tertiary)" }}>{module.description ?? module.module_key}</div>
                  </td>
                  <td style={{ padding: "12px 10px", borderBottom: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)" }}>{module.dashboard_area ?? "Admin"}</td>
                  <td style={{ padding: "12px 10px", borderBottom: "1px solid var(--border)" }}><code style={{ fontSize: 11 }}>{module.engine_key ?? "—"}</code></td>
                  <td style={{ padding: "12px 10px", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      <Badge variant={module.is_enabled ? "success" : "muted"}>{module.is_enabled ? "Enabled" : "Disabled"}</Badge>
                      {module.is_required && <Badge variant="warning">Required</Badge>}
                    </div>
                  </td>
                  <td style={{ padding: "12px 10px", borderBottom: "1px solid var(--border)" }}>
                    <Badge variant={String(module.source ?? "").includes("runtime") ? "success" : "muted"}>{(module.source ?? "registry").replaceAll("_", " ")}</Badge>
                  </td>
                  <td style={{ padding: "12px 10px", borderBottom: "1px solid var(--border)", textAlign: "right" }}>
                    {module.route_path ? <Link href={module.route_path}><Btn size="xs" variant="ghost">Open <ExternalLink size={11} /></Btn></Link> : <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>No route</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </TableSurface>
        </div>
      )}
      </Card>
    </div>
  );
}

function Notice({ children, tone }: { children: React.ReactNode; tone: "success" | "danger" | "info" }) {
  const color = tone === "success" ? "var(--success)" : tone === "danger" ? "var(--danger)" : "var(--brand)";
  return <div style={{ padding: "12px 15px", borderRadius: "var(--radius-lg)", background: `color-mix(in srgb, ${color} 8%, transparent)`, border: `1px solid color-mix(in srgb, ${color} 26%, var(--border))`, color, fontSize: 13 }}>{children}</div>;
}

export default function CategoryDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const id = String(params.id);
  const requestedTab = searchParams.get("tab");
  const [activeTab, setActiveTab] = useState<TabKey>(() => isTabKey(requestedTab) ? requestedTab : "overview");
  const runtime = useApi(useCallback(() => categoryRuntimeApi.getCategoryRuntime(id), [id]), [id]);
  const activate = useAction(async (value: boolean) => {
    if (value) await categoryRuntimeApi.activateCategory(id);
    else await categoryRuntimeApi.deactivateCategory(id);
    runtime.refetch();
  });
  const r: CategoryRuntime | null = runtime.data;
  const cat = r?.category as (CategoryRuntime["category"] & {
    linked_counts?: CategoryLinkedCounts;
    readiness_status?: string;
    readiness_items?: CategoryReadinessItem[];
  }) | undefined;

  React.useEffect(() => {
    if (isTabKey(requestedTab) && requestedTab !== activeTab) setActiveTab(requestedTab);
  }, [requestedTab, activeTab]);

  const switchTab = (tab: TabKey) => {
    setActiveTab(tab);
    const next = new URLSearchParams(searchParams.toString());
    next.set("tab", tab);
    router.replace(`/admin/categories/${id}?${next.toString()}`, { scroll: false });
  };

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
          <Metric label="Modules" value={`${(r?.dashboard_modules ?? []).filter(m => m.is_enabled).length}/${(r?.dashboard_modules ?? []).length}`} good={(r?.dashboard_modules ?? []).some(m => m.is_enabled)} />
        </div>
        <div style={{ display: "flex", gap: 2, borderBottom: "1px solid var(--border)", marginBottom: 20, overflowX: "auto" }}>
          {TABS.map(tab => <button key={tab.key} onClick={() => switchTab(tab.key)} style={{ display: "flex", gap: 6, alignItems: "center", padding: "10px 16px", border: 0, borderBottom: activeTab === tab.key ? "2px solid var(--brand)" : "2px solid transparent", background: "transparent", color: activeTab === tab.key ? "var(--text-primary)" : "var(--text-secondary)", fontWeight: activeTab === tab.key ? 650 : 450, cursor: "pointer", whiteSpace: "nowrap" }}>{tab.icon}{tab.label}</button>)}
        </div>
        {activeTab === "overview" && <Card>
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}><ShieldCheck size={17} style={{ color: "var(--success)" }} /><strong>Persisted category configuration</strong></div>
          <InfoRow label="Category ID"><code>{cat.category_id}</code></InfoRow>
          <InfoRow label="Slug"><code>{cat.slug}</code></InfoRow>
          <InfoRow label="Vertical"><code>{cat.vertical_type ?? "Not assigned"}</code></InfoRow>
          <InfoRow label="Readiness"><Badge variant={(cat.readiness_status ?? "") === "ready" ? "success" : "warning"}>{(cat.readiness_status ?? "unknown").replaceAll("_", " ")}</Badge></InfoRow>
          <InfoRow label="Category type">{cat.category_type ?? "Not configured"}</InfoRow>
          <InfoRow label="Customer flow">{cat.customer_flow_type ? FLOW_LABEL[cat.customer_flow_type] ?? cat.customer_flow_type : "Not configured"}</InfoRow>
          <InfoRow label="Provider dashboard">{cat.provider_dashboard_type ? DASHBOARD_LABEL[cat.provider_dashboard_type] ?? cat.provider_dashboard_type : "Not configured"}</InfoRow>
          <InfoRow label="Provider registration"><Badge variant={cat.is_provider_registerable ? "success" : "muted"}>{cat.is_provider_registerable ? "Allowed" : "Disabled"}</Badge></InfoRow>
          <InfoRow label="Tenant selectable"><Badge variant={cat.tenant_selectable ? "success" : "muted"}>{cat.tenant_selectable ? "Yes" : "No"}</Badge></InfoRow>
          <InfoRow label="Pricing supported"><Badge variant={cat.pricing_supported ? "success" : "muted"}>{cat.pricing_supported ? "Yes" : "No"}</Badge></InfoRow>
          <InfoRow label="Last updated">{cat.updated_at ? new Date(cat.updated_at).toLocaleString() : "—"}</InfoRow>
        </Card>}
        {activeTab === "readiness" && <ReadinessTab cat={cat} />}
        {activeTab === "customer" && <CustomerFlowTab category={cat} />}
        {activeTab === "finance" && <FinancePolicyTab categoryId={cat.category_id} />}
        {activeTab === "catalog" && <CatalogLinksTab cat={cat} />}
        {activeTab === "skills" && <TechnicianSkillsTab categoryId={cat.category_id} />}
        {activeTab === "engines" && r && <EnginesTab runtime={r} />}
        {activeTab === "modules" && r && <ModulesTab runtime={r} />}
      </>}
  </AdminLayout>;
}
