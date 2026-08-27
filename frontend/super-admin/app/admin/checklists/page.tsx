"use client";
import React, { useState, useCallback } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import HomeServicesCatalogNav from "../../../components/catalog/HomeServicesCatalogNav";
import { Card, Badge, Btn, Modal, Input, SectionHeader, DataTable, EmptyState, SummaryCard, Pagination,} from "../../../components/shared/ui";
import { IconPicker } from "../../../components/shared/IconPicker";
import {
  checklistCatalogApi, catalogApi, catalogWorkspaceApi,
  type ChecklistTemplateRow, type ChecklistTemplateVersionDetail, type ChecklistItemType,
  type JobTypeChecklistMappingRow, type ChecklistPurpose, type ChecklistUsage,
  type ChecklistActor, type ChecklistCompletionGate,
  type ServiceCategory, type MasterService, type MasterServiceJobTypeLink,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import OperationsDirectoryControls from "../../../components/enterprise/OperationsDirectoryControls";
import type { ColumnDef } from "../../../components/enterprise/EnterpriseColumnManager";
import { Plus, ClipboardList, CheckCircle2, Pencil, Archive, ListChecks, ShieldAlert, RefreshCw, Search, ExternalLink } from "lucide-react";

const PURPOSES: ChecklistPurpose[] = [
  "PRE_ARRIVAL", "INSPECTION", "PRE_WORK", "EXECUTION", "SAFETY", "COMPLETION", "HANDOVER",
];
const ITEM_TYPES: ChecklistItemType[] = [
  "CHECKBOX", "YES_NO", "SHORT_TEXT", "LONG_TEXT", "NUMBER", "MEASUREMENT",
  "SINGLE_SELECT", "MULTI_SELECT", "PHOTO", "DOCUMENT", "SIGNATURE",
];
const USAGES: ChecklistUsage[] = ["DISABLED", "OPTIONAL", "REQUIRED"];
const ACTORS: ChecklistActor[] = ["TECHNICIAN", "STAFF", "TENANT_ADMIN", "CUSTOMER"];
const GATES: ChecklistCompletionGate[] = [
  "NONE", "REQUIRE_BEFORE_INSPECTION_COMPLETE", "REQUIRE_BEFORE_ESTIMATE_SUBMISSION",
  "REQUIRE_BEFORE_WORK_START", "REQUIRE_BEFORE_JOB_COMPLETION", "REQUIRE_BEFORE_HANDOVER",
];

type Tab = "templates" | "mappings" | "health";
const TEMPLATE_COLUMNS: ColumnDef[] = [
  { key: "name", label: "Checklist", visible: true, order: 0 },
  { key: "code", label: "Code", visible: true, order: 1 },
  { key: "purpose", label: "Purpose", visible: true, order: 2 },
  { key: "version_status", label: "Version", visible: true, order: 3 },
  { key: "active_mapping_count", label: "Mappings", visible: true, order: 4 },
  { key: "updated_at", label: "Updated", visible: true, order: 5 },
];
const MAPPING_COLUMNS: ColumnDef[] = [
  { key: "template_name", label: "Checklist", visible: true, order: 0 },
  { key: "master_service_name", label: "Master Service", visible: true, order: 1 },
  { key: "job_type_label", label: "Job Type", visible: true, order: 2 },
  { key: "phase", label: "Phase", visible: true, order: 3 },
  { key: "usage", label: "Usage", visible: true, order: 4 },
  { key: "actor", label: "Actor", visible: true, order: 5 },
  { key: "completion_gate", label: "Gate", visible: true, order: 6 },
  { key: "status", label: "Status", visible: true, order: 7 },
];

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
  const [templateQuery, setTemplateQuery] = useState("");
  const [templatePurpose, setTemplatePurpose] = useState("");
  const [templateStatus, setTemplateStatus] = useState(() => searchParams.get("status") === "archived" ? "archived" : "active");
  const [templatePage, setTemplatePage] = useState(1);
  const [templatePageSize, setTemplatePageSize] = useState(25);
  const [templateColumns, setTemplateColumns] = useState<ColumnDef[]>(TEMPLATE_COLUMNS);
  const [mappingColumns, setMappingColumns] = useState<ColumnDef[]>(MAPPING_COLUMNS);
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
        subtitle="Create reusable checklists and publish them to exact job-type blueprints."
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn size="sm" variant="secondary" onClick={() => { templates.refetch(); mappings.refetch(); }}>
              <RefreshCw size={14} style={{ marginRight: 4 }}/> Refresh
            </Btn>
            <NewTemplateButton onCreated={() => { templates.refetch(); notify("Template created as a draft."); }} />
          </div>
        }
      />
      <HomeServicesCatalogNav active="checklists" />

      {tab === "templates" && (
        <OperationsDirectoryControls resourceKey="admin_checklist_templates"
          filters={{ q: templateQuery, status: templateStatus, purpose: templatePurpose }}
          sort={{ sort_by: "updated_at", sort_direction: "desc" }} columns={templateColumns}
          onColumnsChange={setTemplateColumns} onApplyView={(filters) => {
            setTemplateQuery(String(filters.q ?? filters.search ?? "")); setTemplateStatus(String(filters.status ?? "active"));
            setTemplatePurpose(String(filters.purpose ?? "")); setTemplatePage(1);
          }}/>
      )}
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
        <OperationsDirectoryControls resourceKey="admin_checklist_mappings"
          filters={{ q: mappingQuery, status: mappingStatus, usage: mappingUsage, actor: mappingActor }}
          sort={{ sort_by: "updated_at", sort_direction: "desc" }} columns={mappingColumns}
          onColumnsChange={setMappingColumns} onApplyView={(filters) => {
            setMappingQuery(String(filters.q ?? filters.search ?? "")); setMappingStatus(String(filters.status ?? ""));
            setMappingUsage(String(filters.usage ?? "")); setMappingActor(String(filters.actor ?? "")); setMappingPage(1);
          }}/>
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
            templates={templateList} loading={templates.loading}
            onRefetch={() => { templates.refetch(); mappings.refetch(); }}
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
            onRefetch={() => mappings.refetch()} notify={notify}
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

function NewTemplateButton({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", code: "", description: "", purpose: "INSPECTION" as ChecklistPurpose });
  const [iconUrl, setIconUrl] = useState<string | null>(null);
  const create = useAction(useCallback(async () => {
    await checklistCatalogApi.createTemplate({
      name: form.name, code: form.code || form.name.toUpperCase().replace(/[^A-Z0-9]+/g, "_").slice(0, 60),
      description: form.description || undefined, purpose: form.purpose,
      icon_url: iconUrl || undefined,
    });
    setOpen(false); setForm({ name: "", code: "", description: "", purpose: "INSPECTION" }); setIconUrl(null); onCreated();
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
            Templates start as an unmapped Draft. Runtime use requires an explicit Job-Type mapping (next step, in the Mappings tab).
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

function TemplatesWorkspace({ templates, loading, onRefetch, notify }: {
  templates: ChecklistTemplateRow[]; loading: boolean; onRefetch: () => void;
  notify: (msg: string, ok?: boolean) => void;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [retireOpen, setRetireOpen] = useState(false);
  const [retireReason, setRetireReason] = useState("");
  const selected = templates.find(t => t.id === selectedId) ?? null;

  const versionQuery = useApi(useCallback(
    () => selectedId
      ? (editing ? checklistCatalogApi.getOrCreateDraftVersion(selectedId) : checklistCatalogApi.getLatestVersion(selectedId))
      : Promise.resolve(null),
    [selectedId, editing]), [selectedId, editing]);
  const version: ChecklistTemplateVersionDetail | null = versionQuery.data;

  const publish = useAction(useCallback(async (changeSummary: string) => {
    if (!version) return;
    await checklistCatalogApi.publishVersion(version.id, changeSummary || undefined);
    setEditing(false);
    onRefetch(); notify("Version published.");
  }, [version, versionQuery, onRefetch, notify]));

  const archive = useAction(useCallback(async () => {
    if (!selected) return;
    await checklistCatalogApi.archiveTemplate(selected.id, retireReason);
    setRetireOpen(false); setRetireReason(""); setSelectedId(null);
    onRefetch(); notify("Template retired and active mappings disabled.");
  }, [selected, retireReason, onRefetch, notify]));

  if (!loading && templates.length === 0) {
    return (
      <Card padding={40}>
        <EmptyState
          icon={<ClipboardList size={28} />}
          title="No checklist templates yet"
          description="Create your first template, then map it to an exact Job Type before it can be used on real jobs."
        />
      </Card>
    );
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "280px 1fr 280px", gap: 16, alignItems: "start" }}>
      {/* Left: Template Library */}
      <Card padding={0}>
        <div style={{ padding: 14, borderBottom: "1px solid var(--border)", fontSize: 13, fontWeight: 600 }}>Template Library</div>
        <div style={{ maxHeight: 560, overflowY: "auto" }}>
          {templates.map(t => (
            <div key={t.id} onClick={() => { setSelectedId(t.id); setEditing(false); }} style={{
              padding: "12px 14px", cursor: "pointer",
              borderLeft: selectedId === t.id ? "3px solid var(--primary)" : "3px solid transparent",
              background: selectedId === t.id ? "var(--surface-sunken)" : "transparent",
              borderBottom: "1px solid var(--border)",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>{t.name}</span>
                <Badge size="sm" variant={t.latest_version?.status === "PUBLISHED" ? "success" : t.latest_version?.status === "ARCHIVED" ? "muted" : "warning"}>
                  {t.latest_version?.status ?? "DRAFT"}
                </Badge>
              </div>
              <div style={{ fontSize: 11, color: "var(--muted-text)", marginTop: 4 }}>
                v{t.latest_version?.version_number ?? 1} · {t.mapping_count} mapping{t.mapping_count === 1 ? "" : "s"}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Center: Editor */}
      <Card padding={0}>
        {!selected ? (
          <div style={{ padding: 40 }}>
            <EmptyState icon={<ClipboardList size={24} />} title="Select a template" description="Choose a template from the library to edit its checklist items." />
          </div>
        ) : (
          <div>
            <div style={{ padding: 16, borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text)" }}>{selected.name}</div>
                <div style={{ fontSize: 12, color: "var(--muted-text)", marginTop: 2 }}>{selected.description || "No description."}</div>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <Link href={`/admin/checklists/${selected.id}`}><Btn size="xs" variant="secondary"><ExternalLink size={12}/> Details</Btn></Link>
                {selected.status !== "archived" && (
                  <>
                  <Btn size="xs" variant="ghost" onClick={() => setRetireOpen(true)} loading={archive.loading}>
                    <Archive size={12} style={{ marginRight: 4 }} /> Retire
                  </Btn></>
                )}
              </div>
            </div>
            <div style={{ padding: 16 }}>
              {version && version.status !== "DRAFT" && (
                <div style={{ padding: "8px 12px", borderRadius: "var(--radius-md)", background: "var(--surface-sunken)",
                  border: "1px solid var(--border)", fontSize: 12, color: "var(--muted-text)", marginBottom: 12 }}>
                  Viewing immutable published v{version.version_number}. Start a draft to edit without changing live jobs.
                  <span style={{ marginLeft: 10 }}><Btn size="xs" variant="secondary" onClick={() => setEditing(true)}>Create editable draft</Btn></span>
                </div>
              )}
              {version?.sections.map(section => (
                <div key={section.id} style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 8 }}>{section.title}</div>
                  {section.items.map(item => (
                    <div key={item.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 10px",
                      border: "1px solid var(--border)", borderRadius: "var(--radius-md)", marginBottom: 6 }}>
                      <Badge size="sm" variant="info">{item.item_type}</Badge>
                      <span style={{ fontSize: 13, color: "var(--text)", flex: 1 }}>{item.label}</span>
                      {item.is_required && <Badge size="sm" variant="warning">Required</Badge>}
                      {item.evidence_required && <Badge size="sm" variant="muted">Evidence</Badge>}
                      {item.condition_rules && <Badge size="sm" variant="muted">Conditional</Badge>}
                    </div>
                  ))}
                  {version.status === "DRAFT" && <AddItemRow sectionId={section.id} onAdded={() => versionQuery.refetch()} />}
                </div>
              ))}
              {version?.status === "DRAFT" && <AddSectionRow versionId={version.id} onAdded={() => versionQuery.refetch()} />}

              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 20, borderTop: "1px solid var(--border)", paddingTop: 14 }}>
                <PublishControl disabled={!version || version.status !== "DRAFT"} loading={publish.loading}
                  onPublish={summary => publish.execute(summary)} />
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Right: Governance Inspector */}
      <Card padding={16}>
        <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12 }}>Governance Inspector</div>
        {!selected ? (
          <div style={{ fontSize: 12, color: "var(--muted-text)" }}>Select a template to view readiness and mapping impact.</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 6 }}>Version</div>
              <div style={{ fontSize: 13 }}>Current: <strong>{selected.latest_version?.version_number ?? "—"}</strong></div>
              <div style={{ fontSize: 13 }}>Status: <Badge size="sm" variant={selected.latest_version?.status === "PUBLISHED" ? "success" : "warning"}>{selected.latest_version?.status ?? "DRAFT"}</Badge></div>
            </div>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 6 }}>Mappings</div>
              <div style={{ fontSize: 13 }}>{selected.mapping_count} active Job-Type mapping{selected.mapping_count === 1 ? "" : "s"}</div>
            </div>
            <div style={{ padding: "10px 12px", borderRadius: "var(--radius-md)", background: "var(--warning-bg)",
              border: "1px solid var(--warning-border)", fontSize: 11, color: "var(--warning-text)" }}>
              Work start still requires approved estimate. Checklist gates complement, never replace, the estimate-approval gate.
            </div>
          </div>
        )}
      </Card>
      <Modal open={retireOpen} onClose={() => setRetireOpen(false)} title="Retire checklist template">
        <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>Historical job instances remain immutable. Active mappings are disabled so new jobs stop receiving this checklist.</p>
        <textarea value={retireReason} onChange={event => setRetireReason(event.target.value)} rows={3}
          placeholder="Reason for retirement (minimum 5 characters)" style={{ ...selectStyle, resize: "vertical" }}/>
        {archive.error && <p style={{ fontSize: 12, color: "var(--danger-text)" }}>{archive.error}</p>}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 14 }}>
          <Btn variant="secondary" onClick={() => setRetireOpen(false)}>Cancel</Btn>
          <Btn variant="danger" disabled={retireReason.trim().length < 5} loading={archive.loading} onClick={() => archive.execute()}>Retire template</Btn>
        </div>
      </Modal>
    </div>
  );
}

function PublishControl({ disabled, loading, onPublish }: { disabled: boolean; loading: boolean; onPublish: (summary: string) => void }) {
  const [summary, setSummary] = useState("");
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
      <input placeholder="Change summary (optional)" value={summary} onChange={e => setSummary(e.target.value)}
        style={{ ...selectStyle, width: 220 }} />
      <Btn size="sm" variant="primary" disabled={disabled} loading={loading} onClick={() => onPublish(summary)}>Publish Version</Btn>
    </div>
  );
}

function AddSectionRow({ versionId, onAdded }: { versionId: string | null; onAdded: () => void }) {
  const [title, setTitle] = useState("");
  const add = useAction(useCallback(async () => {
    if (!versionId || !title.trim()) return;
    await checklistCatalogApi.addSection(versionId, title.trim());
    setTitle(""); onAdded();
  }, [versionId, title, onAdded]));
  return (
    <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
      <input placeholder="New section title" value={title} onChange={e => setTitle(e.target.value)} style={selectStyle} />
      <Btn size="sm" variant="secondary" disabled={!title.trim()} loading={add.loading} onClick={() => add.execute()}>Add Section</Btn>
    </div>
  );
}

function AddItemRow({ sectionId, onAdded }: { sectionId: string; onAdded: () => void }) {
  const [label, setLabel] = useState("");
  const [itemType, setItemType] = useState<ChecklistItemType>("CHECKBOX");
  const [required, setRequired] = useState(false);
  const [evidence, setEvidence] = useState(false);
  const add = useAction(useCallback(async () => {
    if (!label.trim()) return;
    await checklistCatalogApi.addItem(sectionId, {
      item_type: itemType, label: label.trim(), is_required: required, evidence_required: evidence,
    });
    setLabel(""); setRequired(false); setEvidence(false); onAdded();
  }, [sectionId, label, itemType, required, evidence, onAdded]));
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginTop: 6 }}>
      <input placeholder="Item label" value={label} onChange={e => setLabel(e.target.value)} style={{ ...selectStyle, flex: 1, minWidth: 140 }} />
      <select value={itemType} onChange={e => setItemType(e.target.value as ChecklistItemType)} style={{ ...selectStyle, width: 140 }}>
        {ITEM_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
      </select>
      <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12 }}>
        <input type="checkbox" checked={required} onChange={e => setRequired(e.target.checked)} /> Required
      </label>
      <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12 }}>
        <input type="checkbox" checked={evidence} onChange={e => setEvidence(e.target.checked)} /> Evidence
      </label>
      <Btn size="xs" variant="secondary" disabled={!label.trim()} loading={add.loading} onClick={() => add.execute()}>Add Item</Btn>
    </div>
  );
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
        ) : <Btn size="xs" variant="ghost" onClick={async () => { await checklistCatalogApi.enableMapping(row.id); onRefetch(); notify("Mapping enabled."); }}>Enable</Btn>
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

  const cats = useApi(useCallback(() => catalogApi.listCategories(true), []), [], { enabled: open });
  const catList: ServiceCategory[] = cats.data?.categories ?? [];
  const svcs = useApi(useCallback(
    () => masterServiceId || !categoryId ? Promise.resolve({ services: [] as MasterService[] }) : catalogApi.listMasterServices(categoryId),
    [categoryId]), [categoryId], { enabled: open && !!categoryId });
  const svcList: MasterService[] = svcs.data?.services ?? [];
  const jobTypes = useApi(useCallback(
    () => masterServiceId ? catalogWorkspaceApi.getJobTypesForService(masterServiceId) : Promise.resolve({ items: [] as MasterServiceJobTypeLink[] }),
    [masterServiceId]), [masterServiceId], { enabled: open && !!masterServiceId });
  const jobTypeList: MasterServiceJobTypeLink[] = jobTypes.data?.items ?? [];

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
          {create.error && (
            <div style={{ padding: "10px 14px", borderRadius: 9, background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{create.error}</p>
            </div>
          )}
          <FieldRow label="Checklist Template Version (published only)">
            <input value={templateSearch} onChange={event => setTemplateSearch(event.target.value)}
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
            <input value={phase} onChange={e => setPhase(e.target.value)} placeholder="inspection" style={selectStyle} />
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
              {GATES.map(g => <option key={g} value={g}>{g.replace(/^REQUIRE_/, "").replace(/_/g, " ")}</option>)}
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
