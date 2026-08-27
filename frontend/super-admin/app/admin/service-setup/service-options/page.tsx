"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Archive, CheckCircle2, PauseCircle, Plus, Search } from "lucide-react";
import { PageHeader } from "@serviceos/design-system";
import { serviceOptionApi, type ServiceOption34E } from "../../../../lib/api";
import { Badge, Btn, DataTable, Input, Modal, Pagination, Select, Textarea } from "../../../../components/shared/ui";

const PAGE_SIZE = 25;
const STATUSES = ["active", "inactive", "archived", "deprecated", "pending_review"];
const OPTION_TYPES = ["add_on", "upgrade", "material", "tool", "visit_fee", "equipment_type"];
type OptionRow = ServiceOption34E & Record<string, unknown>;

function statusVariant(status: string): "success" | "warning" | "danger" | "muted" | "info" {
  if (status === "active") return "success";
  if (status === "inactive") return "warning";
  if (status === "deprecated") return "danger";
  if (status === "pending_review") return "info";
  return "muted";
}

export default function ServiceOptionsPage() {
  const [items, setItems] = useState<ServiceOption34E[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", code: "", description: "", option_type: "add_on", unit: "per_unit", default_price: "0", vertical_type: "", is_customer_selectable: true });
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
      const result = await serviceOptionApi.listOptions({ status: statusFilter || undefined, search: debouncedSearch || undefined, page, page_size: PAGE_SIZE });
      setItems(result.items ?? []);
      setTotal(result.total ?? 0);
    } catch (error) {
      setItems([]);
      setTotal(0);
      setLoadError(error instanceof Error ? error.message : "Could not load service options.");
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, page, statusFilter]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { setPage(1); }, [debouncedSearch, statusFilter]);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!form.name.trim()) { setFormError("Name is required."); return; }
    if (Number(form.default_price) < 0) { setFormError("Default price cannot be negative."); return; }
    setSaving(true);
    setFormError("");
    try {
      await serviceOptionApi.createOption({ ...form, name: form.name.trim(), code: form.code.trim(), description: form.description.trim(), vertical_type: form.vertical_type.trim() });
      setShowCreate(false);
      setForm({ name: "", code: "", description: "", option_type: "add_on", unit: "per_unit", default_price: "0", vertical_type: "", is_customer_selectable: true });
      setActionMessage("Service option created.");
      await load();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Could not create the service option.");
    } finally {
      setSaving(false);
    }
  }

  async function changeStatus(option: ServiceOption34E, action: "activate" | "deactivate" | "archive") {
    setActionBusy(`${option.id}:${action}`);
    setActionMessage("");
    try {
      if (action === "activate") await serviceOptionApi.activateOption(option.id);
      else if (action === "deactivate") await serviceOptionApi.deactivateOption(option.id);
      else await serviceOptionApi.archiveOption(option.id);
      setActionMessage(`Service option ${action === "activate" ? "activated" : action === "deactivate" ? "deactivated" : "archived"}.`);
      await load();
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "The status change failed.");
    } finally {
      setActionBusy("");
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--layout-page-gap)" }}>
      <PageHeader eyebrow="Catalog" context="Service setup" title="Service Options" description={`${total.toLocaleString()} selectable options and variants available to service blueprints.`}
        actions={<Btn onClick={() => { setFormError(""); setShowCreate(true); }}><Plus size={14} /> New option</Btn>} />

      <div style={{ display: "flex", gap: "var(--layout-control-gap)", alignItems: "flex-end", flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 280px", maxWidth: 440 }}><Input placeholder="Search name, code, or description" value={search} onChange={setSearch} icon={<Search />} /></div>
        <div style={{ width: 190 }}><Select value={statusFilter} onChange={setStatusFilter} placeholder="All statuses" options={STATUSES.map(value => ({ value, label: value.replace(/_/g, " ") }))} /></div>
      </div>

      {loadError && <div role="alert" style={{ padding: "var(--space-3) var(--space-4)", border: "1px solid var(--danger-border)", borderRadius: "var(--radius-md)", background: "var(--danger-bg)", color: "var(--danger-text)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "var(--space-3)" }}><span style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", fontSize: 13 }}><AlertTriangle size={15} />{loadError}</span><Btn size="sm" variant="secondary" onClick={load}>Retry</Btn></div>}
      {actionMessage && <div role="status" style={{ fontSize: 13, color: "var(--text-secondary)" }}>{actionMessage}</div>}

      <div>
        <DataTable<OptionRow> loading={loading} rows={items as OptionRow[]} emptyText="No service options match the current filters." columns={[
          { key: "name", label: "Option", render: (value, row) => <div><div style={{ fontWeight: 650 }}>{String(value)}</div><div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>{row.description || "No description"}</div></div> },
          { key: "code", label: "Code", render: value => <code style={{ fontSize: 12 }}>{String(value || "—")}</code> },
          { key: "option_type", label: "Type", render: value => String(value || "—").replace(/_/g, " ") },
          { key: "vertical_type", label: "Vertical", render: value => String(value || "All") },
          { key: "default_price", label: "Default", render: value => `₹${Number(value || 0).toLocaleString("en-IN")}` },
          { key: "is_customer_selectable", label: "Customer", render: value => <Badge variant={value ? "info" : "muted"}>{value ? "Selectable" : "Internal"}</Badge> },
          { key: "status", label: "Status", render: value => <Badge variant={statusVariant(String(value))}>{String(value).replace(/_/g, " ")}</Badge> },
          { key: "id", label: "Actions", render: (_, row) => <div style={{ display: "flex", gap: "var(--space-1)", flexWrap: "wrap" }}>
            {row.status !== "active" && <Btn size="xs" variant="ghost" loading={actionBusy === `${row.id}:activate`} onClick={() => changeStatus(row, "activate")}><CheckCircle2 size={12} />Activate</Btn>}
            {row.status === "active" && <Btn size="xs" variant="ghost" loading={actionBusy === `${row.id}:deactivate`} onClick={() => changeStatus(row, "deactivate")}><PauseCircle size={12} />Deactivate</Btn>}
            {row.status !== "archived" && <Btn size="xs" variant="ghost" loading={actionBusy === `${row.id}:archive`} onClick={() => changeStatus(row, "archive")}><Archive size={12} />Archive</Btn>}
          </div> },
        ]} />
        <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPage={setPage} />
      </div>

      <Modal open={showCreate} onClose={() => !saving && setShowCreate(false)} title="New service option" size="lg">
        <form onSubmit={handleCreate} style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "var(--space-4)" }}>
            <Input label="Name" required value={form.name} onChange={value => setForm(current => ({ ...current, name: value }))} placeholder="Split AC" />
            <Input label="Code" value={form.code} onChange={value => setForm(current => ({ ...current, code: value }))} placeholder="split_ac" hint="Leave blank to generate from the name." />
          </div>
          <Textarea label="Description" value={form.description} onChange={value => setForm(current => ({ ...current, description: value }))} rows={3} />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "var(--space-4)" }}>
            <Select label="Option type" value={form.option_type} onChange={value => setForm(current => ({ ...current, option_type: value }))} options={OPTION_TYPES.map(value => ({ value, label: value.replace(/_/g, " ") }))} />
            <Input label="Vertical type" value={form.vertical_type} onChange={value => setForm(current => ({ ...current, vertical_type: value }))} placeholder="home_service" />
            <Input label="Default price" type="number" value={form.default_price} onChange={value => setForm(current => ({ ...current, default_price: value }))} hint="Tenant pricing can override catalog defaults where policy allows." />
            <Input label="Unit" value={form.unit} onChange={value => setForm(current => ({ ...current, unit: value }))} placeholder="per_unit" />
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", fontSize: 13 }}><input type="checkbox" checked={form.is_customer_selectable} onChange={event => setForm(current => ({ ...current, is_customer_selectable: event.target.checked }))} />Customer selectable</label>
          {formError && <p role="alert" style={{ margin: 0, color: "var(--danger-text)", fontSize: 13 }}>{formError}</p>}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-2)" }}><Btn type="button" variant="secondary" disabled={saving} onClick={() => setShowCreate(false)}>Cancel</Btn><Btn type="submit" loading={saving}>Create service option</Btn></div>
        </form>
      </Modal>
    </div>
  );
}
