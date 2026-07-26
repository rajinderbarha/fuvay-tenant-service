"use client";
/**
 * Pricing Config (Super Admin) — platform-wide city tier minimum prices.
 * PROVEN: pricingApi.listCityTiers/create/update/delete all connected.
 *
 * floor_price = Minimum Allowed Price (fallback when no service-level rule exists).
 * service_name = optional; when set, this is a service-specific rule overriding the category default.
 * min_price/max_price = shown to customers as estimate range.
 */
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader } from "../../../components/shared/ui";
import { pricingApi, catalogApi, type ServiceCategory } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import type { CityTierConfig } from "../../../lib/api";

const TIER_BADGE_FALLBACK: "success"|"warning"|"muted" = "muted";

type FormState = {
  city_name: string; tier: string; service_category: string;
  service_name: string;
  floor_price: string; min_price: string; max_price: string;
  default_estimate: string; visit_fee: string; bargain_floor: string;
  provider_override_allowed: boolean;
  notes: string; is_active: boolean;
};
const EMPTY_FORM: FormState = {
  city_name:"", tier:"", service_category:"",
  service_name:"",
  floor_price:"", min_price:"", max_price:"",
  default_estimate:"", visit_fee:"", bargain_floor:"",
  provider_override_allowed: true,
  notes:"", is_active:true,
};

export default function PricingConfigPage() {
  const [tierFilter,     setTierFilter]     = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  const configs = useApi(useCallback(
    () => pricingApi.listCityTiers(tierFilter || undefined, categoryFilter || undefined, 100),
    [tierFilter, categoryFilter]
  ));

  // Load categories and tiers dynamically
  const categoriesData = useApi(useCallback(() => catalogApi.listCategories(true), []));
  const tiersData = useApi(useCallback(() => catalogApi.listTiers(true), []));
  const CATEGORIES = (categoriesData.data?.categories ?? []).map((c: ServiceCategory) => ({
    value: c.slug, label: c.name,
  }));
  // Use pricing tiers from DB (code field is what city_tier_configs stores in its tier column)
  const TIERS = (tiersData.data?.tiers ?? []).map(t => ({ value: t.code, label: t.name }));

  const [modalOpen, setModalOpen] = useState(false);
  const [editing,   setEditing]   = useState<CityTierConfig | null>(null);
  const [form,      setForm]      = useState<FormState>(EMPTY_FORM);

  const createAction = useAction(useCallback(
    (data: {
      city_name:string; tier:string; service_category:string; service_name:string;
      floor_price:number; min_price?:number; max_price?:number;
      default_estimate?:number; visit_fee?:number; bargain_floor?:number;
      provider_override_allowed:boolean; notes?:string;
    }) => pricingApi.createCityTier(data), []));

  const updateAction = useAction(useCallback(
    (id: string, data: Partial<{
      floor_price:number; min_price:number|null; max_price:number|null;
      default_estimate:number|null; visit_fee:number|null; bargain_floor:number|null;
      provider_override_allowed:boolean; is_active:boolean; notes:string;
    }>) => pricingApi.updateCityTier(id, data), []));

  const deactivateAction = useAction(useCallback((id: string) => pricingApi.deleteCityTier(id), []));

  function openCreate() { setEditing(null); setForm(EMPTY_FORM); setModalOpen(true); }
  function openEdit(c: CityTierConfig) {
    setEditing(c);
    setForm({
      city_name: c.city_name, tier: c.tier, service_category: c.service_category,
      service_name: (c as unknown as {service_name?:string}).service_name ?? "",
      floor_price: String(c.floor_price),
      min_price: String((c as unknown as {min_price?:number}).min_price ?? ""),
      max_price: String((c as unknown as {max_price?:number}).max_price ?? ""),
      default_estimate: String((c as unknown as {default_estimate?:number}).default_estimate ?? ""),
      visit_fee: String((c as unknown as {visit_fee?:number}).visit_fee ?? ""),
      bargain_floor: String((c as unknown as {bargain_floor?:number}).bargain_floor ?? ""),
      provider_override_allowed: (c as unknown as {provider_override_allowed?:boolean}).provider_override_allowed ?? true,
      notes: c.notes ?? "", is_active: c.is_active,
    });
    setModalOpen(true);
  }

  const opt = (s: string): number | undefined => {
    const n = parseFloat(s);
    return Number.isNaN(n) ? undefined : n;
  };

  async function handleSave() {
    const floorPrice = parseFloat(form.floor_price);
    if (Number.isNaN(floorPrice)) return;

    const res = editing
      ? await updateAction.execute(editing.id, {
          floor_price: floorPrice,
          min_price: opt(form.min_price) ?? null,
          max_price: opt(form.max_price) ?? null,
          default_estimate: opt(form.default_estimate) ?? null,
          visit_fee: opt(form.visit_fee) ?? null,
          bargain_floor: opt(form.bargain_floor) ?? null,
          provider_override_allowed: form.provider_override_allowed,
          is_active: form.is_active,
          notes: form.notes,
        })
      : await createAction.execute({
          city_name: form.city_name, tier: form.tier,
          service_category: form.service_category,
          service_name: form.service_name.trim(),
          floor_price: floorPrice,
          min_price: opt(form.min_price),
          max_price: opt(form.max_price),
          default_estimate: opt(form.default_estimate),
          visit_fee: opt(form.visit_fee),
          bargain_floor: opt(form.bargain_floor),
          provider_override_allowed: form.provider_override_allowed,
          notes: form.notes || undefined,
        });
    if (res) { configs.refetch(); setModalOpen(false); }
  }

  async function handleDeactivate(id: string) {
    const res = await deactivateAction.execute(id);
    if (res !== null) configs.refetch();
  }

  const action = editing ? updateAction : createAction;
  const rows   = configs.data?.configs ?? [];

  const columns = [
    { key:"city_name", label:"City", render:(_:unknown,row:CityTierConfig) => (
      <span style={{ fontWeight:600 }}>{row.city_name}</span>
    )},
    { key:"tier", label:"Tier", width:130, render:(_:unknown,row:CityTierConfig) => {
      const tierDef = (tiersData.data?.tiers ?? []).find(t => t.code === row.tier);
      return <Badge variant={TIER_BADGE_FALLBACK}>{tierDef?.name ?? row.tier.replace(/_/g," ")}</Badge>;
    }},
    { key:"service_category", label:"Category", render:(_:unknown,row:CityTierConfig) => (
      <div>
        <span>{row.service_category.replace(/_/g," ")}</span>
        {(row as unknown as {service_name?:string}).service_name && (
          <p style={{ margin:"2px 0 0", fontSize:11, color:"var(--brand)" }}>
            {(row as unknown as {service_name:string}).service_name}
          </p>
        )}
      </div>
    )},
    { key:"floor_price", label:"Min Allowed Price", width:160, render:(_:unknown,row:CityTierConfig) => (
      <div>
        <span style={{ fontWeight:700 }}>₹{row.floor_price.toLocaleString("en-IN")}</span>
        {(row as unknown as {min_price?:number}).min_price != null && (
          <p style={{ margin:"2px 0 0", fontSize:11, color:"var(--text-secondary)" }}>
            ₹{(row as unknown as {min_price:number}).min_price.toLocaleString("en-IN")} – ₹{((row as unknown as {max_price?:number}).max_price ?? 0).toLocaleString("en-IN")}
          </p>
        )}
      </div>
    )},
    { key:"is_active", label:"Status", width:100, render:(_:unknown,row:CityTierConfig) => (
      <Badge variant={row.is_active ? "success" : "muted"}>{row.is_active ? "Active" : "Inactive"}</Badge>
    )},
    { key:"id", label:"", width:160, render:(_:unknown,row:CityTierConfig) => (
      <div style={{ display:"flex", gap:8 }} onClick={e => e.stopPropagation()}>
        <Btn variant="ghost" size="xs" onClick={() => openEdit(row)}>Edit</Btn>
        {row.is_active && (
          <Btn variant="ghost" size="xs" onClick={() => handleDeactivate(row.id)}>Deactivate</Btn>
        )}
      </div>
    )},
  ];

  return (
    <AdminLayout activeNav="pricing">
      <SectionHeader
        title="Pricing Rules"
        subtitle="Platform-wide category and service minimum prices — provider cannot price below the Minimum Allowed Price"
        actions={<Btn variant="primary" size="sm" onClick={openCreate}>+ New Pricing Rule</Btn>}
      />

      <Card padding={12} style={{ marginBottom:16, background:"var(--surface-sunken)", border:"1px solid var(--border)" }}>
        <p style={{ fontSize:12, color:"var(--text-secondary)", margin:0 }}>
          <strong>Minimum Allowed Price</strong> is a platform floor that applies to all services in that category (category-wide fallback).{" "}
          Set a <strong>Service Name</strong> to create a service-specific rule that overrides the category default.{" "}
          Providers can optionally set their own price within Min–Max range when Provider Override is enabled.
        </p>
      </Card>

      <Card padding={16} style={{ marginBottom:16 }}>
        <div style={{ display:"flex", gap:12, flexWrap:"wrap" }}>
          <div style={{ minWidth:200 }}>
            <Select label="" value={tierFilter} onChange={setTierFilter} placeholder="All tiers" options={TIERS}/>
          </div>
          <div style={{ minWidth:200 }}>
            <Select label="" value={categoryFilter} onChange={setCategoryFilter} placeholder="All categories" options={CATEGORIES}/>
          </div>
          {(tierFilter || categoryFilter) && (
            <Btn variant="ghost" size="sm" onClick={() => { setTierFilter(""); setCategoryFilter(""); }}>
              Clear filters
            </Btn>
          )}
        </div>
      </Card>

      {configs.error && (
        <div style={{ padding:"12px 16px", borderRadius:10, background:"var(--danger-bg)",
          border:"1px solid var(--danger-border)", marginBottom:16 }}>
          <p style={{ fontSize:13, color:"var(--danger-text)", margin:0 }}>{configs.error}</p>
        </div>
      )}

      <DataTable
        columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
        rows={rows as unknown as Record<string, unknown>[]}
        loading={configs.loading}
        emptyText="No pricing rules match your filters."
      />

      <Modal open={modalOpen} onClose={() => setModalOpen(false)}
        title={editing ? `Edit: ${editing.city_name}` : "New Pricing Rule"}>
        <div style={{ display:"flex", flexDirection:"column", gap:14, maxHeight:"75vh", overflowY:"auto", paddingRight:4 }}>
          {action.error && (
            <div style={{ padding:"10px 14px", borderRadius:"var(--radius-md)", background:"var(--danger-bg)",
              border:"1px solid var(--danger-border)" }}>
              <p style={{ fontSize:13, color:"var(--danger-text)", margin:0 }}>{action.error}</p>
            </div>
          )}

          {/* Location */}
          <div style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>Location</div>
          <Input label="City Name *" placeholder="e.g. Mumbai" value={form.city_name}
            onChange={v => setForm(p => ({ ...p, city_name:v }))} disabled={!!editing}/>
          {!editing && (
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
              <Select label="Tier *" value={form.tier} onChange={v => setForm(p => ({ ...p, tier:v }))} options={TIERS}/>
              <Select label="Category *" value={form.service_category}
                onChange={v => setForm(p => ({ ...p, service_category:v }))} options={CATEGORIES}/>
            </div>
          )}
          {editing && (
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
              <div>
                <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)" }}>Tier</label>
                <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:"7px 0 0" }}>{form.tier.replace(/_/g," ")}</p>
              </div>
              <div>
                <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)" }}>Category</label>
                <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:"7px 0 0" }}>{form.service_category.replace(/_/g," ")}</p>
              </div>
            </div>
          )}

          {/* Service scope */}
          <div style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)", marginTop:4 }}>Service Scope</div>
          <Input
            label="Service Name (optional)"
            placeholder="Leave empty for category-wide fallback (e.g. AC Repair)"
            value={form.service_name}
            onChange={v => setForm(p => ({ ...p, service_name:v }))}
            disabled={!!editing}
            hint="Set this to create a service-specific rule. Empty = applies to all services in the category."
          />

          {/* Pricing */}
          <div style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)", marginTop:4 }}>Pricing</div>
          <div style={{ padding:"8px 12px", borderRadius:"var(--radius-md)", background:"var(--surface-sunken)",
            fontSize:12, color:"var(--text-secondary)" }}>
            <strong>Minimum Allowed Price</strong> is the hard floor — providers cannot price below this. This is the minimum price providers can charge for this category/service in this city tier.
          </div>
          <Input label="Minimum Allowed Price (₹) *" placeholder="e.g. 299" type="number"
            value={form.floor_price} onChange={v => setForm(p => ({ ...p, floor_price:v }))}/>

          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
            <Input label="Min Price ₹ (shown to customer)" type="number" placeholder="optional"
              value={form.min_price} onChange={v => setForm(p => ({ ...p, min_price:v }))}
              hint="Lower end of estimate range"/>
            <Input label="Max Price ₹ (shown to customer)" type="number" placeholder="optional"
              value={form.max_price} onChange={v => setForm(p => ({ ...p, max_price:v }))}
              hint="Upper end of estimate range"/>
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:12 }}>
            <Input label="Default Estimate ₹" type="number" placeholder="optional"
              value={form.default_estimate} onChange={v => setForm(p => ({ ...p, default_estimate:v }))}/>
            <Input label="Visit Fee ₹" type="number" placeholder="optional"
              value={form.visit_fee} onChange={v => setForm(p => ({ ...p, visit_fee:v }))}/>
            <Input label="Bargain Floor ₹" type="number" placeholder="optional"
              value={form.bargain_floor} onChange={v => setForm(p => ({ ...p, bargain_floor:v }))}
              hint="Minimum after customer negotiation"/>
          </div>

          {/* Flags */}
          <div style={{ display:"flex", gap:16, marginTop:4 }}>
            <label style={{ display:"flex", alignItems:"center", gap:6, fontSize:13, cursor:"pointer" }}>
              <input type="checkbox" checked={form.provider_override_allowed}
                onChange={e => setForm(p => ({ ...p, provider_override_allowed:e.target.checked }))}/>
              Provider Can Override Price
            </label>
            {editing && (
              <label style={{ display:"flex", alignItems:"center", gap:6, fontSize:13, cursor:"pointer" }}>
                <input type="checkbox" checked={form.is_active}
                  onChange={e => setForm(p => ({ ...p, is_active:e.target.checked }))}/>
                Active
              </label>
            )}
          </div>

          <Input label="Notes" placeholder="Optional context for this config..."
            value={form.notes} onChange={v => setForm(p => ({ ...p, notes:v }))}/>

          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="secondary" size="sm" onClick={() => setModalOpen(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={action.loading}
              disabled={!form.city_name || !form.floor_price} onClick={handleSave}>
              {editing ? "Save Changes" : "Create Rule"}
            </Btn>
          </div>
        </div>
      </Modal>
    </AdminLayout>
  );
}
