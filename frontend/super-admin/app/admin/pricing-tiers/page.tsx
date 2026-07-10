"use client";
import { useCallback, useState, Suspense } from "react";
import { useRouter } from "next/navigation";
import { Layers, RefreshCw, Download, Filter, Search } from "lucide-react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader } from "../../../components/shared/ui";
import { SummaryCardsRow } from "../../../components/pricing/SummaryCard";
import { ActionMenu } from "../../../components/pricing/ActionMenu";
import { catalogApi } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import type { PricingTier } from "../../../lib/api";

const TIER_TYPES = [
  { value:"metro",        label:"Metro"        },
  { value:"large_city",   label:"Large City"   },
  { value:"mid_city",     label:"Mid City"     },
  { value:"small_city",   label:"Small City"   },
  { value:"rural",        label:"Rural"        },
  { value:"premium_zone", label:"Premium Zone" },
];
const TRI_STATE = [
  { value:"",     label:"Any"  },
  { value:"yes",  label:"Yes"  },
  { value:"no",   label:"No"   },
];
function triToBool(v: string): boolean | undefined {
  return v === "yes" ? true : v === "no" ? false : undefined;
}

function PricingTiersInner() {
  const router = useRouter();

  const [search,      setSearch]      = useState("");
  const [typeFilter,  setTypeFilter]  = useState("");
  const [statusFilter,setStatusFilter]= useState("");
  const [advOpen,     setAdvOpen]     = useState(false);
  const [usedInRules, setUsedInRules] = useState("");
  const [hasCity,     setHasCity]     = useState("");
  const [hasZip,      setHasZip]      = useState("");

  const summary = useApi(useCallback(() => catalogApi.getTiersSummary(), []));
  const tiers = useApi(useCallback(() => catalogApi.listTiers(
    statusFilter === "" ? undefined : statusFilter === "active",
    {
      q: search || undefined,
      usedInRules: triToBool(usedInRules),
      hasCityMapping: triToBool(hasCity),
      hasZipcodeMapping: triToBool(hasZip),
    },
  ), [search, statusFilter, usedInRules, hasCity, hasZip]));

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<PricingTier | null>(null);
  const [form, setForm] = useState({
    name:"", code:"", tier_type:"mid_city", description:"",
    base_multiplier:"1.0", platform_fee_percent:"0",
    default_commission_percent:"0", default_sla_minutes:"60",
  });
  function F(patch: Partial<typeof form>) { setForm(p => ({ ...p, ...patch })); }

  const createAction  = useAction(useCallback((d: Record<string,unknown>) => catalogApi.createTier(d as never), []));
  const updateAction  = useAction(useCallback((id:string, d: Record<string,unknown>) => catalogApi.updateTier(id, d), []));
  const deleteAction  = useAction(useCallback((id:string) => catalogApi.deleteTier(id), []));
  const hardDelAction = useAction(useCallback((id:string) => catalogApi.hardDeleteTier(id), []));

  function openCreate() {
    setEditing(null);
    setForm({ name:"", code:"", tier_type:"mid_city", description:"",
      base_multiplier:"1.0", platform_fee_percent:"0", default_commission_percent:"0", default_sla_minutes:"60" });
    setModalOpen(true);
  }
  function openEdit(t: PricingTier) {
    setEditing(t);
    setForm({ name:t.name, code:t.code, tier_type:t.tier_type, description:t.description ?? "",
      base_multiplier:String(t.base_multiplier), platform_fee_percent:String(t.platform_fee_percent),
      default_commission_percent:String(t.default_commission_percent), default_sla_minutes:String(t.default_sla_minutes) });
    setModalOpen(true);
  }
  async function handleSave() {
    const payload = { name:form.name, description:form.description || undefined,
      base_multiplier:parseFloat(form.base_multiplier)||1,
      platform_fee_percent:parseFloat(form.platform_fee_percent)||0,
      default_commission_percent:parseFloat(form.default_commission_percent)||0,
      default_sla_minutes:parseInt(form.default_sla_minutes)||60,
      ...(editing ? {} : { code:form.code, tier_type:form.tier_type }) };
    const res = editing ? await updateAction.execute(editing.tier_id, payload) : await createAction.execute(payload);
    if (res) { tiers.refetch(); summary.refetch(); setModalOpen(false); }
  }
  async function handleToggleActive(t: PricingTier) {
    if (t.is_active) {
      if (!confirm("Deactivate this tier? Existing location mappings will still reference it.")) return;
      const res = await deleteAction.execute(t.tier_id); if (res !== null) { tiers.refetch(); summary.refetch(); }
    } else {
      const res = await updateAction.execute(t.tier_id, { is_active: true }); if (res) { tiers.refetch(); summary.refetch(); }
    }
  }
  async function handleArchive(id:string) {
    if (!confirm("Permanently delete this tier? This cannot be undone.")) return;
    const res = await hardDelAction.execute(id); if (res) { tiers.refetch(); summary.refetch(); }
  }
  async function handleExport() {
    const res = await catalogApi.exportTiers(statusFilter === "" ? undefined : statusFilter === "active");
    const header = "name,code,tier_type,base_multiplier,platform_fee_percent,default_sla_minutes,is_active\n";
    const body = res.rows.map(r => [r.name, r.code, r.tier_type, r.base_multiplier, r.platform_fee_percent, r.default_sla_minutes, r.is_active].join(",")).join("\n");
    const blob = new Blob([header + body], { type:"text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "pricing_tiers.csv"; a.click();
    URL.revokeObjectURL(url);
  }

  const rows = tiers.data?.tiers ?? [];
  const s = summary.data;
  const columns = [
    { key:"name", label:"Tier", render:(_:unknown,row:PricingTier) => (
      <div>
        <div style={{ fontWeight:600 }}>{row.name}</div>
        <div style={{ fontSize:11, color:"var(--text-tertiary)", fontFamily:"monospace" }}>{row.code}</div>
      </div>
    )},
    { key:"tier_type", label:"Type", width:120, render:(_:unknown,row:PricingTier) => (
      <span style={{ textTransform:"capitalize" }}>{row.tier_type.replace(/_/g," ")}</span>
    )},
    { key:"base_multiplier", label:"Multiplier", width:100 },
    { key:"platform_fee_percent", label:"Platform Fee", width:110, render:(_:unknown,row:PricingTier) => `${row.platform_fee_percent}%` },
    { key:"default_sla_minutes", label:"Default SLA", width:110, render:(_:unknown,row:PricingTier) => `${row.default_sla_minutes} min` },
    { key:"mapped_locations", label:"Mapped Locations", width:190, render:(_:unknown,row:PricingTier) => {
      const c = row.linked_counts;
      return c ? (
        <span style={{ fontSize:12 }}>Cities: {c.cities} / Zipcodes: {c.zipcodes} / Zones: {c.zones}</span>
      ) : "—";
    }},
    { key:"pricing_rules_count", label:"Pricing Rules", width:130, render:(_:unknown,row:PricingTier) => {
      const c = row.linked_counts;
      return c ? <span style={{ fontSize:12 }}>Rules: {c.rules_total} / Active: {c.rules_active}</span> : "—";
    }},
    { key:"is_active", label:"Status", width:90, render:(_:unknown,row:PricingTier) => (
      <Badge variant={row.is_active ? "success" : "muted"}>{row.is_active ? "Active" : "Inactive"}</Badge>
    )},
    { key:"created_at", label:"Updated", width:120, render:(_:unknown,row:PricingTier) =>
      row.created_at ? new Date(row.created_at).toLocaleDateString() : "—" },
    { key:"tier_id", label:"", width:110, render:(_:unknown,row:PricingTier) => (
      <ActionMenu items={[
        { label:"View Details", onClick:() => router.push(`/admin/pricing/tiers/${row.tier_id}`) },
        { label:"Edit Tier", onClick:() => openEdit(row) },
        { label:"View Mapped Locations", onClick:() => router.push(`/admin/location-mapping?tier_id=${row.tier_id}`) },
        { label:"View Pricing Rules", onClick:() => router.push(`/admin/pricing-rules?tier_id=${row.tier_id}`) },
        { label: row.is_active ? "Deactivate" : "Activate", onClick:() => handleToggleActive(row) },
        !row.is_active && { label:"Archive (Permanent Delete)", onClick:() => handleArchive(row.tier_id), destructive:true },
        { label:"Audit Logs", onClick:() => router.push(`/admin/pricing/tiers/${row.tier_id}#audit`) },
      ]}/>
    )},
  ];

  return (
    <AdminLayout activeNav="pricing-tiers">
      <SectionHeader
        title="Pricing Tiers"
        subtitle="Define platform pricing tiers used by city, zipcode, zone, SLA, and service price rules."/>
      <div style={{ padding:"0 28px 32px" }}>
        {s && (
          <SummaryCardsRow cards={[
            { label:"Total Tiers", value:s.total_tiers },
            { label:"Active Tiers", value:s.active_tiers },
            { label:"Mapped Cities", value:s.mapped_cities },
            { label:"Mapped Zipcodes", value:s.mapped_zipcodes },
            { label:"Rules Using Tiers", value:s.rules_using_tiers },
            { label:"Unmapped Tiers", value:s.unmapped_tiers, accent: s.unmapped_tiers > 0 },
          ]}/>
        )}

        <Card padding={16}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:16, flexWrap:"wrap", gap:10 }}>
            <div style={{ display:"flex", alignItems:"center", gap:10 }}>
              <Layers size={18} color="var(--brand)"/>
              <span style={{ fontWeight:700, fontSize:15 }}>Pricing Tiers</span>
              <Badge variant="muted">{rows.length}</Badge>
            </div>
            <div style={{ display:"flex", gap:8 }}>
              <Btn variant="secondary" size="sm" icon={<RefreshCw size={13}/>} onClick={() => { tiers.refetch(); summary.refetch(); }}>Refresh</Btn>
              <Btn variant="secondary" size="sm" icon={<Download size={13}/>} onClick={handleExport}>Export</Btn>
              <Btn variant="primary" size="sm" onClick={openCreate}>+ New Tier</Btn>
            </div>
          </div>

          <div style={{ display:"grid", gridTemplateColumns:"1fr 160px 130px auto", gap:10, marginBottom:12 }}>
            <div style={{ position:"relative" }}>
              <Search size={14} style={{ position:"absolute", left:10, top:"50%", transform:"translateY(-50%)", color:"var(--text-tertiary)", pointerEvents:"none" }}/>
              <input placeholder="Search tier name / code…" value={search} onChange={e => setSearch(e.target.value)}
                style={{ width:"100%", height:34, paddingLeft:32, paddingRight:12, fontSize:13, borderRadius:8,
                  border:"1px solid var(--border)", background:"var(--surface)", color:"var(--text-primary)",
                  outline:"none", fontFamily:"inherit", boxSizing:"border-box" }}/>
            </div>
            <Select label="" value={typeFilter} onChange={setTypeFilter} placeholder="All types"
              options={[{ value:"", label:"All types" }, ...TIER_TYPES]}/>
            <Select label="" value={statusFilter} onChange={setStatusFilter} placeholder="All statuses"
              options={[{ value:"", label:"All statuses" }, { value:"active", label:"Active" }, { value:"inactive", label:"Inactive" }]}/>
            <Btn variant="secondary" size="sm" icon={<Filter size={13}/>} onClick={() => setAdvOpen(o => !o)}>
              Advanced Filters
            </Btn>
          </div>

          {advOpen && (
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:10, marginBottom:16, padding:12, background:"var(--surface-sunken)", borderRadius:8 }}>
              <Select label="Used In Rules" value={usedInRules} onChange={setUsedInRules} options={TRI_STATE}/>
              <Select label="Has City Mapping" value={hasCity} onChange={setHasCity} options={TRI_STATE}/>
              <Select label="Has Zipcode Mapping" value={hasZip} onChange={setHasZip} options={TRI_STATE}/>
            </div>
          )}

          {(createAction.error || updateAction.error || deleteAction.error || hardDelAction.error) && (
            <p style={{ color:"var(--danger-text)", fontSize:13 }}>
              {createAction.error || updateAction.error || deleteAction.error || hardDelAction.error}
            </p>
          )}
          <DataTable
            columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
            rows={(typeFilter ? rows.filter(r => r.tier_type === typeFilter) : rows) as unknown as Record<string,unknown>[]}
            loading={tiers.loading}
            emptyText="No pricing tiers yet. Create your first tier to start mapping cities."/>
        </Card>

        <Modal open={modalOpen} onClose={() => setModalOpen(false)}
          title={editing ? `Edit Tier: ${editing.name}` : "New Pricing Tier"}>
          <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
            {(createAction.error || updateAction.error) && (
              <p style={{ color:"var(--danger-text)", fontSize:13 }}>{createAction.error || updateAction.error}</p>
            )}
            <Input label="Tier Name *" placeholder="e.g. Metro Tier" value={form.name} onChange={v => F({ name:v })}/>
            {!editing && (
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
                <Input label="Code *" placeholder="e.g. METRO" value={form.code} onChange={v => F({ code:v })}/>
                <Select label="Tier Type *" value={form.tier_type} onChange={v => F({ tier_type:v })} options={TIER_TYPES}/>
              </div>
            )}
            <Input label="Description" placeholder="Optional description" value={form.description} onChange={v => F({ description:v })}/>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
              <Input label="Base Multiplier" type="number" placeholder="1.0" value={form.base_multiplier} onChange={v => F({ base_multiplier:v })}
                hint="Price multiplier vs. base pricing rule (1.0 = no change)"/>
              <Input label="Platform Fee %" type="number" placeholder="0" value={form.platform_fee_percent} onChange={v => F({ platform_fee_percent:v })}/>
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
              <Input label="Default Commission % (legacy)" type="number" value={form.default_commission_percent} onChange={() => {}} disabled
                hint="Legacy/default only. Commission is managed in Finance → Commission Rules."/>
              <Input label="SLA Minutes" type="number" placeholder="60" value={form.default_sla_minutes} onChange={v => F({ default_sla_minutes:v })}/>
            </div>
            <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
              <Btn variant="secondary" size="sm" onClick={() => setModalOpen(false)}>Cancel</Btn>
              <Btn variant="primary" size="sm" loading={createAction.loading || updateAction.loading}
                disabled={!form.name || (!editing && !form.code)} onClick={handleSave}>
                {editing ? "Save Changes" : "Create Tier"}
              </Btn>
            </div>
          </div>
        </Modal>
      </div>
    </AdminLayout>
  );
}

export default function PricingTiersPage() {
  return (
    <Suspense fallback={<div style={{ padding:40 }}>Loading…</div>}>
      <PricingTiersInner/>
    </Suspense>
  );
}
