"use client";
import React, { useState, useCallback, useEffect } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Modal, Input, Select, SectionHeader, DataTable } from "../../../components/shared/ui";
import {
  serviceOptionApi, catalogApi,
  type IssueType34E, type ServiceIssueMapping34E, type ServiceCategory, type MasterService,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { AlertTriangle, Plus, Pencil, Power, PowerOff, Archive, Link2, X, Check } from "lucide-react";

const SEV_BADGE: Record<string, "danger" | "warning" | "info" | "muted"> = {
  critical: "danger", high: "warning", medium: "info", low: "muted",
};

const STATUS_BADGE: Record<string, "success" | "warning" | "muted" | "danger"> = {
  active: "success", inactive: "warning", archived: "muted",
};

const BLANK_FORM = {
  name: "", code: "", severity: "medium", description: "",
  requires_photo: false, requires_description: false, customer_visible: true,
  display_order: 0, status: "active", category_id: "", master_service_id: "",
};
type FormState = typeof BLANK_FORM;

// ── Cascading service selector for "Map to Service" in create modal ────────────
function ServiceSelector({
  categoryId, setCategoryId, serviceId, setServiceId,
}: {
  categoryId: string; setCategoryId: (v: string) => void;
  serviceId: string; setServiceId: (v: string) => void;
}) {
  const cats = useApi(useCallback(() => catalogApi.listCategories(true), []));
  const svcs = useApi(
    useCallback(() => categoryId
      ? catalogApi.listMasterServices(categoryId)
      : Promise.resolve({ services: [] as MasterService[] }),
      [categoryId]
    )
  );
  const catList: ServiceCategory[] = cats.data?.categories ?? [];
  const svcList: MasterService[] = svcs.data?.services ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div>
        <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 5 }}>Category</label>
        <select value={categoryId} onChange={e => { setCategoryId(e.target.value); setServiceId(""); }}
          style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text)", fontSize: 13, outline: "none" }}>
          <option value="">— All categories —</option>
          {catList.map(c => <option key={c.category_id} value={c.category_id}>{c.name}</option>)}
        </select>
      </div>
      {categoryId && (
        <div>
          <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 5 }}>Master Service (optional)</label>
          <select value={serviceId} onChange={e => setServiceId(e.target.value)}
            style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text)", fontSize: 13, outline: "none" }}>
            <option value="">— Select service to map —</option>
            {svcList.map(s => <option key={s.service_id} value={s.service_id}>{s.service_name}</option>)}
          </select>
        </div>
      )}
    </div>
  );
}

// ── Mapping panel (shown as inline modal) ────────────────────────────────────
function MappingModal({ issue, onClose }: { issue: IssueType34E; onClose: () => void }) {
  const mappingsFetch = useApi(
    useCallback(() => serviceOptionApi.listServiceIssueMappings(
      // list all services for this issue — approach: we fetch the issue's direct service mappings
      // The endpoint is per-service, so we'll use a workaround: list all mappings for this issue
      // by calling list endpoint filtered; however, API is service-centric.
      // We'll use a dummy UUID that won't exist so we get empty, then manually fetch via the issue
      // Actually the endpoint is GET /v1/admin/master-services/{id}/issues which is service-centric.
      // We don't have an issue-centric endpoint. Use empty string sentinel.
      "00000000-0000-0000-0000-000000000000"
    ), [])
  );

  const cats = useApi(useCallback(() => catalogApi.listCategories(true), []));
  const catList: ServiceCategory[] = cats.data?.categories ?? [];

  const [selCat, setSelCat] = useState("");
  const [selSvc, setSelSvc] = useState("");
  const [addedMappings, setAddedMappings] = useState<string[]>([]);

  const svcs = useApi(
    useCallback(() => selCat
      ? catalogApi.listMasterServices(selCat)
      : Promise.resolve({ services: [] as MasterService[] }),
      [selCat]
    )
  );
  const svcList: MasterService[] = svcs.data?.services ?? [];

  const addAction = useAction(useCallback(async (svcId: string) => {
    await serviceOptionApi.addServiceIssueMapping(svcId, { issue_type_id: issue.id });
    setAddedMappings(p => [...p, svcId]);
    setSelSvc("");
  }, [issue.id]));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ padding: "10px 14px", borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)", fontSize: 13 }}>
        <strong>{issue.name}</strong> · {issue.code}
        <span style={{ marginLeft: 8 }}><Badge variant={SEV_BADGE[issue.severity] ?? "muted"} size="sm">{issue.severity}</Badge></span>
      </div>

      <div>
        <div style={{ fontSize: 12, fontWeight: 700, color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
          Map to Service
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <select value={selCat} onChange={e => { setSelCat(e.target.value); setSelSvc(""); }}
            style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text)", fontSize: 13, outline: "none" }}>
            <option value="">— Select category —</option>
            {catList.map(c => <option key={c.category_id} value={c.category_id}>{c.name}</option>)}
          </select>
          {selCat && (
            <div style={{ display: "flex", gap: 8 }}>
              <select value={selSvc} onChange={e => setSelSvc(e.target.value)}
                style={{ flex: 1, padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text)", fontSize: 13, outline: "none" }}>
                <option value="">— Select service —</option>
                {svcList.map(s => <option key={s.service_id} value={s.service_id}>{s.service_name}</option>)}
              </select>
              <Btn size="sm" disabled={!selSvc} loading={addAction.loading}
                onClick={() => selSvc && addAction.execute(selSvc)}>
                <Link2 size={13} style={{ marginRight: 4 }} /> Map
              </Btn>
            </div>
          )}
          {addAction.error && <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{addAction.error}</p>}
        </div>
      </div>

      {addedMappings.length > 0 && (
        <div style={{ padding: "8px 12px", borderRadius: 8, background: "var(--success-bg, rgba(34,197,94,.08))", border: "1px solid var(--success-border)", fontSize: 12, color: "var(--success-text,#166534)" }}>
          <Check size={13} style={{ marginRight: 4 }} />
          {addedMappings.length} mapping{addedMappings.length > 1 ? "s" : ""} added in this session.
        </div>
      )}

      <p style={{ fontSize: 11, color: "var(--muted-text)", margin: 0 }}>
        This issue type will appear in the customer booking flow for the mapped service when the service has requires_issue_type = true.
      </p>

      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <Btn variant="ghost" size="sm" onClick={onClose}>Close</Btn>
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function IssueTypesPage() {
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [serviceFilter, setServiceFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  const [modal, setModal]     = useState<"none" | "create" | "edit" | "map">("none");
  const [editing, setEditing] = useState<IssueType34E | null>(null);
  const [mapping, setMapping] = useState<IssueType34E | null>(null);
  const [form, setForm]       = useState<FormState>(BLANK_FORM);
  const [mapCatId, setMapCatId] = useState("");
  const [mapSvcId, setMapSvcId] = useState("");
  const [toast, setToast]     = useState<{ msg: string; ok: boolean } | null>(null);

  const notify = (msg: string, ok = true) => { setToast({ msg, ok }); setTimeout(() => setToast(null), 3500); };

  const cats = useApi(useCallback(() => catalogApi.listCategories(true), []));
  const catList: ServiceCategory[] = cats.data?.categories ?? [];

  // Services filtered by selected category filter
  const filterSvcs = useApi(
    useCallback(() => categoryFilter
      ? catalogApi.listMasterServices(categoryFilter)
      : Promise.resolve({ services: [] as MasterService[] }),
      [categoryFilter]
    )
  );
  const filterSvcList: MasterService[] = filterSvcs.data?.services ?? [];

  const list = useApi(
    useCallback(() => serviceOptionApi.listIssueTypes({
      search: search || undefined,
      category_id: categoryFilter || undefined,
      master_service_id: serviceFilter || undefined,
      status: statusFilter || undefined,
      page,
      page_size: 30,
    }), [search, categoryFilter, serviceFilter, statusFilter, page])
  );

  const items: (IssueType34E & { mapped_services_count?: number })[] = (list.data as { items?: (IssueType34E & { mapped_services_count?: number })[] } | null)?.items ?? [];
  const total: number = (list.data as { total?: number } | null)?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 30));

  // Severity filter applied client-side (or re-fetch with it)
  const rows = severityFilter ? items.filter(r => r.severity === severityFilter) : items;

  function openCreate() {
    setForm(BLANK_FORM); setEditing(null); setMapCatId(""); setMapSvcId(""); setModal("create");
  }
  function openEdit(row: IssueType34E) {
    setForm({
      name: row.name, code: row.code, severity: row.severity,
      description: row.description ?? "",
      requires_photo: row.requires_photo, requires_description: row.requires_description,
      customer_visible: (row as IssueType34E & { customer_visible?: boolean }).customer_visible ?? true,
      display_order: row.display_order, status: row.status,
      category_id: row.category_id ?? "", master_service_id: row.master_service_id ?? "",
    });
    setEditing(row); setModal("edit");
  }

  const createAction = useAction(async (data: FormState) => {
    const created = await serviceOptionApi.createIssueType({
      name: data.name, code: data.code, severity: data.severity,
      description: data.description || undefined,
      requires_photo: data.requires_photo,
      requires_description: data.requires_description,
      customer_visible: data.customer_visible,
      display_order: data.display_order,
      status: data.status,
      category_id: data.category_id || undefined,
    });
    // If a service was selected, create the mapping
    if (mapSvcId && created && (created as unknown as { id?: string } | null)) {
      const createdId = (created as unknown as { id?: string; data?: { id?: string } })?.id
        || (created as unknown as { data?: { id?: string } })?.data?.id;
      if (createdId) {
        try {
          await serviceOptionApi.addServiceIssueMapping(mapSvcId, { issue_type_id: createdId });
        } catch {
          // non-fatal
        }
      }
    }
    list.refetch(); setModal("none"); notify("Issue type created.");
  });

  const editAction = useAction(async ({ id, data }: { id: string; data: FormState }) => {
    await serviceOptionApi.updateIssueType(id, {
      name: data.name, code: data.code, severity: data.severity,
      description: data.description || undefined,
      requires_photo: data.requires_photo,
      requires_description: data.requires_description,
      customer_visible: data.customer_visible,
      display_order: data.display_order,
      status: data.status,
      category_id: data.category_id || undefined,
    });
    list.refetch(); setModal("none"); notify("Issue type updated.");
  });

  const activateAction = useAction(async (id: string) => {
    await serviceOptionApi.activateIssueType(id); list.refetch(); notify("Activated.");
  });

  const deactivateAction = useAction(async (id: string) => {
    await serviceOptionApi.deactivateIssueType(id); list.refetch(); notify("Deactivated.");
  });

  const archiveAction = useAction(async (id: string) => {
    await serviceOptionApi.archiveIssueType(id); list.refetch(); notify("Archived.");
  });

  const columns = [
    {
      key: "code", label: "Code", width: 140,
      render: (_: unknown, row: IssueType34E) => (
        <span style={{ fontFamily: "monospace", fontSize: 11, fontWeight: 600,
          background: "var(--surface-sunken)", padding: "2px 7px", borderRadius: 5,
          border: "1px solid var(--border)", color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
          {row.code}
        </span>
      ),
    },
    {
      key: "name", label: "Name / Description",
      render: (_: unknown, row: IssueType34E) => (
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>{row.name}</div>
          {row.description && (
            <div style={{ fontSize: 11, color: "var(--muted-text)", marginTop: 2 }}>{row.description}</div>
          )}
        </div>
      ),
    },
    {
      key: "severity", label: "Severity", width: 100,
      render: (_: unknown, row: IssueType34E) => (
        <Badge variant={SEV_BADGE[row.severity] ?? "muted"} size="sm">{row.severity}</Badge>
      ),
    },
    {
      key: "mapped_services_count", label: "Mapped Services", width: 120,
      render: (_: unknown, row: IssueType34E & { mapped_services_count?: number }) => (
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontWeight: 700, fontSize: 14, fontVariantNumeric: "tabular-nums" }}>
            {row.mapped_services_count ?? 0}
          </span>
          {(row.mapped_services_count ?? 0) === 0 && (
            <span style={{ fontSize: 10, color: "var(--danger-text,#b91c1c)" }}>Unmapped</span>
          )}
        </div>
      ),
    },
    {
      key: "requires_photo", label: "Photo", width: 65,
      render: (_: unknown, row: IssueType34E) => (
        <span style={{ fontSize: 12, color: row.requires_photo ? "var(--primary)" : "var(--muted-text)" }}>
          {row.requires_photo ? "Yes" : "No"}
        </span>
      ),
    },
    {
      key: "requires_description", label: "Desc", width: 65,
      render: (_: unknown, row: IssueType34E) => (
        <span style={{ fontSize: 12, color: row.requires_description ? "var(--primary)" : "var(--muted-text)" }}>
          {row.requires_description ? "Yes" : "No"}
        </span>
      ),
    },
    {
      key: "customer_visible", label: "Visible", width: 65,
      render: (_: unknown, row: IssueType34E & { customer_visible?: boolean }) => (
        <span style={{ fontSize: 12, color: row.customer_visible !== false ? "var(--success)" : "var(--muted-text)" }}>
          {row.customer_visible !== false ? "Yes" : "No"}
        </span>
      ),
    },
    {
      key: "status", label: "Status", width: 90,
      render: (_: unknown, row: IssueType34E) => (
        <Badge variant={STATUS_BADGE[row.status] ?? "muted"} size="sm">{row.status}</Badge>
      ),
    },
    {
      key: "id", label: "Actions", width: 160,
      render: (_: unknown, row: IssueType34E) => (
        <div style={{ display: "flex", gap: 4 }}>
          <Btn size="xs" variant="ghost" onClick={() => openEdit(row)}><Pencil size={11} /></Btn>
          <Btn size="xs" variant="ghost" onClick={() => { setMapping(row); setModal("map"); }}>
            <Link2 size={11} />
          </Btn>
          {row.status === "active" && (
            <Btn size="xs" variant="ghost" loading={deactivateAction.loading}
              onClick={() => deactivateAction.execute(row.id)}><PowerOff size={11} /></Btn>
          )}
          {row.status === "inactive" && (
            <Btn size="xs" variant="ghost" loading={activateAction.loading}
              onClick={() => activateAction.execute(row.id)}><Power size={11} /></Btn>
          )}
          {row.status !== "archived" && (
            <Btn size="xs" variant="ghost" loading={archiveAction.loading}
              onClick={() => { if (confirm(`Archive "${row.name}"?`)) archiveAction.execute(row.id); }}>
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
    <AdminLayout activeNav="issue-types">
      <SectionHeader
        title="Issue Types"
        subtitle={`${total} master problem / fault types across all services`}
        actions={<Btn size="sm" variant="primary" onClick={openCreate}><Plus size={14} style={{ marginRight: 4 }} /> New Issue Type</Btn>}
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
              placeholder="Name or code…"
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
          <div style={{ minWidth: 120 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "var(--muted-text)", marginBottom: 5 }}>Severity</div>
            <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)}
              style={{ height: 36, padding: "0 10px", border: "1px solid var(--border)", borderRadius: 8, fontSize: 13, background: "var(--card-bg)", color: "var(--text)", outline: "none" }}>
              <option value="">All</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
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
          rows={rows as unknown as Record<string, unknown>[]}
          loading={list.loading}
          emptyText={search || categoryFilter || serviceFilter || severityFilter || statusFilter
            ? "No issue types match the current filters."
            : "No issue types yet. Create the first one."}
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
        title={modal === "create" ? "New Issue Type" : "Edit Issue Type"}
        size="lg">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {(createAction.error || editAction.error) && (
            <div style={{ padding: "10px 14px", borderRadius: 9, background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{createAction.error || editAction.error}</p>
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <Input label="Name *" placeholder="AC Not Cooling" value={form.name}
              onChange={v => setForm(f => ({ ...f, name: v }))} />
            <Input label="Code *" placeholder="AC_NOT_COOLING" value={form.code}
              onChange={v => setForm(f => ({ ...f, code: v.toUpperCase() }))} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <FieldRow label="Default Severity">
              <StyledSelect value={form.severity} onChange={v => setForm(f => ({ ...f, severity: v }))}
                options={[{ value: "low", label: "Low" }, { value: "medium", label: "Medium" },
                          { value: "high", label: "High" }, { value: "critical", label: "Critical" }]} />
            </FieldRow>
            <FieldRow label="Status">
              <StyledSelect value={form.status} onChange={v => setForm(f => ({ ...f, status: v }))}
                options={[{ value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }]} />
            </FieldRow>
          </div>

          <FieldRow label="Description">
            <textarea value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Brief description of this issue type…" rows={2}
              style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text)", fontSize: 13, fontFamily: "inherit", resize: "vertical", outline: "none", boxSizing: "border-box" }} />
          </FieldRow>

          <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
            <CheckRow label="Customer Visible" checked={form.customer_visible}
              onChange={v => setForm(f => ({ ...f, customer_visible: v }))} />
            <CheckRow label="Requires Photo" checked={form.requires_photo}
              onChange={v => setForm(f => ({ ...f, requires_photo: v }))} />
            <CheckRow label="Requires Description" checked={form.requires_description}
              onChange={v => setForm(f => ({ ...f, requires_description: v }))} />
          </div>

          <Input label="Display Order" type="number" value={String(form.display_order)}
            onChange={v => setForm(f => ({ ...f, display_order: Number(v) || 0 }))} />

          {/* Mapping section — only in create */}
          {modal === "create" && (
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 10 }}>
                Map to Service (optional)
              </div>
              <ServiceSelector
                categoryId={mapCatId} setCategoryId={setMapCatId}
                serviceId={mapSvcId} setServiceId={setMapSvcId}
              />
              {mapCatId && !mapSvcId && (
                <p style={{ fontSize: 11, color: "var(--muted-text)", marginTop: 6 }}>
                  Select a service to map this issue — or skip and map later via the link icon.
                </p>
              )}
              {!mapCatId && (
                <p style={{ fontSize: 11, color: "var(--muted-text)", marginTop: 6 }}>
                  Without a service mapping, this issue type won't appear in the customer booking flow.
                </p>
              )}
            </div>
          )}

          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setModal("none")}>Cancel</Btn>
            <Btn variant="primary" size="sm"
              disabled={!form.name.trim() || !form.code.trim()}
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

      {/* Map to Service Modal */}
      <Modal open={modal === "map" && !!mapping}
        onClose={() => { setModal("none"); setMapping(null); list.refetch(); }}
        title="Map Issue Type to Service">
        {mapping && (
          <MappingModal issue={mapping} onClose={() => { setModal("none"); setMapping(null); list.refetch(); }} />
        )}
      </Modal>
    </AdminLayout>
  );
}
