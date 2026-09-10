"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Archive, CheckCircle2, PauseCircle, Pencil, Plus, Search } from "lucide-react";
import { PageHeader } from "@serviceos/design-system";
import { serviceOptionApi, type IssueType34E } from "../../../../lib/api";
import { Badge, Btn, DataTable, Input, Modal, Pagination, Select, Textarea } from "../../../../components/shared/ui";
import { IconPicker } from "../../../../components/shared/IconPicker";

const PAGE_SIZE = 25;
const SEVERITIES = ["low", "medium", "high", "urgent"];
const STATUSES = ["active", "inactive", "archived", "deprecated"];
type IssueRow = IssueType34E & Record<string, unknown>;

function statusVariant(status: string): "success" | "warning" | "danger" | "muted" | "info" {
  if (status === "active") return "success";
  if (status === "inactive") return "warning";
  if (status === "deprecated") return "danger";
  if (status === "pending_review") return "info";
  return "muted";
}

function severityVariant(severity: string): "danger" | "warning" | "muted" {
  if (severity === "urgent" || severity === "high") return "danger";
  if (severity === "medium") return "warning";
  return "muted";
}

export default function IssueTypesPage() {
  const [items, setItems] = useState<IssueType34E[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<IssueType34E | null>(null);
  const [form, setForm] = useState({ name: "", code: "", description: "", icon_url: "", image_url: "", severity: "medium", vertical_type: "", requires_photo: false, requires_description: false });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [actionBusy, setActionBusy] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const result = await serviceOptionApi.listIssueTypes({ status: statusFilter || undefined, search: debouncedSearch || undefined, page, page_size: PAGE_SIZE });
      setItems(result.items ?? []);
      setTotal(result.total ?? 0);
    } catch (error) {
      setItems([]);
      setTotal(0);
      setLoadError(error instanceof Error ? error.message : "Could not load issue types.");
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, page, statusFilter]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { setPage(1); }, [debouncedSearch, statusFilter]);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!form.name.trim()) { setFormError("Name is required."); return; }
    setSaving(true);
    setFormError("");
    try {
      const payload = { ...form, name: form.name.trim(), code: form.code.trim(), description: form.description.trim(), icon_url: form.icon_url || null, image_url: form.image_url || null, vertical_type: form.vertical_type.trim(), severity_default: form.severity } as Parameters<typeof serviceOptionApi.createIssueType>[0];
      if (editing) await serviceOptionApi.updateIssueType(editing.id, payload);
      else await serviceOptionApi.createIssueType(payload);
      setShowCreate(false);
      setEditing(null);
      setForm({ name: "", code: "", description: "", icon_url: "", image_url: "", severity: "medium", vertical_type: "", requires_photo: false, requires_description: false });
      setActionMessage(editing ? "Issue type updated." : "Issue type created.");
      await load();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Could not create the issue type.");
    } finally {
      setSaving(false);
    }
  }

  async function changeStatus(item: IssueType34E, action: "activate" | "deactivate" | "archive") {
    setActionBusy(`${item.id}:${action}`);
    setActionMessage("");
    try {
      if (action === "activate") await serviceOptionApi.activateIssueType(item.id);
      else if (action === "deactivate") await serviceOptionApi.deactivateIssueType(item.id);
      else await serviceOptionApi.archiveIssueType(item.id);
      setActionMessage(`Issue type ${action === "activate" ? "activated" : action === "deactivate" ? "deactivated" : "archived"}.`);
      await load();
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "The status change failed.");
    } finally {
      setActionBusy("");
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--layout-page-gap)" }}>
      <PageHeader eyebrow="Catalog" context="Service setup" title="Issue Types" description={`${total.toLocaleString()} problem categories available to booking flows.`}
        actions={<Btn onClick={() => { setEditing(null); setForm({ name: "", code: "", description: "", icon_url: "", image_url: "", severity: "medium", vertical_type: "", requires_photo: false, requires_description: false }); setFormError(""); setShowCreate(true); }}><Plus size={14} /> New issue type</Btn>} />

      <div style={{ display: "flex", gap: "var(--layout-control-gap)", alignItems: "flex-end", flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 280px", maxWidth: 440 }}><Input placeholder="Search name, code, or description" value={search} onChange={setSearch} icon={<Search />} /></div>
        <div style={{ width: 190 }}><Select value={statusFilter} onChange={setStatusFilter} placeholder="All statuses" options={STATUSES.map(value => ({ value, label: value.replace(/_/g, " ") }))} /></div>
      </div>

      {loadError && <div role="alert" style={{ padding: "var(--space-3) var(--space-4)", border: "1px solid var(--danger-border)", borderRadius: "var(--radius-md)", background: "var(--danger-bg)", color: "var(--danger-text)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "var(--space-3)" }}><span style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", fontSize: 13 }}><AlertTriangle size={15} />{loadError}</span><Btn size="sm" variant="secondary" onClick={load}>Retry</Btn></div>}
      {actionMessage && <div role="status" style={{ fontSize: 13, color: "var(--text-secondary)" }}>{actionMessage}</div>}

      <div>
        <DataTable<IssueRow> loading={loading} rows={items as IssueRow[]} emptyText="No issue types match the current filters." columns={[
          { key: "name", label: "Issue type", render: (value, row) => <div style={{ display: "flex", alignItems: "center", gap: 10 }}>{row.icon_url ? <img src={String(row.icon_url)} alt="" style={{ width: 38, height: 38, borderRadius: 9, objectFit: "cover", border: "1px solid var(--border)" }} /> : null}<div><div style={{ fontWeight: 650 }}>{String(value)}</div><div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>{row.description || "No description"}</div></div></div> },
          { key: "code", label: "Code", render: value => <code style={{ fontSize: 12 }}>{String(value || "—")}</code> },
          { key: "severity", label: "Severity", render: value => <Badge variant={severityVariant(String(value))}>{String(value)}</Badge> },
          { key: "vertical_type", label: "Vertical", render: value => String(value || "All") },
          { key: "requires_photo", label: "Evidence", render: (value, row) => <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{value ? "Photo" : row.requires_description ? "Description" : "None"}</span> },
          { key: "status", label: "Status", render: value => <Badge variant={statusVariant(String(value))}>{String(value).replace(/_/g, " ")}</Badge> },
          { key: "id", label: "Actions", render: (_, row) => <div style={{ display: "flex", gap: "var(--space-1)", flexWrap: "wrap" }}>
            <Btn size="xs" variant="ghost" onClick={() => { setEditing(row); setForm({ name: row.name, code: row.code, description: row.description ?? "", icon_url: row.icon_url ?? "", image_url: row.image_url ?? "", severity: row.severity, vertical_type: row.vertical_type ?? "", requires_photo: row.requires_photo, requires_description: row.requires_description }); setFormError(""); setShowCreate(true); }}><Pencil size={12} />Edit</Btn>
            {row.status !== "active" && <Btn size="xs" variant="ghost" loading={actionBusy === `${row.id}:activate`} onClick={() => changeStatus(row, "activate")}><CheckCircle2 size={12} />Activate</Btn>}
            {row.status === "active" && <Btn size="xs" variant="ghost" loading={actionBusy === `${row.id}:deactivate`} onClick={() => changeStatus(row, "deactivate")}><PauseCircle size={12} />Deactivate</Btn>}
            {row.status !== "archived" && <Btn size="xs" variant="ghost" loading={actionBusy === `${row.id}:archive`} onClick={() => changeStatus(row, "archive")}><Archive size={12} />Archive</Btn>}
          </div> },
        ]} />
        <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPage={setPage} />
      </div>

      <Modal open={showCreate} onClose={() => !saving && setShowCreate(false)} title={editing ? `Edit ${editing.name}` : "New issue type"} size="lg">
        <form onSubmit={handleCreate} style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "var(--space-4)" }}>
            <Input label="Name" required value={form.name} onChange={value => setForm(current => ({ ...current, name: value }))} placeholder="Not cooling" />
            <Input label="Code" value={form.code} onChange={value => setForm(current => ({ ...current, code: value }))} placeholder="not_cooling" hint="Leave blank to generate from the name." />
          </div>
          <Textarea label="Description" value={form.description} onChange={value => setForm(current => ({ ...current, description: value }))} rows={3} />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "var(--space-4)" }}>
            <div>
              <IconPicker label="Fuvay app icon" noun="problem app icon" context="issue_type_image" value={form.icon_url} onChange={value => setForm(current => ({ ...current, icon_url: value ?? "" }))} />
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "6px 0 0" }}>Square icon used in the app and internal catalog.</p>
            </div>
            <div>
              <IconPicker label="Instagram card image" noun="Instagram problem image" context="instagram_card_image" value={form.image_url} onChange={value => setForm(current => ({ ...current, image_url: value ?? "" }))} />
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "6px 0 0" }}>Public HTTPS artwork for Instagram. The app icon is the fallback.</p>
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "var(--space-4)" }}>
            <Select label="Default severity" value={form.severity} onChange={value => setForm(current => ({ ...current, severity: value }))} options={SEVERITIES.map(value => ({ value, label: value }))} />
            <Input label="Vertical type" value={form.vertical_type} onChange={value => setForm(current => ({ ...current, vertical_type: value }))} placeholder="home_service" />
          </div>
          <div style={{ display: "flex", gap: "var(--space-5)", flexWrap: "wrap" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", fontSize: 13 }}><input type="checkbox" checked={form.requires_photo} onChange={event => setForm(current => ({ ...current, requires_photo: event.target.checked }))} />Requires photo</label>
            <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", fontSize: 13 }}><input type="checkbox" checked={form.requires_description} onChange={event => setForm(current => ({ ...current, requires_description: event.target.checked }))} />Requires description</label>
          </div>
          {formError && <p role="alert" style={{ margin: 0, color: "var(--danger-text)", fontSize: 13 }}>{formError}</p>}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-2)" }}><Btn type="button" variant="secondary" disabled={saving} onClick={() => setShowCreate(false)}>Cancel</Btn><Btn type="submit" loading={saving}>{editing ? "Save changes" : "Create issue type"}</Btn></div>
        </form>
      </Modal>
    </div>
  );
}
