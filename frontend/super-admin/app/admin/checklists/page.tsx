"use client";
import React, { useState, useCallback, useEffect, useRef } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import HomeServicesCatalogNav from "../../../components/catalog/HomeServicesCatalogNav";
import { Card, Badge, Btn, Modal, Input, SectionHeader, DataTable, EmptyState, SummaryCard, Pagination,} from "../../../components/shared/ui";
import { ChecklistTemplateEditor } from "../../../components/catalog/ChecklistTemplateEditor";
import { CHECKLIST_GATES, CHECKLIST_PURPOSES, checklistLabel } from "../../../components/catalog/checklist-config";
import { IconPicker } from "../../../components/shared/IconPicker";
import {
  checklistCatalogApi, catalogApi, catalogWorkspaceApi,
  type ChecklistTemplateRow,
  type JobTypeChecklistMappingRow, type ChecklistPurpose, type ChecklistUsage,
  type ChecklistActor, type ChecklistCompletionGate,
  type ServiceCategory, type MasterService, type MasterServiceJobTypeLink,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { Plus, ClipboardList, CheckCircle2, Pencil, ListChecks, ShieldAlert, RefreshCw, Search } from "lucide-react";

const PURPOSES: ChecklistPurpose[] = [
  "PRE_ARRIVAL", "INSPECTION", "PRE_WORK", "EXECUTION", "SAFETY", "COMPLETION", "HANDOVER",
];
const USAGES: ChecklistUsage[] = ["DISABLED", "OPTIONAL", "REQUIRED"];
const ACTORS: ChecklistActor[] = ["TECHNICIAN", "STAFF", "TENANT_ADMIN", "CUSTOMER"];

type Tab = "templates" | "mappings" | "health";
const selectStyle: React.CSSProperties = {
  width: "100%", padding: "8px 10px", borderRadius: "var(--radius-md)",
  border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text)",
  fontSize: 13, outline: "none",
};
const fieldLabel: React.CSSProperties = {
  fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 5,
};

function FieldRow({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label style={fieldLabel}>{label}</label>{children}</div>;
}

export default function ChecklistLibraryPage() {
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<Tab>("templates");
  const [createdTemplateId, setCreatedTemplateId] = useState<string | null>(null);
  const [templateQuery, setTemplateQuery] = useState("");
  const [templatePurpose, setTemplatePurpose] = useState("");
  const [templateStatus, setTemplateStatus] = useState(() => searchParams.get("status") === "archived" ? "archived" : "active");
  const [templatePage, setTemplatePage] = useState(1);
  const [templatePageSize, setTemplatePageSize] = useState(25);
  const [mappingQuery, setMappingQuery] = useState("");
  const [mappingUsage, setMappingUsage] = useState("");
  const [mappingActor, setMappingActor] = useState("");
  const [mappingStatus, setMappingStatus] = useState("");
  const [mappingPage, setMappingPage] = useState(1);
  const [mappingPageSize, setMappingPageSize] = useState(25);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const notify = (msg: string, ok = true) => { setToast({ msg, ok }); setTimeout(() => setToast(null), 3500); };

  const templates = useApi(useCallback(() => checklistCatalogApi.listTemplatesDirectory({
    q: templateQuery || undefined,
    status: templateStatus || undefined,
    purpose: (templatePurpose || undefined) as ChecklistPurpose | undefined,
    page: templatePage,
    page_size: templatePageSize,
  }), [templateQuery, templateStatus, templatePurpose, templatePage, templatePageSize]), [templateQuery, templateStatus, templatePurpose, templatePage, templatePageSize]);
  const templateList: ChecklistTemplateRow[] = templates.data?.items ?? [];
  const mappings = useApi(useCallback(() => checklistCatalogApi.listMappingsDirectory({
    q: mappingQuery || undefined,
    status: mappingStatus || undefined,
    usage: (mappingUsage || undefined) as ChecklistUsage | undefined,
    actor: (mappingActor || undefined) as ChecklistActor | undefined,
    page: mappingPage,
    page_size: mappingPageSize,
  }), [mappingQuery, mappingStatus, mappingUsage, mappingActor, mappingPage, mappingPageSize]), [mappingQuery, mappingStatus, mappingUsage, mappingActor, mappingPage, mappingPageSize]);
  const mappingList: JobTypeChecklistMappingRow[] = mappings.data?.items ?? [];
  const summary = useApi(useCallback(() => checklistCatalogApi.getSummary(), []));

  return (
    <AdminLayout activeNav="checklist-templates">
      <SectionHeader
        title="Checklist Library"
        subtitle="Author sections and items → publish a version → map it to the exact service and job type."
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn size="sm" variant="secondary" onClick={() => { templates.refetch(); mappings.refetch(); summary.refetch(); }}>
              <RefreshCw size={14} style={{ marginRight: 4 }}/> Refresh
            </Btn>
            <NewTemplateButton onCreated={id => { setCreatedTemplateId(id); setTemplateQuery(""); setTemplatePurpose(""); setTemplateStatus("active"); setTemplatePage(1); setTab("templates"); templates.refetch(); summary.refetch(); notify("Draft created. Add its sections and checklist items below."); }} />
          </div>
        }
      />
      <HomeServicesCatalogNav active="checklists" />

      {tab === "templates" && (
        <Card padding={14} style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <div style={{ position: "relative", flex: "1 1 280px" }}>
              <Search size={14} style={{ position: "absolute", left: 11, top: 10, color: "var(--text-tertiary)" }}/>
              <input aria-label="Search checklist templates" placeholder="Search name, code, or description…"
                value={templateQuery} onChange={e => { setTemplateQuery(e.target.value); setTemplatePage(1); }}
                style={{ ...selectStyle, paddingLeft: 34 }}/>
            </div>
            <select aria-label="Filter by checklist purpose" value={templatePurpose}
              onChange={e => { setTemplatePurpose(e.target.value); setTemplatePage(1); }}
              style={{ ...selectStyle, width: 210 }}>
              <option value="">All purposes</option>
              {PURPOSES.map(p => <option key={p} value={p}>{p.replace(/_/g, " ")}</option>)}
            </select>
            <select aria-label="Filter by checklist lifecycle" value={templateStatus}
              onChange={e => { setTemplateStatus(e.target.value); setTemplatePage(1); }} style={{ ...selectStyle, width: 160 }}>
              <option value="active">Active</option><option value="archived">Retired</option><option value="">All lifecycle</option>
            </select>
            <span style={{ fontSize: 12, color: "var(--text-tertiary)", marginLeft: "auto" }}>
              {templates.data?.total ?? 0} templates
            </span>
          </div>
        </Card>
      )}

      {tab === "mappings" && (
        <Card padding={14} style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <input aria-label="Search mappings" placeholder="Search phase or gate…" value={mappingQuery}
              onChange={e => { setMappingQuery(e.target.value); setMappingPage(1); }} style={{ ...selectStyle, width: 240 }}/>
            <select aria-label="Filter mapping status" value={mappingStatus}
              onChange={e => { setMappingStatus(e.target.value); setMappingPage(1); }}
              style={{ ...selectStyle, width: 190 }}>
              <option value="">All mapping statuses</option>
              <option value="active">Active</option>
              <option value="disabled">Disabled</option>
            </select>
            <select aria-label="Filter mapping usage" value={mappingUsage} onChange={e => { setMappingUsage(e.target.value); setMappingPage(1); }} style={{ ...selectStyle, width: 150 }}>
              <option value="">All usage</option>{USAGES.map(value => <option key={value}>{value}</option>)}
            </select>
            <select aria-label="Filter mapping actor" value={mappingActor} onChange={e => { setMappingActor(e.target.value); setMappingPage(1); }} style={{ ...selectStyle, width: 170 }}>
              <option value="">All actors</option>{ACTORS.map(value => <option key={value}>{value}</option>)}
            </select>
            <span style={{ fontSize: 12, color: "var(--text-tertiary)", marginLeft: "auto" }}>
              {mappings.data?.total ?? 0} mappings
            </span>
          </div>
        </Card>
      )}

      {toast && (
        <div style={{ padding: "10px 16px", borderRadius: 10, marginBottom: 12,
          background: toast.ok ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.ok ? "var(--success-text)" : "var(--danger-text)", fontSize: 13 }}>
          {toast.ok ? "✓" : "✗"} {toast.msg}
        </div>
      )}

      {(templates.error || mappings.error || summary.error) && <p role="alert" style={{ color: "var(--danger-text)" }}>{templates.error || mappings.error || summary.error} Use Refresh to retry.</p>}
      {/* Summary cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 20 }}>
        <SummaryCard icon={<ClipboardList />} label="Active Templates" value={summary.data?.active_templates ?? 0} />
        <SummaryCard icon={<CheckCircle2 />} label="Published Versions" value={summary.data?.published_versions ?? 0} accent="var(--success-text)" />
        <SummaryCard icon={<Pencil />} label="Draft Versions" value={summary.data?.draft_versions ?? 0} accent="var(--warning-text)" />
        <SummaryCard icon={<ShieldAlert />} label="Unmapped" value={summary.data?.unmapped_templates ?? 0} accent="var(--warning-text)" />
        <SummaryCard icon={<ListChecks />} label="Active Mappings" value={summary.data?.active_mappings ?? 0} />
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 20 }}>
        {([["templates", "Templates"], ["mappings", "Job-Type Mappings"], ["health", "Execution Health"]] as [Tab, string][]).map(([id, label]) => (
          <button key={id} onClick={() => setTab(id)} style={{
            padding: "10px 16px", fontSize: 13, fontWeight: 600, background: "none", border: "none",
            borderBottom: tab === id ? "2px solid var(--primary)" : "2px solid transparent",
            color: tab === id ? "var(--primary)" : "var(--text-secondary)", cursor: "pointer",
          }}>{label}</button>
        ))}
      </div>

      {tab === "templates" && (
        <>
          <TemplatesWorkspace
            templates={templateList} loading={templates.loading} preferredTemplateId={createdTemplateId}
            onRefetch={() => { templates.refetch(); mappings.refetch(); summary.refetch(); }}
            notify={notify}
          />
          <DirectoryPager page={templates.data?.page ?? templatePage} pages={templates.data?.pages ?? 1}
            total={templates.data?.total ?? 0} pageSize={templatePageSize} onPageSize={setTemplatePageSize} onPage={setTemplatePage}/>
        </>
      )}
      {tab === "mappings" && (
        <>
          <MappingsTab
            mappings={mappingList} loading={mappings.loading} templates={templateList}
            onRefetch={() => { mappings.refetch(); summary.refetch(); }} notify={notify}
          />
          <DirectoryPager page={mappings.data?.page ?? mappingPage} pages={mappings.data?.pages ?? 1}
            total={mappings.data?.total ?? 0} pageSize={mappingPageSize} onPageSize={setMappingPageSize} onPage={setMappingPage}/>
        </>
      )}
      {tab === "health" && <ExecutionHealthTab />}
    </AdminLayout>
  );
}

function DirectoryPager({ page, pages, total, pageSize, onPageSize, onPage }: { page: number; pages: number; total: number; pageSize: number; onPageSize: (size: number) => void; onPage: (page: number) => void }) {
  return <Pagination page={page} pageSize={pageSize} total={total} pageCount={pages} onPage={onPage}
    pageSizes={[25, 50, 100]} onPageSize={size => { onPageSize(size); onPage(1); }} alwaysShow />;
}


// ── New Template ──────────────────────────────────────────────────────────

function NewTemplateButton({ onCreated }: { onCreated: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", code: "", description: "", purpose: "INSPECTION" as ChecklistPurpose });
  const [iconUrl, setIconUrl] = useState<string | null>(null);
  const create = useAction(useCallback(async () => {
    const created = await checklistCatalogApi.createTemplate({
      name: form.name, code: form.code || form.name.toUpperCase().replace(/[^A-Z0-9]+/g, "_").slice(0, 60),
      description: form.description || undefined, purpose: form.purpose,
      icon_url: iconUrl || undefined,
    });
    setOpen(false); setForm({ name: "", code: "", description: "", purpose: "INSPECTION" }); setIconUrl(null); onCreated(created.id);
  }, [form, iconUrl, onCreated]));

  return (
    <>
      <Btn size="sm" variant="primary" onClick={() => setOpen(true)}>
        <Plus size={14} style={{ marginRight: 4 }} /> New Template
      </Btn>
      <Modal open={open} onClose={() => setOpen(false)} title="New Checklist Template" size="md">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {create.error && (
            <div style={{ padding: "10px 14px", borderRadius: 9, background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{create.error}</p>
            </div>
          )}
          <Input label="Name *" placeholder="AC Repair Inspection" value={form.name} onChange={v => setForm(f => ({ ...f, name: v }))} />
          <Input label="Code (auto-generated if blank)" placeholder="AC_REPAIR_INSPECTION" value={form.code}
            onChange={v => setForm(f => ({ ...f, code: v.toUpperCase() }))} />
          <FieldRow label="Purpose">
            <select value={form.purpose} onChange={e => setForm(f => ({ ...f, purpose: e.target.value as ChecklistPurpose }))} style={selectStyle}>
              {PURPOSES.map(p => <option key={p} value={p}>{p.replace(/_/g, " ")}</option>)}
            </select>
          </FieldRow>
          <FieldRow label="Description">
            <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              rows={2} placeholder="Technician inspection checklist before estimate preparation."
              style={{ ...selectStyle, fontFamily: "inherit", resize: "vertical" }} />
          </FieldRow>
          <IconPicker label="Icon" context="checklist_icon" value={iconUrl} onChange={setIconUrl}/>
          <div style={{ padding: "8px 12px", borderRadius: "var(--radius-md)", background: "var(--surface-sunken)",
            border: "1px solid var(--border)", fontSize: 12, color: "var(--muted-text)" }}>
            Create a draft, add sections and items, then publish. Only published versions can be mapped to a job type.
          </div>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setOpen(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" disabled={!form.name.trim()} loading={create.loading} onClick={() => create.execute()}>
              Create Draft
            </Btn>
          </div>
        </div>
      </Modal>
    </>
  );
}

// ── Templates workspace (3-column) ───────────────────────────────────────

function TemplatesWorkspace({ templates, loading, preferredTemplateId, onRefetch, notify }: {
  templates: ChecklistTemplateRow[]; loading: boolean; preferredTemplateId: string | null;
  onRefetch: () => void; notify: (message: string, ok?: boolean) => void;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const appliedPreferred = useRef<string | null>(null);
  useEffect(() => {
    if (preferredTemplateId && appliedPreferred.current !== preferredTemplateId && templates.some(row => row.id === preferredTemplateId)) {
      appliedPreferred.current = preferredTemplateId;
      setSelectedId(preferredTemplateId);
    }
    else if (!templates.some(row => row.id === selectedId)) setSelectedId(templates[0]?.id ?? null);
  }, [templates, preferredTemplateId, selectedId]);
  const selected = templates.find(row => row.id === selectedId);
  const [retireOpen, setRetireOpen] = useState(false);
  const [reason, setReason] = useState("");
  const retire = useAction(async () => {
    if (!selected) return;
    await checklistCatalogApi.archiveTemplate(selected.id, reason.trim());
    setRetireOpen(false); setReason(""); onRefetch(); notify("Template retired. Existing job records are preserved.");
  });
  if (loading && !templates.length) return <Card padding={24}>Loading checklists…</Card>;
  if (!templates.length) return <Card padding={32}><EmptyState icon={<ClipboardList/>} title="No templates match" description="Create a checklist template or adjust the filters."/></Card>;
  return <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "flex-start" }}>
    <Card padding={8} style={{ flex: "1 1 230px", maxWidth: 310 }}>
      <div style={{ padding: 10, fontWeight: 700, fontSize: 13 }}>Templates</div>
      {templates.map(row => <button key={row.id} onClick={() => setSelectedId(row.id)} aria-pressed={row.id === selectedId}
        style={{ display: "block", width: "100%", textAlign: "left", padding: 14, marginBottom: 4, border: "1px solid var(--border)", borderRadius: 8, background: row.id === selectedId ? "var(--surface-sunken)" : "transparent", color: "var(--text-primary)", cursor: "pointer" }}>
        <strong style={{ display: "block", marginBottom: 8 }}>{row.name}</strong>
        <Badge size="sm" variant={row.latest_version?.status === "PUBLISHED" ? "success" : "warning"}>{row.latest_version?.status ?? "DRAFT"}</Badge>
        <div style={{ marginTop: 8, fontSize: 12, color: "var(--text-secondary)" }}>{row.item_count ?? 0} items · {row.active_mapping_count ?? 0} active mappings</div>
      </button>)}
    </Card>
    <Card padding={20} style={{ flex: "3 1 520px", minWidth: 0 }}>
      {selected && <>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 16 }}>
          <div style={{ flex: 1 }}><h2 style={{ margin: "0 0 6px", fontSize: 20 }}>{selected.name}</h2><small>{selected.code} · {selected.purpose.replaceAll("_", " ")}</small></div>
          <Link href={`/admin/checklists/${selected.id}`}><Btn size="sm" variant="secondary">Details & history</Btn></Link>
          {selected.status !== "archived" && <Btn size="sm" variant="ghost" onClick={() => setRetireOpen(true)}>Retire</Btn>}
        </div>
        <ChecklistTemplateEditor key={selected.id} templateId={selected.id} retired={selected.status === "archived"} onChanged={onRefetch}/>
      </>}
    </Card>
    <Modal open={retireOpen} onClose={() => setRetireOpen(false)} title="Retire checklist template">
      <p>Active mappings will be disabled. Existing job checklists remain unchanged.</p>
      <textarea aria-label="Retirement reason" rows={3} style={selectStyle} value={reason} onChange={event => setReason(event.target.value)} placeholder="Reason (at least 5 characters)"/>
      {retire.error && <p role="alert">{retire.error}</p>}
      <Btn variant="danger" disabled={reason.trim().length < 5} loading={retire.loading} onClick={() => retire.execute()}>Retire template</Btn>
    </Modal>
  </div>;
}

// ── Job-Type Mappings tab ─────────────────────────────────────────────────

function MappingsTab({ mappings, loading, templates, onRefetch, notify }: {
  mappings: JobTypeChecklistMappingRow[]; loading: boolean; templates: ChecklistTemplateRow[];
  onRefetch: () => void; notify: (msg: string, ok?: boolean) => void;
}) {
  const [disableRow, setDisableRow] = useState<JobTypeChecklistMappingRow | null>(null);
  const [disableReason, setDisableReason] = useState("");
  const disable = useAction(useCallback(async () => {
    if (!disableRow) return;
    await checklistCatalogApi.disableMapping(disableRow.id, disableReason);
    setDisableRow(null); setDisableReason(""); onRefetch(); notify("Mapping disabled.");
  }, [disableRow, disableReason, onRefetch, notify]));
  const columns = [
    { key: "template_name", label: "Checklist", width: 170, render: (_: unknown, row: JobTypeChecklistMappingRow) => <span><strong>{row.template_name ?? "Unknown"}</strong><br/><small style={{color:"var(--text-tertiary)"}}>v{row.template_version ?? "—"}</small></span> },
    { key: "master_service_name", label: "Master Service", width: 150 },
    { key: "job_type_label", label: "Job Type", width: 120 },
    { key: "phase", label: "Phase", width: 120 },
    {
      key: "usage", label: "Usage", width: 100,
      render: (_: unknown, row: JobTypeChecklistMappingRow) => (
        <Badge size="sm" variant={row.usage === "REQUIRED" ? "warning" : row.usage === "DISABLED" ? "muted" : "info"}>{row.usage}</Badge>
      ),
    },
    { key: "actor", label: "Actor", width: 110 },
    {
      key: "completion_gate", label: "Gate", width: 220,
      render: (_: unknown, row: JobTypeChecklistMappingRow) => (
        <span style={{ fontSize: 12 }}>{row.completion_gate.replace(/^REQUIRE_/, "").replace(/_/g, " ")}</span>
      ),
    },
    {
      key: "status", label: "Status", width: 90,
      render: (_: unknown, row: JobTypeChecklistMappingRow) => (
        <Badge size="sm" variant={row.status === "active" ? "success" : "muted"}>{row.status}</Badge>
      ),
    },
    {
      key: "id", label: "Actions", width: 100,
      render: (_: unknown, row: JobTypeChecklistMappingRow) => (
        row.status === "active" ? (
          <Btn size="xs" variant="ghost" onClick={() => setDisableRow(row)}>
            Disable
          </Btn>
        ) : <Btn size="xs" variant="ghost" onClick={async () => { try { await checklistCatalogApi.enableMapping(row.id); onRefetch(); notify("Mapping enabled."); } catch (error) { notify(error instanceof Error ? error.message : "Could not enable mapping.", false); } }}>Enable</Btn>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <NewMappingButton onCreated={() => { onRefetch(); notify("Mapping created."); }} />
      </div>
      <Card padding={0}>
        <DataTable
          columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
          rows={mappings as unknown as Record<string, unknown>[]}
          loading={loading}
          emptyText="No Job-Type mappings yet. A checklist has no runtime effect until mapped to an exact Job Type."
        />
      </Card>
      <Modal open={!!disableRow} onClose={() => setDisableRow(null)} title="Disable checklist mapping">
        <p style={{fontSize:13,color:"var(--text-secondary)"}}>Existing job instances remain unchanged. New matching jobs will no longer receive this mapping.</p>
        <textarea value={disableReason} onChange={event=>setDisableReason(event.target.value)} rows={3} placeholder="Reason for disabling (minimum 5 characters)" style={{...selectStyle,resize:"vertical"}}/>
        {disable.error&&<p style={{fontSize:12,color:"var(--danger-text)"}}>{disable.error}</p>}
        <div style={{display:"flex",justifyContent:"flex-end",gap:8,marginTop:14}}><Btn variant="secondary" onClick={()=>setDisableRow(null)}>Cancel</Btn><Btn variant="danger" disabled={disableReason.trim().length<5} loading={disable.loading} onClick={()=>disable.execute()}>Disable mapping</Btn></div>
      </Modal>
    </div>
  );
}

function NewMappingButton({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [templateSearch, setTemplateSearch] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [masterServiceId, setMasterServiceId] = useState("");
  const [jobTypeLinkId, setJobTypeLinkId] = useState("");
  const [templateVersionId, setTemplateVersionId] = useState("");
  const [phase, setPhase] = useState("inspection");
  const [usage, setUsage] = useState<ChecklistUsage>("REQUIRED");
  const [actor, setActor] = useState<ChecklistActor>("TECHNICIAN");
  const [gate, setGate] = useState<ChecklistCompletionGate>("NONE");

  const templateOptions = useApi(useCallback(
    () => checklistCatalogApi.listPublishedTemplateOptions(templateSearch, 50),
    [templateSearch]), [templateSearch], { enabled: open });
  const publishedTemplates = templateOptions.data ?? [];
  const selectedPurpose = publishedTemplates.find(row => row.latest_version?.id === templateVersionId)?.purpose;
  const allowedGates = selectedPurpose ? CHECKLIST_GATES[selectedPurpose] : ["NONE" as ChecklistCompletionGate];
  useEffect(() => { if (!allowedGates.includes(gate)) setGate("NONE"); }, [selectedPurpose]);

  const cats = useApi(useCallback(() => catalogApi.listCategories(true), []), [], { enabled: open });
  const catList: ServiceCategory[] = cats.data?.categories ?? [];
  const svcs = useApi(useCallback(
    () => !categoryId ? Promise.resolve({ services: [] as MasterService[] }) : catalogApi.listMasterServices(categoryId),
    [categoryId]), [categoryId], { enabled: open && !!categoryId });
  const svcList: MasterService[] = svcs.data?.services ?? [];
  const jobTypes = useApi(useCallback(
    () => masterServiceId ? catalogWorkspaceApi.getJobTypesForService(masterServiceId) : Promise.resolve({ items: [] as MasterServiceJobTypeLink[] }),
    [masterServiceId]), [masterServiceId], { enabled: open && !!masterServiceId });
  const jobTypeList: MasterServiceJobTypeLink[] = (jobTypes.data?.items ?? []).filter(row => row.is_active);

  const create = useAction(useCallback(async () => {
    await checklistCatalogApi.createMapping({
      master_service_job_type_id: jobTypeLinkId, checklist_template_version_id: templateVersionId,
      phase, usage, actor, completion_gate: gate,
    });
    setOpen(false); onCreated();
  }, [jobTypeLinkId, templateVersionId, phase, usage, actor, gate, onCreated]));

  return (
    <>
      <Btn size="sm" variant="primary" onClick={() => setOpen(true)}>
        <Plus size={14} style={{ marginRight: 4 }} /> New Mapping
      </Btn>
      <Modal open={open} onClose={() => setOpen(false)} title="New Job-Type Checklist Mapping" size="md">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {(create.error || templateOptions.error || cats.error || svcs.error || jobTypes.error) && (
            <div style={{ padding: "10px 14px", borderRadius: 9, background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{create.error || templateOptions.error || cats.error || svcs.error || jobTypes.error}</p>
            </div>
          )}
          <FieldRow label="Checklist Template Version (published only)">
            <input value={templateSearch} onChange={event => { setTemplateSearch(event.target.value); setTemplateVersionId(""); }}
              placeholder="Search checklist name or code" style={{ ...selectStyle, marginBottom: 8 }} />
            <select value={templateVersionId} onChange={e => setTemplateVersionId(e.target.value)} style={selectStyle}>
              <option value="">— Select —</option>
              {publishedTemplates.map(t => (
                <option key={t.id} value={t.latest_version!.id}>{t.name} (v{t.latest_version!.version_number})</option>
              ))}
            </select>
          </FieldRow>
          <FieldRow label="Service Category (Business Vertical → Service Group entry point)">
            <select value={categoryId} onChange={e => { setCategoryId(e.target.value); setMasterServiceId(""); setJobTypeLinkId(""); }} style={selectStyle}>
              <option value="">— Select —</option>
              {catList.map(c => <option key={c.category_id} value={c.category_id}>{c.name}</option>)}
            </select>
          </FieldRow>
          {categoryId && (
            <FieldRow label="Master Service">
              <select value={masterServiceId} onChange={e => { setMasterServiceId(e.target.value); setJobTypeLinkId(""); }} style={selectStyle}>
                <option value="">— Select —</option>
                {svcList.map(s => <option key={s.service_id} value={s.service_id}>{s.service_name}</option>)}
              </select>
            </FieldRow>
          )}
          {masterServiceId && (
            <FieldRow label="Job Type (exact blueprint)">
              <select value={jobTypeLinkId} onChange={e => setJobTypeLinkId(e.target.value)} style={selectStyle}>
                <option value="">— Select —</option>
                {jobTypeList.map(l => <option key={l.id} value={l.id}>{l.job_type?.label ?? l.job_type_id}</option>)}
              </select>
            </FieldRow>
          )}
          <FieldRow label="Phase">
            <select aria-label="Checklist phase" value={phase} onChange={e => setPhase(e.target.value)} style={selectStyle}>{CHECKLIST_PURPOSES.map(value => <option key={value} value={value.toLowerCase()}>{checklistLabel(value)}</option>)}</select>
          </FieldRow>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <FieldRow label="Usage">
              <select value={usage} onChange={e => setUsage(e.target.value as ChecklistUsage)} style={selectStyle}>
                {USAGES.map(u => <option key={u} value={u}>{u}</option>)}
              </select>
            </FieldRow>
            <FieldRow label="Actor">
              <select value={actor} onChange={e => setActor(e.target.value as ChecklistActor)} style={selectStyle}>
                {ACTORS.map(a => <option key={a} value={a}>{a}</option>)}
              </select>
            </FieldRow>
          </div>
          <FieldRow label="Completion Gate">
            <select value={gate} onChange={e => setGate(e.target.value as ChecklistCompletionGate)} style={selectStyle}>
              {allowedGates.map(g => <option key={g} value={g}>{checklistLabel(g)}</option>)}
            </select>
          </FieldRow>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setOpen(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" disabled={!templateVersionId || !jobTypeLinkId} loading={create.loading} onClick={() => create.execute()}>
              Create Mapping
            </Btn>
          </div>
        </div>
      </Modal>
    </>
  );
}

// ── Execution Health tab ──────────────────────────────────────────────────

function ExecutionHealthTab() {
  const health = useApi(useCallback(() => checklistCatalogApi.getExecutionHealth(), []));
  const h = health.data;
  if (health.error) return <Card><p role="alert">{health.error}</p><Btn onClick={health.refetch}>Retry</Btn></Card>;
  if (health.loading) return <Card>Loading execution health…</Card>;
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
      <SummaryCard icon={<ClipboardList />} label="Total Instances" value={h?.total_instances ?? 0} />
      <SummaryCard icon={<CheckCircle2 />} label="Completed" value={h?.completed_instances ?? 0} accent="var(--success-text)" />
      <SummaryCard icon={<Pencil />} label="In Progress" value={h?.in_progress_instances ?? 0} accent="var(--warning-text)" />
      <SummaryCard icon={<ShieldAlert />} label="Blocked" value={h?.blocked_instances ?? 0} accent="var(--danger-text)" />
      <SummaryCard icon={<ListChecks />} label="Completion Rate"
        value={h?.required_completion_rate != null ? `${Math.round(h.required_completion_rate * 100)}%` as unknown as number : "—" as unknown as number} />
    </div>
  );
}
