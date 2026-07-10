"use client";
import React, { useState, useCallback } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Modal, Input, SectionHeader, DataTable } from "../../../components/shared/ui";
import {
  serviceOptionApi, catalogApi,
  type MasterChecklistItem, type ServiceCategory, type MasterService,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { Plus, Pencil, Power, PowerOff, Archive, Eye, Sparkles } from "lucide-react";

const STATUS_BADGE: Record<string, "success" | "warning" | "muted" | "danger"> = {
  active: "success", inactive: "warning", archived: "muted",
};

const OWNER_ROLES = ["customer", "tenant_owner", "tenant_manager", "technician", "support_admin", "system"];

const BLANK_FORM = {
  title: "", code: "", description: "", owner_role: "technician",
  is_required: true, customer_visible: false, staff_visible: true, tenant_visible: true,
  display_order: 0, status: "active", category_id: "", master_service_id: "",
};
type FormState = typeof BLANK_FORM;

export default function ChecklistsPage() {
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [serviceFilter, setServiceFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  const [modal, setModal]     = useState<"none" | "view" | "create" | "edit">("none");
  const [editing, setEditing] = useState<MasterChecklistItem | null>(null);
  const [viewing, setViewing] = useState<MasterChecklistItem | null>(null);
  const [form, setForm]       = useState<FormState>(BLANK_FORM);
  const [toast, setToast]     = useState<{ msg: string; ok: boolean } | null>(null);

  const notify = (msg: string, ok = true) => { setToast({ msg, ok }); setTimeout(() => setToast(null), 3500); };

  const cats = useApi(useCallback(() => catalogApi.listCategories(true), []));
  const catList: ServiceCategory[] = cats.data?.categories ?? [];

  const filterSvcs = useApi(useCallback(
    () => categoryFilter ? catalogApi.listMasterServices(categoryFilter) : Promise.resolve({ services: [] as MasterService[] }),
    [categoryFilter]), [categoryFilter]);
  const filterSvcList: MasterService[] = filterSvcs.data?.services ?? [];

  const list = useApi(useCallback(() => serviceOptionApi.listChecklistItems({
    search: search || undefined,
    category_id: categoryFilter || undefined,
    master_service_id: serviceFilter || undefined,
    status: statusFilter || undefined,
    page, page_size: 30,
  }), [search, categoryFilter, serviceFilter, statusFilter, page]), [search, categoryFilter, serviceFilter, statusFilter, page]);

  const items: MasterChecklistItem[] = list.data?.items ?? [];
  const total: number = list.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 30));

  function categoryName(id?: string) {
    return catList.find(c => c.category_id === id)?.name ?? null;
  }

  function openCreate() { setForm(BLANK_FORM); setEditing(null); setModal("create"); }
  function openView(row: MasterChecklistItem) { setViewing(row); setModal("view"); }
  function openEdit(row: MasterChecklistItem) {
    setForm({
      title: row.title, code: row.code, description: row.description ?? "",
      owner_role: row.owner_role, is_required: row.is_required,
      customer_visible: row.customer_visible, staff_visible: row.staff_visible,
      tenant_visible: row.tenant_visible, display_order: row.display_order,
      status: row.status, category_id: row.category_id ?? "", master_service_id: row.master_service_id ?? "",
    });
    setEditing(row); setModal("edit");
  }

  const createAction = useAction(useCallback(async (data: FormState) => {
    await serviceOptionApi.createChecklistItem({
      title: data.title, code: data.code || undefined, description: data.description || undefined,
      owner_role: data.owner_role, is_required: data.is_required,
      customer_visible: data.customer_visible, staff_visible: data.staff_visible,
      tenant_visible: data.tenant_visible, display_order: data.display_order,
      status: data.status, category_id: data.category_id || undefined,
      master_service_id: data.master_service_id || undefined,
    });
    list.refetch(); setModal("none"); notify("Checklist item created.");
  }, [list]));

  const editAction = useAction(useCallback(async ({ id, data }: { id: string; data: FormState }) => {
    await serviceOptionApi.updateChecklistItem(id, {
      title: data.title, description: data.description || undefined,
      owner_role: data.owner_role, is_required: data.is_required,
      customer_visible: data.customer_visible, staff_visible: data.staff_visible,
      tenant_visible: data.tenant_visible, display_order: data.display_order,
    });
    list.refetch(); setModal("none"); notify("Checklist item updated.");
  }, [list]));

  const enableAction = useAction(useCallback(async (id: string) => {
    await serviceOptionApi.enableChecklistItem(id); list.refetch(); notify("Enabled.");
  }, [list]));
  const disableAction = useAction(useCallback(async (id: string) => {
    await serviceOptionApi.disableChecklistItem(id); list.refetch(); notify("Disabled.");
  }, [list]));
  const archiveAction = useAction(useCallback(async (id: string) => {
    await serviceOptionApi.archiveChecklistItem(id); list.refetch(); notify("Archived.");
  }, [list]));

  const seedAction = useAction(useCallback(async () => {
    const result = await serviceOptionApi.seedDefaultChecklists();
    list.refetch();
    if (result.created.length > 0) {
      notify(`Seeded ${result.created.length} checklist item(s)${result.skipped.length ? `, ${result.skipped.length} already existed` : ""}.`);
    } else {
      notify("All baseline checklist items already exist — nothing to seed.");
    }
  }, [list]));

  const columns = [
    {
      key: "code", label: "Code", width: 160,
      render: (_: unknown, row: MasterChecklistItem) => (
        <span style={{ fontFamily: "monospace", fontSize: 11, fontWeight: 600,
          background: "var(--surface-sunken)", padding: "2px 7px", borderRadius: 5,
          border: "1px solid var(--border)", color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
          {row.code}
        </span>
      ),
    },
    {
      key: "title", label: "Title / Description",
      render: (_: unknown, row: MasterChecklistItem) => (
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>{row.title}</div>
          {row.description && (
            <div style={{ fontSize: 11, color: "var(--muted-text)", marginTop: 2 }}>{row.description}</div>
          )}
        </div>
      ),
    },
    {
      key: "owner_role", label: "Owner Role", width: 130,
      render: (_: unknown, row: MasterChecklistItem) => (
        <Badge variant="info" size="sm">{row.owner_role}</Badge>
      ),
    },
    {
      key: "is_required", label: "Required", width: 90,
      render: (_: unknown, row: MasterChecklistItem) => (
        <span style={{ fontSize: 12, color: row.is_required ? "var(--primary)" : "var(--muted-text)" }}>
          {row.is_required ? "Required" : "Optional"}
        </span>
      ),
    },
    {
      key: "visibility", label: "Visibility", width: 180,
      render: (_: unknown, row: MasterChecklistItem) => (
        <span style={{ fontSize: 11, color: "var(--muted-text)" }}>
          {[row.customer_visible && "Customer", row.staff_visible && "Staff", row.tenant_visible && "Tenant"]
            .filter(Boolean).join(", ") || "—"}
        </span>
      ),
    },
    {
      key: "status", label: "Status", width: 90,
      render: (_: unknown, row: MasterChecklistItem) => (
        <Badge variant={STATUS_BADGE[row.status] ?? "muted"} size="sm">{row.status}</Badge>
      ),
    },
    {
      key: "id", label: "Actions", width: 170,
      render: (_: unknown, row: MasterChecklistItem) => (
        <div style={{ display: "flex", gap: 4 }} onClick={e => e.stopPropagation()}>
          <Btn size="xs" variant="ghost" onClick={() => openView(row)}><Eye size={11} /></Btn>
          <Btn size="xs" variant="ghost" onClick={() => openEdit(row)}><Pencil size={11} /></Btn>
          {row.status === "active" && (
            <Btn size="xs" variant="ghost" loading={disableAction.loading}
              onClick={() => disableAction.execute(row.id)}><PowerOff size={11} /></Btn>
          )}
          {row.status === "inactive" && (
            <Btn size="xs" variant="ghost" loading={enableAction.loading}
              onClick={() => enableAction.execute(row.id)}><Power size={11} /></Btn>
          )}
          {row.status !== "archived" && (
            <Btn size="xs" variant="ghost" loading={archiveAction.loading}
              onClick={() => { if (confirm(`Archive "${row.title}"?`)) archiveAction.execute(row.id); }}>
              <Archive size={11} />
            </Btn>
          )}
        </div>
      ),
    },
  ];

  const FieldRow = ({ label, children }: { label: string; children: React.ReactNode }) => (
    <div>
      <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 5 }}>{label}</label>
      {children}
    </div>
  );
  const StyledSelect = ({ value, onChange, options }: { value: string; onChange: (v: string) => void; options: { value: string; label: string }[] }) => (
    <select value={value} onChange={e => onChange(e.target.value)}
      style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text)", fontSize: 13, outline: "none" }}>
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
  const CheckRow = ({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) => (
    <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)}
        style={{ width: 15, height: 15, cursor: "pointer" }} />
      {label}
    </label>
  );

  return (
    <AdminLayout activeNav="checklist-templates">
      <SectionHeader
        title="Checklists"
        subtitle={`${total} technician/staff completion checklist items across all services`}
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn size="sm" variant="secondary" loading={seedAction.loading} onClick={() => seedAction.execute()}>
              <Sparkles size={14} style={{ marginRight: 4 }} /> Seed Defaults
            </Btn>
            <Btn size="sm" variant="primary" onClick={openCreate}>
              <Plus size={14} style={{ marginRight: 4 }} /> New Checklist Item
            </Btn>
          </div>
        }
      />

      {toast && (
        <div style={{ padding: "10px 16px", borderRadius: 10, marginBottom: 12,
          background: toast.ok ? "var(--success-bg,rgba(34,197,94,.08))" : "var(--danger-bg)",
          border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.ok ? "var(--success-text,#166534)" : "var(--danger-text)", fontSize: 13 }}>
          {toast.ok ? "✓" : "✗"} {toast.msg}
        </div>
      )}

      {/* Toolbar */}
      <Card padding={0} style={{ marginBottom: 16 }}>
        <div style={{ padding: "12px 16px", display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ flex: 1, minWidth: 180 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "var(--muted-text)", marginBottom: 5 }}>Search</div>
            <input
              placeholder="Title or code…"
              value={searchInput}
              onChange={e => setSearchInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") { setSearch(searchInput); setPage(1); } }}
              style={{ width: "100%", height: 36, padding: "0 12px", border: "1px solid var(--border)", borderRadius: 8, fontSize: 13, background: "var(--card-bg)", color: "var(--text)", outline: "none", boxSizing: "border-box" }}
            />
          </div>
          <div style={{ minWidth: 160 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "var(--muted-text)", marginBottom: 5 }}>Category</div>
            <select value={categoryFilter} onChange={e => { setCategoryFilter(e.target.value); setServiceFilter(""); setPage(1); }}
              style={{ height: 36, padding: "0 10px", border: "1px solid var(--border)", borderRadius: 8, fontSize: 13, background: "var(--card-bg)", color: "var(--text)", outline: "none" }}>
              <option value="">All Categories</option>
              {catList.map(c => <option key={c.category_id} value={c.category_id}>{c.name}</option>)}
            </select>
          </div>
          {categoryFilter && (
            <div style={{ minWidth: 180 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "var(--muted-text)", marginBottom: 5 }}>Service</div>
              <select value={serviceFilter} onChange={e => { setServiceFilter(e.target.value); setPage(1); }}
                style={{ height: 36, padding: "0 10px", border: "1px solid var(--border)", borderRadius: 8, fontSize: 13, background: "var(--card-bg)", color: "var(--text)", outline: "none" }}>
                <option value="">All Services</option>
                {filterSvcList.map(s => <option key={s.service_id} value={s.service_id}>{s.service_name}</option>)}
              </select>
            </div>
          )}
          <div style={{ minWidth: 110 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "var(--muted-text)", marginBottom: 5 }}>Status</div>
            <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
              style={{ height: 36, padding: "0 10px", border: "1px solid var(--border)", borderRadius: 8, fontSize: 13, background: "var(--card-bg)", color: "var(--text)", outline: "none" }}>
              <option value="">All</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="archived">Archived</option>
            </select>
          </div>
          <Btn variant="ghost" size="sm" onClick={() => list.refetch()}>↻</Btn>
        </div>
      </Card>

      {/* Table */}
      <Card padding={0}>
        <DataTable
          columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
          rows={items as unknown as Record<string, unknown>[]}
          loading={list.loading}
          onRowClick={row => openView(row as unknown as MasterChecklistItem)}
          emptyText={search || categoryFilter || serviceFilter || statusFilter
            ? "No checklist items match the current filters."
            : "No checklist items yet. Create the first one."}
        />
        {totalPages > 1 && (
          <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--muted-text)" }}>{total} total · page {page} of {totalPages}</span>
            <div style={{ display: "flex", gap: 8 }}>
              <Btn variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Prev</Btn>
              <Btn variant="ghost" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next →</Btn>
            </div>
          </div>
        )}
      </Card>

      {/* Create / Edit Modal */}
      <Modal open={modal === "create" || modal === "edit"}
        onClose={() => setModal("none")}
        title={modal === "create" ? "New Checklist Item" : "Edit Checklist Item"}
        size="lg">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {(createAction.error || editAction.error) && (
            <div style={{ padding: "10px 14px", borderRadius: 9, background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{createAction.error || editAction.error}</p>
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <Input label="Title *" placeholder="Completion Note" value={form.title}
              onChange={v => setForm(f => ({ ...f, title: v }))} />
            <Input label="Code" placeholder="COMPLETION_NOTE" value={form.code}
              onChange={v => setForm(f => ({ ...f, code: v.toUpperCase() }))} disabled={modal === "edit"} />
          </div>

          <FieldRow label="Description">
            <textarea value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="What the technician/staff must record…" rows={2}
              style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text)", fontSize: 13, fontFamily: "inherit", resize: "vertical", outline: "none", boxSizing: "border-box" }} />
          </FieldRow>

          {modal === "create" ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              <FieldRow label="Owner Role">
                <StyledSelect value={form.owner_role} onChange={v => setForm(f => ({ ...f, owner_role: v }))}
                  options={OWNER_ROLES.map(r => ({ value: r, label: r }))} />
              </FieldRow>
              <FieldRow label="Category">
                <select value={form.category_id} onChange={e => { setForm(f => ({ ...f, category_id: e.target.value, master_service_id: "" })); }}
                  style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text)", fontSize: 13, outline: "none" }}>
                  <option value="">— None —</option>
                  {catList.map(c => <option key={c.category_id} value={c.category_id}>{c.name}</option>)}
                </select>
              </FieldRow>
            </div>
          ) : (
            <FieldRow label="Owner Role">
              <StyledSelect value={form.owner_role} onChange={v => setForm(f => ({ ...f, owner_role: v }))}
                options={OWNER_ROLES.map(r => ({ value: r, label: r }))} />
            </FieldRow>
          )}

          {modal === "create" && form.category_id && (
            <FieldRow label="Master Service (link this checklist item to a service)">
              <ChecklistServiceSelector categoryId={form.category_id}
                value={form.master_service_id}
                onChange={v => setForm(f => ({ ...f, master_service_id: v }))} />
            </FieldRow>
          )}

          {modal === "edit" && editing && (
            <div style={{ padding: "8px 12px", borderRadius: 8, background: "var(--surface-sunken)",
              border: "1px solid var(--border)", fontSize: 12, color: "var(--muted-text)" }}>
              Linked to: <strong style={{ color: "var(--text)" }}>
                {categoryName(editing.category_id) ?? "no category"}
              </strong>
              {editing.master_service_id && <> · service ID <code>{editing.master_service_id.slice(0, 8)}…</code></>}
              {" "}(service linking is set at creation and can't be changed here)
            </div>
          )}

          <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
            <CheckRow label="Required" checked={form.is_required}
              onChange={v => setForm(f => ({ ...f, is_required: v }))} />
            <CheckRow label="Customer Visible" checked={form.customer_visible}
              onChange={v => setForm(f => ({ ...f, customer_visible: v }))} />
            <CheckRow label="Staff Visible" checked={form.staff_visible}
              onChange={v => setForm(f => ({ ...f, staff_visible: v }))} />
            <CheckRow label="Tenant Visible" checked={form.tenant_visible}
              onChange={v => setForm(f => ({ ...f, tenant_visible: v }))} />
          </div>

          <Input label="Display Order" type="number" value={String(form.display_order)}
            onChange={v => setForm(f => ({ ...f, display_order: Number(v) || 0 }))} />

          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setModal("none")}>Cancel</Btn>
            <Btn variant="primary" size="sm"
              disabled={!form.title.trim()}
              loading={createAction.loading || editAction.loading}
              onClick={() => {
                if (modal === "create") createAction.execute(form);
                else if (editing) editAction.execute({ id: editing.id, data: form });
              }}>
              {modal === "create" ? "Create" : "Save Changes"}
            </Btn>
          </div>
        </div>
      </Modal>

      {/* View Detail Modal */}
      <Modal open={modal === "view" && !!viewing}
        onClose={() => { setModal("none"); setViewing(null); }}
        title={viewing?.title ?? "Checklist Item"}
        size="md">
        {viewing && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <Badge variant={STATUS_BADGE[viewing.status] ?? "muted"}>{viewing.status}</Badge>
              <Badge variant="info">{viewing.owner_role}</Badge>
              <Badge variant={viewing.is_required ? "warning" : "muted"}>
                {viewing.is_required ? "Required" : "Optional"}
              </Badge>
            </div>

            <div>
              <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 6px" }}>Code</p>
              <code style={{ fontSize: 13, color: "var(--text)" }}>{viewing.code}</code>
            </div>

            {viewing.description && (
              <div>
                <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                  textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 6px" }}>Description</p>
                <p style={{ fontSize: 13, color: "var(--text)", margin: 0, lineHeight: 1.5 }}>{viewing.description}</p>
              </div>
            )}

            <div>
              <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 6px" }}>Visibility</p>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {viewing.customer_visible && <Badge variant="muted" size="sm">Customer</Badge>}
                {viewing.staff_visible && <Badge variant="muted" size="sm">Staff</Badge>}
                {viewing.tenant_visible && <Badge variant="muted" size="sm">Tenant</Badge>}
                {!viewing.customer_visible && !viewing.staff_visible && !viewing.tenant_visible && (
                  <span style={{ fontSize: 12, color: "var(--muted-text)" }}>Not visible to anyone</span>
                )}
              </div>
            </div>

            <div>
              <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 6px" }}>Linked Category / Service</p>
              <p style={{ fontSize: 13, color: "var(--text)", margin: 0 }}>
                {categoryName(viewing.category_id) ?? "No category"}
                {viewing.master_service_id && <> · service ID <code style={{ fontSize: 11 }}>{viewing.master_service_id.slice(0, 8)}…</code></>}
              </p>
            </div>

            {viewing.workflow_step_key && (
              <div>
                <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                  textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 6px" }}>Workflow Step</p>
                <code style={{ fontSize: 12 }}>{viewing.workflow_step_key}</code>
              </div>
            )}

            <div style={{ display: "flex", gap: 16, fontSize: 12, color: "var(--muted-text)" }}>
              <span>Display order: {viewing.display_order}</span>
              {viewing.created_at && <span>Created: {new Date(viewing.created_at).toLocaleDateString()}</span>}
            </div>

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", borderTop: "1px solid var(--border)", paddingTop: 14 }}>
              <Btn variant="ghost" size="sm" onClick={() => { setModal("none"); setViewing(null); }}>Close</Btn>
              <Btn variant="primary" size="sm" onClick={() => { openEdit(viewing); }}>
                <Pencil size={13} style={{ marginRight: 4 }} /> Edit
              </Btn>
            </div>
          </div>
        )}
      </Modal>
    </AdminLayout>
  );
}

function ChecklistServiceSelector({ categoryId, value, onChange }: {
  categoryId: string; value: string; onChange: (v: string) => void;
}) {
  const svcs = useApi(useCallback(() => catalogApi.listMasterServices(categoryId), [categoryId]), [categoryId]);
  const svcList: MasterService[] = svcs.data?.services ?? [];
  return (
    <select value={value} onChange={e => onChange(e.target.value)}
      style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text)", fontSize: 13, outline: "none" }}>
      <option value="">— None —</option>
      {svcList.map(s => <option key={s.service_id} value={s.service_id}>{s.service_name}</option>)}
    </select>
  );
}
