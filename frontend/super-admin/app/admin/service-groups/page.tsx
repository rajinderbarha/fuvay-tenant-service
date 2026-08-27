"use client";
import React, { useState, useCallback, useEffect, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import HomeServicesCatalogNav from "../../../components/catalog/HomeServicesCatalogNav";
import OperationsDirectoryControls from "../../../components/enterprise/OperationsDirectoryControls";
import type { ColumnDef } from "../../../components/enterprise/EnterpriseColumnManager";
import {
  Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader, SummaryCard, Pagination,} from "../../../components/shared/ui";
import { IconPicker } from "../../../components/shared/IconPicker";
import { ActionMenu } from "../../../components/shared/layout";
import {
  catalogApi,
  type ServiceGroupEnriched, type ServiceCategory,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { RefreshCw, AlertCircle, CheckSquare, Square } from "lucide-react";

// ── Label maps ─────────────────────────────────────────────────────────────────
const STATUS_LABEL: Record<string, string> = {
  active: "Active", inactive: "Inactive", deleted: "Retired",
};
const STATUS_VARIANT: Record<string, "success" | "warning" | "muted"> = {
  active: "success", inactive: "warning", deleted: "muted",
};
const READINESS_LABEL: Record<string, string> = {
  ready: "Ready", empty_group: "Empty", inactive: "Inactive",
  archived: "Archived", category_inactive: "Cat. Inactive",
};
const READINESS_VARIANT: Record<string, "success" | "warning" | "muted" | "danger"> = {
  ready: "success", empty_group: "warning",
  inactive: "muted", archived: "muted", category_inactive: "danger",
};

// ── Summary card ───────────────────────────────────────────────────────────────

// ── Form state ─────────────────────────────────────────────────────────────────
type FormState = {
  name: string; code: string; category_id: string;
  description: string; display_order: number; status: string; icon_url: string;
};
const BLANK: FormState = {
  name: "", code: "", category_id: "", description: "",
  display_order: 0, status: "active", icon_url: "",
};
function slugify(s: string) { return s.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, ""); }

const DEFAULT_COLUMNS: ColumnDef[] = [
  { key:"name", label:"Service Group", visible:true, order:0 },
  { key:"category_id", label:"Category", visible:true, order:1 },
  { key:"linked_counts", label:"Linked Records", visible:true, order:2 },
  { key:"runtime_readiness", label:"Readiness", visible:true, order:3 },
  { key:"status", label:"Status", visible:true, order:4 },
  { key:"updated_at", label:"Updated", visible:true, order:5 },
  { key:"id", label:"Actions", visible:true, order:6 },
];

// ── Action menu ────────────────────────────────────────────────────────────────
function GroupActions({ row, onEdit, onActivate, onDeactivate, onArchive, onView }: {
  row: ServiceGroupEnriched;
  onEdit: () => void;
  onActivate: () => void;
  onDeactivate: () => void;
  onArchive: () => void;
  onView: () => void;
}) {
  return (
    <ActionMenu
      size="xs"
      items={[
        { label: "View details", onClick: onView },
        { label: "Edit group", onClick: onEdit },
        row.status !== "active" && { label: "Activate", onClick: onActivate, divider: true },
        row.status === "active" && { label: "Deactivate", onClick: onDeactivate, divider: true },
        { label: "Retire", onClick: onArchive, variant: "danger" },
      ]}
    />
  );
}

// ── Detail drawer ──────────────────────────────────────────────────────────────
// ── Main page ──────────────────────────────────────────────────────────────────
export default function ServiceGroupsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Filters
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [lifecycleFilter, setLifecycleFilter] = useState<"current" | "retired">(() => searchParams.get("lifecycle") === "retired" ? "retired" : "current");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [hasServicesFilter, setHasServicesFilter] = useState<"" | "true" | "false">("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sortBy, setSortBy] = useState("display_order");
  const [sortDir, setSortDir] = useState("asc");
  const [columnsConfig, setColumnsConfig] = useState<ColumnDef[]>(DEFAULT_COLUMNS);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  // Modal / detail
  const [modal, setModal] = useState<"none" | "create" | "edit">("none");
  const [editing, setEditing] = useState<ServiceGroupEnriched | null>(null);
  const [archiveId, setArchiveId] = useState<string | null>(null);
  const [archiveReason, setArchiveReason] = useState("");
  const [form, setForm] = useState<FormState>(BLANK);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => { setDebouncedQ(q.trim()); setPage(1); }, 300);
    return () => clearTimeout(timer);
  }, [q]);

  // Data
  const summary = useApi(useCallback(() => catalogApi.getServiceGroupsSummary(), []));
  const categories = useApi(useCallback(() => catalogApi.listCategories(true), []));
  const groups = useApi(useCallback(
    () => catalogApi.listServiceGroups({
      categoryId: categoryFilter || undefined,
      status: statusFilter || undefined,
      retired: lifecycleFilter === "retired",
      q: debouncedQ || undefined,
      hasServices: hasServicesFilter === "" ? undefined : hasServicesFilter === "true",
      sortBy, sortDir,
      limit: pageSize,
      offset: (page - 1) * pageSize,
    }),
    [categoryFilter, statusFilter, lifecycleFilter, debouncedQ, hasServicesFilter, sortBy, sortDir, page, pageSize],
  ), [categoryFilter, statusFilter, lifecycleFilter, debouncedQ, hasServicesFilter, sortBy, sortDir, page, pageSize]);

  const notify = (msg: string, ok = true) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3500);
  };

  const catMap: Record<string, string> = useMemo(() => {
    const m: Record<string, string> = {};
    (categories.data?.categories ?? []).forEach((c: ServiceCategory) => { m[c.category_id] = c.name; });
    return m;
  }, [categories.data]);

  const catOptions = useMemo(() =>
    (categories.data?.categories ?? []).map((c: ServiceCategory) => ({ value: c.category_id, label: c.name })),
    [categories.data]);

  const catFilterOptions = [{ value: "", label: "All Categories" }, ...catOptions];

  // Actions
  const createAction = useAction(async (data: FormState) => {
    await catalogApi.createServiceGroup({
      name: data.name, category_id: data.category_id,
      code: data.code || undefined, description: data.description || undefined,
      display_order: data.display_order, icon_url: data.icon_url || undefined,
    });
    groups.refetch(); summary.refetch(); setModal("none"); notify("Service group created.");
  });

  const editAction = useAction(async ({ id, data }: { id: string; data: FormState }) => {
    await catalogApi.updateServiceGroup(id, {
      name: data.name, description: data.description || undefined,
      display_order: data.display_order, expected_updated_at: editing?.updated_at,
      icon_url: data.icon_url || undefined,
    });
    groups.refetch(); summary.refetch(); setModal("none"); notify("Service group updated.");
  });

  const activateAction = useAction(async (id: string) => {
    await catalogApi.activateServiceGroup(id);
    groups.refetch(); summary.refetch(); notify("Group activated.");
  });

  const deactivateAction = useAction(async (id: string) => {
    await catalogApi.deactivateServiceGroup(id);
    groups.refetch(); summary.refetch(); notify("Group deactivated.");
  });

  const archiveAction = useAction(async ({ id, reason }: { id:string; reason:string }) => {
    await catalogApi.archiveServiceGroup(id, reason);
    groups.refetch(); summary.refetch(); setArchiveId(null); setArchiveReason(""); notify("Group retired and recorded in the audit trail.");
  });
  const bulkAction = useAction(async (action: "activate" | "deactivate") => {
    const result = await catalogApi.bulkServiceGroupStatus([...selected], action);
    setSelected(new Set()); groups.refetch(); summary.refetch();
    notify(`${result.updated_count} groups ${action === "activate" ? "activated" : "deactivated"}.${result.errors.length ? ` ${result.errors.length} failed.` : ""}`, result.errors.length === 0);
  });

  function openCreate() { setForm(BLANK); setEditing(null); setModal("create"); }
  function openEdit(g: ServiceGroupEnriched) {
    setForm({ name: g.name, code: g.code, category_id: g.category_id, description: g.description ?? "", display_order: g.display_order, status: g.status, icon_url: g.icon_url ?? "" });
    setEditing(g); setModal("edit");
  }
  function setF<K extends keyof FormState>(k: K, v: FormState[K]) {
    setForm(p => { const n = { ...p, [k]: v }; if (k === "name" && !editing) n.code = slugify(v as string); return n; });
  }

  const s = summary.data;
  const rows = groups.data?.groups ?? [];
  useEffect(() => { setSelected(new Set()); }, [page, pageSize, categoryFilter, statusFilter, lifecycleFilter, hasServicesFilter, debouncedQ]);
  const canSave = !!form.name && !!form.category_id;
  const activeAction = editing ? editAction : createAction;

  const allColumns = [
    { key:"select", label:"", width:38, render:(_:unknown,row:ServiceGroupEnriched)=><button aria-label={`Select ${row.name}`} onClick={e=>{e.stopPropagation();setSelected(current=>{const next=new Set(current);next.has(row.id)?next.delete(row.id):next.add(row.id);return next;})}} style={{background:"none",border:"none",cursor:"pointer",color:selected.has(row.id)?"var(--brand)":"var(--text-tertiary)",display:"flex"}}>{selected.has(row.id)?<CheckSquare size={15}/>:<Square size={15}/>}</button> },
    {
      key: "name", label: "Group",
      render: (_: unknown, row: ServiceGroupEnriched) => (
        <div>
          <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{row.name}</span>
          <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-secondary)" }}>{row.code} · {row.slug}</p>
        </div>
      ),
    },
    {
      key: "category_id", label: "Category",
      render: (_: unknown, row: ServiceGroupEnriched) => (
        <span style={{ fontSize: 13 }}>{row.category_name}</span>
      ),
    },
    {
      key: "linked_counts", label: "Linked Services",
      render: (_: unknown, row: ServiceGroupEnriched) => (
        <div style={{ textAlign: "center" }}>
          <span style={{ fontSize: 16, fontWeight: 700 }}>{row.linked_counts?.services ?? 0}</span>
          <p style={{ margin: "1px 0 0", fontSize: 10, color: "var(--text-secondary)" }}>{row.linked_counts?.providers ?? 0} providers</p>
        </div>
      ),
    },
    {
      key: "runtime_readiness", label: "Readiness",
      render: (_: unknown, row: ServiceGroupEnriched) => (
        <Badge variant={READINESS_VARIANT[row.runtime_readiness] ?? "muted"}>
          {READINESS_LABEL[row.runtime_readiness] ?? row.runtime_readiness}
        </Badge>
      ),
    },
    {
      key: "status", label: "Status", width: 100,
      render: (_: unknown, row: ServiceGroupEnriched) => (
        <Badge variant={STATUS_VARIANT[row.status] ?? "muted"}>{STATUS_LABEL[row.status] ?? row.status}</Badge>
      ),
    },
    {
      key: "updated_at", label: "Updated", width: 110,
      render: (_: unknown, row: ServiceGroupEnriched) => (
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
          {row.updated_at ? new Date(row.updated_at).toLocaleDateString() : "—"}
        </span>
      ),
    },
    {
      key: "id", label: "", width: 120,
      render: (_: unknown, row: ServiceGroupEnriched) => row.deleted_at ? (
        <Btn variant="ghost" size="xs" onClick={() => router.push(`/admin/service-groups/${row.id}`)}>View / restore</Btn>
      ) : (
        <GroupActions
          row={row}
          onView={() => router.push(`/admin/service-groups/${row.id}`)}
          onEdit={() => openEdit(row)}
          onActivate={() => activateAction.execute(row.id)}
          onDeactivate={() => deactivateAction.execute(row.id)}
          onArchive={() => setArchiveId(row.id)}
        />
      ),
    },
  ];
  const visibleKeys = new Set(columnsConfig.filter(column => column.visible).map(column => column.key));
  const columns = allColumns.filter(column => column.key === "select" || visibleKeys.has(column.key));

  return (
    <AdminLayout activeNav="service-groups">
      <div className="catalog-admin-page">
      {/* Header */}
      <SectionHeader
        title="Service Groups"
        subtitle="Intermediate grouping layer between Categories and Master Services (e.g. 'AC Services' under 'Home Services')"
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="secondary" size="sm" onClick={() => { groups.refetch(); summary.refetch(); }}>
              <RefreshCw size={14} style={{ marginRight: 4 }} /> Refresh
            </Btn>
            <Btn variant="primary" size="sm" onClick={openCreate}>+ New Group</Btn>
          </div>
        }
      />
      <HomeServicesCatalogNav active="groups" />

      <OperationsDirectoryControls resourceKey="admin_service_groups"
        filters={{ q:debouncedQ, category_id:categoryFilter, status:statusFilter, lifecycle:lifecycleFilter, has_services:hasServicesFilter }}
        sort={{ sort_by:sortBy, sort_direction:sortDir }} columns={columnsConfig}
        onColumnsChange={setColumnsConfig}
        onApplyView={(filters, sort) => {
          setQ(String(filters.q ?? filters.search ?? ""));
          setCategoryFilter(String(filters.category_id ?? "")); setStatusFilter(String(filters.status ?? ""));
          setLifecycleFilter(filters.lifecycle === "retired" ? "retired" : "current");
          setHasServicesFilter(String(filters.has_services ?? "") as ""|"true"|"false");
          setSortBy(String(sort.sort_by ?? "display_order")); setSortDir(String(sort.sort_direction ?? "asc")); setPage(1);
        }}/>
      {/* Toast */}
      {toast && (
        <div style={{
          position: "fixed", top: 16, right: 16, zIndex: 9999, padding: "10px 18px",
          borderRadius: 10, background: toast.ok ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.ok ? "var(--success-text)" : "var(--danger-text)", fontSize: 13,
        }}>{toast.msg}</div>
      )}

      {/* Summary cards */}
      {s && (
        <div style={{ display: "grid", gridTemplateColumns:"repeat(auto-fit,minmax(150px,1fr))", gap: 12, margin:"16px 0 20px" }}>
          <SummaryCard label="Total Groups" value={s.total} />
          <SummaryCard label="Active" value={s.active} accent="var(--success-text, #22543d)" />
          <SummaryCard label="Inactive" value={s.inactive} accent="var(--warning-text, #744210)" />
          <SummaryCard label="With Services" value={s.groups_with_services} />
          <SummaryCard label="Empty Groups" value={s.empty_groups} accent="var(--danger-text, #c53030)" sub="no services linked" />
          <SummaryCard label="Runtime Ready" value={s.runtime_ready} accent="var(--brand, #1a56db)" />
          <SummaryCard label="Retired" value={s.retired} accent="var(--text-tertiary)" sub="recoverable" />
        </div>
      )}
      {summary.loading && (
        <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
          {[...Array(6)].map((_, i) => (
            <div key={i} style={{ flex: "1 1 140px", height: 80, borderRadius:"var(--radius-lg)", background: "var(--border)" }} className="skeleton" />
          ))}
        </div>
      )}

      {/* Filters */}
      <Card padding={16} style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <input
              placeholder="Search by name, code, or slug…"
              value={q} onChange={e => setQ(e.target.value)}
              style={{
                width: "100%", padding: "8px 12px", borderRadius:"var(--radius-md)", fontSize: 13,
                border: "1px solid var(--border)", background: "var(--surface)",
                color: "var(--text-primary)", outline: "none", boxSizing: "border-box",
              }}
            />
          </div>
          <div style={{ minWidth: 180 }}>
            <Select label="" value={categoryFilter} onChange={v => { setCategoryFilter(v); setPage(1); }}
              placeholder="All Categories" options={catFilterOptions} />
          </div>
          <div style={{ minWidth: 140 }}>
            <Select label="" value={statusFilter} onChange={v => { setStatusFilter(v); setPage(1); }}
              placeholder="All Statuses"
              options={[{ value: "", label: "All Statuses" }, { value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }]} />
          </div>
          <div style={{ minWidth: 150 }}>
            <Select label="" value={lifecycleFilter} onChange={value => { setLifecycleFilter(value as "current" | "retired"); setStatusFilter(""); setPage(1); }}
              options={[{ value: "current", label: "Current records" }, { value: "retired", label: `Retired (${s?.retired ?? 0})` }]} />
          </div>
          <Btn variant="ghost" size="sm" onClick={() => setShowAdvanced(p => !p)}>
            Advanced {showAdvanced ? "▲" : "▼"}
          </Btn>
          {(categoryFilter || statusFilter || q || hasServicesFilter) && (
            <Btn variant="ghost" size="sm" onClick={() => { setCategoryFilter(""); setStatusFilter(""); setQ(""); setHasServicesFilter(""); }}>
              Clear Filters
            </Btn>
          )}
        </div>

        {showAdvanced && (
          <div style={{ marginTop: 12, display: "flex", gap: 12, flexWrap: "wrap", paddingTop: 12, borderTop: "1px solid var(--border)" }}>
            <div style={{ minWidth: 180 }}>
              <Select label="Has Services" value={hasServicesFilter}
                onChange={v => { setHasServicesFilter(v as "" | "true" | "false"); setPage(1); }}
                options={[{ value: "", label: "Any" }, { value: "true", label: "Has Services" }, { value: "false", label: "Empty Groups" }]} />
            </div>
            <div style={{ minWidth:180 }}><Select label="Sort by" value={sortBy} onChange={v=>{setSortBy(v);setPage(1)}} options={[{value:"display_order",label:"Display order"},{value:"name",label:"Name"},{value:"category",label:"Category"},{value:"status",label:"Status"},{value:"updated_at",label:"Last updated"}]}/></div>
            <div style={{ minWidth:140 }}><Select label="Direction" value={sortDir} onChange={v=>{setSortDir(v);setPage(1)}} options={[{value:"asc",label:"Ascending"},{value:"desc",label:"Descending"}]}/></div>
          </div>
        )}
      </Card>

      {/* Active filter chips */}
      {(categoryFilter || statusFilter || q || hasServicesFilter) && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          {categoryFilter && <Badge variant="muted">Category: {catMap[categoryFilter] ?? categoryFilter}</Badge>}
          {statusFilter && <Badge variant="muted">Status: {STATUS_LABEL[statusFilter] ?? statusFilter}</Badge>}
          {q && <Badge variant="muted">Search: {q}</Badge>}
          {hasServicesFilter && <Badge variant="muted">Has Services: {hasServicesFilter}</Badge>}
        </div>
      )}

      {selected.size > 0 && <Card padding={12} style={{ marginBottom:12, borderColor:"var(--brand)" }}><div style={{display:"flex",alignItems:"center",gap:8,flexWrap:"wrap"}}><b style={{fontSize:13}}>{selected.size} selected</b><Btn size="sm" variant="primary" loading={bulkAction.loading} onClick={()=>bulkAction.execute("activate")}>Activate</Btn><Btn size="sm" variant="secondary" loading={bulkAction.loading} onClick={()=>bulkAction.execute("deactivate")}>Deactivate</Btn><Btn size="sm" variant="ghost" onClick={()=>setSelected(new Set())}>Clear</Btn><span style={{marginLeft:"auto",fontSize:11,color:"var(--text-tertiary)"}}>Bulk actions are limited to 100 records per request.</span></div></Card>}

      {/* Error */}
      {groups.error && (
        <div style={{ padding: "12px 16px", borderRadius: 10, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", marginBottom: 16 }}>
          <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>
            <AlertCircle size={14} style={{ marginRight: 4 }} />
            {groups.error}
          </p>
        </div>
      )}

      {/* Table */}
      <DataTable
        columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
        rows={rows as unknown as Record<string, unknown>[]}
        loading={groups.loading}
        onRowClick={row => router.push(`/admin/service-groups/${(row as unknown as ServiceGroupEnriched).id}`)}
        emptyText={lifecycleFilter === "retired" ? "No retired service groups." : "No service groups found. Create your first service group to organize master services within a category."}
      />
      <DirectoryPagination
        page={page}
        pageSize={pageSize}
        total={groups.data?.total ?? 0}
        onPage={setPage}
        onPageSize={(value) => { setPageSize(value); setPage(1); }}
      />

      {/* Create / Edit Modal */}
      <Modal open={modal !== "none"} onClose={() => setModal("none")}
        title={editing ? `Edit: ${editing.name}` : "New Service Group"}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {activeAction.error && (
            <div style={{ padding: "10px 14px", borderRadius:"var(--radius-md)", background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>{activeAction.error}</p>
            </div>
          )}

          {!editing ? (
            <Select label="Category *" value={form.category_id} onChange={v => setF("category_id", v)}
              options={catOptions} placeholder="Select category…" />
          ) : (
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)" }}>Category (locked)</label>
              <p style={{ fontSize: 13, color: "var(--text-tertiary, var(--text-secondary))", margin: "6px 0 0" }}>{catMap[form.category_id] ?? form.category_id}</p>
            </div>
          )}

          <Input label="Group Name *" placeholder="e.g. AC Services" value={form.name}
            onChange={v => setF("name", v)} />
          <Input label="Code" placeholder="e.g. ac_services"
            value={form.code} onChange={v => setF("code", v)}
            hint="Unique identifier. Auto-filled from name." />
          <Input label="Description" placeholder="Optional context about this group"
            value={form.description} onChange={v => setF("description", v)} />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Input label="Display Order" type="number" value={String(form.display_order)}
              onChange={v => setF("display_order", parseInt(v) || 0)} />
            {editing && <div style={{alignSelf:"end",padding:"9px 11px",border:"1px solid var(--border)",borderRadius:8,fontSize:12,color:"var(--text-secondary)"}}>Status changes use audited row actions.</div>}
          </div>
          <IconPicker label="Icon" context="category_icon" value={form.icon_url}
            onChange={v => setF("icon_url", v ?? "")} />

          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="secondary" size="sm" onClick={() => setModal("none")}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={activeAction.loading} disabled={!canSave}
              onClick={() => editing
                ? editAction.execute({ id: editing.id, data: form })
                : createAction.execute(form)}>
              {editing ? "Save Changes" : "Create Group"}
            </Btn>
          </div>
        </div>
      </Modal>

      {/* Retire confirm */}
      <Modal open={!!archiveId} onClose={() => setArchiveId(null)} title="Retire Service Group">
        <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 16 }}>
          This will retire the service group. It will no longer appear in active catalogs.
          Only groups with no linked master services can be retired.
        </p>
        <textarea rows={3} value={archiveReason} onChange={e=>setArchiveReason(e.target.value)} placeholder="Retirement reason (minimum 10 characters)" style={{width:"100%",boxSizing:"border-box",padding:10,border:"1px solid var(--border)",borderRadius:8,background:"var(--input-bg)",color:"var(--text-primary)"}}/>
        {archiveAction.error && (
          <p style={{ fontSize: 13, color: "var(--danger-text)", marginBottom: 12 }}>{archiveAction.error}</p>
        )}
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <Btn variant="secondary" size="sm" onClick={() => setArchiveId(null)}>Cancel</Btn>
          <Btn variant="danger" size="sm" loading={archiveAction.loading} disabled={archiveReason.trim().length<10}
            onClick={() => archiveId && archiveAction.execute({id:archiveId,reason:archiveReason})}>
            Retire group
          </Btn>
        </div>
      </Modal>
      </div>
    </AdminLayout>
  );
}

function DirectoryPagination({
  page,
  pageSize,
  total,
  onPage,
  onPageSize,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPage: (page: number) => void;
  onPageSize: (pageSize: number) => void;
}) {
  return <Pagination page={page} pageSize={pageSize} total={total} onPage={onPage}
    pageSizes={[25, 50, 100]} onPageSize={size => { onPageSize(size); onPage(1); }} alwaysShow />;
}
