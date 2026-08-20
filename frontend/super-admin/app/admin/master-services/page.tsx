"use client";
import React, { useState, useCallback, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import HomeServicesCatalogNav from "../../../components/catalog/HomeServicesCatalogNav";
import OperationsDirectoryControls from "../../../components/enterprise/OperationsDirectoryControls";
import type { ColumnDef } from "../../../components/enterprise/EnterpriseColumnManager";
import {
  Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader, SummaryCard,} from "../../../components/shared/ui";
import { IconPicker } from "../../../components/shared/IconPicker";
import {
  catalogApi,
  type MasterServiceEnriched, type ServiceCategory, type ServiceGroup,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { RefreshCw, AlertCircle, CheckSquare, Square, X } from "lucide-react";

// ── Constant maps ───────────────────────────────────────────────────────────────
const JOB_TYPES = [
  { value: "repair",          label: "Repair" },
  { value: "installation",    label: "Installation" },
  { value: "uninstallation",  label: "Uninstallation" },
  { value: "inspection",      label: "Inspection" },
  { value: "maintenance",     label: "Maintenance" },
  { value: "cleaning",        label: "Cleaning" },
  { value: "consultation",    label: "Consultation" },
  { value: "service",         label: "Service" },
  { value: "custom",          label: "Custom" },
];
const PRICING_MODELS = [
  { value: "fixed",           label: "Fixed" },
  { value: "range",           label: "Range" },
  { value: "post_assessment", label: "Post-Assessment" },
  { value: "hourly",          label: "Hourly" },
];
const READINESS_VARIANT: Record<string, "success" | "warning" | "muted" | "danger"> = {
  ready: "success", fallback_only: "warning", missing_rules: "danger",
  inactive: "muted", not_required: "muted",
  missing_brand_mapping: "warning", missing_service_options: "warning",
  missing_issue_types: "warning", missing_pricing: "danger",
  missing_job_types: "danger", missing_workflows: "warning",
  category_inactive: "danger", group_unavailable: "danger",
};
const READINESS_LABEL: Record<string, string> = {
  ready: "Ready", fallback_only: "Fallback", missing_rules: "No Rules",
  inactive: "Inactive", not_required: "—",
  missing_brand_mapping: "No Brands", missing_service_options: "No Options",
  missing_issue_types: "No Issues", missing_pricing: "No Pricing",
  missing_job_types: "No Job Types", missing_workflows: "Workflow Missing",
  category_inactive: "Category Inactive", group_unavailable: "Group Unavailable",
};

const DEFAULT_COLUMNS: ColumnDef[] = [
  { key:"select", label:"Select", visible:true, order:0 },
  { key:"name", label:"Master Service", visible:true, order:1 },
  { key:"job_type", label:"Legacy Job Type", visible:false, order:2 },
  { key:"pricing_model", label:"Legacy Pricing Behavior", visible:false, order:3 },
  { key:"requires_issue_type", label:"Requirements", visible:true, order:4 },
  { key:"linked_counts", label:"Blueprint", visible:true, order:5 },
  { key:"runtime_readiness", label:"Readiness", visible:true, order:6 },
  { key:"is_active", label:"Status", visible:true, order:7 },
  { key:"id", label:"Actions", visible:true, order:8 },
];

// ── Form types ─────────────────────────────────────────────────────────────────
type FormState = {
  name: string;
  category_id: string;
  service_group_id: string;
  description: string;
  icon_url: string;
};

const BLANK: FormState = {
  name: "", category_id: "", service_group_id: "", description: "", icon_url: "",
};

// ── Summary card ───────────────────────────────────────────────────────────────

// ── Chip group display ─────────────────────────────────────────────────────────
function ReqChips({ svc }: { svc: MasterServiceEnriched }) {
  const flags: { label: string; on: boolean }[] = [
    { label: "Brand", on: !!svc.is_brand_required },
    { label: "Type",  on: !!svc.is_type_required },
    { label: "Issue", on: !!svc.requires_issue_type },
    { label: "Checklist", on: !!svc.requires_checklist },
    { label: "Schedule",  on: !!svc.requires_schedule },
    { label: "Address",   on: !!svc.requires_address },
  ].filter(f => f.on);
  if (!flags.length) return <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>None</span>;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
      {flags.map(f => (
        <span key={f.label} style={{
          fontSize: 10, padding: "2px 6px", borderRadius: 4,
          background: "var(--brand-muted, rgba(26,86,219,.08))", color: "var(--brand, #1a56db)", fontWeight: 600,
        }}>{f.label}</span>
      ))}
    </div>
  );
}

// ── Linked counts display ──────────────────────────────────────────────────────
function LinkedCounts({ lc }: { lc: MasterServiceEnriched["linked_counts"] }) {
  const items = [
    { k: "brands", label: "Br" },
    { k: "options", label: "Opt" },
    { k: "issues", label: "Iss" },
    { k: "pricing_rules", label: "Pr" },
    { k: "providers", label: "Prov" },
  ] as const;
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      {items.map(({ k, label }) => (
        <div key={k} style={{ textAlign: "center" }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: lc[k] === 0 ? "var(--text-tertiary, var(--text-secondary))" : "var(--text-primary)" }}>{lc[k]}</span>
          <span style={{ fontSize: 10, color: "var(--text-secondary)", marginLeft: 2 }}>{label}</span>
        </div>
      ))}
    </div>
  );
}

// ── Action menu ────────────────────────────────────────────────────────────────
function ServiceActionMenu({ row, onEdit, onActivate, onDeactivate, onArchive, onView }: {
  row: MasterServiceEnriched;
  onEdit: () => void;
  onActivate: () => void;
  onDeactivate: () => void;
  onArchive: () => void;
  onView: () => void;
}) {
  const [open, setOpen] = useState(false);
  const items = [
    { label: "View Details", action: onView },
    { label: "Edit Service", action: onEdit },
    null,
    !row.is_active ? { label: "Activate", action: onActivate } : null,
    row.is_active ? { label: "Deactivate", action: onDeactivate } : null,
    { label: "Retire", action: onArchive, danger: true },
  ];
  return (
    <div style={{ position: "relative" }} onClick={e => e.stopPropagation()}>
      <Btn variant="ghost" size="xs" onClick={() => setOpen(o => !o)}>Actions ▾</Btn>
      {open && (
        <>
          <div style={{ position: "fixed", inset: 0, zIndex: 1000 }} onClick={() => setOpen(false)} />
          <div style={{
            position: "absolute", right: 0, top: "100%", zIndex: 1001, marginTop: 4,
            background: "var(--surface)", border: "1px solid var(--border)",
            borderRadius: 10, minWidth: 180, boxShadow: "0 8px 24px rgba(0,0,0,.12)",
            overflow: "hidden",
          }}>
            {items.map((item, i) =>
              item === null ? (
                <hr key={i} style={{ margin: 0, border: "none", borderTop: "1px solid var(--border)" }} />
              ) : item ? (
                <button key={i} onClick={() => { setOpen(false); item.action(); }} style={{
                  display: "block", width: "100%", textAlign: "left",
                  padding: "9px 16px", fontSize: 13, background: "none", border: "none",
                  cursor: "pointer", color: item.danger ? "var(--danger-text, #e53e3e)" : "var(--text-primary)",
                }}>
                  {item.label}
                </button>
              ) : null
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ── New Master Service -- canonical creation (migration 160) ────────────────
// Job-type-agnostic: Service Group, Service Name, Description, Display Order
// only. No Job Type, Pricing Model, prices, or Brand/Type/workflow
// requirement fields -- those are added afterward as Job-Type Blueprint
// child records in the Catalog Workspace, which this navigates to on success.
function MasterServiceCreateModal({ open, onClose, onCreated, catOptions, allGroups }: {
  open: boolean; onClose: () => void; onCreated: () => void;
  catOptions: { value: string; label: string }[];
  allGroups: { id: string; name: string; category_id: string }[];
}) {
  const [name, setName] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [groupId, setGroupId] = useState("");
  const [description, setDescription] = useState("");
  const [displayOrder, setDisplayOrder] = useState(0);
  const [iconUrl, setIconUrl] = useState<string | null>(null);
  const createAction = useAction(catalogApi.createMasterServiceV2);

  const groupOptions = useMemo(
    () => allGroups.filter(g => !categoryId || g.category_id === categoryId).map(g => ({ value: g.id, label: g.name })),
    [allGroups, categoryId]);

  function reset() {
    setName(""); setCategoryId(""); setGroupId(""); setDescription(""); setDisplayOrder(0); setIconUrl(null);
  }

  async function submit() {
    const result = await createAction.execute({
      service_name: name.trim(), category_id: categoryId, service_group_id: groupId,
      description: description.trim() || undefined, display_order: displayOrder,
      icon_url: iconUrl || undefined,
    });
    if (result) { reset(); onCreated(); }
  }

  const canSave = !!name.trim() && !!categoryId && !!groupId;

  return (
    <Modal open={open} onClose={onClose} title="New Master Service">
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {createAction.error && (
          <div style={{ padding: "10px 14px", borderRadius: "var(--radius-md)", background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
            <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>{createAction.error}</p>
          </div>
        )}
        {/* A master service cannot exist without a category and a group, so when
            none exist the form is unfillable. It used to just render two empty
            dropdowns and a permanently disabled Create button, with nothing
            saying why — say it, and link to where the prerequisite is made. */}
        {catOptions.length === 0 && (
          <div style={{ padding: "10px 14px", borderRadius: "var(--radius-md)",
            background: "var(--warning-bg)", border: "1px solid var(--warning-border)" }}>
            <p style={{ fontSize: 12, color: "var(--warning-text)", margin: 0 }}>
              No categories exist yet. A master service must belong to a category and a
              service group, so create those first in{" "}
              <a href="/admin/categories" style={{ color: "inherit", fontWeight: 700 }}>Categories</a>
              {" "}and{" "}
              <a href="/admin/service-groups" style={{ color: "inherit", fontWeight: 700 }}>Service Groups</a>.
            </p>
          </div>
        )}
        <Input label="Service Name *" placeholder="e.g. Air Conditioner" value={name} onChange={setName}/>
        {/* Labelled "Category" to match the filter bar, the edit modal and the
            Categories page — this one field called itself "Business Vertical"
            while everything else called the same thing a Category. */}
        <Select label="Category *" value={categoryId}
          onChange={v => { setCategoryId(v); setGroupId(""); }}
          options={catOptions}
          placeholder={catOptions.length ? "Select…" : "No categories available"}/>
        <Select label="Service Group *" value={groupId} onChange={setGroupId}
          options={groupOptions}
          placeholder={!categoryId ? "Select a category first"
            : groupOptions.length ? "Select…" : "No groups in this category"}/>
        {categoryId && groupOptions.length === 0 && (
          <p style={{ fontSize: 11, color: "var(--warning-text)", margin: "-6px 0 0" }}>
            This category has no service groups yet — create one in Service Groups first.
          </p>
        )}
        <Input label="Description" placeholder="Optional description for this service"
          value={description} onChange={setDescription}/>
        <Input label="Display Order" type="number" value={String(displayOrder)}
          onChange={v => setDisplayOrder(parseInt(v, 10) || 0)}/>
        <IconPicker label="Icon" context="service_icon" value={iconUrl} onChange={setIconUrl}/>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
          Job types (Repair, Installation, …), pricing behavior, and Brand/Type requirements are
          configured after creation, per job type, in this service's Job-Type Blueprint.
        </p>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <Btn variant="secondary" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" loading={createAction.loading} disabled={!canSave} onClick={submit}>
            Create Service
          </Btn>
        </div>
      </div>
    </Modal>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function MasterServicesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Filters
  // `qInput` is what the box shows; `q` is what the API is asked for. They are
  // separate because `q` is a refetch dependency — bound directly to the input
  // it fired one request per keystroke, so typing "air conditioner" cost 16
  // round trips and the results flickered through every prefix on the way.
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [groupFilter, setGroupFilter] = useState(() => searchParams.get("service_group_id") ?? "");
  const [jobTypeFilter, setJobTypeFilter] = useState("");
  const [pricingModelFilter, setPricingModelFilter] = useState("");
  const [isActiveFilter, setIsActiveFilter] = useState("");
  const [lifecycleFilter, setLifecycleFilter] = useState<"current" | "retired">(() => searchParams.get("lifecycle") === "retired" ? "retired" : "current");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 50;

  // Modal / detail
  const [modal, setModal] = useState<"none" | "create-service" | "edit">("none");
  const [editing, setEditing] = useState<MasterServiceEnriched | null>(null);
  const [archiveId, setArchiveId] = useState<string | null>(null);
  const [archiveReason, setArchiveReason] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [columnsConfig, setColumnsConfig] = useState<ColumnDef[]>(DEFAULT_COLUMNS);
  const [readinessFilter, setReadinessFilter] = useState("");
  const [hasProvidersFilter, setHasProvidersFilter] = useState("");
  const [sortBy, setSortBy] = useState("display_order");
  const [sortDir, setSortDir] = useState<"asc"|"desc">("asc");
  const [form, setForm] = useState<FormState>({ ...BLANK });
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  // Data
  // BUG FIX: useApi(fetcher, deps) needs deps passed to BOTH the inner
  // useCallback AND useApi itself -- its own `run` callback was memoized
  // with an empty/stale deps array, so category/group/filter changes never
  // actually refetched (same pattern already fixed on other pages this
  // session).
  const summary = useApi(useCallback(() => catalogApi.getMasterServicesSummary(), []), []);
  const categories = useApi(useCallback(() => catalogApi.listCategories(true), []), []);
  const allGroups = useApi(useCallback(
    () => catalogApi.listServiceGroups({ categoryId: categoryFilter || undefined }),
    [categoryFilter],
  ), [categoryFilter]);
  const services = useApi(useCallback(
    () => catalogApi.listMasterServicesEnterprise({
      q: q || undefined,
      categoryId: categoryFilter || undefined,
      serviceGroupId: groupFilter || undefined,
      jobType: jobTypeFilter || undefined,
      pricingModel: pricingModelFilter || undefined,
      isActive: isActiveFilter === "" ? undefined : isActiveFilter === "true",
      retired: lifecycleFilter === "retired",
      readiness: readinessFilter || undefined,
      hasProviders: hasProvidersFilter === "" ? undefined : hasProvidersFilter === "true",
      sortBy, sortDir,
      limit: pageSize,
      offset: (page - 1) * pageSize,
    }),
    [q, categoryFilter, groupFilter, jobTypeFilter, pricingModelFilter, isActiveFilter, lifecycleFilter, readinessFilter, hasProvidersFilter, sortBy, sortDir, page],
  ), [q, categoryFilter, groupFilter, jobTypeFilter, pricingModelFilter, isActiveFilter, lifecycleFilter, readinessFilter, hasProvidersFilter, sortBy, sortDir, page]);

  // Debounce the search box into the fetch dependency.
  React.useEffect(() => {
    const timer = setTimeout(() => {
      if (qInput.trim() !== q) { setQ(qInput.trim()); setPage(1); }
    }, 350);
    return () => clearTimeout(timer);
  }, [qInput, q]);

  // One shared timer: every notify() used to start its own without cancelling
  // the previous one, so a second toast inherited the first's countdown and
  // vanished early — and an unmount left the timer running.
  const toastTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const notify = React.useCallback((msg: string, ok = true) => {
    setToast({ msg, ok });
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 3500);
  }, []);
  React.useEffect(() => () => { if (toastTimer.current) clearTimeout(toastTimer.current); }, []);

  const catMap = useMemo(() => {
    const m: Record<string, string> = {};
    (categories.data?.categories ?? []).forEach((c: ServiceCategory) => { m[c.category_id] = c.name; });
    return m;
  }, [categories.data]);

  const groupMap = useMemo(() => {
    const m: Record<string, string> = {};
    (allGroups.data?.groups ?? []).forEach((g: ServiceGroup) => { m[g.id] = g.name; });
    return m;
  }, [allGroups.data]);

  const catOptions = useMemo(() =>
    (categories.data?.categories ?? []).map((c: ServiceCategory) => ({ value: c.category_id, label: c.name })),
    [categories.data]);

  const groupOptions = useMemo(() =>
    (allGroups.data?.groups ?? []).map((g: ServiceGroup) => ({ value: g.id, label: g.name })),
    [allGroups.data]);

  // Actions
  const editAction = useAction(async ({ id, data }: { id: string; data: FormState }) => {
    await catalogApi.updateMasterService(id, {
      service_name: data.name,
      service_group_id: data.service_group_id || undefined,
      // base_price/min_price/max_price are no longer admin-writable
      // (MODULE-L5-56) -- pricing is tenant-owned only.
      description: data.description || undefined,
      icon_url: data.icon_url || undefined,
      // Brand/Type/Issue/Checklist/Schedule/Address requirements are no
      // longer edited from this form -- they are configured per exact Job
      // Type in the Job-Type Blueprint (Dimensions/Problems & Questions/
      // Checklist/Workflow tabs). Existing values are left untouched here.
    });
    services.refetch(); summary.refetch(); setModal("none"); notify("Service updated.");
  });

  const activateAction = useAction(async (id: string) => {
    await catalogApi.activateMasterService(id);
    services.refetch(); summary.refetch(); notify("Service activated.");
  });

  const deactivateAction = useAction(async (id: string) => {
    await catalogApi.deactivateMasterService(id);
    services.refetch(); summary.refetch(); notify("Service deactivated.");
  });

  const archiveAction = useAction(async (id: string) => {
    await catalogApi.archiveMasterService(id, archiveReason);
    services.refetch(); summary.refetch(); setArchiveId(null); setArchiveReason(""); notify("Service retired and recorded in the audit trail.");
  });

  const bulkAction = useAction(async (action: "activate"|"deactivate") => {
    const result = await catalogApi.bulkMasterServiceStatus(selectedIds, action);
    setSelectedIds([]); await services.refetch(); await summary.refetch();
    notify(`${result.updated_count} service${result.updated_count === 1 ? "" : "s"} updated${result.errors.length ? `; ${result.errors.length} skipped` : ""}.`, result.errors.length === 0);
  });

  // Every filter that narrows the list, including the ones behind "Advanced".
  // The chip row and the Clear button previously ignored readiness/provider
  // usage, so a list could be filtered by them with nothing on screen saying so
  // and no way to undo it without reopening Advanced and hunting for the field.
  const activeFilters = useMemo(() => {
    const items: { key: string; label: string; clear: () => void }[] = [];
    if (q) items.push({ key: "q", label: `Search: ${q}`, clear: () => { setQInput(""); setQ(""); } });
    if (categoryFilter) items.push({ key: "cat", label: `Category: ${catMap[categoryFilter] ?? categoryFilter}`,
      clear: () => { setCategoryFilter(""); setGroupFilter(""); } });
    if (groupFilter) items.push({ key: "grp", label: `Group: ${groupMap[groupFilter] ?? groupFilter}`,
      clear: () => setGroupFilter("") });
    if (jobTypeFilter) items.push({ key: "jt", label: `Job Type: ${JOB_TYPES.find(j => j.value === jobTypeFilter)?.label ?? jobTypeFilter}`,
      clear: () => setJobTypeFilter("") });
    if (pricingModelFilter) items.push({ key: "pm", label: `Model: ${PRICING_MODELS.find(p => p.value === pricingModelFilter)?.label ?? pricingModelFilter}`,
      clear: () => setPricingModelFilter("") });
    if (isActiveFilter) items.push({ key: "act", label: `Status: ${isActiveFilter === "true" ? "Active" : "Inactive"}`,
      clear: () => setIsActiveFilter("") });
    if (readinessFilter) items.push({ key: "rdy", label: `Readiness: ${READINESS_LABEL[readinessFilter] ?? readinessFilter}`,
      clear: () => setReadinessFilter("") });
    if (hasProvidersFilter) items.push({ key: "prov", label: `Provider usage: ${hasProvidersFilter === "true" ? "Used" : "Not used"}`,
      clear: () => setHasProvidersFilter("") });
    return items;
  }, [q, categoryFilter, groupFilter, jobTypeFilter, pricingModelFilter, isActiveFilter,
      readinessFilter, hasProvidersFilter, catMap, groupMap]);

  const advancedFilterCount = (readinessFilter ? 1 : 0) + (hasProvidersFilter ? 1 : 0)
    + (jobTypeFilter ? 1 : 0) + (pricingModelFilter ? 1 : 0);

  function clearAllFilters() {
    setQInput(""); setQ(""); setCategoryFilter(""); setGroupFilter("");
    setJobTypeFilter(""); setPricingModelFilter(""); setIsActiveFilter("");
    setReadinessFilter(""); setHasProvidersFilter("");
    // Without this the page number survived the clear, so clearing filters on
    // page 4 left an empty table over a list that now had one page.
    setPage(1);
  }

  function openCreate() { setModal("create-service"); }
  function openEdit(svc: MasterServiceEnriched) {
    setForm({
      name: svc.name, category_id: svc.category_id,
      service_group_id: svc.service_group_id ?? "",
      description: svc.description ?? "",
      icon_url: svc.icon_url ?? "",
    });
    setEditing(svc); setModal("edit");
  }
  function setF<K extends keyof FormState>(k: K, v: FormState[K]) { setForm(p => ({ ...p, [k]: v })); }
  const canSave = !!form.name && !!form.category_id && !!form.service_group_id;
  const s = summary.data;
  const rows = services.data?.services ?? [];
  const activeAction = editAction;

  const allSelected = rows.length > 0 && rows.every(row => selectedIds.includes(row.id));
  const allColumns = [
    {
      key: "select", label: "",
      render: (_: unknown, row: MasterServiceEnriched) => <button aria-label={`Select ${row.name}`} onClick={event => { event.stopPropagation(); setSelectedIds(current => current.includes(row.id) ? current.filter(id => id !== row.id) : [...current, row.id]); }} style={{ border:0, background:"none", color:"var(--brand)", cursor:"pointer", padding:2 }}>{selectedIds.includes(row.id) ? <CheckSquare size={16}/> : <Square size={16}/>}</button>,
    },
    {
      key: "name", label: "Service",
      render: (_: unknown, row: MasterServiceEnriched) => row.deleted_at ? (
        <Btn variant="ghost" size="xs" onClick={() => router.push(`/admin/master-services/${row.id}`)}>View / restore</Btn>
      ) : (
        <div>
          <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{row.name}</span>
          <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-secondary)" }}>
            {catMap[row.category_id] ?? "—"}
            {row.service_group_id ? ` › ${groupMap[row.service_group_id] ?? "—"}` : ""}
          </p>
        </div>
      ),
    },
    {
      key: "job_type", label: "Legacy Job Type", width: 120,
      render: (_: unknown, row: MasterServiceEnriched) => (
        <Badge variant="muted">{JOB_TYPES.find(j => j.value === row.job_type)?.label ?? row.job_type}</Badge>
      ),
    },
    {
      key: "pricing_model", label: "Legacy Behavior", width: 120,
      render: (_: unknown, row: MasterServiceEnriched) => (
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
          {PRICING_MODELS.find(p => p.value === row.pricing_model)?.label ?? row.pricing_model}
        </span>
      ),
    },
    {
      key: "requires_issue_type", label: "Requirements",
      render: (_: unknown, row: MasterServiceEnriched) => <ReqChips svc={row} />,
    },
    {
      key: "linked_counts", label: "Blueprint",
      render: (_: unknown, row: MasterServiceEnriched) => <LinkedCounts lc={row.linked_counts} />,
    },
    {
      key: "runtime_readiness", label: "Runtime",
      render: (_: unknown, row: MasterServiceEnriched) => (
        <Badge variant={READINESS_VARIANT[row.runtime_readiness] ?? "muted"}>
          {READINESS_LABEL[row.runtime_readiness] ?? row.runtime_readiness}
        </Badge>
      ),
    },
    {
      key: "is_active", label: "Status", width: 90,
      render: (_: unknown, row: MasterServiceEnriched) => (
        <Badge variant={row.is_active ? "success" : "muted"}>{row.is_active ? "Active" : "Inactive"}</Badge>
      ),
    },
    {
      key: "id", label: "", width: 120,
      render: (_: unknown, row: MasterServiceEnriched) => (
        <ServiceActionMenu
          row={row}
          onView={() => router.push(`/admin/master-services/${row.id}`)}
          onEdit={() => openEdit(row)}
          onActivate={() => activateAction.execute(row.id)}
          onDeactivate={() => deactivateAction.execute(row.id)}
          onArchive={() => setArchiveId(row.id)}
        />
      ),
    },
  ];
  const visibleKeys = new Set(columnsConfig.filter(column => column.visible).map(column => column.key));
  const columns = allColumns.filter(column => visibleKeys.has(column.key));

  return (
    <AdminLayout activeNav="master-services">
      <div className="catalog-admin-page">
      <SectionHeader
        title="Master Services"
        subtitle="Canonical service identity and hierarchy. Configure job-type behavior in Catalog Workspace; providers own price amounts."
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="secondary" size="sm" onClick={() => { services.refetch(); summary.refetch(); }}>
              <RefreshCw size={14} style={{ marginRight: 4 }} /> Refresh
            </Btn>
            <Btn variant="primary" size="sm" onClick={openCreate}>+ New Service</Btn>
          </div>
        }
      />
      <HomeServicesCatalogNav active="services" />

      <OperationsDirectoryControls resourceKey="admin_master_services"
        filters={{ q, category_id:categoryFilter, service_group_id:groupFilter, job_type:jobTypeFilter, pricing_model:pricingModelFilter, is_active:isActiveFilter, lifecycle:lifecycleFilter, readiness:readinessFilter, has_providers:hasProvidersFilter }}
        sort={{ sort_by:sortBy, sort_direction:sortDir }} columns={columnsConfig}
        onColumnsChange={setColumnsConfig}
        onApplyView={(filters, sort) => {
          setQ(String(filters.q ?? filters.search ?? "")); setCategoryFilter(String(filters.category_id ?? ""));
          setGroupFilter(String(filters.service_group_id ?? "")); setJobTypeFilter(String(filters.job_type ?? ""));
          setPricingModelFilter(String(filters.pricing_model ?? "")); setIsActiveFilter(String(filters.is_active ?? ""));
          setLifecycleFilter(filters.lifecycle === "retired" ? "retired" : "current");
          setReadinessFilter(String(filters.readiness ?? "")); setHasProvidersFilter(String(filters.has_providers ?? ""));
          setSortBy(String(sort.sort_by ?? "display_order")); setSortDir(String(sort.sort_direction ?? "asc") as "asc"|"desc"); setPage(1);
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
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
          <SummaryCard label="Total Services" value={s.total} />
          <SummaryCard label="Active" value={s.active} accent="var(--success-text, #22543d)" />
          <SummaryCard label="Inactive" value={s.inactive} accent="var(--warning-text, #744210)" />
          <SummaryCard label="Blueprint Ready" value={s.blueprint_ready} accent="var(--brand, #1a56db)" />
          <SummaryCard label="Needs Blueprint Work" value={s.blueprint_attention} accent="var(--danger-text, #c53030)" />
          <SummaryCard label="Provider Enabled" value={s.provider_enabled} />
        </div>
      )}
      {summary.loading && (
        <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
          {[...Array(6)].map((_, i) => (
            <div key={i} style={{ flex: "1 1 140px", height: 80, borderRadius:"var(--radius-lg)", background: "var(--border)" }} className="skeleton" />
          ))}
        </div>
      )}
      {/* A failed summary used to render nothing at all — not the cards, not the
          skeleton, not an error — so the KPI row silently disappeared and looked
          like a layout glitch rather than a failed request. */}
      {!summary.loading && summary.error && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 20, padding: "10px 14px",
          borderRadius: "var(--radius-md)", background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
          <AlertCircle size={14} style={{ color: "var(--danger-text)", flexShrink: 0 }} />
          <span style={{ fontSize: 12, color: "var(--danger-text)" }}>
            Summary counts unavailable: {summary.error}
          </span>
          <Btn size="xs" variant="ghost" onClick={() => summary.refetch()}>Retry</Btn>
        </div>
      )}

      {lifecycleFilter === "current" && selectedIds.length > 0 && <Card padding={12} style={{ marginBottom:14, borderColor:"var(--brand)" }}><div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", gap:12 }}><span style={{ fontSize:13, fontWeight:650 }}>{selectedIds.length} selected</span><div style={{ display:"flex", gap:8 }}><Btn size="sm" variant="secondary" loading={bulkAction.loading} onClick={()=>bulkAction.execute("activate")}>Activate</Btn><Btn size="sm" variant="secondary" loading={bulkAction.loading} onClick={()=>bulkAction.execute("deactivate")}>Deactivate</Btn><Btn size="sm" variant="ghost" onClick={()=>setSelectedIds([])}>Clear</Btn></div></div>{bulkAction.error && <p style={{ color:"var(--danger-text)", fontSize:12 }}>{bulkAction.error}</p>}</Card>}

      {/* By job type breakdown */}
      {s?.by_job_type && Object.keys(s.by_job_type).length > 0 && (
        <div style={{ marginBottom: 16, display: "flex", gap: 8, flexWrap: "wrap" }}>
          {Object.entries(s.by_job_type).map(([jt, count]) => (
            <button key={jt} onClick={() => { setJobTypeFilter(jobTypeFilter === jt ? "" : jt); setPage(1); }} style={{
              padding: "4px 12px", borderRadius: 20, fontSize: 12, fontWeight: 500,
              border: `1px solid ${jobTypeFilter === jt ? "var(--brand, #1a56db)" : "var(--border)"}`,
              background: jobTypeFilter === jt ? "var(--brand-muted, rgba(26,86,219,.08))" : "var(--surface)",
              color: jobTypeFilter === jt ? "var(--brand, #1a56db)" : "var(--text-secondary)",
              cursor: "pointer",
            }}>
              {JOB_TYPES.find(j => j.value === jt)?.label ?? jt}: {count as number}
            </button>
          ))}
        </div>
      )}

      {/* Filters */}
      <Card padding={16} style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <input
              placeholder="Search by service name…"
              aria-label="Search master services"
              value={qInput} onChange={e => setQInput(e.target.value)}
              style={{
                width: "100%", padding: "8px 12px", borderRadius:"var(--radius-md)", fontSize: 13,
                border: "1px solid var(--border)", background: "var(--surface)",
                color: "var(--text-primary)", outline: "none", boxSizing: "border-box",
              }}
            />
          </div>
          <div style={{ minWidth: 180 }}>
            <Select label="" value={categoryFilter} onChange={v => { setCategoryFilter(v); setGroupFilter(""); setPage(1); }}
              placeholder="All Categories"
              options={[{ value: "", label: "All Categories" }, ...catOptions]} />
          </div>
          <div style={{ minWidth: 160 }}>
            <Select label="" value={groupFilter} onChange={v => { setGroupFilter(v); setPage(1); }}
              placeholder="All Groups"
              options={[{ value: "", label: "All Groups" }, ...groupOptions]} />
          </div>
          <div style={{ minWidth: 140 }}>
            <Select label="" value={isActiveFilter} onChange={v => { setIsActiveFilter(v); setPage(1); }}
              placeholder="Any Status"
              options={[{ value: "", label: "Any Status" }, { value: "true", label: "Active" }, { value: "false", label: "Inactive" }]} />
          </div>
          <div style={{ minWidth: 150 }}>
            <Select label="" value={lifecycleFilter} onChange={value => { setLifecycleFilter(value as "current" | "retired"); setIsActiveFilter(""); setSelectedIds([]); setPage(1); }}
              options={[{ value: "current", label: "Current records" }, { value: "retired", label: `Retired (${s?.retired ?? 0})` }]} />
          </div>
          {/* The count makes filters hidden behind this panel visible from the
              outside — previously an Advanced filter could be narrowing the
              list with no on-screen trace of it at all. */}
          <Btn variant="ghost" size="sm" onClick={() => setShowAdvanced(p => !p)}>
            Advanced{advancedFilterCount > 0 ? ` (${advancedFilterCount})` : ""} {showAdvanced ? "▲" : "▼"}
          </Btn>
          {activeFilters.length > 0 && (
            <Btn variant="ghost" size="sm" onClick={clearAllFilters}>
              Clear {activeFilters.length > 1 ? `all (${activeFilters.length})` : ""}
            </Btn>
          )}
        </div>

        {showAdvanced && (
          <div style={{ marginTop: 12, display: "flex", gap: 12, flexWrap: "wrap", paddingTop: 12, borderTop: "1px solid var(--border)" }}>
            <div style={{ minWidth: 160 }}>
              {/* setPage(1) like every other filter — without it, changing job
                  type while on page 3 asked for page 3 of a shorter list. */}
              <Select label="Job Type" value={jobTypeFilter} onChange={v => { setJobTypeFilter(v); setPage(1); }}
                options={[{ value: "", label: "All Job Types" }, ...JOB_TYPES]} />
            </div>
            <div style={{ minWidth: 180 }}>
              <Select label="Pricing Model" value={pricingModelFilter} onChange={v => { setPricingModelFilter(v); setPage(1); }}
                options={[{ value: "", label: "All Models" }, ...PRICING_MODELS]} />
            </div>
            <div style={{ minWidth: 190 }}>
              <Select label="Runtime Readiness" value={readinessFilter} onChange={v=>{setReadinessFilter(v);setPage(1)}} options={[{value:"",label:"All readiness"},{value:"ready",label:"Ready"},{value:"missing_job_types",label:"Missing job types"},{value:"missing_workflows",label:"Missing workflow"},{value:"category_inactive",label:"Category inactive"},{value:"group_unavailable",label:"Group unavailable"},{value:"inactive",label:"Inactive"}]}/>
            </div>
            <div style={{ minWidth: 170 }}>
              <Select label="Provider Usage" value={hasProvidersFilter} onChange={v=>{setHasProvidersFilter(v);setPage(1)}} options={[{value:"",label:"Any usage"},{value:"true",label:"Used by providers"},{value:"false",label:"Not used"}]}/>
            </div>
            <div style={{ minWidth: 160 }}>
              <Select label="Sort" value={sortBy} onChange={v=>{setSortBy(v);setPage(1)}} options={[{value:"display_order",label:"Display order"},{value:"name",label:"Service name"},{value:"updated_at",label:"Last updated"},{value:"created_at",label:"Created"}]}/>
            </div>
            <div style={{ minWidth: 120 }}>
              <Select label="Direction" value={sortDir} onChange={v=>{setSortDir(v as "asc"|"desc");setPage(1)}} options={[{value:"asc",label:"Ascending"},{value:"desc",label:"Descending"}]}/>
            </div>
          </div>
        )}
      </Card>

      {/* Active filter chips — every filter including Advanced, each removable
          on its own. They were previously read-only badges that also omitted
          the Advanced filters entirely. */}
      {activeFilters.length > 0 && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12, alignItems: "center" }}>
          {activeFilters.map(f => (
            <span key={f.key} style={{
              display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12,
              padding: "4px 8px 4px 10px", borderRadius: 999,
              background: "var(--surface-sunken)", border: "1px solid var(--border)",
              color: "var(--text-secondary)",
            }}>
              {f.label}
              <button type="button" aria-label={`Remove filter ${f.label}`}
                onClick={() => { f.clear(); setPage(1); }}
                style={{ border: 0, background: "none", cursor: "pointer", padding: 0,
                  display: "flex", color: "var(--text-tertiary)" }}>
                <X size={12}/>
              </button>
            </span>
          ))}
        </div>
      )}

      {services.error && (
        <div style={{ padding: "12px 16px", borderRadius: 10, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", marginBottom: 16 }}>
          <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>
            <AlertCircle size={14} style={{ marginRight: 4 }} />
            {services.error}
          </p>
        </div>
      )}

      {/* Table */}
      {lifecycleFilter === "current" && rows.length > 0 && <div style={{ display:"flex", justifyContent:"flex-end", marginBottom:8 }}><Btn size="xs" variant="ghost" onClick={()=>setSelectedIds(allSelected ? [] : rows.map(row=>row.id))}>{allSelected ? <CheckSquare size={14}/> : <Square size={14}/>} {allSelected ? "Clear page selection" : "Select this page"}</Btn></div>}
      <DataTable
        columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
        rows={rows as unknown as Record<string, unknown>[]}
        loading={services.loading}
        onRowClick={row => router.push(`/admin/master-services/${(row as unknown as MasterServiceEnriched).id}`)}
        emptyText={
          lifecycleFilter === "retired" ? "No retired master services."
          : activeFilters.length > 0
            // Distinguish "nothing matches your filters" from "the catalog is
            // empty" — the old text told an admin whose filter simply matched
            // nothing to go and create a service.
            ? "No master services match these filters. Clear them to see everything."
            : catOptions.length === 0
              ? "No master services yet — and no categories exist to create one under. Start with Categories, then Service Groups."
              : "No master services found. Create your first service to populate the catalog."
        }
      />
      <MasterServicesPagination page={page} pageSize={pageSize} total={services.data?.total ?? 0} onPage={setPage} />

      {/* Edit Modal (existing services only -- job_type/pricing_model/prices/
          Brand/Type/workflow requirements kept here ONLY for backward
          compatibility with services created before migration 160; new
          services are created job-type-agnostic via the modal below and
          configure these per job type in their Job-Type Blueprint) */}
      <Modal open={modal === "edit"} onClose={() => setModal("none")}
        title={`Edit: ${editing?.name ?? ""}`}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14, maxHeight: "70vh", overflowY: "auto", paddingRight: 4 }}>
          {activeAction.error && (
            <div style={{ padding: "10px 14px", borderRadius:"var(--radius-md)", background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>{activeAction.error}</p>
            </div>
          )}

          <Input label="Service Name *" placeholder="e.g. AC Gas Refill" value={form.name}
            onChange={v => setF("name", v)} />

          <div>
            <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)" }}>Category (locked)</label>
            <p style={{ fontSize: 13, color: "var(--text-tertiary, var(--text-secondary))", margin: "6px 0 0" }}>{catMap[form.category_id] ?? form.category_id}</p>
          </div>

          <Select label="Service Group *" value={form.service_group_id}
            onChange={v => setF("service_group_id", v)}
            options={groupOptions}
            placeholder="Choose service group" />

          <div style={{ padding: "10px 12px", borderRadius: "var(--radius-md)", background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
            <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)" }}>
              Job types and runtime behavior are configured in Catalog Workspace. Price amounts are tenant-owned.
              Activation and deactivation use separate audited lifecycle actions.
            </p>
          </div>

          <Input label="Description" placeholder="Optional description for this service"
            value={form.description} onChange={v => setF("description", v)} />

          <IconPicker label="Icon" context="service_icon" value={form.icon_url}
            onChange={v => setF("icon_url", v ?? "")} />

          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="secondary" size="sm" onClick={() => setModal("none")}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={activeAction.loading} disabled={!canSave}
              onClick={() => { if (editing) editAction.execute({ id: editing.id, data: form }); }}>
              Save Changes
            </Btn>
          </div>
        </div>
      </Modal>

      {/* New Master Service -- canonical creation (migration 160), a focused
          form, not the full legacy modal. Navigates to the Catalog Workspace
          on success so the admin can add and configure job types. */}
      <MasterServiceCreateModal open={modal === "create-service"} onClose={() => setModal("none")}
        catOptions={catOptions} allGroups={allGroups.data?.groups ?? []}
        onCreated={() => {
          services.refetch(); summary.refetch(); setModal("none");
          notify("Master service created. Add job types in the Catalog Workspace.");
          router.push("/admin/catalog-workspace");
        }}/>

      {/* Archive confirm */}
      <Modal open={!!archiveId} onClose={() => setArchiveId(null)} title="Retire Master Service">
        <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 16 }}>
          Retirement is blocked while any provider workspace still has this service enabled. Retired services remain auditable and can be restored as inactive.
        </p>
        <textarea value={archiveReason} onChange={event=>setArchiveReason(event.target.value)} rows={3} placeholder="Reason for retiring (minimum 10 characters)" style={{ width:"100%", boxSizing:"border-box", padding:10, borderRadius:8, border:"1px solid var(--border)", background:"var(--input-bg)", color:"var(--text-primary)" }}/>
        {archiveAction.error && (
          <p style={{ fontSize: 13, color: "var(--danger-text)", marginBottom: 12 }}>{archiveAction.error}</p>
        )}
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <Btn variant="secondary" size="sm" onClick={() => setArchiveId(null)}>Cancel</Btn>
          <Btn variant="danger" size="sm" loading={archiveAction.loading} disabled={archiveReason.trim().length<10}
            onClick={() => archiveId && archiveAction.execute(archiveId)}>
            Retire service
          </Btn>
        </div>
      </Modal>
      </div>
    </AdminLayout>
  );
}

function MasterServicesPagination({ page, pageSize, total, onPage }: { page: number; pageSize: number; total: number; onPage: (page: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginTop: 14 }}>
      <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
        {total ? `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} of ${total}` : "0 records"}
      </span>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Btn size="sm" variant="secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</Btn>
        <Badge variant="muted">Page {page} of {pages}</Badge>
        <Btn size="sm" variant="secondary" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</Btn>
      </div>
    </div>
  );
}
