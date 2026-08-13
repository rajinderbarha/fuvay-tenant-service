"use client";
import React, { useCallback, useState, useEffect, useMemo } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import HomeServicesCatalogNav from "../../../components/catalog/HomeServicesCatalogNav";
import {
  Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader, Skeleton, EmptyState, SummaryCard,} from "../../../components/shared/ui";
import { IconPicker } from "../../../components/shared/IconPicker";
import { catalogApi, typesApi } from "../../../lib/api";
import type {
  ServiceTypeMaster, ServiceTypeSummary, BrandMasterSummary,
  ServiceTypeMapRecord, BrandMapRecord, Brand34D, BrandRequest34D,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { Plus, RefreshCw, Download, Search, ChevronDown, X, Info, Map } from "lucide-react";

// ── Multi-select checkbox list (categories / service groups) ─────────────────
// Shared by the Type and Brand mapping modals below -- lets an admin pick
// several categories (used purely to filter the group list) and several
// service groups at once, creating one mapping row per selected group in a
// single submit instead of repeating the form N times.
function MultiCheckList({ label, options, selected, onToggle, emptyText = "None available" }: {
  label: string; options: { value: string; label: string }[];
  selected: string[]; onToggle: (v: string) => void; emptyText?: string;
}) {
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
      <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>{label}</label>
      <div style={{ display:"flex", flexDirection:"column", gap:4, maxHeight:160, overflowY:"auto",
        border:"1px solid var(--border)", borderRadius:"var(--radius-md)", padding:8 }}>
        {options.length === 0
          ? <span style={{ fontSize:12, color:"var(--text-tertiary)" }}>{emptyText}</span>
          : options.map(o => (
            <label key={o.value} style={{ display:"flex", alignItems:"center", gap:8, fontSize:13, cursor:"pointer" }}>
              <input type="checkbox" checked={selected.includes(o.value)} onChange={() => onToggle(o.value)} />
              {o.label}
            </label>
          ))}
      </div>
    </div>
  );
}

function toggleInList(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter(v => v !== value) : [...list, value];
}

// Mirrors the backend's own _slugify (admin_catalog/types_service.py) so the
// slug shown while typing matches what will actually be saved -- the
// backend already auto-generates a slug from name when none is sent, but
// the form always sent whatever the (previously blank, manually-typed)
// slug field held, which was confusing UX ("why do I have to fill this in
// myself"). Still editable by hand after that -- auto-fill stops once the
// user types into Slug directly.
function slugify(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

// ── Constants ────────────────────────────────────────────────────────────────
const TYPE_FAMILIES = [
  { value:"",              label:"All Families" },
  { value:"appliance_type", label:"Appliance Type" },
  { value:"home_size",      label:"Home Size" },
  { value:"vehicle_type",   label:"Vehicle Type" },
  { value:"fuel_type",      label:"Fuel Type" },
  { value:"property_type",  label:"Property Type" },
  { value:"custom",         label:"Custom" },
];

const STATUS_OPTIONS = [
  { value:"",         label:"All Status" },
  { value:"active",   label:"Active" },
  { value:"inactive", label:"Inactive" },
  { value:"archived", label:"Archived" },
];

type Tab = "types" | "brands" | "brand-requests" | "type-mappings" | "brand-mappings";

// ── Root Page ────────────────────────────────────────────────────────────────
export default function TypesBrandsPage() {
  const [tab, setTab] = useState<Tab>("types");

  const tabs: { key: Tab; label: string }[] = [
    { key:"types",          label:"Service Types" },
    { key:"brands",         label:"Brands" },
    { key:"brand-requests", label:"Brand Requests" },
    { key:"type-mappings",  label:"Type Mappings" },
    { key:"brand-mappings", label:"Brand-Service Mapping" },
  ];

  return (
    <AdminLayout activeNav="types-brands">
      <SectionHeader
        title="Types & Brands"
        subtitle="Master data for service variants and product brands — create once, map across services."
      />
      <HomeServicesCatalogNav active="types-brands" />

      {/* Tab bar */}
      <div style={{ display:"flex", gap:4, marginBottom:20, borderBottom:"2px solid var(--border)", paddingBottom:0 }}>
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            padding:"10px 20px", border:"none", background:"none", cursor:"pointer",
            fontSize:13, fontWeight:600,
            color: tab === t.key ? "var(--accent)" : "var(--text-secondary)",
            borderBottom: tab === t.key ? "2px solid var(--accent)" : "2px solid transparent",
            marginBottom:-2, transition:"all 0.15s",
          }}>{t.label}</button>
        ))}
      </div>

      {tab === "types"          && <ServiceTypesTab />}
      {tab === "brands"         && <BrandMasterTab />}
      {tab === "brand-requests" && <BrandRequestsTab />}
      {tab === "type-mappings"  && <TypeMappingsTab />}
      {tab === "brand-mappings" && <BrandMappingsTab />}
    </AdminLayout>
  );
}

// ── Shared SummaryCard ────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────────────
// SERVICE TYPES TAB
// ─────────────────────────────────────────────────────────────────────────────
function ServiceTypesTab() {
  const [q,        setQ]        = useState("");
  const [status,   setStatus]   = useState("");
  const [family,   setFamily]   = useState("");
  const [page,     setPage]     = useState(1);

  const [createOpen, setCreateOpen] = useState(false);
  const [editItem,   setEditItem]   = useState<ServiceTypeMaster | null>(null);
  const [detailItem, setDetailItem] = useState<ServiceTypeMaster | null>(null);

  const summaryRes = useApi(useCallback(() => typesApi.summary(), []), []);
  const listRes    = useApi(useCallback(
    () => typesApi.list({
      q: q || undefined, status: status || undefined,
      page, page_size: 50,
    }),
    [q, status, page],
  ), [q, status, page]);

  const activateAction   = useAction(useCallback((id:string) => typesApi.activate(id),   []));
  const deactivateAction = useAction(useCallback((id:string) => typesApi.deactivate(id), []));
  const archiveAction    = useAction(useCallback((id:string) => typesApi.archive(id),    []));

  async function doStatus(id:string, action:"activate"|"deactivate"|"archive") {
    if (action === "activate")   await activateAction.execute(id);
    if (action === "deactivate") await deactivateAction.execute(id);
    if (action === "archive")    await archiveAction.execute(id);
    listRes.refetch(); summaryRes.refetch();
  }

  const sum = summaryRes.data;

  const columns = [
    { key:"name",          label:"Type",            render:(_v:unknown, row:any) => (
      <div>
        <div style={{ fontWeight:600, fontSize:13 }}>{row.name}</div>
        <div style={{ fontSize:11, color:"var(--text-tertiary)" }}>{row.code ?? row.slug}</div>
      </div>
    )},
    { key:"type_family",   label:"Family",          render:(_v:unknown, row:any) => row.type_family
      ? <Badge variant="info">{row.type_family.replace(/_/g," ")}</Badge> : <span style={{color:"var(--text-tertiary)"}}>—</span> },
    { key:"categories",    label:"Mapped",          render:(_v:unknown, row:any) => (
      <div style={{ fontSize:12 }}>
        <span style={{ color:"var(--text-secondary)" }}>Cat: </span><strong>{row.category_count}</strong>
        {"  "}
        <span style={{ color:"var(--text-secondary)" }}>Svc: </span><strong>{row.service_count}</strong>
      </div>
    )},
    { key:"customer_visible", label:"Customer Visible", render:(_v:unknown, row:any) => (
      <Badge variant={row.customer_visible ? "success" : "default"}>{row.customer_visible ? "Yes" : "No"}</Badge>
    )},
    { key:"status",        label:"Status",          render:(_v:unknown, row:any) => (
      <Badge variant={row.status==="active"?"success":row.status==="inactive"?"warning":"default"}>
        {row.status}
      </Badge>
    )},
    { key:"updated_at",    label:"Updated",         render:(_v:unknown, row:any) => (
      <span style={{ fontSize:11, color:"var(--text-tertiary)" }}>
        {new Date(row.updated_at).toLocaleDateString("en-IN")}
      </span>
    )},
    { key:"actions",       label:"Actions",         render:(_v:unknown, row:any) => (
      <TypeActionMenu row={row}
        onView={() => {
          typesApi.get(row.type_id).then(r => setDetailItem(r));
        }}
        onEdit={() => setEditItem(row)}
        onActivate={() => doStatus(row.type_id, "activate")}
        onDeactivate={() => doStatus(row.type_id, "deactivate")}
        onArchive={() => doStatus(row.type_id, "archive")}
      />
    )},
  ];

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
      {/* Summary Cards */}
      <div style={{ display:"flex", gap:12, flexWrap:"wrap" }}>
        {summaryRes.loading
          ? [1,2,3,4,5,6].map(i => <Skeleton key={i} height={72} style={{ flex:"1 1 130px", minWidth:110, borderRadius:"var(--radius-lg)" }}/>)
          : <>
            <SummaryCard label="Total"             value={sum?.total ?? 0} accent />
            <SummaryCard label="Active"            value={sum?.active ?? 0} />
            <SummaryCard label="Inactive"          value={sum?.inactive ?? 0} />
            <SummaryCard label="Mapped"            value={sum?.mapped ?? 0} />
            <SummaryCard label="Unmapped"          value={sum?.unmapped ?? 0} />
            <SummaryCard label="Customer Visible"  value={sum?.customer_visible ?? 0} />
          </>
        }
      </div>

      {/* Toolbar */}
      <Card padding={16}>
        <div style={{ display:"flex", gap:10, flexWrap:"wrap", alignItems:"center" }}>
          <div style={{ position:"relative", flex:"1 1 220px" }}>
            <Search size={14} style={{ position:"absolute", left:10, top:"50%", transform:"translateY(-50%)", color:"var(--text-tertiary)" }}/>
            <input value={q} onChange={e=>{setQ(e.target.value);setPage(1);}}
              placeholder="Search name, code, slug…"
              style={{ width:"100%", paddingLeft:32, paddingRight:10, height:36, borderRadius:"var(--radius-md)",
                border:"1px solid var(--border)", background:"var(--input-bg)",
                color:"var(--text-primary)", fontSize:13, outline:"none", boxSizing:"border-box" }}/>
          </div>
          <select value={status} onChange={e=>{setStatus(e.target.value);setPage(1);}}
            style={{ height:36, borderRadius:"var(--radius-md)", border:"1px solid var(--border)", background:"var(--input-bg)",
              color:"var(--text-primary)", fontSize:13, padding:"0 10px" }}>
            {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          {/* Mapped/Unmapped filter dropdown removed 2026-08-05 at explicit
              user request -- the MAPPED column and the Mapped/Unmapped
              summary cards already convey this, and mapping is managed from
              the dedicated Type Mappings tab. */}
          <div style={{ marginLeft:"auto", display:"flex", gap:8 }}>
            <Btn variant="ghost" size="sm" onClick={() => { listRes.refetch(); summaryRes.refetch(); }}>
              <RefreshCw size={14}/>
            </Btn>
            <Btn variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
              <Plus size={14}/> New Type
            </Btn>
          </div>
        </div>
      </Card>

      {/* Table */}
      <Card padding={0}>
        {listRes.loading
          ? <div style={{ padding:32 }}><Skeleton height={200}/></div>
          : listRes.data?.types.length === 0
            ? <EmptyState title="No service types yet"
                description="Create reusable types to use across services. Examples: Split, Window, Front Load, 1 BHK."
                action={<Btn variant="primary" size="sm" onClick={() => setCreateOpen(true)}><Plus size={14}/> New Type</Btn>}/>
            : <DataTable columns={columns} rows={(listRes.data?.types ?? []) as unknown as Record<string, unknown>[]}/>
        }
        {/* Pagination */}
        {(listRes.data?.pages ?? 1) > 1 && (
          <div style={{ display:"flex", justifyContent:"center", gap:8, padding:16 }}>
            <Btn variant="ghost" size="sm" onClick={() => setPage(p=>Math.max(1,p-1))} disabled={page===1}>Prev</Btn>
            <span style={{ fontSize:12, color:"var(--text-secondary)", alignSelf:"center" }}>
              Page {page} / {listRes.data?.pages}
            </span>
            <Btn variant="ghost" size="sm" onClick={() => setPage(p=>p+1)} disabled={page>=(listRes.data?.pages??1)}>Next</Btn>
          </div>
        )}
      </Card>

      {/* Modals */}
      {createOpen && (
        <TypeFormModal title="New Service Type" onClose={() => setCreateOpen(false)}
          onSaved={() => { setCreateOpen(false); listRes.refetch(); summaryRes.refetch(); }}/>
      )}
      {editItem && (
        <TypeFormModal title="Edit Service Type" initial={editItem} onClose={() => setEditItem(null)}
          onSaved={() => { setEditItem(null); listRes.refetch(); summaryRes.refetch(); }}/>
      )}
      {detailItem && (
        <TypeDetailDrawer item={detailItem} onClose={() => setDetailItem(null)}/>
      )}
    </div>
  );
}

// ── Type Action Menu ──────────────────────────────────────────────────────────
// Mapping is managed exclusively from the dedicated "Type Mappings" tab now
// (explicit user request) -- this menu no longer has a "Manage Mappings"
// shortcut, so this tab is purely Type CRUD.
function TypeActionMenu({ row, onView, onEdit, onActivate, onDeactivate, onArchive }:
  { row:ServiceTypeMaster; onView():void; onEdit():void;
    onActivate():void; onDeactivate():void; onArchive():void }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ position:"relative" }}>
      <Btn variant="ghost" size="sm" onClick={() => setOpen(o=>!o)}>
        Actions <ChevronDown size={12}/>
      </Btn>
      {open && (
        <div onClick={e=>e.stopPropagation()} style={{
          position:"absolute", right:0, top:"calc(100% + 4px)", zIndex:1000,
          background:"var(--card-bg)", border:"1px solid var(--border)", borderRadius:10,
          boxShadow:"0 8px 24px rgba(0,0,0,0.12)", minWidth:160, overflow:"hidden",
        }}>
          {[
            { label:"View Details",   fn:() => { onView(); setOpen(false); } },
            { label:"Edit Type",      fn:() => { onEdit(); setOpen(false); } },
            row.status !== "active"   ? { label:"Activate",   fn:() => { onActivate(); setOpen(false); } } : null,
            row.status === "active"   ? { label:"Deactivate", fn:() => { onDeactivate(); setOpen(false); } } : null,
            row.status !== "archived" ? { label:"Archive",    fn:() => { onArchive(); setOpen(false); }, danger:true } : null,
          ].filter(Boolean).map((item:any) => (
            <button key={item.label} onClick={item.fn} style={{
              display:"block", width:"100%", textAlign:"left", padding:"9px 16px",
              background:"none", border:"none", cursor:"pointer", fontSize:13,
              color: item.danger ? "var(--danger-text)" : "var(--text-primary)",
              borderBottom:"1px solid var(--border)",
            }}>{item.label}</button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Type Form Modal ───────────────────────────────────────────────────────────
function TypeFormModal({ title, initial, onClose, onSaved }:
  { title:string; initial?:ServiceTypeMaster|null; onClose():void; onSaved():void }) {
  const [form, setForm] = useState({
    name:             initial?.name ?? "",
    code:             initial?.code ?? "",
    slug:             initial?.slug ?? "",
    description:      initial?.description ?? "",
    type_family:      initial?.type_family ?? "",
    customer_visible: initial?.customer_visible ?? true,
    status:           initial?.status ?? "active",
    display_order:    initial?.display_order ?? 0,
  });
  const [iconUrl, setIconUrl] = useState<string | null>(initial?.icon_url ?? null);
  // Only auto-fill slug for brand-new records, and only until the user
  // edits Slug by hand.
  const [slugTouched, setSlugTouched] = useState(!!initial?.slug);

  const createAction = useAction(useCallback((d:object) => typesApi.create(d), []));
  const updateAction = useAction(useCallback((d:object) =>
    typesApi.update(initial!.type_id, d), [initial]));

  async function handleSave() {
    const payload = { ...form, icon_url: iconUrl || undefined };
    const res = initial
      ? await updateAction.execute(payload)
      : await createAction.execute(payload);
    if (res) onSaved();
  }

  const F = (label:string, key:keyof typeof form, type:"text"|"textarea"|"number" = "text") => (
    <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
      <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>{label}</label>
      {type === "textarea"
        ? <textarea value={form[key] as string}
            onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))} rows={2}
            style={{ borderRadius:"var(--radius-md)", border:"1px solid var(--border)", background:"var(--input-bg)",
              color:"var(--text-primary)", fontSize:13, padding:"8px 10px", resize:"vertical" }}/>
        : <input type={type} value={form[key] as string|number}
            onChange={e => {
              const v = type === "number" ? +e.target.value : e.target.value;
              if (key === "slug") setSlugTouched(true);
              setForm(f => ({
                ...f, [key]: v,
                ...(key === "name" && !slugTouched ? { slug: slugify(String(v)) } : {}),
              }));
            }}
            style={{ height:36, borderRadius:"var(--radius-md)", border:"1px solid var(--border)", background:"var(--input-bg)",
              color:"var(--text-primary)", fontSize:13, padding:"0 10px" }}/>
      }
    </div>
  );

  const err = createAction.error ?? updateAction.error;
  const loading = createAction.loading || updateAction.loading;

  return (
    <Modal open title={title} onClose={onClose}>
      <div style={{ display:"flex", flexDirection:"column", gap:14, minWidth:360 }}>
        {err && <div style={{ padding:"8px 12px", borderRadius:"var(--radius-md)", background:"var(--danger-bg)",
          fontSize:12, color:"var(--danger-text)" }}>{err}</div>}
        {F("Name *", "name")}
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
          {F("Code", "code")}
          {F("Slug (auto-generated, editable)", "slug")}
        </div>
        {F("Description", "description", "textarea")}
        <IconPicker label="Icon" context="service_icon" value={iconUrl} onChange={setIconUrl}/>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
          <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
            <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>Type Family</label>
            <select value={form.type_family} onChange={e=>setForm(f=>({...f,type_family:e.target.value}))}
              style={{ height:36, borderRadius:"var(--radius-md)", border:"1px solid var(--border)", background:"var(--input-bg)",
                color:"var(--text-primary)", fontSize:13, padding:"0 10px" }}>
              {TYPE_FAMILIES.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
            <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>Status</label>
            <select value={form.status} onChange={e=>setForm(f=>({...f,status:e.target.value}))}
              style={{ height:36, borderRadius:"var(--radius-md)", border:"1px solid var(--border)", background:"var(--input-bg)",
                color:"var(--text-primary)", fontSize:13, padding:"0 10px" }}>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <input type="checkbox" id="cv" checked={form.customer_visible}
            onChange={e=>setForm(f=>({...f,customer_visible:e.target.checked}))}/>
          <label htmlFor="cv" style={{ fontSize:13, cursor:"pointer" }}>Customer Visible</label>
        </div>
        {F("Display Order", "display_order", "number")}
        <div style={{ display:"flex", gap:10, justifyContent:"flex-end", paddingTop:4 }}>
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" loading={loading} onClick={handleSave}>
            {initial ? "Save Changes" : "Create Type"}
          </Btn>
        </div>
      </div>
    </Modal>
  );
}

// ── Type Detail Drawer ────────────────────────────────────────────────────────
function TypeDetailDrawer({ item, onClose }: { item:ServiceTypeMaster; onClose():void }) {
  const rows: [string, string][] = [
    ["Name",             item.name],
    ["Code",             item.code ?? "—"],
    ["Slug",             item.slug],
    ["Description",      item.description ?? "—"],
    ["Type Family",      item.type_family?.replace(/_/g," ") ?? "—"],
    ["Customer Visible", item.customer_visible ? "Yes" : "No"],
    ["Status",           item.status],
    ["Display Order",    String(item.display_order)],
    ["Mapped Categories",String(item.category_count)],
    ["Mapped Services",  String(item.service_count)],
    ["Created",          new Date(item.created_at).toLocaleString("en-IN")],
    ["Updated",          new Date(item.updated_at).toLocaleString("en-IN")],
  ];

  return (
    <Modal open title={`Type: ${item.name}`} onClose={onClose}>
      <div style={{ minWidth:360 }}>
        {rows.map(([label, val]) => (
          <div key={label} style={{ display:"flex", gap:12, padding:"8px 0",
            borderBottom:"1px solid var(--border)" }}>
            <span style={{ fontSize:12, color:"var(--text-tertiary)", width:130, flexShrink:0 }}>{label}</span>
            <span style={{ fontSize:12, color:"var(--text-primary)", fontWeight:500 }}>{val}</span>
          </div>
        ))}
        {(item.mappings ?? []).length > 0 && (
          <div style={{ marginTop:16 }}>
            <div style={{ fontSize:12, fontWeight:600, color:"var(--text-tertiary)",
              textTransform:"uppercase", letterSpacing:"0.05em", marginBottom:8 }}>Mappings</div>
            {(item.mappings ?? []).map(m => (
              <div key={m.mapping_id} style={{ fontSize:12, padding:"5px 0",
                borderBottom:"1px solid var(--border)", color:"var(--text-secondary)" }}>
                {m.category_name ?? m.category_id ?? "—"}
                {m.service_name ? ` → ${m.service_name}` : ""}
                <span style={{ marginLeft:8 }}><Badge variant={m.status==="active"?"success":"default"}>{m.status}</Badge></span>
              </div>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}

// ── Add Type Mapping Modal ────────────────────────────────────────────────────
function AddTypeMappingModal({ typeId, typeName, onClose, onSaved }:
  { typeId:string; typeName:string; onClose():void; onSaved():void }) {
  // A Type (e.g. "Split AC", "Window AC") belongs to a Service Group (e.g.
  // "AC Services"), not directly to the whole top-level Category (e.g. "Home
  // Services") -- ServiceTypeMapping.service_group_id is the real association
  // (backend already supports it; this form previously never exposed it and
  // forced category_id as the required field instead). Category is kept only
  // as a filter to narrow the Service Group list, matching how Service Group
  // itself is always scoped to exactly one category. Both are multi-select:
  // one submit creates one mapping row per selected service group.
  const [categoryIds,     setCategoryIds]     = useState<string[]>([]);
  const [serviceGroupIds, setServiceGroupIds] = useState<string[]>([]);
  const [serviceId,       setServiceId]       = useState("");
  const [custVis,         setCustVis]         = useState(true);

  const categories = useApi(useCallback(() => catalogApi.listCategories(true), []), []);
  const serviceGroups = useApi(useCallback(() => catalogApi.listServiceGroups(), []), []);
  const allGroups = serviceGroups.data?.groups ?? [];

  // Was previously a pure "add" form with no visibility into what this
  // type is already mapped to -- a user could only tell whether a mapping
  // "took" by counting rows on the outer list, and had no way to edit or
  // remove an existing one from here at all.
  const existing = useApi(useCallback(() => typesApi.listMappings({ type_id: typeId }), [typeId]), [typeId]);
  const removeAction = useAction(useCallback((mappingId: string) => typesApi.deleteMapping(mappingId), []));
  const mappedGroupIds = useMemo(() =>
    new Set((existing.data?.mappings ?? []).map(m => m.service_group_id).filter(Boolean) as string[]),
    [existing.data]);

  // Already-mapped groups are excluded here -- re-selecting one and
  // submitting again silently created a duplicate mapping row (visible only
  // as a Cat/Svc count bump on the outer list, easy to mistake for "nothing
  // happened"). Remove the existing mapping first (Currently Mapped, above)
  // if you need to change it.
  const visibleGroups = (categoryIds.length === 0
    ? allGroups : allGroups.filter(g => categoryIds.includes(g.category_id))
  ).filter(g => !mappedGroupIds.has(g.id));
  // "Service" filter only makes sense once exactly one group is selected.
  const singleGroupId = serviceGroupIds.length === 1 ? serviceGroupIds[0] : undefined;
  const services   = useApi(useCallback(
    () => singleGroupId ? catalogApi.listMasterServices(undefined, undefined, undefined, singleGroupId) : Promise.resolve({ services:[] }),
    [singleGroupId],
  ), [singleGroupId]);

  const catNameById = useMemo(() => {
    const m: Record<string,string> = {};
    (categories.data?.categories ?? []).forEach((c:any) => { m[c.category_id] = c.name; });
    return m;
  }, [categories.data]);
  const groupNameById = useMemo(() => {
    const m: Record<string,string> = {};
    allGroups.forEach(g => { m[g.id] = g.name; });
    return m;
  }, [allGroups]);

  const action = useAction(useCallback(async (groupIds: string[]) => {
    const results = await Promise.all(groupIds.map(gid => {
      const group = allGroups.find(g => g.id === gid);
      return typesApi.createMapping({
        type_id: typeId, service_group_id: gid,
        category_id: group?.category_id,
        service_id: groupIds.length === 1 ? (serviceId || undefined) : undefined,
        customer_visible: custVis,
      });
    }));
    return results;
  }, [typeId, serviceId, custVis, allGroups]));

  async function handleSave() {
    if (serviceGroupIds.length === 0) return;
    const res = await action.execute(serviceGroupIds);
    if (res) { setServiceGroupIds([]); setServiceId(""); existing.refetch(); onSaved(); }
  }

  async function handleRemove(mappingId: string) {
    const res = await removeAction.execute(mappingId);
    if (res) existing.refetch();
  }

  return (
    <Modal open title={`Map Type: ${typeName}`} onClose={onClose}>
      <div style={{ display:"flex", flexDirection:"column", gap:14, minWidth:320 }}>
        <div>
          <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>Currently Mapped</label>
          {existing.loading ? (
            <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"6px 0 0" }}>Loading…</p>
          ) : (existing.data?.mappings ?? []).length === 0 ? (
            <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"6px 0 0" }}>Not mapped to anything yet.</p>
          ) : (
            <div style={{ display:"flex", flexDirection:"column", gap:6, marginTop:6, maxHeight:160, overflowY:"auto" }}>
              {(existing.data?.mappings ?? []).map(m => (
                <div key={m.mapping_id} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                  padding:"6px 10px", borderRadius:"var(--radius-md)", background:"var(--surface-sunken)", fontSize:12 }}>
                  <span>
                    {m.service_group_id ? (groupNameById[m.service_group_id] ?? "Service group") : (m.category_id ? catNameById[m.category_id] ?? "Category" : "—")}
                    {m.service_id && " · specific service"}
                  </span>
                  <button onClick={() => handleRemove(m.mapping_id)} disabled={removeAction.loading}
                    style={{ background:"none", border:"none", color:"var(--danger-text)", cursor:"pointer", fontSize:12, padding:0 }}>
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
        <div style={{ borderTop:"1px solid var(--border)", paddingTop:12, fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>
          Add New Mapping
        </div>
        {action.error && <div style={{ padding:"8px 12px", borderRadius:"var(--radius-md)", background:"var(--danger-bg)",
          fontSize:12, color:"var(--danger-text)" }}>{action.error}</div>}
        <MultiCheckList label="Category (filter)" emptyText="No categories"
          options={(categories.data?.categories ?? []).map((c:any) => ({ value:c.category_id, label:c.name }))}
          selected={categoryIds}
          onToggle={v => { setCategoryIds(p => toggleInList(p, v)); setServiceGroupIds([]); setServiceId(""); }}/>
        <MultiCheckList label="Service Group *" emptyText="No service groups match the selected categories"
          options={visibleGroups.map(g => ({ value:g.id, label: categoryIds.length === 0 ? `${g.name} (${g.category_name})` : g.name }))}
          selected={serviceGroupIds}
          onToggle={v => { setServiceGroupIds(p => toggleInList(p, v)); setServiceId(""); }}/>
        <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
          <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>
            Service (optional{serviceGroupIds.length > 1 ? " — only when a single group is selected" : ""})
          </label>
          <select value={serviceId} onChange={e=>setServiceId(e.target.value)} disabled={!singleGroupId}
            style={{ height:36, borderRadius:"var(--radius-md)", border:"1px solid var(--border)", background:"var(--input-bg)",
              color:"var(--text-primary)", fontSize:13, padding:"0 10px",
              opacity: singleGroupId ? 1 : 0.5 }}>
            <option value="">All services in group</option>
            {(services.data?.services ?? []).map((s:any) =>
              <option key={s.service_id} value={s.service_id}>{s.name}</option>
            )}
          </select>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <input type="checkbox" id="cvm" checked={custVis} onChange={e=>setCustVis(e.target.checked)}/>
          <label htmlFor="cvm" style={{ fontSize:13, cursor:"pointer" }}>Customer Visible</label>
        </div>
        <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" loading={action.loading} onClick={handleSave}
            disabled={serviceGroupIds.length === 0}>
            Add Mapping{serviceGroupIds.length > 1 ? ` (${serviceGroupIds.length} groups)` : ""}
          </Btn>
        </div>
      </div>
    </Modal>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// BRAND REQUESTS TAB
// ─────────────────────────────────────────────────────────────────────────────
const REQUEST_STATUS_VARIANT: Record<string, "success" | "warning" | "muted" | "danger"> = {
  pending: "warning", approved: "success", rejected: "danger", merged: "muted",
};

function BrandRequestsTab() {
  const [statusFilter, setStatusFilter] = useState("pending");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [actionModal, setActionModal] = useState<{ type: "approve" | "reject" | "merge"; req: BrandRequest34D } | null>(null);
  const [adminNote, setAdminNote] = useState("");
  const [existingBrandId, setExistingBrandId] = useState("");
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  const notify = (msg: string, ok = true) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3500);
  };

  const requests = useApi(useCallback(
    () => catalogApi.listBrandRequests({ status: statusFilter || undefined, search: query || undefined, page, pageSize }),
    [statusFilter, query, page],
  ), [statusFilter, query, page]);

  const brands = useApi(useCallback(() => catalogApi.listBrands({ status: "active" }), []), []);

  const approveAction = useAction(async ({ id }: { id: string }) => {
    await catalogApi.approveBrandRequest(id, adminNote || undefined);
    requests.refetch(); setActionModal(null); setAdminNote(""); notify("Request approved.");
  });
  const rejectAction = useAction(async ({ id }: { id: string }) => {
    await catalogApi.rejectBrandRequest(id, adminNote || undefined);
    requests.refetch(); setActionModal(null); setAdminNote(""); notify("Request rejected.");
  });
  const mergeAction = useAction(async ({ id }: { id: string }) => {
    await catalogApi.mergeBrandRequest(id, existingBrandId, adminNote || undefined);
    requests.refetch(); setActionModal(null); setAdminNote(""); setExistingBrandId(""); notify("Brand request merged with existing brand.");
  });

  function openAction(type: "approve" | "reject" | "merge", req: BrandRequest34D) {
    setActionModal({ type, req }); setAdminNote(""); setExistingBrandId("");
  }

  const rows = requests.data?.requests ?? [];
  const activeBrands = brands.data?.brands ?? [];
  const modal = actionModal;
  const modalTitle = modal?.type === "approve" ? "Approve Request" : modal?.type === "reject" ? "Reject Request" : "Merge with Existing Brand";
  const currentAction = modal?.type === "approve" ? approveAction : modal?.type === "reject" ? rejectAction : mergeAction;

  const columns = [
    {
      key: "requested_brand_name", label: "Requested Brand",
      render: (_: unknown, row: BrandRequest34D) => (
        <div>
          <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{row.requested_brand_name}</span>
          {row.normalized_name && (
            <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-secondary)" }}>normalized: {row.normalized_name}</p>
          )}
        </div>
      ),
    },
    {
      key: "reason", label: "Reason",
      render: (_: unknown, row: BrandRequest34D) => (
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{row.reason || "—"}</span>
      ),
    },
    {
      key: "status", label: "Status", width: 110,
      render: (_: unknown, row: BrandRequest34D) => (
        <Badge variant={REQUEST_STATUS_VARIANT[row.status] ?? "muted"}>{row.status}</Badge>
      ),
    },
    {
      key: "created_at", label: "Created", width: 120,
      render: (_: unknown, row: BrandRequest34D) => (
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
          {row.created_at ? new Date(row.created_at).toLocaleDateString() : "—"}
        </span>
      ),
    },
    {
      key: "request_id", label: "Actions", width: 260,
      render: (_: unknown, row: BrandRequest34D) => row.status === "pending" ? (
        <div style={{ display: "flex", gap: 6 }} onClick={e => e.stopPropagation()}>
          <Btn variant="primary" size="xs" onClick={() => openAction("approve", row)}>Approve</Btn>
          <Btn variant="secondary" size="xs" onClick={() => openAction("merge", row)}>Merge Existing</Btn>
          <Btn variant="danger" size="xs" onClick={() => openAction("reject", row)}>Reject</Btn>
        </div>
      ) : (
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
          {row.reviewed_at ? `Reviewed ${new Date(row.reviewed_at).toLocaleDateString()}` : "—"}
        </span>
      ),
    },
  ];

  return (
    <div>
      {toast && (
        <div style={{
          position: "fixed", top: 16, right: 16, zIndex: 9999, padding: "10px 18px",
          borderRadius: 10, background: toast.ok ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.ok ? "var(--success-text)" : "var(--danger-text)", fontSize: 13,
        }}>{toast.msg}</div>
      )}

      <div style={{ display: "flex", gap: 8, marginBottom: 16, justifyContent: "space-between" }}>
        <div style={{ display: "flex", gap: 8 }}>
          {[
            { value: "pending", label: "Pending" },
            { value: "approved", label: "Approved" },
            { value: "merged", label: "Merged" },
            { value: "rejected", label: "Rejected" },
            { value: "", label: "All" },
          ].map(opt => (
            <button key={opt.value} onClick={() => { setStatusFilter(opt.value); setPage(1); }} style={{
              padding: "6px 14px", borderRadius: 20, fontSize: 13, fontWeight: 500,
              border: `1px solid ${statusFilter === opt.value ? "var(--brand, #1a56db)" : "var(--border)"}`,
              background: statusFilter === opt.value ? "var(--brand-muted, rgba(26,86,219,.08))" : "var(--surface)",
              color: statusFilter === opt.value ? "var(--brand, #1a56db)" : "var(--text-secondary)",
              cursor: "pointer",
            }}>{opt.label}</button>
          ))}
        </div>
        <Btn variant="secondary" size="sm" onClick={() => requests.refetch()}>
          <RefreshCw size={14} style={{ marginRight: 4 }} /> Refresh
        </Btn>
      </div>

      <Card padding={14} style={{ marginBottom: 14 }}>
        <div style={{ position: "relative" }}>
          <Search size={14} style={{ position: "absolute", left: 11, top: 10, color: "var(--text-tertiary)" }}/>
          <input value={query} onChange={e => { setQuery(e.target.value); setPage(1); }}
            aria-label="Search brand requests" placeholder="Search requested brand, normalized name, or reason…"
            style={{ width: "100%", height: 36, boxSizing: "border-box", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--input-bg)", color: "var(--text-primary)", fontSize: 13, padding: "0 10px 0 34px" }}/>
        </div>
      </Card>

      <DataTable
        columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
        rows={rows as unknown as Record<string, unknown>[]}
        loading={requests.loading}
        emptyText="No brand requests found for this status."
      />
      {(requests.data?.pages ?? 1) > 1 && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14 }}>
          <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{requests.data?.total ?? 0} requests</span>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <Btn size="sm" variant="secondary" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</Btn>
            <Badge variant="muted">Page {page} of {requests.data?.pages ?? 1}</Badge>
            <Btn size="sm" variant="secondary" disabled={page >= (requests.data?.pages ?? 1)} onClick={() => setPage(p => p + 1)}>Next</Btn>
          </div>
        </div>
      )}

      <Modal open={!!modal} onClose={() => setActionModal(null)} title={modalTitle}>
        {modal && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
              Brand: <strong style={{ color: "var(--text-primary)" }}>{modal.req.requested_brand_name}</strong>
            </p>

            {modal.type === "merge" && (
              <Select label="Merge into existing brand *" value={existingBrandId}
                onChange={setExistingBrandId} placeholder="Select existing brand…"
                options={activeBrands.map(b => ({ value: b.brand_id, label: b.display_name || b.name }))} />
            )}

            <Input label="Admin Note" placeholder="Reason / message to requester (optional)"
              value={adminNote} onChange={setAdminNote} />

            {currentAction.error && (
              <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>{currentAction.error}</p>
            )}

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <Btn variant="secondary" size="sm" onClick={() => setActionModal(null)}>Cancel</Btn>
              <Btn
                variant={modal.type === "reject" ? "danger" : "primary"}
                size="sm"
                loading={currentAction.loading}
                disabled={modal.type === "merge" && !existingBrandId}
                onClick={() => currentAction.execute({ id: modal.req.request_id })}
              >
                {modal.type === "approve" ? "Approve" : modal.type === "reject" ? "Reject" : "Merge"}
              </Btn>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// BRAND MASTER TAB
// ─────────────────────────────────────────────────────────────────────────────
function BrandMasterTab() {
  const [q,      setQ]      = useState("");
  const [status, setStatus] = useState("");
  const [page,   setPage]   = useState(1);

  const [createOpen, setCreateOpen] = useState(false);
  const [editItem,   setEditItem]   = useState<Brand34D | null>(null);
  const [detailItem, setDetailItem] = useState<Brand34D | null>(null);

  const summaryRes = useApi(useCallback(() => typesApi.brandSummary(), []), []);
  const listRes    = useApi(useCallback(
    () => catalogApi.listBrands({ search: q || undefined, status: status || undefined, page, page_size: 50 }),
    [q, status, page],
  ), [q, status, page]);

  const activateAction   = useAction(useCallback((id:string) => catalogApi.activateBrand(id),   []));
  const deactivateAction = useAction(useCallback((id:string) => catalogApi.deactivateBrand(id), []));
  const archiveAction    = useAction(useCallback((id:string) => catalogApi.archiveBrand(id),    []));

  async function doStatus(id:string, action:"activate"|"deactivate"|"archive") {
    if (action === "activate")   await activateAction.execute(id);
    if (action === "deactivate") await deactivateAction.execute(id);
    if (action === "archive")    await archiveAction.execute(id);
    listRes.refetch(); summaryRes.refetch();
  }

  const sum = summaryRes.data;

  const columns = [
    { key:"name",    label:"Brand", render:(_v:unknown, row:any) => (
      <div>
        <div style={{ fontWeight:600, fontSize:13 }}>{row.name}</div>
        <div style={{ fontSize:11, color:"var(--text-tertiary)" }}>{row.code ?? row.slug}</div>
      </div>
    )},
    { key:"scope",   label:"Scope", render:(_v:unknown, row:any) => (
      <Badge variant={row.is_global ? "info" : "default"}>{row.is_global ? "Global" : "Restricted"}</Badge>
    )},
    { key:"cats",    label:"Mapped", render:(_v:unknown, row:any) => (
      <div style={{ fontSize:12 }}>
        <span style={{ color:"var(--text-secondary)" }}>Cat: </span>
        <strong>{row.category_mappings?.length ?? 0}</strong>
        {"  "}
        <span style={{ color:"var(--text-secondary)" }}>Svc: </span>
        <strong>{row.service_mappings?.length ?? 0}</strong>
      </div>
    )},
    { key:"status",  label:"Status", render:(_v:unknown, row:any) => (
      <Badge variant={row.status==="active"?"success":row.status==="inactive"?"warning":"default"}>
        {row.status}
      </Badge>
    )},
    { key:"updated", label:"Updated", render:(_v:unknown, row:any) => (
      <span style={{ fontSize:11, color:"var(--text-tertiary)" }}>
        {new Date(row.created_at ?? "").toLocaleDateString("en-IN")}
      </span>
    )},
    { key:"actions", label:"Actions", render:(_v:unknown, row:any) => (
      <BrandActionMenu row={row}
        onView={() => setDetailItem(row)}
        onEdit={() => setEditItem(row)}
        onActivate={() => doStatus(row.brand_id, "activate")}
        onDeactivate={() => doStatus(row.brand_id, "deactivate")}
        onArchive={() => doStatus(row.brand_id, "archive")}
      />
    )},
  ];

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
      {/* Summary Cards */}
      <div style={{ display:"flex", gap:12, flexWrap:"wrap" }}>
        {summaryRes.loading
          ? [1,2,3,4,5,6].map(i => <Skeleton key={i} height={72} style={{ flex:"1 1 130px", minWidth:110, borderRadius:"var(--radius-lg)" }}/>)
          : <>
            <SummaryCard label="Total"    value={sum?.total ?? 0} accent />
            <SummaryCard label="Active"   value={sum?.active ?? 0} />
            <SummaryCard label="Inactive" value={sum?.inactive ?? 0} />
            <SummaryCard label="Mapped"   value={sum?.mapped ?? 0} />
            <SummaryCard label="Unmapped" value={sum?.unmapped ?? 0} />
            <SummaryCard label="Global"   value={sum?.global ?? 0} />
          </>
        }
      </div>

      {/* Toolbar */}
      <Card padding={16}>
        <div style={{ display:"flex", gap:10, flexWrap:"wrap", alignItems:"center" }}>
          <div style={{ position:"relative", flex:"1 1 220px" }}>
            <Search size={14} style={{ position:"absolute", left:10, top:"50%", transform:"translateY(-50%)", color:"var(--text-tertiary)" }}/>
            <input value={q} onChange={e=>{setQ(e.target.value);setPage(1);}}
              placeholder="Search brand name, code…"
              style={{ width:"100%", paddingLeft:32, paddingRight:10, height:36, borderRadius:"var(--radius-md)",
                border:"1px solid var(--border)", background:"var(--input-bg)",
                color:"var(--text-primary)", fontSize:13, outline:"none", boxSizing:"border-box" }}/>
          </div>
          <select value={status} onChange={e=>{setStatus(e.target.value);setPage(1);}}
            style={{ height:36, borderRadius:"var(--radius-md)", border:"1px solid var(--border)", background:"var(--input-bg)",
              color:"var(--text-primary)", fontSize:13, padding:"0 10px" }}>
            {STATUS_OPTIONS.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <div style={{ marginLeft:"auto", display:"flex", gap:8 }}>
            <Btn variant="ghost" size="sm" onClick={() => { listRes.refetch(); summaryRes.refetch(); }}>
              <RefreshCw size={14}/>
            </Btn>
            <Btn variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
              <Plus size={14}/> New Brand
            </Btn>
          </div>
        </div>
      </Card>

      {/* Table */}
      <Card padding={0}>
        {listRes.loading
          ? <div style={{ padding:32 }}><Skeleton height={200}/></div>
          : (listRes.data?.brands ?? []).length === 0
            ? <EmptyState title="No brands yet"
                description="Create reusable brands and map them to relevant services. Examples: Samsung, LG, Daikin."
                action={<Btn variant="primary" size="sm" onClick={() => setCreateOpen(true)}><Plus size={14}/> New Brand</Btn>}/>
            : <DataTable columns={columns} rows={(listRes.data?.brands ?? []) as unknown as Record<string, unknown>[]}/>
        }
        {/* Pagination -- was previously missing entirely on this tab (fetched
            page_size:50 but gave no way to reach page 2+). */}
        {Math.ceil((listRes.data?.total ?? 0) / 50) > 1 && (
          <div style={{ display:"flex", justifyContent:"center", gap:8, padding:16 }}>
            <Btn variant="ghost" size="sm" onClick={() => setPage(p=>Math.max(1,p-1))} disabled={page===1}>Prev</Btn>
            <span style={{ fontSize:12, color:"var(--text-secondary)", alignSelf:"center" }}>
              Page {page} / {Math.ceil((listRes.data?.total ?? 0) / 50)}
            </span>
            <Btn variant="ghost" size="sm" onClick={() => setPage(p=>p+1)} disabled={page>=Math.ceil((listRes.data?.total ?? 0) / 50)}>Next</Btn>
          </div>
        )}
      </Card>

      {/* Modals */}
      {createOpen && (
        <BrandFormModal title="New Brand" onClose={() => setCreateOpen(false)}
          onSaved={() => { setCreateOpen(false); listRes.refetch(); summaryRes.refetch(); }}/>
      )}
      {editItem && (
        <BrandFormModal title="Edit Brand" initial={editItem} onClose={() => setEditItem(null)}
          onSaved={() => { setEditItem(null); listRes.refetch(); summaryRes.refetch(); }}/>
      )}
      {detailItem && (
        <BrandDetailDrawer item={detailItem} onClose={() => setDetailItem(null)}/>
      )}
    </div>
  );
}

// Mapping is managed exclusively from the dedicated "Brand-Service Mapping"
// tab now (explicit user request, same as Service Types) -- this tab is
// purely Brand CRUD.
function BrandActionMenu({ row, onView, onEdit, onActivate, onDeactivate, onArchive }:
  { row:Brand34D; onView():void; onEdit():void;
    onActivate():void; onDeactivate():void; onArchive():void }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ position:"relative" }}>
      <Btn variant="ghost" size="sm" onClick={() => setOpen(o=>!o)}>
        Actions <ChevronDown size={12}/>
      </Btn>
      {open && (
        <div onClick={e=>e.stopPropagation()} style={{
          position:"absolute", right:0, top:"calc(100% + 4px)", zIndex:1000,
          background:"var(--card-bg)", border:"1px solid var(--border)", borderRadius:10,
          boxShadow:"0 8px 24px rgba(0,0,0,0.12)", minWidth:160, overflow:"hidden",
        }}>
          {[
            { label:"View Details",   fn:() => { onView(); setOpen(false); } },
            { label:"Edit Brand",     fn:() => { onEdit(); setOpen(false); } },
            row.status !== "active"   ? { label:"Activate",   fn:() => { onActivate(); setOpen(false); } } : null,
            row.status === "active"   ? { label:"Deactivate", fn:() => { onDeactivate(); setOpen(false); } } : null,
            row.status !== "archived" ? { label:"Archive", fn:() => { onArchive(); setOpen(false); }, danger:true } : null,
          ].filter(Boolean).map((item:any) => (
            <button key={item.label} onClick={item.fn} style={{
              display:"block", width:"100%", textAlign:"left", padding:"9px 16px",
              background:"none", border:"none", cursor:"pointer", fontSize:13,
              color: item.danger ? "var(--danger-text)" : "var(--text-primary)",
              borderBottom:"1px solid var(--border)",
            }}>{item.label}</button>
          ))}
        </div>
      )}
    </div>
  );
}

function BrandFormModal({ title, initial, onClose, onSaved }:
  { title:string; initial?:Brand34D|null; onClose():void; onSaved():void }) {
  const [form, setForm] = useState({
    name:             initial?.name ?? "",
    code:             initial?.code ?? "",
    slug:             initial?.slug ?? "",
    description:      initial?.description ?? "",
    is_global:        initial?.is_global ?? true,
    status:           initial?.status ?? "active",
    display_order:    initial?.display_order ?? 0,
    country_of_origin: initial?.country_of_origin ?? "",
    website_url:      initial?.website_url ?? "",
  });
  // Same auto-slug-from-name UX as the Service Type form, stops once the
  // user edits Slug by hand.
  const [slugTouched, setSlugTouched] = useState(!!initial?.slug);

  const createAction = useAction(useCallback((d:object) => catalogApi.createBrand(d as Partial<Brand34D> & { name: string }), []));
  const updateAction = useAction(useCallback((d:object) => catalogApi.updateBrand(initial!.brand_id, d), [initial]));

  async function handleSave() {
    const res = initial ? await updateAction.execute(form) : await createAction.execute(form);
    if (res) onSaved();
  }

  const err = createAction.error ?? updateAction.error;
  const loading = createAction.loading || updateAction.loading;

  return (
    <Modal open title={title} onClose={onClose}>
      <div style={{ display:"flex", flexDirection:"column", gap:14, minWidth:360 }}>
        {err && <div style={{ padding:"8px 12px", borderRadius:"var(--radius-md)", background:"var(--danger-bg)",
          fontSize:12, color:"var(--danger-text)" }}>{err}</div>}
        {([
          ["Name *", "name"], ["Code", "code"], ["Slug (auto-generated, editable)", "slug"],
          ["Country of Origin", "country_of_origin"], ["Website URL", "website_url"],
        ] as [string, keyof typeof form][]).map(([label, key]) => (
          <div key={key} style={{ display:"flex", flexDirection:"column", gap:4 }}>
            <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>{label}</label>
            <input value={form[key] as string}
              onChange={e => {
                const v = e.target.value;
                if (key === "slug") setSlugTouched(true);
                setForm(f => ({
                  ...f, [key]: v,
                  ...(key === "name" && !slugTouched ? { slug: slugify(v) } : {}),
                }));
              }}
              style={{ height:36, borderRadius:"var(--radius-md)", border:"1px solid var(--border)", background:"var(--input-bg)",
                color:"var(--text-primary)", fontSize:13, padding:"0 10px" }}/>
          </div>
        ))}
        <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
          <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>Description</label>
          <textarea value={form.description} onChange={e=>setForm(f=>({...f,description:e.target.value}))} rows={2}
            style={{ borderRadius:"var(--radius-md)", border:"1px solid var(--border)", background:"var(--input-bg)",
              color:"var(--text-primary)", fontSize:13, padding:"8px 10px", resize:"vertical" }}/>
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
          <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
            <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>Status</label>
            <select value={form.status} onChange={e=>setForm(f=>({...f,status:e.target.value as Brand34D["status"]}))}
              style={{ height:36, borderRadius:"var(--radius-md)", border:"1px solid var(--border)", background:"var(--input-bg)",
                color:"var(--text-primary)", fontSize:13, padding:"0 10px" }}>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
          <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
            <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>Display Order</label>
            <input type="number" value={form.display_order}
              onChange={e=>setForm(f=>({...f,display_order:+e.target.value}))}
              style={{ height:36, borderRadius:"var(--radius-md)", border:"1px solid var(--border)", background:"var(--input-bg)",
                color:"var(--text-primary)", fontSize:13, padding:"0 10px" }}/>
          </div>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <input type="checkbox" id="isg" checked={form.is_global} onChange={e=>setForm(f=>({...f,is_global:e.target.checked}))}/>
          <label htmlFor="isg" style={{ fontSize:13, cursor:"pointer" }}>Global Brand (available across all categories)</label>
        </div>
        <div style={{ display:"flex", gap:10, justifyContent:"flex-end", paddingTop:4 }}>
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" loading={loading} onClick={handleSave}>
            {initial ? "Save Changes" : "Create Brand"}
          </Btn>
        </div>
      </div>
    </Modal>
  );
}

function BrandDetailDrawer({ item, onClose }: { item:Brand34D; onClose():void }) {
  const rows: [string, string][] = [
    ["Name",              item.name],
    ["Code",              item.code ?? "—"],
    ["Slug",              item.slug],
    ["Description",       item.description ?? "—"],
    ["Scope",             item.is_global ? "Global" : "Restricted"],
    ["Status",            item.status],
    ["Country of Origin", item.country_of_origin ?? "—"],
    ["Website",           item.website_url ?? "—"],
    ["Display Order",     String(item.display_order)],
    ["Category Mappings", String(item.category_mappings?.length ?? 0)],
    ["Service Mappings",  String(item.service_mappings?.length ?? 0)],
  ];
  return (
    <Modal open title={`Brand: ${item.name}`} onClose={onClose}>
      <div style={{ minWidth:360 }}>
        {rows.map(([label, val]) => (
          <div key={label} style={{ display:"flex", gap:12, padding:"8px 0",
            borderBottom:"1px solid var(--border)" }}>
            <span style={{ fontSize:12, color:"var(--text-tertiary)", width:140, flexShrink:0 }}>{label}</span>
            <span style={{ fontSize:12, color:"var(--text-primary)", fontWeight:500, wordBreak:"break-all" }}>{val}</span>
          </div>
        ))}
        {(item.category_mappings ?? []).length > 0 && (
          <div style={{ marginTop:16 }}>
            <div style={{ fontSize:12, fontWeight:600, color:"var(--text-tertiary)", textTransform:"uppercase",
              letterSpacing:"0.05em", marginBottom:8 }}>Category Mappings</div>
            {item.category_mappings!.map((m:any) => (
              <div key={m.category_id} style={{ fontSize:12, padding:"4px 0",
                borderBottom:"1px solid var(--border)", color:"var(--text-secondary)" }}>
                {m.category_name ?? m.category_id}
              </div>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}

function AddBrandMappingModal({ brandId, brandName, onClose, onSaved }:
  { brandId:string; brandName:string; onClose():void; onSaved():void }) {
  // Same fix as AddTypeMappingModal -- a Brand belongs to a Service Group
  // (e.g. "AC Services"), not directly to the whole Category. BrandMapping.
  // service_group_id already exists on the backend. Category is a multi-
  // select filter narrowing the group list; Service Group is multi-select
  // and is the real saved association (one row per selected group).
  const [categoryIds,     setCategoryIds]     = useState<string[]>([]);
  const [serviceGroupIds, setServiceGroupIds] = useState<string[]>([]);
  const [serviceId,       setServiceId]       = useState("");
  const [custVis,         setCustVis]         = useState(true);

  const categories = useApi(useCallback(() => catalogApi.listCategories(true), []));
  const serviceGroups = useApi(useCallback(() => catalogApi.listServiceGroups(), []));
  const allGroups = serviceGroups.data?.groups ?? [];
  const visibleGroups = categoryIds.length === 0
    ? allGroups : allGroups.filter(g => categoryIds.includes(g.category_id));
  const singleGroupId = serviceGroupIds.length === 1 ? serviceGroupIds[0] : undefined;
  const services   = useApi(useCallback(
    () => singleGroupId ? catalogApi.listMasterServices(undefined, undefined, undefined, singleGroupId) : Promise.resolve({ services:[] }),
    [singleGroupId],
  ));

  const action = useAction(useCallback(async (groupIds: string[]) => {
    return Promise.all(groupIds.map(gid => {
      const group = allGroups.find(g => g.id === gid);
      return typesApi.createBrandMapping({
        brand_id: brandId, service_group_id: gid,
        category_id: group?.category_id,
        service_id: groupIds.length === 1 ? (serviceId || undefined) : undefined,
        customer_visible: custVis,
      });
    }));
  }, [brandId, serviceId, custVis, allGroups]));

  async function handleSave() {
    if (serviceGroupIds.length === 0) return;
    const res = await action.execute(serviceGroupIds);
    if (res) onSaved();
  }

  return (
    <Modal open title={`Map Brand: ${brandName}`} onClose={onClose}>
      <div style={{ display:"flex", flexDirection:"column", gap:14, minWidth:320 }}>
        {action.error && <div style={{ padding:"8px 12px", borderRadius:"var(--radius-md)", background:"var(--danger-bg)",
          fontSize:12, color:"var(--danger-text)" }}>{action.error}</div>}
        <MultiCheckList label="Category (filter)" emptyText="No categories"
          options={(categories.data?.categories ?? []).map((c:any) => ({ value:c.category_id, label:c.name }))}
          selected={categoryIds}
          onToggle={v => { setCategoryIds(p => toggleInList(p, v)); setServiceGroupIds([]); setServiceId(""); }}/>
        <MultiCheckList label="Service Group *" emptyText="No service groups match the selected categories"
          options={visibleGroups.map(g => ({ value:g.id, label: categoryIds.length === 0 ? `${g.name} (${g.category_name})` : g.name }))}
          selected={serviceGroupIds}
          onToggle={v => { setServiceGroupIds(p => toggleInList(p, v)); setServiceId(""); }}/>
        <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
          <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>
            Service (optional{serviceGroupIds.length > 1 ? " — only when a single group is selected" : ""})
          </label>
          <select value={serviceId} onChange={e=>setServiceId(e.target.value)} disabled={!singleGroupId}
            style={{ height:36, borderRadius:"var(--radius-md)", border:"1px solid var(--border)", background:"var(--input-bg)",
              color:"var(--text-primary)", fontSize:13, padding:"0 10px",
              opacity: singleGroupId ? 1 : 0.5 }}>
            <option value="">All services in group</option>
            {(services.data?.services ?? []).map((s:any) =>
              <option key={s.service_id} value={s.service_id}>{s.name}</option>
            )}
          </select>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <input type="checkbox" id="cvbm" checked={custVis} onChange={e=>setCustVis(e.target.checked)}/>
          <label htmlFor="cvbm" style={{ fontSize:13, cursor:"pointer" }}>Customer Visible</label>
        </div>
        <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" loading={action.loading} onClick={handleSave}
            disabled={serviceGroupIds.length === 0}>
            Add Mapping{serviceGroupIds.length > 1 ? ` (${serviceGroupIds.length} groups)` : ""}
          </Btn>
        </div>
      </div>
    </Modal>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TYPE MAPPINGS TAB
// ─────────────────────────────────────────────────────────────────────────────
function TypeMappingsTab() {
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);

  const listRes = useApi(useCallback(
    () => typesApi.listMappings({ page }),
    [page],
  ), [page]);

  const deleteAction = useAction(useCallback((id:string) => typesApi.deleteMapping(id), []));
  const pageSize = 50;
  const totalPages = Math.max(1, Math.ceil((listRes.data?.total ?? 0) / pageSize));

  const columns = [
    { key:"type_name",     label:"Type",     render:(_v:unknown, row:any) => (
      <span style={{ fontWeight:600, fontSize:13 }}>{row.type_name ?? row.type_id.slice(0,8)}</span>
    )},
    { key:"category_name", label:"Category", render:(_v:unknown, row:any) => (
      <span style={{ fontSize:13 }}>{row.category_name ?? row.category_id?.slice(0,8) ?? "—"}</span>
    )},
    { key:"service_name",  label:"Service",  render:(_v:unknown, row:any) => (
      <span style={{ fontSize:13, color:"var(--text-secondary)" }}>
        {row.service_name ?? (row.service_id ? row.service_id.slice(0,8) : "Any")}
      </span>
    )},
    { key:"customer_visible", label:"Customer", render:(_v:unknown, row:any) => (
      <Badge variant={row.customer_visible ? "success" : "default"}>{row.customer_visible ? "Yes" : "No"}</Badge>
    )},
    { key:"status",  label:"Status", render:(_v:unknown, row:any) => (
      <Badge variant={row.status==="active"?"success":"default"}>{row.status}</Badge>
    )},
    { key:"actions", label:"Actions", render:(_v:unknown, row:any) => (
      <Btn variant="ghost" size="sm"
        onClick={async () => {
          if (confirm("Remove this mapping?")) {
            await deleteAction.execute(row.mapping_id);
            listRes.refetch();
          }
        }}>Remove</Btn>
    )},
  ];

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
        <div>
          <div style={{ fontSize:14, fontWeight:600 }}>Type Mappings</div>
          <div style={{ fontSize:12, color:"var(--text-tertiary)" }}>
            Explicit links between service types and categories/services.
          </div>
        </div>
        <div style={{ display:"flex", gap:8 }}>
          <Btn variant="ghost" size="sm" onClick={() => listRes.refetch()}><RefreshCw size={14}/></Btn>
          <Btn variant="primary" size="sm" onClick={() => setCreateOpen(true)}><Plus size={14}/> Add Mapping</Btn>
        </div>
      </div>

      <Card padding={0}>
        {listRes.loading
          ? <div style={{ padding:32 }}><Skeleton height={200}/></div>
          : (listRes.data?.mappings ?? []).length === 0
            ? <EmptyState title="No type mappings yet"
                description="Map service types to categories or services to control booking flow visibility."
                action={<Btn variant="primary" size="sm" onClick={() => setCreateOpen(true)}><Plus size={14}/> Add Mapping</Btn>}/>
            : <DataTable columns={columns} rows={(listRes.data?.mappings ?? []) as unknown as Record<string, unknown>[]}/>
        }
        {totalPages > 1 && (
          <div style={{ display:"flex", justifyContent:"center", gap:8, padding:16 }}>
            <Btn variant="ghost" size="sm" onClick={() => setPage(p=>Math.max(1,p-1))} disabled={page===1}>Prev</Btn>
            <span style={{ fontSize:12, color:"var(--text-secondary)", alignSelf:"center" }}>Page {page} / {totalPages}</span>
            <Btn variant="ghost" size="sm" onClick={() => setPage(p=>p+1)} disabled={page>=totalPages}>Next</Btn>
          </div>
        )}
      </Card>

      {createOpen && (
        <CreateTypeMappingFullModal onClose={() => setCreateOpen(false)}
          onSaved={() => { setCreateOpen(false); listRes.refetch(); }}/>
      )}
    </div>
  );
}

function CreateTypeMappingFullModal({ onClose, onSaved }:{ onClose():void; onSaved():void }) {
  // See AddTypeMappingModal above -- a Type belongs to a Service Group, not
  // directly to a Category. Category is a multi-select filter to narrow the
  // Service Group list; Service Group is the multi-select saved association
  // (one mapping row per selected group).
  const [typeId,          setTypeId]          = useState("");
  const [categoryIds,     setCategoryIds]     = useState<string[]>([]);
  const [serviceGroupIds, setServiceGroupIds] = useState<string[]>([]);
  const [serviceId,       setServiceId]       = useState("");
  const [custVis,         setCustVis]         = useState(true);

  const typesRes   = useApi(useCallback(() => typesApi.list({ status:"active", page_size:200 }), []), []);
  const categories = useApi(useCallback(() => catalogApi.listCategories(true), []), []);
  const serviceGroups = useApi(useCallback(() => catalogApi.listServiceGroups(), []), []);
  const allGroups = serviceGroups.data?.groups ?? [];
  const visibleGroups = categoryIds.length === 0
    ? allGroups : allGroups.filter(g => categoryIds.includes(g.category_id));
  const singleGroupId = serviceGroupIds.length === 1 ? serviceGroupIds[0] : undefined;
  const services   = useApi(useCallback(
    () => singleGroupId ? catalogApi.listMasterServices(undefined, undefined, undefined, singleGroupId) : Promise.resolve({ services:[] }),
    [singleGroupId],
  ), [singleGroupId]);

  const action = useAction(useCallback(async (groupIds: string[]) => {
    return Promise.all(groupIds.map(gid => {
      const group = allGroups.find(g => g.id === gid);
      return typesApi.createMapping({
        type_id: typeId, service_group_id: gid,
        category_id: group?.category_id,
        service_id: groupIds.length === 1 ? (serviceId || undefined) : undefined,
        customer_visible: custVis,
      });
    }));
  }, [typeId, serviceId, custVis, allGroups]));

  async function handleSave() {
    if (!typeId || serviceGroupIds.length === 0) return;
    const res = await action.execute(serviceGroupIds);
    if (res) onSaved();
  }

  return (
    <Modal open title="Add Type Mapping" onClose={onClose}>
      <div style={{ display:"flex", flexDirection:"column", gap:14, minWidth:340 }}>
        {action.error && <div style={{ padding:"8px 12px", borderRadius:"var(--radius-md)", background:"var(--danger-bg)",
          fontSize:12, color:"var(--danger-text)" }}>{action.error}</div>}
        <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
          <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>Type *</label>
          <select value={typeId} onChange={e=>setTypeId(e.target.value)}
            style={{ height:36, borderRadius:"var(--radius-md)", border:"1px solid var(--border)", background:"var(--input-bg)",
              color:"var(--text-primary)", fontSize:13, padding:"0 10px" }}>
            <option value="">Select…</option>
            {(typesRes.data?.types ?? []).map((t:ServiceTypeMaster) =>
              <option key={t.type_id} value={t.type_id}>{t.name}</option>
            )}
          </select>
        </div>
        <MultiCheckList label="Category (filter)" emptyText="No categories"
          options={(categories.data?.categories ?? []).map((c:any) => ({ value:c.category_id, label:c.name }))}
          selected={categoryIds}
          onToggle={v => { setCategoryIds(p => toggleInList(p, v)); setServiceGroupIds([]); setServiceId(""); }}/>
        <MultiCheckList label="Service Group *" emptyText="No service groups match the selected categories"
          options={visibleGroups.map(g => ({ value:g.id, label: categoryIds.length === 0 ? `${g.name} (${g.category_name})` : g.name }))}
          selected={serviceGroupIds}
          onToggle={v => { setServiceGroupIds(p => toggleInList(p, v)); setServiceId(""); }}/>
        <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
          <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>
            Service (optional{serviceGroupIds.length > 1 ? " — only when a single group is selected" : ""})
          </label>
          <select value={serviceId} onChange={e=>setServiceId(e.target.value)} disabled={!singleGroupId}
            style={{ height:36, borderRadius:"var(--radius-md)", border:"1px solid var(--border)", background:"var(--input-bg)",
              color:"var(--text-primary)", fontSize:13, padding:"0 10px", opacity:singleGroupId?1:0.5 }}>
            <option value="">All services in group</option>
            {(services.data?.services ?? []).map((s:any) =>
              <option key={s.service_id} value={s.service_id}>{s.name}</option>
            )}
          </select>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <input type="checkbox" id="cvtm2" checked={custVis} onChange={e=>setCustVis(e.target.checked)}/>
          <label htmlFor="cvtm2" style={{ fontSize:13, cursor:"pointer" }}>Customer Visible</label>
        </div>
        <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" loading={action.loading} onClick={handleSave}
            disabled={!typeId || serviceGroupIds.length === 0}>
            Add Mapping{serviceGroupIds.length > 1 ? ` (${serviceGroupIds.length} groups)` : ""}
          </Btn>
        </div>
      </div>
    </Modal>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// BRAND MAPPINGS TAB
// ─────────────────────────────────────────────────────────────────────────────
function BrandMappingsTab() {
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);

  const listRes = useApi(useCallback(
    () => typesApi.listBrandMappings({ page }),
    [page],
  ), [page]);

  const deleteAction = useAction(useCallback((id:string) => typesApi.deleteBrandMapping(id), []));
  const pageSize = 50;
  const totalPages = Math.max(1, Math.ceil((listRes.data?.total ?? 0) / pageSize));

  const columns = [
    { key:"brand_name",    label:"Brand",    render:(_v:unknown, row:any) => (
      <span style={{ fontWeight:600, fontSize:13 }}>{row.brand_name ?? row.brand_id.slice(0,8)}</span>
    )},
    { key:"category_name", label:"Category", render:(_v:unknown, row:any) => (
      <span style={{ fontSize:13 }}>{row.category_name ?? row.category_id?.slice(0,8) ?? "—"}</span>
    )},
    { key:"service_name",  label:"Service",  render:(_v:unknown, row:any) => (
      <span style={{ fontSize:13, color:"var(--text-secondary)" }}>
        {row.service_name ?? (row.service_id ? row.service_id.slice(0,8) : "Any")}
      </span>
    )},
    { key:"customer_visible", label:"Customer", render:(_v:unknown, row:any) => (
      <Badge variant={row.customer_visible ? "success" : "default"}>{row.customer_visible ? "Yes" : "No"}</Badge>
    )},
    { key:"status",  label:"Status", render:(_v:unknown, row:any) => (
      <Badge variant={row.status==="active"?"success":"default"}>{row.status}</Badge>
    )},
    { key:"actions", label:"Actions", render:(_v:unknown, row:any) => (
      <Btn variant="ghost" size="sm"
        onClick={async () => {
          if (confirm("Remove this mapping?")) {
            await deleteAction.execute(row.mapping_id);
            listRes.refetch();
          }
        }}>Remove</Btn>
    )},
  ];

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
        <div>
          <div style={{ fontSize:14, fontWeight:600 }}>Brand Mappings</div>
          <div style={{ fontSize:12, color:"var(--text-tertiary)" }}>
            Explicit links between brands and categories/services for booking flow filtering.
          </div>
        </div>
        <div style={{ display:"flex", gap:8 }}>
          <Btn variant="ghost" size="sm" onClick={() => listRes.refetch()}><RefreshCw size={14}/></Btn>
          <Btn variant="primary" size="sm" onClick={() => setCreateOpen(true)}><Plus size={14}/> Add Mapping</Btn>
        </div>
      </div>

      <Card padding={0}>
        {listRes.loading
          ? <div style={{ padding:32 }}><Skeleton height={200}/></div>
          : (listRes.data?.mappings ?? []).length === 0
            ? <EmptyState title="No brand mappings yet"
                description="Map brands to categories or services to control which brands appear in the booking flow."
                action={<Btn variant="primary" size="sm" onClick={() => setCreateOpen(true)}><Plus size={14}/> Add Mapping</Btn>}/>
            : <DataTable columns={columns} rows={(listRes.data?.mappings ?? []) as unknown as Record<string, unknown>[]}/>
        }
        {totalPages > 1 && (
          <div style={{ display:"flex", justifyContent:"center", gap:8, padding:16 }}>
            <Btn variant="ghost" size="sm" onClick={() => setPage(p=>Math.max(1,p-1))} disabled={page===1}>Prev</Btn>
            <span style={{ fontSize:12, color:"var(--text-secondary)", alignSelf:"center" }}>Page {page} / {totalPages}</span>
            <Btn variant="ghost" size="sm" onClick={() => setPage(p=>p+1)} disabled={page>=totalPages}>Next</Btn>
          </div>
        )}
      </Card>

      {createOpen && (
        <CreateBrandMappingFullModal onClose={() => setCreateOpen(false)}
          onSaved={() => { setCreateOpen(false); listRes.refetch(); }}/>
      )}
    </div>
  );
}

function CreateBrandMappingFullModal({ onClose, onSaved }:{ onClose():void; onSaved():void }) {
  // Same fix as CreateTypeMappingFullModal -- Brand belongs to Service
  // Group, not directly to Category. Both Category (filter) and Service
  // Group (real association) are multi-select.
  const [brandId,         setBrandId]         = useState("");
  const [categoryIds,     setCategoryIds]     = useState<string[]>([]);
  const [serviceGroupIds, setServiceGroupIds] = useState<string[]>([]);
  const [serviceId,       setServiceId]       = useState("");
  const [custVis,         setCustVis]         = useState(true);

  const brandsRes  = useApi(useCallback(() => catalogApi.listBrands({ status:"active", page_size:200 }), []), []);
  const categories = useApi(useCallback(() => catalogApi.listCategories(true), []), []);
  const serviceGroups = useApi(useCallback(() => catalogApi.listServiceGroups(), []), []);
  const allGroups = serviceGroups.data?.groups ?? [];
  const visibleGroups = categoryIds.length === 0
    ? allGroups : allGroups.filter(g => categoryIds.includes(g.category_id));
  const singleGroupId = serviceGroupIds.length === 1 ? serviceGroupIds[0] : undefined;
  const services   = useApi(useCallback(
    () => singleGroupId ? catalogApi.listMasterServices(undefined, undefined, undefined, singleGroupId) : Promise.resolve({ services:[] }),
    [singleGroupId],
  ), [singleGroupId]);

  const action = useAction(useCallback(async (groupIds: string[]) => {
    return Promise.all(groupIds.map(gid => {
      const group = allGroups.find(g => g.id === gid);
      return typesApi.createBrandMapping({
        brand_id: brandId, service_group_id: gid,
        category_id: group?.category_id,
        service_id: groupIds.length === 1 ? (serviceId || undefined) : undefined,
        customer_visible: custVis,
      });
    }));
  }, [brandId, serviceId, custVis, allGroups]));

  async function handleSave() {
    if (!brandId || serviceGroupIds.length === 0) return;
    const res = await action.execute(serviceGroupIds);
    if (res) onSaved();
  }

  return (
    <Modal open title="Add Brand Mapping" onClose={onClose}>
      <div style={{ display:"flex", flexDirection:"column", gap:14, minWidth:340 }}>
        {action.error && <div style={{ padding:"8px 12px", borderRadius:"var(--radius-md)", background:"var(--danger-bg)",
          fontSize:12, color:"var(--danger-text)" }}>{action.error}</div>}
        <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
          <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>Brand *</label>
          <select value={brandId} onChange={e=>setBrandId(e.target.value)}
            style={{ height:36, borderRadius:"var(--radius-md)", border:"1px solid var(--border)", background:"var(--input-bg)",
              color:"var(--text-primary)", fontSize:13, padding:"0 10px" }}>
            <option value="">Select…</option>
            {(brandsRes.data?.brands ?? []).map((b:Brand34D) =>
              <option key={b.brand_id} value={b.brand_id}>{b.name}</option>
            )}
          </select>
        </div>
        <MultiCheckList label="Category (filter)" emptyText="No categories"
          options={(categories.data?.categories ?? []).map((c:any) => ({ value:c.category_id, label:c.name }))}
          selected={categoryIds}
          onToggle={v => { setCategoryIds(p => toggleInList(p, v)); setServiceGroupIds([]); setServiceId(""); }}/>
        <MultiCheckList label="Service Group *" emptyText="No service groups match the selected categories"
          options={visibleGroups.map(g => ({ value:g.id, label: categoryIds.length === 0 ? `${g.name} (${g.category_name})` : g.name }))}
          selected={serviceGroupIds}
          onToggle={v => { setServiceGroupIds(p => toggleInList(p, v)); setServiceId(""); }}/>
        <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
          <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>
            Service (optional{serviceGroupIds.length > 1 ? " — only when a single group is selected" : ""})
          </label>
          <select value={serviceId} onChange={e=>setServiceId(e.target.value)} disabled={!singleGroupId}
            style={{ height:36, borderRadius:"var(--radius-md)", border:"1px solid var(--border)", background:"var(--input-bg)",
              color:"var(--text-primary)", fontSize:13, padding:"0 10px", opacity:singleGroupId?1:0.5 }}>
            <option value="">All services in group</option>
            {(services.data?.services ?? []).map((s:any) =>
              <option key={s.service_id} value={s.service_id}>{s.name}</option>
            )}
          </select>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <input type="checkbox" id="cvbm2" checked={custVis} onChange={e=>setCustVis(e.target.checked)}/>
          <label htmlFor="cvbm2" style={{ fontSize:13, cursor:"pointer" }}>Customer Visible</label>
        </div>
        <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" loading={action.loading} onClick={handleSave}
            disabled={!brandId || serviceGroupIds.length === 0}>
            Add Mapping{serviceGroupIds.length > 1 ? ` (${serviceGroupIds.length} groups)` : ""}
          </Btn>
        </div>
      </div>
    </Modal>
  );
}
