"use client";
import React, { useState, useCallback, useMemo } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader,
} from "../../../components/shared/ui";
import { catalogApi, type Brand34D, type BrandDuplicateWarning } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { RefreshCw, Download, Merge } from "lucide-react";

const STATUS_VARIANT: Record<string, "success" | "warning" | "muted" | "danger"> = {
  active: "success", inactive: "warning", archived: "muted",
  deprecated: "muted", pending_review: "warning", rejected: "danger",
};

type FormState = {
  name: string; code: string; display_name: string; description: string;
  website_url: string; country_of_origin: string; logo_url: string;
  is_global: boolean; display_order: number; force: boolean;
};
const BLANK: FormState = {
  name: "", code: "", display_name: "", description: "",
  website_url: "", country_of_origin: "", logo_url: "",
  is_global: true, display_order: 0, force: false,
};

function isDupWarning(r: unknown): r is BrandDuplicateWarning {
  return (r as BrandDuplicateWarning)?.warning === "BRAND_DUPLICATE_POSSIBLE";
}

function BrandActionMenu({ brand, onEdit, onActivate, onDeactivate, onArchive, onMerge }: {
  brand: Brand34D;
  onEdit: () => void;
  onActivate: () => void;
  onDeactivate: () => void;
  onArchive: () => void;
  onMerge: () => void;
}) {
  const [open, setOpen] = useState(false);
  const items = [
    { label: "Edit Brand", action: onEdit },
    { label: "Merge Into…", action: onMerge },
    null,
    brand.status !== "active" ? { label: "Activate", action: onActivate } : null,
    brand.status === "active" ? { label: "Deactivate", action: onDeactivate } : null,
    { label: "Archive", action: onArchive, danger: true },
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
              item === null
                ? <hr key={i} style={{ margin: 0, border: "none", borderTop: "1px solid var(--border)" }} />
                : item
                  ? <button key={i} onClick={() => { setOpen(false); item.action(); }} style={{
                      display: "block", width: "100%", textAlign: "left",
                      padding: "9px 16px", fontSize: 13, background: "none", border: "none",
                      cursor: "pointer", color: item.danger ? "var(--danger-text, #e53e3e)" : "var(--text-primary)",
                    }}>{item.label}</button>
                  : null
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default function BrandsPage() {
  const [q, setQ]             = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [modal, setModal]     = useState<"none" | "create" | "edit" | "merge">("none");
  const [editing, setEditing] = useState<Brand34D | null>(null);
  const [mergeSource, setMergeSource] = useState<Brand34D | null>(null);
  const [mergeTarget, setMergeTarget] = useState("");
  const [mergeNote, setMergeNote]     = useState("");
  const [dupWarning, setDupWarning]   = useState<BrandDuplicateWarning | null>(null);
  const [form, setForm]       = useState<FormState>({ ...BLANK });
  const [toast, setToast]     = useState<{ msg: string; ok: boolean } | null>(null);

  const notify = (msg: string, ok = true) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3500);
  };

  const brands = useApi(useCallback(
    () => catalogApi.listBrands({ search: q || undefined, status: statusFilter || undefined }),
    [q, statusFilter],
  ));

  const createAction = useAction(async (data: FormState) => {
    const result = await catalogApi.createBrand({
      name: data.name, code: data.code || undefined, display_name: data.display_name || undefined,
      description: data.description || undefined, website_url: data.website_url || undefined,
      country_of_origin: data.country_of_origin || undefined, logo_url: data.logo_url || undefined,
      is_global: data.is_global, display_order: data.display_order, force: data.force,
    });
    if (isDupWarning(result)) {
      setDupWarning(result);
      return;
    }
    setDupWarning(null);
    brands.refetch(); setModal("none"); notify("Brand created.");
  });

  const editAction = useAction(async ({ id, data }: { id: string; data: FormState }) => {
    await catalogApi.updateBrand(id, {
      display_name: data.display_name || undefined,
      description: data.description || undefined,
      website_url: data.website_url || undefined,
      country_of_origin: data.country_of_origin || undefined,
      logo_url: data.logo_url || undefined,
      is_global: data.is_global,
      display_order: data.display_order,
    });
    brands.refetch(); setModal("none"); notify("Brand updated.");
  });

  const activateAction  = useAction(async (id: string) => { await catalogApi.activateBrand(id);   brands.refetch(); notify("Brand activated."); });
  const deactivateAction= useAction(async (id: string) => { await catalogApi.deactivateBrand(id); brands.refetch(); notify("Brand deactivated."); });
  const archiveAction   = useAction(async (id: string) => { await catalogApi.archiveBrand(id);    brands.refetch(); notify("Brand archived."); });
  const seedAction      = useAction(async () => { await catalogApi.seedBrands(); brands.refetch(); notify("Starter brands seeded."); });
  const mergeAction     = useAction(async () => {
    if (!mergeSource || !mergeTarget) return;
    await catalogApi.mergeBrand(mergeSource.brand_id, mergeTarget, mergeNote || undefined);
    brands.refetch(); setModal("none"); setMergeSource(null); setMergeTarget(""); setMergeNote(""); notify("Brands merged.");
  });

  function openCreate() { setForm({ ...BLANK }); setEditing(null); setDupWarning(null); setModal("create"); }
  function openEdit(b: Brand34D) {
    setForm({ name: b.name, code: b.code ?? "", display_name: b.display_name, description: b.description ?? "",
      website_url: b.website_url ?? "", country_of_origin: b.country_of_origin ?? "",
      logo_url: b.logo_url ?? "", is_global: b.is_global, display_order: b.display_order, force: false });
    setEditing(b); setModal("edit");
  }
  function openMerge(b: Brand34D) { setMergeSource(b); setMergeTarget(""); setMergeNote(""); setModal("merge"); }
  function setF<K extends keyof FormState>(k: K, v: FormState[K]) { setForm(p => ({ ...p, [k]: v })); }

  const rows = brands.data?.brands ?? [];
  const total = brands.data?.total ?? 0;
  const otherBrands = useMemo(() => rows.filter(b => b.brand_id !== mergeSource?.brand_id), [rows, mergeSource]);
  const activeAction = editing ? editAction : createAction;
  const canSave = !!form.name;

  const columns = [
    {
      key: "name", label: "Brand",
      render: (_: unknown, row: Brand34D) => (
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {row.logo_url
            ? <img src={row.logo_url} alt={row.name} style={{ width: 32, height: 32, objectFit: "contain", borderRadius: 6, border: "1px solid var(--border)" }} />
            : <div style={{ width: 32, height: 32, borderRadius: 6, background: "var(--border)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight: 700, color: "var(--text-secondary)" }}>
                {row.name[0]?.toUpperCase()}
              </div>
          }
          <div>
            <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{row.display_name || row.name}</span>
            <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-secondary)" }}>{row.code ?? row.slug}</p>
          </div>
        </div>
      ),
    },
    {
      key: "status", label: "Status", width: 120,
      render: (_: unknown, row: Brand34D) => (
        <Badge variant={STATUS_VARIANT[row.status] ?? "muted"}>{row.status.replace(/_/g, " ")}</Badge>
      ),
    },
    {
      key: "is_global", label: "Scope", width: 90,
      render: (_: unknown, row: Brand34D) => (
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{row.is_global ? "Global" : "Regional"}</span>
      ),
    },
    {
      key: "country_of_origin", label: "Origin", width: 100,
      render: (_: unknown, row: Brand34D) => (
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{row.country_of_origin || "—"}</span>
      ),
    },
    {
      key: "provider_usage_count", label: "Providers", width: 90,
      render: (_: unknown, row: Brand34D) => (
        <span style={{ fontSize: 13, fontWeight: 600 }}>{row.provider_usage_count ?? 0}</span>
      ),
    },
    {
      key: "category_mapping_count", label: "Categories", width: 90,
      render: (_: unknown, row: Brand34D) => (
        <span style={{ fontSize: 13 }}>{row.category_mapping_count ?? 0}</span>
      ),
    },
    {
      key: "brand_id", label: "", width: 120,
      render: (_: unknown, row: Brand34D) => (
        <BrandActionMenu brand={row}
          onEdit={() => openEdit(row)}
          onActivate={() => activateAction.execute(row.brand_id)}
          onDeactivate={() => deactivateAction.execute(row.brand_id)}
          onArchive={() => archiveAction.execute(row.brand_id)}
          onMerge={() => openMerge(row)}
        />
      ),
    },
  ];

  return (
    <AdminLayout activeNav="brands">
      <SectionHeader
        title="Brand Management"
        subtitle={`${total} brands in the platform catalog. Providers select from these brands when setting up their services.`}
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="secondary" size="sm" loading={seedAction.loading} onClick={() => seedAction.execute()}>
              Seed Starters
            </Btn>
            <Btn variant="secondary" size="sm" onClick={() => brands.refetch()}>
              <RefreshCw size={14} style={{ marginRight: 4 }} /> Refresh
            </Btn>
            <Btn variant="primary" size="sm" onClick={openCreate}>+ New Brand</Btn>
          </div>
        }
      />

      {toast && (
        <div style={{
          position: "fixed", top: 16, right: 16, zIndex: 9999, padding: "10px 18px",
          borderRadius: 10, background: toast.ok ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.ok ? "var(--success-text)" : "var(--danger-text)", fontSize: 13,
        }}>{toast.msg}</div>
      )}

      <Card padding={16} style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ flex: 1, minWidth: 220 }}>
            <input placeholder="Search brands by name, code, or slug…" value={q} onChange={e => setQ(e.target.value)}
              style={{ width: "100%", padding: "8px 12px", borderRadius:"var(--radius-md)", fontSize: 13, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", outline: "none", boxSizing: "border-box" }} />
          </div>
          <div style={{ minWidth: 160 }}>
            <Select label="" value={statusFilter} onChange={setStatusFilter}
              placeholder="All Statuses"
              options={[
                { value: "", label: "All Statuses" }, { value: "active", label: "Active" },
                { value: "inactive", label: "Inactive" }, { value: "pending_review", label: "Pending Review" },
                { value: "archived", label: "Archived" },
              ]} />
          </div>
          {(q || statusFilter) && (
            <Btn variant="ghost" size="sm" onClick={() => { setQ(""); setStatusFilter(""); }}>Clear</Btn>
          )}
        </div>
      </Card>

      {brands.error && (
        <div style={{ padding: "12px 16px", borderRadius: 10, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", marginBottom: 16 }}>
          <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>{brands.error}</p>
        </div>
      )}

      <DataTable
        columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
        rows={rows as unknown as Record<string, unknown>[]}
        loading={brands.loading}
        emptyText="No brands found. Use 'Seed Starters' to add 25 common appliance/electronics brands, or create brands manually."
      />

      {/* Create / Edit */}
      <Modal open={modal === "create" || modal === "edit"} onClose={() => setModal("none")}
        title={editing ? `Edit: ${editing.display_name || editing.name}` : "New Brand"}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {activeAction.error && (
            <div style={{ padding: "10px 14px", borderRadius:"var(--radius-md)", background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>{activeAction.error}</p>
            </div>
          )}
          {dupWarning && (
            <div style={{ padding: "12px 14px", borderRadius:"var(--radius-md)", background: "var(--warning-bg, #fffbeb)", border: "1px solid var(--warning-border, #f6e05e)" }}>
              <p style={{ fontSize: 13, fontWeight: 600, color: "var(--warning-text, #744210)", margin: "0 0 6px" }}>Possible Duplicate Detected</p>
              <p style={{ fontSize: 12, color: "var(--warning-text, #744210)", margin: "0 0 10px" }}>{dupWarning.message}</p>
              <div style={{ display: "flex", gap: 8 }}>
                <Btn variant="secondary" size="xs" onClick={() => setDupWarning(null)}>Cancel</Btn>
                <Btn variant="primary" size="xs" onClick={() => { setF("force", true); createAction.execute({ ...form, force: true }); }}>
                  Create Anyway
                </Btn>
              </div>
            </div>
          )}

          <Input label="Brand Name *" placeholder="e.g. Samsung" value={form.name}
            onChange={v => setF("name", v)} disabled={!!editing} />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Input label="Display Name" placeholder="e.g. Samsung Electronics" value={form.display_name}
              onChange={v => setF("display_name", v)} />
            <Input label="Code" placeholder="e.g. samsung" value={form.code}
              onChange={v => setF("code", v)} disabled={!!editing} />
          </div>
          <Input label="Description" placeholder="Optional short description" value={form.description}
            onChange={v => setF("description", v)} />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Input label="Country of Origin" placeholder="e.g. South Korea" value={form.country_of_origin}
              onChange={v => setF("country_of_origin", v)} />
            <Input label="Display Order" type="number" value={String(form.display_order)}
              onChange={v => setF("display_order", parseInt(v) || 0)} />
          </div>
          <Input label="Website URL" placeholder="https://samsung.com" value={form.website_url}
            onChange={v => setF("website_url", v)} />
          <Input label="Logo URL" placeholder="https://…/logo.png" value={form.logo_url}
            onChange={v => setF("logo_url", v)} />

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <button onClick={() => setF("is_global", !form.is_global)} style={{
              width: 40, height: 22, borderRadius: 11, border: "none", cursor: "pointer", position: "relative",
              background: form.is_global ? "var(--brand, #1a56db)" : "var(--border)",
            }}>
              <span style={{ position: "absolute", top: 2, left: form.is_global ? 20 : 2, width: 18, height: 18, borderRadius: "50%", background: "#fff", transition: "left .2s" }} />
            </button>
            <span style={{ fontSize: 13 }}>Global Brand (available across all categories)</span>
          </div>

          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="secondary" size="sm" onClick={() => setModal("none")}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={activeAction.loading} disabled={!canSave}
              onClick={() => editing
                ? editAction.execute({ id: editing.brand_id, data: form })
                : createAction.execute(form)}>
              {editing ? "Save Changes" : "Create Brand"}
            </Btn>
          </div>
        </div>
      </Modal>

      {/* Merge */}
      <Modal open={modal === "merge"} onClose={() => setModal("none")}
        title={`Merge: ${mergeSource?.display_name || mergeSource?.name}`}>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 14 }}>
          The source brand will be marked as deprecated and its providers/services will be remapped to the target.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Select label="Merge Into (target brand) *" value={mergeTarget}
            onChange={setMergeTarget} placeholder="Select target brand…"
            options={otherBrands.filter(b => b.status === "active").map(b => ({ value: b.brand_id, label: b.display_name || b.name }))} />
          <Input label="Admin Note" placeholder="Reason for merge (optional)" value={mergeNote}
            onChange={setMergeNote} />
          {mergeAction.error && <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>{mergeAction.error}</p>}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="secondary" size="sm" onClick={() => setModal("none")}>Cancel</Btn>
            <Btn variant="danger" size="sm" loading={mergeAction.loading} disabled={!mergeTarget}
              onClick={() => mergeAction.execute()}>
              Merge Brands
            </Btn>
          </div>
        </div>
      </Modal>
    </AdminLayout>
  );
}
