"use client";
import React, { useState, useCallback, useMemo } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader, SummaryCard,} from "../../../components/shared/ui";
import { IconPicker } from "../../../components/shared/IconPicker";
import {
  catalogApi,
  type ServiceGroup, type ServiceGroupEnriched,
  type ServiceGroupsSummary, type ServiceCategory,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { ChevronRight, RefreshCw, Download, BarChart2, Package, AlertCircle, CheckCircle2, Settings } from "lucide-react";

// ── Label maps ─────────────────────────────────────────────────────────────────
const STATUS_LABEL: Record<string, string> = {
  active: "Active", inactive: "Inactive", deleted: "Archived",
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

// ── Action menu ────────────────────────────────────────────────────────────────
function GroupActionMenu({ row, onEdit, onActivate, onDeactivate, onArchive, onView }: {
  row: ServiceGroupEnriched;
  onEdit: () => void;
  onActivate: () => void;
  onDeactivate: () => void;
  onArchive: () => void;
  onView: () => void;
}) {
  const [open, setOpen] = useState(false);
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
            {[
              { label: "View Details", action: onView },
              { label: "Edit Group", action: onEdit },
              null,
              row.status !== "active" ? { label: "Activate", action: onActivate } : null,
              row.status === "active" ? { label: "Deactivate", action: onDeactivate } : null,
              { label: "Archive", action: onArchive, danger: true },
            ].map((item, i) =>
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

// ── Detail drawer ──────────────────────────────────────────────────────────────
function GroupDetailDrawer({ group, catMap, onClose }: {
  group: ServiceGroupEnriched | null;
  catMap: Record<string, string>;
  onClose: () => void;
}) {
  if (!group) return null;
  const lc = group.linked_counts;
  return (
    <div style={{
      position: "fixed", right: 0, top: 0, height: "100vh", width: 420, zIndex: 2000,
      background: "var(--surface)", borderLeft: "1px solid var(--border)",
      overflowY: "auto", boxShadow: "-4px 0 24px rgba(0,0,0,.12)",
      display: "flex", flexDirection: "column",
    }}>
      <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>{group.name}</h3>
          <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>{group.code}</p>
        </div>
        <Btn variant="ghost" size="xs" onClick={onClose}>✕</Btn>
      </div>

      <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Status row */}
        <div style={{ display: "flex", gap: 8 }}>
          <Badge variant={STATUS_VARIANT[group.status] ?? "muted"}>{STATUS_LABEL[group.status] ?? group.status}</Badge>
          <Badge variant={READINESS_VARIANT[group.runtime_readiness]}>{READINESS_LABEL[group.runtime_readiness]}</Badge>
        </div>

        {/* Overview */}
        <section>
          <p style={{ margin: "0 0 10px", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".06em", color: "var(--text-secondary)" }}>Overview</p>
          {[
            ["Category", catMap[group.category_id] ?? group.category_id],
            ["Slug", group.slug],
            ["Description", group.description || "—"],
            ["Display Order", String(group.display_order)],
            ["Created", group.created_at ? new Date(group.created_at).toLocaleDateString() : "—"],
            ["Updated", group.updated_at ? new Date(group.updated_at).toLocaleDateString() : "—"],
          ].map(([k, v]) => (
            <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "7px 0", borderBottom: "1px solid var(--border-subtle, var(--border))", fontSize: 13 }}>
              <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>{k}</span>
              <span style={{ color: "var(--text-primary)", textAlign: "right", maxWidth: 240, wordBreak: "break-word" }}>{v}</span>
            </div>
          ))}
        </section>

        {/* Linked counts */}
        <section>
          <p style={{ margin: "0 0 10px", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".06em", color: "var(--text-secondary)" }}>Linked Resources</p>
          <div style={{ display: "flex", gap: 12 }}>
            <div style={{ flex: 1, background: "var(--surface-alt, var(--surface))", border: "1px solid var(--border)", borderRadius: 10, padding: "12px 16px", textAlign: "center" }}>
              <p style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>{lc.services}</p>
              <p style={{ margin: "4px 0 0", fontSize: 11, color: "var(--text-secondary)" }}>Master Services</p>
            </div>
            <div style={{ flex: 1, background: "var(--surface-alt, var(--surface))", border: "1px solid var(--border)", borderRadius: 10, padding: "12px 16px", textAlign: "center" }}>
              <p style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>{lc.providers}</p>
              <p style={{ margin: "4px 0 0", fontSize: 11, color: "var(--text-secondary)" }}>Providers Using</p>
            </div>
          </div>
        </section>

        {/* Hierarchy */}
        <section>
          <p style={{ margin: "0 0 10px", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".06em", color: "var(--text-secondary)" }}>Catalog Hierarchy</p>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
            <span style={{ color: "var(--text-primary)" }}>{catMap[group.category_id] ?? "Category"}</span>
            <ChevronRight size={14} />
            <span style={{ color: "var(--brand, #1a56db)", fontWeight: 600 }}>{group.name}</span>
            <ChevronRight size={14} />
            <span style={{ color: "var(--text-tertiary, var(--text-secondary))" }}>{lc.services} service{lc.services !== 1 ? "s" : ""}</span>
          </div>
        </section>
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function ServiceGroupsPage() {
  // Filters
  const [q, setQ] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [hasServicesFilter, setHasServicesFilter] = useState<"" | "true" | "false">("");

  // Modal / detail
  const [modal, setModal] = useState<"none" | "create" | "edit">("none");
  const [editing, setEditing] = useState<ServiceGroupEnriched | null>(null);
  const [detailGroup, setDetailGroup] = useState<ServiceGroupEnriched | null>(null);
  const [archiveId, setArchiveId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(BLANK);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  // Data
  const summary = useApi(useCallback(() => catalogApi.getServiceGroupsSummary(), []));
  const categories = useApi(useCallback(() => catalogApi.listCategories(true), []));
  const groups = useApi(useCallback(
    () => catalogApi.listServiceGroups({
      categoryId: categoryFilter || undefined,
      status: statusFilter || undefined,
      q: q || undefined,
      hasServices: hasServicesFilter === "" ? undefined : hasServicesFilter === "true",
    }),
    [categoryFilter, statusFilter, q, hasServicesFilter],
  ));

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
      display_order: data.display_order, status: data.status,
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

  const archiveAction = useAction(async (id: string) => {
    await catalogApi.archiveServiceGroup(id);
    groups.refetch(); summary.refetch(); setArchiveId(null); notify("Group archived.");
  });

  const exportAction = useAction(async () => {
    const result = await catalogApi.exportServiceGroups({ categoryId: categoryFilter || undefined, status: statusFilter || undefined });
    const rows = result?.rows ?? [];
    const csv = [
      ["Name", "Code", "Category", "Status", "Services", "Providers", "Readiness", "Updated"].join(","),
      ...rows.map(r => [
        `"${r.name}"`, r.code, `"${catMap[r.category_id] ?? r.category_id}"`,
        r.status, r.linked_counts?.services ?? 0, r.linked_counts?.providers ?? 0,
        r.runtime_readiness, r.updated_at ?? "",
      ].join(","))
    ].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = "service-groups.csv"; a.click();
    notify("Exported.");
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
  const canSave = !!form.name && !!form.category_id;
  const activeAction = editing ? editAction : createAction;

  const columns = [
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
      render: (_: unknown, row: ServiceGroupEnriched) => (
        <GroupActionMenu
          row={row}
          onView={() => setDetailGroup(row)}
          onEdit={() => openEdit(row)}
          onActivate={() => activateAction.execute(row.id)}
          onDeactivate={() => deactivateAction.execute(row.id)}
          onArchive={() => setArchiveId(row.id)}
        />
      ),
    },
  ];

  return (
    <AdminLayout activeNav="service-groups">
      {/* Header */}
      <SectionHeader
        title="Service Groups"
        subtitle="Intermediate grouping layer between Categories and Master Services (e.g. 'AC Services' under 'Home Services')"
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="secondary" size="sm" loading={exportAction.loading} onClick={() => exportAction.execute()}>
              <Download size={14} style={{ marginRight: 4 }} /> Export
            </Btn>
            <Btn variant="secondary" size="sm" onClick={() => { groups.refetch(); summary.refetch(); }}>
              <RefreshCw size={14} style={{ marginRight: 4 }} /> Refresh
            </Btn>
            <Btn variant="primary" size="sm" onClick={openCreate}>+ New Group</Btn>
          </div>
        }
      />

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
          <SummaryCard label="Total Groups" value={s.total} />
          <SummaryCard label="Active" value={s.active} accent="var(--success-text, #22543d)" />
          <SummaryCard label="Inactive" value={s.inactive} accent="var(--warning-text, #744210)" />
          <SummaryCard label="With Services" value={s.groups_with_services} />
          <SummaryCard label="Empty Groups" value={s.empty_groups} accent="var(--danger-text, #c53030)" sub="no services linked" />
          <SummaryCard label="Runtime Ready" value={s.runtime_ready} accent="var(--brand, #1a56db)" />
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
            <Select label="" value={categoryFilter} onChange={setCategoryFilter}
              placeholder="All Categories" options={catFilterOptions} />
          </div>
          <div style={{ minWidth: 140 }}>
            <Select label="" value={statusFilter} onChange={setStatusFilter}
              placeholder="All Statuses"
              options={[{ value: "", label: "All Statuses" }, { value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }]} />
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
                onChange={v => setHasServicesFilter(v as "" | "true" | "false")}
                options={[{ value: "", label: "Any" }, { value: "true", label: "Has Services" }, { value: "false", label: "Empty Groups" }]} />
            </div>
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
        onRowClick={row => setDetailGroup(row as unknown as ServiceGroupEnriched)}
        emptyText="No service groups found. Create your first service group to organize master services within a category."
      />

      {/* Detail drawer */}
      <GroupDetailDrawer group={detailGroup} catMap={catMap} onClose={() => setDetailGroup(null)} />
      {detailGroup && (
        <div style={{ position: "fixed", inset: 0, zIndex: 1999, background: "rgba(0,0,0,.4)" }}
          onClick={() => setDetailGroup(null)} />
      )}

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
            {editing && (
              <Select label="Status" value={form.status} onChange={v => setF("status", v)}
                options={[{ value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }]} />
            )}
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

      {/* Archive confirm */}
      <Modal open={!!archiveId} onClose={() => setArchiveId(null)} title="Archive Service Group">
        <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 16 }}>
          This will archive the service group. It will no longer appear in active catalogs.
          Only groups with no linked master services can be archived.
        </p>
        {archiveAction.error && (
          <p style={{ fontSize: 13, color: "var(--danger-text)", marginBottom: 12 }}>{archiveAction.error}</p>
        )}
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <Btn variant="secondary" size="sm" onClick={() => setArchiveId(null)}>Cancel</Btn>
          <Btn variant="danger" size="sm" loading={archiveAction.loading}
            onClick={() => archiveId && archiveAction.execute(archiveId)}>
            Archive
          </Btn>
        </div>
      </Modal>
    </AdminLayout>
  );
}
