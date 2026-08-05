"use client";
import React, { useState, useCallback } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Modal, Input, SectionHeader, DataTable, EmptyState, SummaryCard,} from "../../../components/shared/ui";
import { IconPicker } from "../../../components/shared/IconPicker";
import {
  checklistCatalogApi, catalogApi, catalogWorkspaceApi,
  type ChecklistTemplateRow, type ChecklistTemplateVersionDetail, type ChecklistItemType,
  type JobTypeChecklistMappingRow, type ChecklistPurpose, type ChecklistUsage,
  type ChecklistActor, type ChecklistCompletionGate,
  type ServiceCategory, type MasterService, type MasterServiceJobTypeLink,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { Plus, ClipboardList, CheckCircle2, Pencil, Archive, ListChecks, ShieldAlert } from "lucide-react";

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
  const [tab, setTab] = useState<Tab>("templates");
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const notify = (msg: string, ok = true) => { setToast({ msg, ok }); setTimeout(() => setToast(null), 3500); };

  const templates = useApi(useCallback(() => checklistCatalogApi.listTemplates(), []));
  const templateList: ChecklistTemplateRow[] = templates.data ?? [];
  const mappings = useApi(useCallback(() => checklistCatalogApi.listMappings(), []));
  const mappingList: JobTypeChecklistMappingRow[] = mappings.data ?? [];

  const publishedCount = templateList.filter(t => t.latest_version?.status === "PUBLISHED").length;
  const draftCount = templateList.filter(t => t.latest_version?.status === "DRAFT").length;
  const needReviewCount = templateList.filter(t => t.latest_version?.status === "DRAFT" && t.mapping_count > 0).length;

  return (
    <AdminLayout activeNav="checklist-templates">
      <SectionHeader
        title="Checklist Library"
        subtitle="Create reusable checklists and publish them to exact job-type blueprints."
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn size="sm" variant="secondary">Preview</Btn>
            <Btn size="sm" variant="secondary">View Audit</Btn>
            <NewTemplateButton onCreated={() => { templates.refetch(); notify("Template created as a draft."); }} />
          </div>
        }
      />

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
        <SummaryCard icon={<ClipboardList />} label="Templates" value={templateList.length} />
        <SummaryCard icon={<CheckCircle2 />} label="Published" value={publishedCount} accent="var(--success-text)" />
        <SummaryCard icon={<Pencil />} label="Draft" value={draftCount} accent="var(--warning-text)" />
        <SummaryCard icon={<ShieldAlert />} label="Need Review" value={needReviewCount} accent="var(--warning-text)" />
        <SummaryCard icon={<ListChecks />} label="Job-Type Mappings" value={mappingList.length} />
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
        <TemplatesWorkspace
          templates={templateList} loading={templates.loading}
          onRefetch={() => { templates.refetch(); mappings.refetch(); }}
          notify={notify}
        />
      )}
      {tab === "mappings" && (
        <MappingsTab
          mappings={mappingList} loading={mappings.loading} templates={templateList}
          onRefetch={() => mappings.refetch()} notify={notify}
        />
      )}
      {tab === "health" && <ExecutionHealthTab />}
    </AdminLayout>
  );
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
  const selected = templates.find(t => t.id === selectedId) ?? null;

  const versionQuery = useApi(useCallback(
    () => selectedId ? checklistCatalogApi.getOrCreateDraftVersion(selectedId) : Promise.resolve(null),
    [selectedId]), [selectedId]);
  const version: ChecklistTemplateVersionDetail | null = versionQuery.data;

  const publish = useAction(useCallback(async (changeSummary: string) => {
    if (!version) return;
    await checklistCatalogApi.publishVersion(version.id, changeSummary || undefined);
    versionQuery.refetch(); onRefetch(); notify("Version published.");
  }, [version, versionQuery, onRefetch, notify]));

  const archive = useAction(useCallback(async () => {
    if (!selected) return;
    await checklistCatalogApi.archiveTemplate(selected.id);
    onRefetch(); notify("Template archived.");
  }, [selected, onRefetch, notify]));

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
            <div key={t.id} onClick={() => setSelectedId(t.id)} style={{
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
                {selected.status !== "archived" && (
                  <Btn size="xs" variant="ghost" onClick={() => archive.execute()} loading={archive.loading}>
                    <Archive size={12} style={{ marginRight: 4 }} /> Archive
                  </Btn>
                )}
              </div>
            </div>
            <div style={{ padding: 16 }}>
              {version && version.status !== "DRAFT" && (
                <div style={{ padding: "8px 12px", borderRadius: "var(--radius-md)", background: "var(--surface-sunken)",
                  border: "1px solid var(--border)", fontSize: 12, color: "var(--muted-text)", marginBottom: 12 }}>
                  Viewing published v{version.version_number}. Editing content will create a new draft version automatically.
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
                  <AddItemRow sectionId={section.id} onAdded={() => versionQuery.refetch()} />
                </div>
              ))}
              <AddSectionRow versionId={version?.id ?? null} onAdded={() => versionQuery.refetch()} />

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
  const publishedTemplates = templates.filter(t => t.latest_version?.status === "PUBLISHED");
  const columns = [
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
          <Btn size="xs" variant="ghost" onClick={async () => { await checklistCatalogApi.disableMapping(row.id); onRefetch(); notify("Mapping disabled."); }}>
            Disable
          </Btn>
        ) : <span style={{ fontSize: 11, color: "var(--muted-text)" }}>—</span>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <NewMappingButton publishedTemplates={publishedTemplates} onCreated={() => { onRefetch(); notify("Mapping created."); }} />
      </div>
      <Card padding={0}>
        <DataTable
          columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
          rows={mappings as unknown as Record<string, unknown>[]}
          loading={loading}
          emptyText="No Job-Type mappings yet. A checklist has no runtime effect until mapped to an exact Job Type."
        />
      </Card>
    </div>
  );
}

function NewMappingButton({ publishedTemplates, onCreated }: { publishedTemplates: ChecklistTemplateRow[]; onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [categoryId, setCategoryId] = useState("");
  const [masterServiceId, setMasterServiceId] = useState("");
  const [jobTypeLinkId, setJobTypeLinkId] = useState("");
  const [templateVersionId, setTemplateVersionId] = useState("");
  const [phase, setPhase] = useState("inspection");
  const [usage, setUsage] = useState<ChecklistUsage>("REQUIRED");
  const [actor, setActor] = useState<ChecklistActor>("TECHNICIAN");
  const [gate, setGate] = useState<ChecklistCompletionGate>("NONE");

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
