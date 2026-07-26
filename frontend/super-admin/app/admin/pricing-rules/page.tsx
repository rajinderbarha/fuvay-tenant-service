"use client";
import React, { useCallback, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Filter, AlertTriangle } from "lucide-react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader } from "../../../components/shared/ui";
import { SummaryCardsRow } from "../../../components/pricing/SummaryCard";
import { ActionMenu } from "../../../components/pricing/ActionMenu";
import { ResolutionPathTrace } from "../../../components/pricing/ResolutionPathTrace";
import { catalogApi, serviceOptionApi } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import type { PricingRule, PricingPreviewResult, ServiceOptionMapping34E } from "../../../lib/api";

const JOB_TYPES = [
  { value:"repair",          label:"Repair"          },
  { value:"installation",    label:"Installation"    },
  { value:"uninstallation",  label:"Uninstallation"  },
  { value:"inspection",      label:"Inspection"      },
  { value:"maintenance",     label:"Maintenance"     },
  { value:"cleaning",        label:"Cleaning"        },
  { value:"consultation",    label:"Consultation"    },
  { value:"service",         label:"Service"         },
  { value:"custom",          label:"Custom"          },
];
const PRICING_MODELS = [
  { value:"fixed", label:"Fixed" }, { value:"range", label:"Range" },
  { value:"post_assessment", label:"Post-assessment" }, { value:"hourly", label:"Hourly" },
];

function validityLabel(row: PricingRule): string {
  if (row.validity_status === "expired") return "Expired";
  if (row.validity_status === "starts_later") return row.effective_from ? `Starts ${new Date(row.effective_from).toLocaleDateString()}` : "Starts Later";
  if (row.validity_status === "always_active") return "Always Active";
  if (row.effective_to) return `Active until ${new Date(row.effective_to).toLocaleDateString()}`;
  return "Active";
}
function scopeLabel(row: PricingRule): string {
  if (row.zipcode) return "Zipcode Rule";
  if (row.city) return "City Rule";
  if (row.brand_id) return "Brand Adjustment";
  if (row.service_type_id) return "Type/Option Rule";
  if (row.tier_id) return "Tier Rule";
  return "Category Fallback";
}
function priceLabel(row: PricingRule): string {
  if (row.pricing_model === "range") return `₹${(row.min_price ?? row.base_price).toLocaleString("en-IN")}–₹${(row.max_price ?? row.base_price).toLocaleString("en-IN")}`;
  if (row.pricing_model === "post_assessment") return `Visit ₹${row.visit_fee.toLocaleString("en-IN")}`;
  if (row.pricing_model === "hourly") return `₹${row.base_price.toLocaleString("en-IN")}/hr`;
  return `₹${row.base_price.toLocaleString("en-IN")}`;
}

function PricingRulesInner() {
  const searchParams = useSearchParams();
  const initialTierId = searchParams.get("tier_id") ?? "";

  const services = useApi(useCallback(() => catalogApi.listMasterServices(undefined, undefined, true), []));
  const types = useApi(useCallback(() => catalogApi.listServiceTypes(), []));
  const brands = useApi(useCallback(() => catalogApi.listBrands(), []));
  const tiers = useApi(useCallback(() => catalogApi.listTiers(true), []));

  const [serviceFilter, setServiceFilter] = useState("");
  const [tierFilter,    setTierFilter]    = useState(initialTierId);
  const [statusFilter,  setStatusFilter]  = useState("");
  const [q,             setQ]             = useState("");
  const [advOpen,       setAdvOpen]       = useState(false);
  const [brandFilter,   setBrandFilter]   = useState("");
  const [typeFilter,    setTypeFilter]    = useState("");
  const [modelFilter,   setModelFilter]   = useState("");
  const [conflictOnly,  setConflictOnly]  = useState(false);
  const [expiringOnly,  setExpiringOnly]  = useState(false);

  const summary = useApi(useCallback(() => catalogApi.getPricingRulesSummary(), []));
  const rules = useApi(useCallback(() => catalogApi.listPricingRules(serviceFilter || undefined, {
    tierId: tierFilter || undefined,
    isActive: statusFilter === "" ? undefined : statusFilter === "active",
    q: q || undefined,
    brandId: brandFilter || undefined,
    serviceTypeId: typeFilter || undefined,
    pricingModel: modelFilter || undefined,
    expiringWithinDays: expiringOnly ? 7 : undefined,
    pageSize: 200,
  }), [serviceFilter, tierFilter, statusFilter, q, brandFilter, typeFilter, modelFilter, expiringOnly]));

  const [modalOpen, setModalOpen] = useState(false);
  const EMPTY = {
    rule_name:"", rule_code:"",
    master_service_id:"", job_type:"repair", tier_id:"", service_type_id:"", brand_id:"",
    service_option_id:"", state:"", district:"", zone:"",
    city:"", zipcode:"", pricing_model:"fixed", priority:"10", bargain_floor:"",
    base_price:"", visit_fee:"0",
    min_price:"", max_price:"", default_estimate:"",
    assessment_fee:"", show_estimated_range:false, estimated_min:"", estimated_max:"", customer_note:"",
    hourly_rate:"", min_hours:"1", estimated_hours:"",
    requires_assessment:false,
  };
  const [form, setForm] = useState(EMPTY);

  const [mappedOptions, setMappedOptions] = useState<ServiceOptionMapping34E[]>([]);
  const [loadingOptions, setLoadingOptions] = useState(false);
  async function loadMappedOptions(serviceId: string) {
    if (!serviceId) { setMappedOptions([]); return; }
    setLoadingOptions(true);
    try {
      const res = await serviceOptionApi.listServiceOptionMappings(serviceId);
      setMappedOptions(Array.isArray(res) ? res : []);
    } catch { setMappedOptions([]); }
    setLoadingOptions(false);
  }
  function F(patch: Partial<typeof EMPTY>) {
    setForm(p => ({ ...p, ...patch }));
    if (patch.master_service_id !== undefined) {
      loadMappedOptions(patch.master_service_id);
      setForm(p => ({ ...p, ...patch, service_option_id: "" }));
    }
  }

  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewForm, setPreviewForm] = useState({ master_service_id:"", city:"", zipcode:"", service_type_id:"", brand_id:"" });
  const [previewResult, setPreviewResult] = useState<PricingPreviewResult | null>(null);

  const createAction = useAction(useCallback((data: Record<string, unknown>) => catalogApi.createPricingRule(data as never), []));
  const updateAction = useAction(useCallback((id: string, data: Record<string, unknown>) => catalogApi.updatePricingRule(id, data), []));
  const deleteAction = useAction(useCallback((id: string) => catalogApi.deletePricingRule(id), []));
  const hardDeleteAction = useAction(useCallback((id: string) => catalogApi.hardDeletePricingRule(id), []));
  const previewAction = useAction(useCallback((data: Record<string, unknown>) => catalogApi.previewPricingRule(data as never), []));

  const pm = form.pricing_model;
  const isFixed   = pm === "fixed";
  const isRange   = pm === "range";
  const isPostAss = pm === "post_assessment";
  const isHourly  = pm === "hourly";
  const isCustomQ = pm === "custom_quote";

  function buildPayload() {
    const base: Record<string, unknown> = {
      rule_name: form.rule_name || undefined,
      rule_code: form.rule_code || undefined,
      master_service_id: form.master_service_id,
      job_type: form.job_type,
      tier_id: form.tier_id || undefined,
      service_type_id: form.service_type_id || undefined,
      brand_id: form.brand_id || undefined,
      service_option_id: form.service_option_id || undefined,
      state: form.state || undefined,
      district: form.district || undefined,
      zone: form.zone || undefined,
      city: form.city || undefined,
      zipcode: form.zipcode || undefined,
      pricing_model: form.pricing_model,
      priority: parseInt(form.priority) || 10,
      bargain_floor: form.bargain_floor ? parseFloat(form.bargain_floor) : undefined,
    };
    if (isFixed) { base.base_price = parseFloat(form.base_price) || 0; base.visit_fee = parseFloat(form.visit_fee) || 0; }
    if (isRange) {
      base.min_price = parseFloat(form.min_price) || 0;
      base.max_price = parseFloat(form.max_price) || 0;
      base.default_estimate = parseFloat(form.default_estimate) || undefined;
      base.visit_fee = parseFloat(form.visit_fee) || 0;
      base.base_price = parseFloat(form.min_price) || 0;
    }
    if (isPostAss) {
      base.visit_fee = parseFloat(form.visit_fee) || 0;
      base.assessment_fee = parseFloat(form.assessment_fee) || undefined;
      base.show_estimated_range = form.show_estimated_range;
      base.customer_note = form.customer_note || undefined;
      base.base_price = parseFloat(form.visit_fee) || 0;
      if (form.show_estimated_range) {
        base.estimated_min = parseFloat(form.estimated_min) || undefined;
        base.estimated_max = parseFloat(form.estimated_max) || undefined;
      }
    }
    if (isHourly) {
      base.hourly_rate = parseFloat(form.hourly_rate) || 0;
      base.min_hours = parseFloat(form.min_hours) || 1;
      base.estimated_hours = parseFloat(form.estimated_hours) || undefined;
      base.visit_fee = parseFloat(form.visit_fee) || 0;
      base.base_price = parseFloat(form.hourly_rate) || 0;
    }
    if (isCustomQ) {
      base.visit_fee = parseFloat(form.visit_fee) || 0;
      base.customer_note = form.customer_note || undefined;
      base.requires_assessment = form.requires_assessment;
      base.base_price = 0;
    }
    return base;
  }

  function isFormValid() {
    if (!form.master_service_id) return false;
    if (isFixed   && !form.base_price) return false;
    if (isRange   && (!form.min_price || !form.max_price)) return false;
    if (isPostAss && !form.visit_fee) return false;
    if (isHourly  && !form.hourly_rate) return false;
    return true;
  }

  function refetchAll() { rules.refetch(); summary.refetch(); }

  async function handleSave() {
    const res = await createAction.execute(buildPayload());
    if (res) { refetchAll(); setModalOpen(false); setForm(EMPTY); }
  }
  function openDuplicate(row: PricingRule) {
    setForm({ ...EMPTY,
      rule_name: row.rule_name ? `${row.rule_name} (Copy)` : "",
      master_service_id: row.master_service_id, job_type: "repair",
      tier_id: row.tier_id ?? "", service_type_id: row.service_type_id ?? "", brand_id: row.brand_id ?? "",
      service_option_id: row.service_option_id ?? "", state: row.state ?? "", district: row.district ?? "", zone: row.zone ?? "",
      city: row.city ?? "", zipcode: row.zipcode ?? "", pricing_model: row.pricing_model,
      priority: String(row.priority), bargain_floor: row.bargain_floor ? String(row.bargain_floor) : "",
      base_price: String(row.base_price), visit_fee: String(row.visit_fee),
      min_price: row.min_price ? String(row.min_price) : "", max_price: row.max_price ? String(row.max_price) : "",
    });
    setModalOpen(true);
  }
  async function handleDeactivate(id: string) { const res = await deleteAction.execute(id); if (res !== null) refetchAll(); }
  async function handleActivate(id: string) { const res = await updateAction.execute(id, { is_active: true }); if (res) refetchAll(); }
  async function handleHardDelete(id: string) {
    if (!confirm("Permanently delete this pricing rule? This cannot be undone.")) return;
    const res = await hardDeleteAction.execute(id);
    if (res) refetchAll();
  }
  async function handleExport() {
    const res = await catalogApi.exportPricingRules({ masterServiceId: serviceFilter || undefined,
      isActive: statusFilter === "" ? undefined : statusFilter === "active" });
    const header = "rule_name,rule_code,pricing_model,base_price,priority,is_active\n";
    const body = res.rows.map(r => [r.rule_name??"", r.rule_code??"", r.pricing_model, r.base_price, r.priority, r.is_active].join(",")).join("\n");
    const blob = new Blob([header + body], { type:"text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "pricing_rules.csv"; a.click();
    URL.revokeObjectURL(url);
  }
  async function handlePreview() {
    const res = await previewAction.execute({ master_service_id:previewForm.master_service_id,
      city:previewForm.city || undefined, zipcode:previewForm.zipcode || undefined,
      service_type_id:previewForm.service_type_id || undefined, brand_id:previewForm.brand_id || undefined });
    setPreviewResult(res ?? null);
  }
  function openPreviewFor(row: PricingRule) {
    setPreviewForm({ master_service_id: row.master_service_id, city: row.city ?? "", zipcode: row.zipcode ?? "",
      service_type_id: row.service_type_id ?? "", brand_id: row.brand_id ?? "" });
    setPreviewResult(null);
    setPreviewOpen(true);
  }

  const serviceOptions = (services.data?.services ?? []).map(s => ({ value:s.service_id, label:s.service_name }));
  const typeOptions = (types.data?.types ?? []).map(t => ({ value:t.type_id, label:t.name }));
  const brandOptions = (brands.data?.brands ?? []).map(b => ({ value:b.brand_id, label:b.name }));
  const tierOptions = (tiers.data?.tiers ?? []).map(t => ({ value:t.tier_id, label:t.name }));
  const rows = (rules.data?.items ?? []).filter(r => conflictOnly ? r.has_conflict : true);
  const s = summary.data;

  const MODEL_HINTS: Record<string, string> = {
    fixed: "Customer pays a fixed base price. Set base price and optional visit fee.",
    range: "Customer sees a price range (min–max). Set min, max, and optional default estimate.",
    post_assessment: "Price is determined after technician inspection. Set visit/inspection fee.",
    hourly: "Price calculated per hour. Set hourly rate and minimum billable hours.",
    custom_quote: "Technician sends a custom quote after inspection. No upfront price.",
  };

  const columns = [
    { key:"rule_name", label:"Rule", render:(_:unknown,row:PricingRule) => (
      <div>
        <div style={{ fontWeight:600, display:"flex", alignItems:"center", gap:6 }}>
          {row.rule_name || row.rule_code || row.rule_id.slice(0,8)}
          {row.has_conflict && <Badge variant="warning" size="sm">Conflict</Badge>}
        </div>
        <div style={{ fontSize:11, color:"var(--text-tertiary)" }}>{row.rule_code} · {row.source ?? "admin"}</div>
      </div>
    )},
    { key:"scope", label:"Scope", width:130, render:(_:unknown,row:PricingRule) => scopeLabel(row) },
    { key:"master_service_id", label:"Service", render:(_:unknown,row:PricingRule) => {
      const svc = services.data?.services.find(x => x.service_id === row.master_service_id);
      return svc ? svc.service_name : row.master_service_id;
    }},
    { key:"pricing_model", label:"Pricing Model", width:130, render:(_:unknown,row:PricingRule) => (
      <span style={{ fontSize:12, fontWeight:500 }}>{row.pricing_model.replace(/_/g," ")}</span>
    )},
    { key:"price", label:"Price / Range", width:150, render:(_:unknown,row:PricingRule) => priceLabel(row) },
    { key:"bargain_floor", label:"Bargain Floor", width:120, render:(_:unknown,row:PricingRule) =>
      row.bargain_floor != null ? `₹${row.bargain_floor.toLocaleString("en-IN")}` : "—" },
    { key:"priority", label:"Priority", width:80 },
    { key:"validity", label:"Validity", width:140, render:(_:unknown,row:PricingRule) => validityLabel(row) },
    { key:"is_active", label:"Status", width:90, render:(_:unknown,row:PricingRule) => (
      <Badge variant={row.is_active ? "success" : "muted"}>{row.is_active ? "Active" : "Inactive"}</Badge>
    )},
    { key:"rule_id", label:"", width:110, render:(_:unknown,row:PricingRule) => (
      <ActionMenu items={[
        { label:"View Details", onClick:() => openPreviewFor(row) },
        { label:"Preview Resolution", onClick:() => openPreviewFor(row) },
        { label:"Duplicate Rule", onClick:() => openDuplicate(row) },
        { label: row.is_active ? "Deactivate" : "Activate", onClick:() => row.is_active ? handleDeactivate(row.rule_id) : handleActivate(row.rule_id) },
        !row.is_active && { label:"Archive (Permanent Delete)", onClick:() => handleHardDelete(row.rule_id), destructive:true },
      ]}/>
    )},
  ];

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
      {s && (
        <SummaryCardsRow cards={[
          { label:"Total Rules", value:s.total_rules },
          { label:"Active Rules", value:s.active_rules },
          { label:"Zipcode Rules", value:s.zipcode_rules },
          { label:"Brand Rules", value:s.brand_rules },
          { label:"Tier Rules", value:s.tier_rules },
          { label:"Conflicting Rules", value:s.conflicting_rules, accent: s.conflicting_rules > 0 },
          { label:"Expiring Soon", value:s.expiring_soon },
          { label:"Expired", value:s.expired_rules },
        ]}/>
      )}
      <Card padding={16}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:12, flexWrap:"wrap", gap:10 }}>
          <h3 style={{ margin:0, fontSize:14, fontWeight:700 }}>Pricing Rules</h3>
          <div style={{ display:"flex", gap:10, alignItems:"center" }}>
            <Btn variant="secondary" size="sm" onClick={() => setPreviewOpen(true)}>Preview Price</Btn>
            <Btn variant="secondary" size="sm" onClick={handleExport}>Export</Btn>
            <Btn variant="secondary" size="sm" onClick={refetchAll}>Refresh</Btn>
            <Btn variant="primary" size="sm" onClick={() => {
              setForm({ ...EMPTY, master_service_id: serviceOptions[0]?.value ?? "" });
              setModalOpen(true);
            }}>+ New Rule</Btn>
          </div>
        </div>

        <div style={{ display:"grid", gridTemplateColumns:"1fr 180px 160px 130px auto", gap:10, marginBottom:12 }}>
          <Input label="" placeholder="Search rule name / code…" value={q} onChange={setQ}/>
          <Select label="" value={serviceFilter} onChange={setServiceFilter} placeholder="All services" options={serviceOptions}/>
          <Select label="" value={tierFilter} onChange={setTierFilter} placeholder="All tiers" options={tierOptions}/>
          <Select label="" value={statusFilter} onChange={setStatusFilter} placeholder="All statuses"
            options={[{ value:"", label:"All statuses" }, { value:"active", label:"Active" }, { value:"inactive", label:"Inactive" }]}/>
          <Btn variant="secondary" size="sm" icon={<Filter size={13}/>} onClick={() => setAdvOpen(o => !o)}>Advanced Filters</Btn>
        </div>

        {advOpen && (
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr auto auto", gap:10, marginBottom:16, padding:12, background:"var(--surface-sunken)", borderRadius:"var(--radius-md)" }}>
            <Select label="Brand" value={brandFilter} onChange={setBrandFilter} placeholder="Any brand" options={brandOptions}/>
            <Select label="Service Type" value={typeFilter} onChange={setTypeFilter} placeholder="Any type" options={typeOptions}/>
            <Select label="Pricing Model" value={modelFilter} onChange={setModelFilter} placeholder="Any model" options={PRICING_MODELS}/>
            <Btn variant={conflictOnly ? "primary" : "secondary"} size="sm" onClick={() => setConflictOnly(v => !v)}>Conflicts Only</Btn>
            <Btn variant={expiringOnly ? "primary" : "secondary"} size="sm" onClick={() => setExpiringOnly(v => !v)}>Expiring Soon</Btn>
          </div>
        )}

        <div style={{ fontSize:12, color:"var(--text-tertiary)", marginBottom:12, padding:"8px 12px", background:"var(--surface-sunken)", borderRadius:"var(--radius-md)" }}>
          Commission is managed in <strong>Finance → Commission Rules</strong>. Pricing Rules only define customer/service pricing and provider allowed price boundaries.
        </div>
        {rules.error && <p style={{ color:"var(--danger-text)", fontSize:13 }}>{rules.error}</p>}
        {(deleteAction.error || hardDeleteAction.error || updateAction.error) && (
          <p style={{ color:"var(--danger-text)", fontSize:13 }}>{deleteAction.error || hardDeleteAction.error || updateAction.error}</p>
        )}
        <DataTable columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
          rows={rows as unknown as Record<string, unknown>[]} loading={rules.loading} emptyText="No pricing rules yet."/>
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New Pricing Rule">
        <div style={{ display:"flex", flexDirection:"column", gap:14, maxHeight:"75vh", overflowY:"auto", paddingRight:4 }}>
          {createAction.error && <p style={{ color:"var(--danger-text)", fontSize:13 }}>{createAction.error}</p>}

          <div style={{ fontSize:12, fontWeight:600, color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em" }}>Rule Identity</div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
            <Input label="Rule Name" placeholder="e.g. AC Installation Split Tier 3" value={form.rule_name} onChange={v => F({ rule_name:v })}/>
            <Input label="Rule Code" placeholder="Auto-generated if blank" value={form.rule_code} onChange={v => F({ rule_code:v })}/>
          </div>

          <div style={{ fontSize:12, fontWeight:600, color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em", borderTop:"1px solid var(--border)", paddingTop:12 }}>
            Service Target
          </div>
          <Select label="Master Service *" value={form.master_service_id}
            onChange={v => F({ master_service_id:v })} placeholder="Select service..." options={serviceOptions}/>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
            <Select label="Job Type *" value={form.job_type} onChange={v => F({ job_type:v })} options={JOB_TYPES}/>
            <Select label="Pricing Model *" value={form.pricing_model} onChange={v => F({ pricing_model:v })} options={[
              ...PRICING_MODELS,
              { value:"custom_quote", label:"Custom Quote" },
            ]}/>
          </div>

          {MODEL_HINTS[pm] && (
            <div style={{ fontSize:12, color:"var(--text-secondary)", background:"var(--surface-sunken)", padding:"8px 12px", borderRadius:"var(--radius-md)", borderLeft:"3px solid var(--brand)" }}>
              {MODEL_HINTS[pm]}
            </div>
          )}

          <div style={{ fontSize:12, fontWeight:600, color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em", borderTop:"1px solid var(--border)", paddingTop:12 }}>
            Pricing Model & Amounts
          </div>
          {isFixed && (
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
              <Input label="Base Price ₹ *" type="number" placeholder="500" value={form.base_price} onChange={v => F({ base_price:v })}/>
              <Input label="Visit Fee ₹" type="number" placeholder="0" value={form.visit_fee} onChange={v => F({ visit_fee:v })}/>
            </div>
          )}
          {isRange && (
            <>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
                <Input label="Min Price ₹ *" type="number" placeholder="300" value={form.min_price} onChange={v => F({ min_price:v })}/>
                <Input label="Max Price ₹ *" type="number" placeholder="1200" value={form.max_price} onChange={v => F({ max_price:v })}/>
              </div>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
                <Input label="Default Estimate ₹" type="number" placeholder="700" value={form.default_estimate} onChange={v => F({ default_estimate:v })}/>
                <Input label="Visit Fee ₹" type="number" placeholder="0" value={form.visit_fee} onChange={v => F({ visit_fee:v })}/>
              </div>
            </>
          )}
          {isPostAss && (
            <>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
                <Input label="Inspection / Visit Fee ₹ *" type="number" placeholder="300" value={form.visit_fee} onChange={v => F({ visit_fee:v })}/>
                <Input label="Assessment Fee ₹ (optional)" type="number" placeholder="0" value={form.assessment_fee} onChange={v => F({ assessment_fee:v })}/>
              </div>
              <label style={{ display:"flex", alignItems:"center", gap:8, fontSize:13, cursor:"pointer" }}>
                <input type="checkbox" checked={form.show_estimated_range} onChange={e => F({ show_estimated_range:e.target.checked })} style={{ accentColor:"var(--brand)" }}/>
                Show estimated price range to customer
              </label>
              {form.show_estimated_range && (
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
                  <Input label="Estimated Min ₹" type="number" placeholder="500" value={form.estimated_min} onChange={v => F({ estimated_min:v })}/>
                  <Input label="Estimated Max ₹" type="number" placeholder="2000" value={form.estimated_max} onChange={v => F({ estimated_max:v })}/>
                </div>
              )}
              <Input label="Customer Note *" placeholder="Final price will be shared after inspection." value={form.customer_note} onChange={v => F({ customer_note:v })}/>
            </>
          )}
          {isHourly && (
            <>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
                <Input label="Hourly Rate ₹ *" type="number" placeholder="300" value={form.hourly_rate} onChange={v => F({ hourly_rate:v })}/>
                <Input label="Min Billable Hours *" type="number" placeholder="1" value={form.min_hours} onChange={v => F({ min_hours:v })}/>
              </div>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
                <Input label="Visit Fee ₹" type="number" placeholder="0" value={form.visit_fee} onChange={v => F({ visit_fee:v })}/>
                <Input label="Estimated Hours" type="number" placeholder="2" value={form.estimated_hours} onChange={v => F({ estimated_hours:v })}/>
              </div>
            </>
          )}
          {isCustomQ && (
            <>
              <Input label="Visit Fee ₹ (optional)" type="number" placeholder="0" value={form.visit_fee} onChange={v => F({ visit_fee:v })}/>
              <label style={{ display:"flex", alignItems:"center", gap:8, fontSize:13, cursor:"pointer" }}>
                <input type="checkbox" checked={form.requires_assessment} onChange={e => F({ requires_assessment:e.target.checked })} style={{ accentColor:"var(--brand)" }}/>
                Requires on-site assessment before quoting
              </label>
              <Input label="Customer Note" placeholder="We'll send you a quote after inspection." value={form.customer_note} onChange={v => F({ customer_note:v })}/>
            </>
          )}

          <div style={{ fontSize:12, fontWeight:600, color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em", borderTop:"1px solid var(--border)", paddingTop:12 }}>
            Bargain Floor & Priority
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
            <Input label="Bargain Floor ₹ (optional)" type="number" placeholder="Lowest negotiable price" value={form.bargain_floor} onChange={v => F({ bargain_floor:v })}
              hint="Customer/provider cannot negotiate below this floor."/>
            <Input label="Priority (higher = preferred match)" type="number" value={form.priority} onChange={v => F({ priority:v })}/>
          </div>

          <div style={{ fontSize:12, fontWeight:600, color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em", borderTop:"1px solid var(--border)", paddingTop:12 }}>
            Location Target (optional — leave blank for universal rule)
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
            <Select label="Tier" value={form.tier_id} onChange={v => F({ tier_id:v })} placeholder="Any tier" options={tierOptions}/>
            <Select label="Service Type" value={form.service_type_id} onChange={v => F({ service_type_id:v })} placeholder="Any type" options={typeOptions}/>
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
            <div>
              <Select
                label="Service Option"
                value={form.service_option_id}
                onChange={v => F({ service_option_id:v })}
                placeholder={
                  !form.master_service_id ? "Select a service first" :
                  loadingOptions ? "Loading…" :
                  mappedOptions.length === 0 ? "No options mapped to this service" :
                  "Any option"
                }
                options={[
                  { value:"", label:"Any option (no option filter)" },
                  ...mappedOptions
                    .filter(m => m.status === "active" && m.option)
                    .map(m => ({ value: m.service_option_id, label: m.option?.name ?? m.service_option_id })),
                ]}
              />
              {form.master_service_id && !loadingOptions && mappedOptions.length === 0 && (
                <p style={{ fontSize:11, color:"var(--warning-text)", margin:"4px 0 0" }}>
                  No options mapped yet. Go to Master Services to add mappings.
                </p>
              )}
            </div>
            <Select label="Brand" value={form.brand_id} onChange={v => F({ brand_id:v })} placeholder="Any brand" options={brandOptions}/>
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:14 }}>
            <Input label="State" value={form.state} onChange={v => F({ state:v })}/>
            <Input label="District" value={form.district} onChange={v => F({ district:v })}/>
            <Input label="Zone" value={form.zone} onChange={v => F({ zone:v })}/>
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
            <Input label="Zipcode" value={form.zipcode} onChange={v => F({ zipcode:v })}/>
            <Input label="City (if no zipcode)" value={form.city} onChange={v => F({ city:v })}/>
          </div>

          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="secondary" size="sm" onClick={() => setModalOpen(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={createAction.loading}
              disabled={!isFormValid()} onClick={handleSave}>Create Rule</Btn>
          </div>
        </div>
      </Modal>

      <Modal open={previewOpen} onClose={() => setPreviewOpen(false)} title="Pricing Preview">
        <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
          {previewAction.error && <p style={{ color:"var(--danger-text)", fontSize:13 }}>{previewAction.error}</p>}
          <Select label="Master Service *" value={previewForm.master_service_id} onChange={v => setPreviewForm(p => ({ ...p, master_service_id:v }))} options={serviceOptions}/>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
            <Input label="City" value={previewForm.city} onChange={v => setPreviewForm(p => ({ ...p, city:v }))}/>
            <Input label="Zipcode" value={previewForm.zipcode} onChange={v => setPreviewForm(p => ({ ...p, zipcode:v }))}/>
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
            <Select label="Type" value={previewForm.service_type_id} onChange={v => setPreviewForm(p => ({ ...p, service_type_id:v }))} placeholder="Any" options={typeOptions}/>
            <Select label="Brand" value={previewForm.brand_id} onChange={v => setPreviewForm(p => ({ ...p, brand_id:v }))} placeholder="Any" options={brandOptions}/>
          </div>
          <Btn variant="primary" size="sm" loading={previewAction.loading} disabled={!previewForm.master_service_id} onClick={handlePreview}>
            Compute Price
          </Btn>
          {previewResult && (
            <div style={{ padding:12, borderRadius:"var(--radius-md)", background:"var(--surface-sunken)" }}>
              <p style={{ margin:0, fontSize:13 }}>Source: <strong>{previewResult.source}</strong></p>
              {previewResult.matched_rule_name && (
                <p style={{ margin:"4px 0 0", fontSize:13 }}>Matched Rule: <strong>{previewResult.matched_rule_name}</strong></p>
              )}
              <p style={{ margin:"4px 0 0", fontSize:18, fontWeight:700 }}>₹{previewResult.base_price.toLocaleString("en-IN")}</p>
              <p style={{ margin:"4px 0 0", fontSize:12, color:"var(--text-tertiary)" }}>+ ₹{previewResult.visit_fee} visit fee · {previewResult.pricing_model.replace(/_/g," ")}</p>
              {previewResult.min_price != null && previewResult.max_price != null && (
                <p style={{ margin:"4px 0 0", fontSize:12, color:"var(--text-tertiary)" }}>
                  Provider Allowed Range: ₹{previewResult.min_price.toLocaleString("en-IN")}–₹{previewResult.max_price.toLocaleString("en-IN")}
                </p>
              )}
              {previewResult.bargain_floor != null && (
                <p style={{ margin:"4px 0 0", fontSize:12, color:"var(--text-tertiary)" }}>Bargain Floor: ₹{previewResult.bargain_floor.toLocaleString("en-IN")}</p>
              )}
              <ResolutionPathTrace path={previewResult.resolution_path} warnings={previewResult.warnings}/>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}

function PricingRulesPageInner() {
  return (
    <AdminLayout activeNav="pricing-rules">
      <div style={{ padding: "12px 16px", margin: "0 28px 16px", borderRadius: 10,
        background: "var(--warning-bg, #fffbeb)", border: "1px solid var(--warning-border, #fde68a)",
        display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <AlertTriangle size={16} style={{ color: "var(--warning-text, #92400e)", flexShrink: 0 }}/>
          <p style={{ fontSize: 13, color: "var(--warning-text, #92400e)", margin: 0 }}>
            This screen is deprecated for Home Services — the dedicated vertical-scoped screen was
            retired (admin no longer sets price boundaries; providers set their own price). Configure
            job types and workflow in the Catalog Workspace instead.
          </p>
        </div>
        <a href="/admin/catalog-workspace" style={{
          fontSize: 12, fontWeight: 700, color: "var(--brand)", textDecoration: "none", whiteSpace: "nowrap" }}>
          Go to Catalog Workspace →
        </a>
      </div>
      <SectionHeader title="Pricing Rules [Deprecated]" subtitle="Configure service pricing by category, service, option/type, brand, tier, city, zone, and zipcode."/>
      <div style={{ padding:"0 28px 32px" }}>
        <PricingRulesInner/>
      </div>
    </AdminLayout>
  );
}

export default function PricingRulesPage() {
  return (
    <Suspense fallback={<div style={{ padding:40 }}>Loading…</div>}>
      <PricingRulesPageInner/>
    </Suspense>
  );
}
