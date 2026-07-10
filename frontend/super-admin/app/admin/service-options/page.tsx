"use client";
import React, { useState, useCallback, useRef, useEffect } from "react";
import Link from "next/link";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { PageShell, PageHeader, SearchBar } from "../../../components/shared/layout";
import { Card, Badge, Btn, Modal, Input, Skeleton } from "../../../components/shared/ui";
import { serviceOptionApi, catalogApi, type ServiceOption34E, type ServiceOptionSummary, type ServiceCategory } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { Settings2, Plus, Pencil, Power, PowerOff, Archive, ExternalLink, ChevronDown, X, SlidersHorizontal } from "lucide-react";

// ─── Constants ──────────────────────────────────────────────────────────────

const OPTION_TYPES = [
  { value: "add_on",    label: "Add-On" },
  { value: "upgrade",   label: "Upgrade" },
  { value: "material",  label: "Material" },
  { value: "tool",      label: "Tool" },
  { value: "visit_fee", label: "Visit Fee" },
  { value: "type",      label: "Type/Variant" },
  { value: "package",   label: "Package" },
  { value: "size",      label: "Size" },
  { value: "duration",  label: "Duration" },
  { value: "mode",      label: "Mode" },
  { value: "unit",      label: "Unit" },
  { value: "custom",    label: "Custom" },
];

const OPTION_TYPE_LABEL: Record<string, string> = Object.fromEntries(OPTION_TYPES.map(t => [t.value, t.label]));

const UNIT_LABEL: Record<string, string> = {
  per_unit: "/ unit", per_hour: "/ hr", flat: "flat", per_sqft: "/ sq.ft",
  per_kg: "/ kg", per_item: "/ item", per_visit: "/ visit", none: "—",
};

const BLANK = {
  name: "", code: "", option_type: "add_on", unit: "per_unit",
  default_price: "0", description: "", is_customer_selectable: true, display_order: 0,
};
type FormState = typeof BLANK;

// ─── Readiness badge ────────────────────────────────────────────────────────

function ReadinessBadge({ row }: { row: ServiceOption34E & { mapped_services_count?: number } }) {
  const mapped = (row.mapped_services_count ?? 0) > 0;
  const hasPrice = Number(row.default_price) > 0;
  if (row.status === "inactive") return <Badge variant="warning" size="sm">Inactive</Badge>;
  if (row.status === "archived") return <Badge variant="muted" size="sm">Archived</Badge>;
  if (!mapped) return <Badge variant="danger" size="sm">Unmapped</Badge>;
  if (!hasPrice) return <Badge variant="warning" size="sm">No price</Badge>;
  return <Badge variant="success" size="sm">Ready</Badge>;
}

// ─── Action menu ────────────────────────────────────────────────────────────

function ActionMenu({ row, onEdit, onActivate, onDeactivate, onArchive }: {
  row: ServiceOption34E;
  onEdit: () => void;
  onActivate: () => void;
  onDeactivate: () => void;
  onArchive: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <Btn size="xs" variant="ghost" onClick={() => setOpen(o => !o)}>
        <ChevronDown size={12}/>
      </Btn>
      {open && (
        <div style={{
          position: "absolute", right: 0, top: "100%", zIndex: 50, minWidth: 170,
          background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: 10,
          boxShadow: "0 4px 20px rgba(0,0,0,0.12)", padding: "4px 0",
        }}>
          {[
            { label: "View Details", href: `/admin/service-options/${row.id}`, icon: <ExternalLink size={12}/> },
            { label: "Edit", onClick: onEdit, icon: <Pencil size={12}/> },
            row.status === "active"
              ? { label: "Deactivate", onClick: onDeactivate, icon: <PowerOff size={12}/>, danger: false }
              : row.status === "inactive"
              ? { label: "Activate", onClick: onActivate, icon: <Power size={12}/> }
              : null,
            row.status !== "archived"
              ? { label: "Archive", onClick: onArchive, icon: <Archive size={12}/>, danger: true }
              : null,
          ].filter(Boolean).map((item, i) => {
            if (!item) return null;
            const style: React.CSSProperties = {
              display: "flex", alignItems: "center", gap: 8,
              padding: "8px 14px", fontSize: 13, cursor: "pointer", width: "100%",
              border: "none", background: "transparent", textAlign: "left",
              color: item.danger ? "var(--danger-text,#b91c1c)" : "var(--text)",
            };
            if ("href" in item && item.href) {
              return (
                <Link key={i} href={item.href} onClick={() => setOpen(false)}
                  style={{ ...style, textDecoration: "none" }}>
                  {item.icon} {item.label}
                </Link>
              );
            }
            return (
              <button key={i} style={style} onClick={() => { item.onClick?.(); setOpen(false); }}>
                {item.icon} {item.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Summary card ───────────────────────────────────────────────────────────

function SummaryCard({ label, value, active, onClick }: {
  label: string; value: number; active?: boolean; onClick?: () => void;
}) {
  return (
    <div onClick={onClick} style={{
      background: active ? "var(--primary)" : "var(--card-bg)",
      border: `1px solid ${active ? "var(--primary)" : "var(--border)"}`,
      borderRadius: 10, padding: "12px 18px", cursor: onClick ? "pointer" : "default",
      flex: 1, minWidth: 100, transition: "all 0.15s",
    }}>
      <div style={{ fontSize: 11, color: active ? "rgba(255,255,255,0.8)" : "var(--muted-text)", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: active ? "#fff" : "var(--text)" }}>{value}</div>
    </div>
  );
}

// ─── Native select helper ───────────────────────────────────────────────────

function NativeSelect({ value, onChange, options, placeholder }: {
  value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
}) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)}
      style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)",
        background: "var(--bg)", color: "var(--text)", fontSize: 13, outline: "none",
        height: 38, minWidth: 140 }}>
      {placeholder && <option value="">{placeholder}</option>}
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}

// ─── Main page ───────────────────────────────────────────────────────────────

export default function ServiceOptionsPage() {
  const [search,        setSearch]        = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [typeFilter,    setTypeFilter]    = useState("");
  const [statusFilter,  setStatusFilter]  = useState("");
  const [mappedFilter,  setMappedFilter]  = useState<"" | "true" | "false">("");
  const [page,          setPage]          = useState(1);
  const [showAdvanced,  setShowAdvanced]  = useState(false);

  // Summary cards — clicking one applies a status/mapping filter
  const [cardFilter, setCardFilter] = useState<string>("");

  const summaryFetch = useApi(useCallback(() => serviceOptionApi.summary(), []));
  const summary: ServiceOptionSummary | null =
    (summaryFetch.data as { data?: ServiceOptionSummary } | null)?.data ?? null;

  const list = useApi(useCallback(
    () => serviceOptionApi.listOptions({
      search:        search   || undefined,
      category_id:   categoryFilter || undefined,
      option_type:   typeFilter     || undefined,
      status:        statusFilter   || undefined,
      mapped:        mappedFilter === "true" ? true : mappedFilter === "false" ? false : undefined,
      page,
      page_size: 50,
    }),
    [search, categoryFilter, typeFilter, statusFilter, mappedFilter, page]
  ));

  const categories = useApi(useCallback(() => catalogApi.listCategories(true), []));
  const [modal,   setModal]   = useState<"none" | "create" | "edit">("none");
  const [editing, setEditing] = useState<ServiceOption34E | null>(null);
  const [form,    setForm]    = useState<FormState>(BLANK);
  const [toast,   setToast]   = useState<{ msg: string; ok: boolean } | null>(null);

  const notify = (msg: string, ok = true) => {
    setToast({ msg, ok }); setTimeout(() => setToast(null), 3500);
  };

  const rows: (ServiceOption34E & { mapped_services_count?: number })[] =
    (list.data as { items?: ServiceOption34E[] } | null)?.items ?? [];
  const totalRows = (list.data as { total?: number } | null)?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalRows / 50));

  function openCreate() { setForm(BLANK); setEditing(null); setModal("create"); }
  function openEdit(row: ServiceOption34E) {
    setForm({
      name: row.name, code: row.code, option_type: row.option_type, unit: row.unit,
      default_price: row.default_price, description: row.description ?? "",
      is_customer_selectable: row.is_customer_selectable, display_order: row.display_order,
    });
    setEditing(row); setModal("edit");
  }

  const createAction = useAction(async (data: FormState) => {
    await serviceOptionApi.createOption({
      name: data.name, code: data.code, option_type: data.option_type, unit: data.unit,
      default_price: data.default_price, description: data.description || undefined,
      is_customer_selectable: data.is_customer_selectable, display_order: data.display_order,
      status: "active",
    });
    summaryFetch.refetch(); list.refetch(); setModal("none"); notify("Service option created.");
  });

  const editAction = useAction(async ({ id, data }: { id: string; data: FormState }) => {
    await serviceOptionApi.updateOption(id, {
      name: data.name, code: data.code, option_type: data.option_type, unit: data.unit,
      default_price: data.default_price, description: data.description || undefined,
      is_customer_selectable: data.is_customer_selectable, display_order: data.display_order,
    });
    summaryFetch.refetch(); list.refetch(); setModal("none"); notify("Service option updated.");
  });

  const activateAction = useAction(async (id: string) => {
    await serviceOptionApi.activateOption(id);
    summaryFetch.refetch(); list.refetch(); notify("Service option activated.");
  });

  const deactivateAction = useAction(async (id: string) => {
    await serviceOptionApi.deactivateOption(id);
    summaryFetch.refetch(); list.refetch(); notify("Service option deactivated.");
  });

  const archiveAction = useAction(async (id: string) => {
    await serviceOptionApi.archiveOption(id);
    summaryFetch.refetch(); list.refetch(); notify("Service option archived.");
  });

  const catOptions = (categories.data?.categories ?? []).map((c: ServiceCategory) => ({ value: c.category_id, label: c.name }));
  const hasFilters = !!(search || categoryFilter || typeFilter || statusFilter || mappedFilter);

  function clearFilters() {
    setSearch(""); setCategoryFilter(""); setTypeFilter(""); setStatusFilter(""); setMappedFilter(""); setPage(1);
  }

  function applyCardFilter(key: string, value: string) {
    clearFilters();
    setCardFilter(key);
    if (key === "unmapped") { setMappedFilter("false"); setStatusFilter("active"); }
    else if (key === "active") setStatusFilter("active");
    else if (key === "inactive") setStatusFilter("inactive");
    else if (key === "archived") setStatusFilter("archived");
    else if (key === "customer_selectable") { setStatusFilter("active"); }
  }

  return (
    <AdminLayout activeNav="service-options">
      <PageShell>
        <PageHeader
          title="Service Options"
          description="Master add-ons, upgrades, types, and extras available across all services"
          primaryAction={<Btn size="sm" variant="primary" onClick={openCreate}><Plus size={14}/> New Option</Btn>}
        />

        {toast && (
          <div style={{ padding: "10px 16px", borderRadius: 10,
            background: toast.ok ? "var(--success-bg)" : "var(--danger-bg)",
            border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
            color: toast.ok ? "var(--success-text)" : "var(--danger-text)", fontSize: 13 }}>
            {toast.ok ? "✓" : "✗"} {toast.msg}
          </div>
        )}

        {/* Summary cards */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {summaryFetch.loading ? (
            [...Array(6)].map((_, i) => <Skeleton key={i} height={60} style={{ flex: 1, minWidth: 100, borderRadius: 10 }}/>)
          ) : summary ? (
            <>
              <SummaryCard label="Total Options"   value={summary.total}             active={cardFilter === "total"} onClick={() => { clearFilters(); setCardFilter("total"); }}/>
              <SummaryCard label="Active"           value={summary.active}            active={cardFilter === "active"} onClick={() => applyCardFilter("active", "active")}/>
              <SummaryCard label="Inactive"         value={summary.inactive}          active={cardFilter === "inactive"} onClick={() => applyCardFilter("inactive", "inactive")}/>
              <SummaryCard label="Cust. Selectable" value={summary.customer_selectable} active={cardFilter === "customer_selectable"} onClick={() => applyCardFilter("customer_selectable", "")}/>
              <SummaryCard label="Mapped"           value={summary.mapped}            active={cardFilter === "mapped"} onClick={() => { clearFilters(); setMappedFilter("true"); setCardFilter("mapped"); }}/>
              <SummaryCard label="Unmapped"         value={summary.unmapped}          active={cardFilter === "unmapped"} onClick={() => applyCardFilter("unmapped", "")}/>
            </>
          ) : null}
        </div>

        {/* Filters */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ flex: 1, minWidth: 220 }}>
            <SearchBar value={search} onChange={v => { setSearch(v); setPage(1); }} placeholder="Search by name or code…"/>
          </div>
          <NativeSelect value={categoryFilter} onChange={v => { setCategoryFilter(v); setPage(1); }}
            options={catOptions} placeholder="All categories"/>
          <NativeSelect value={typeFilter} onChange={v => { setTypeFilter(v); setPage(1); }}
            options={OPTION_TYPES} placeholder="All types"/>
          <NativeSelect value={statusFilter} onChange={v => { setStatusFilter(v); setPage(1); }}
            options={[{ value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }, { value: "archived", label: "Archived" }]}
            placeholder="All statuses"/>
          <Btn variant={showAdvanced ? "primary" : "secondary"} size="sm"
            onClick={() => setShowAdvanced(x => !x)}>
            <SlidersHorizontal size={13}/> Filters
          </Btn>
          {hasFilters && (
            <Btn variant="ghost" size="sm" onClick={clearFilters}><X size={12}/> Clear</Btn>
          )}
        </div>

        {/* Advanced filters */}
        {showAdvanced && (
          <Card padding={16} style={{ display: "flex", gap: 14, flexWrap: "wrap", alignItems: "center" }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: "var(--muted-text)", marginBottom: 6 }}>Mapping Status</div>
              <NativeSelect value={mappedFilter}
                onChange={v => { setMappedFilter(v as "" | "true" | "false"); setPage(1); }}
                options={[{ value: "true", label: "Mapped only" }, { value: "false", label: "Unmapped only" }]}
                placeholder="All"/>
            </div>
          </Card>
        )}

        {/* Active filter chips */}
        {hasFilters && (
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {search && <Chip label={`Search: ${search}`} onRemove={() => setSearch("")}/>}
            {categoryFilter && <Chip label={`Category: ${catOptions.find(c => c.value === categoryFilter)?.label ?? categoryFilter}`} onRemove={() => setCategoryFilter("")}/>}
            {typeFilter && <Chip label={`Type: ${OPTION_TYPE_LABEL[typeFilter] ?? typeFilter}`} onRemove={() => setTypeFilter("")}/>}
            {statusFilter && <Chip label={`Status: ${statusFilter}`} onRemove={() => setStatusFilter("")}/>}
            {mappedFilter && <Chip label={mappedFilter === "true" ? "Mapped" : "Unmapped"} onRemove={() => setMappedFilter("")}/>}
          </div>
        )}

        {list.error && (
          <div style={{ padding: "10px 16px", borderRadius: 10,
            background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
            color: "var(--danger-text)", fontSize: 13 }}>
            ✗ {list.error}
          </div>
        )}

        <Card padding={0}>
          {list.loading ? (
            <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 8 }}>
              {[...Array(6)].map((_, i) => <Skeleton key={i} height={52} style={{ borderRadius: 8 }}/>)}
            </div>
          ) : rows.length === 0 ? (
            <div style={{ padding: 48, textAlign: "center" }}>
              <Settings2 size={32} style={{ color: "var(--text-tertiary)", margin: "0 auto 12px", display: "block" }}/>
              <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: 0 }}>
                {hasFilters ? "No service options match your filters." : "No service options yet. Create the first one."}
              </p>
              {hasFilters && (
                <Btn variant="ghost" size="sm" style={{ marginTop: 12 }} onClick={clearFilters}>Clear filters</Btn>
              )}
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                    {["Code", "Name", "Type", "Unit", "Mapped", "Readiness", "Price", "Customer?", "Status", ""].map(h => (
                      <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontSize: 11,
                        fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase",
                        letterSpacing: "0.06em", whiteSpace: "nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => (
                    <tr key={row.id} style={{ borderBottom: i < rows.length - 1 ? "1px solid var(--border)" : "none" }}>
                      <td style={{ padding: "10px 14px" }}>
                        <span style={{ fontFamily: "monospace", fontSize: 12, fontWeight: 600,
                          background: "var(--surface-sunken)", padding: "2px 8px", borderRadius: 5,
                          border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                          {row.code}
                        </span>
                      </td>
                      <td style={{ padding: "10px 14px", maxWidth: 220 }}>
                        <Link href={`/admin/service-options/${row.id}`} style={{ textDecoration: "none" }}>
                          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--primary)", margin: 0 }}>{row.name}</p>
                        </Link>
                        {row.description && (
                          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0",
                            whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: 200 }}>
                            {row.description}
                          </p>
                        )}
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        <Badge variant="info" size="sm">{OPTION_TYPE_LABEL[row.option_type] ?? row.option_type}</Badge>
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{UNIT_LABEL[row.unit] ?? row.unit}</span>
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        {(row.mapped_services_count ?? 0) > 0 ? (
                          <Link href={`/admin/service-options/${row.id}`} style={{ textDecoration: "none" }}>
                            <Badge variant="success" size="sm">{row.mapped_services_count} svc{row.mapped_services_count !== 1 ? "s" : ""}</Badge>
                          </Link>
                        ) : (
                          <span style={{ fontSize: 11, color: "var(--danger-text)",
                            background: "var(--danger-bg)", padding: "2px 8px", borderRadius: 4,
                            border: "1px solid var(--danger-border)" }}>Unmapped</span>
                        )}
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        <ReadinessBadge row={row}/>
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        <span style={{ fontFamily: "monospace", fontSize: 13, fontWeight: 600 }}>
                          ₹{Number(row.default_price).toFixed(2)}
                        </span>
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        <Badge variant={row.is_customer_selectable ? "success" : "muted"} size="sm">
                          {row.is_customer_selectable ? "Yes" : "No"}
                        </Badge>
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        <Badge variant={row.status === "active" ? "success" : row.status === "inactive" ? "warning" : "muted"} size="sm">
                          {row.status}
                        </Badge>
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                          <Btn size="xs" variant="ghost" onClick={() => openEdit(row)}><Pencil size={12}/></Btn>
                          <ActionMenu
                            row={row}
                            onEdit={() => openEdit(row)}
                            onActivate={() => activateAction.execute(row.id)}
                            onDeactivate={() => deactivateAction.execute(row.id)}
                            onArchive={() => archiveAction.execute(row.id)}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "12px 16px", borderTop: "1px solid var(--border)" }}>
              <span style={{ fontSize: 12, color: "var(--muted-text)" }}>
                Page {page} of {totalPages} ({totalRows} options)
              </span>
              <div style={{ display: "flex", gap: 8 }}>
                <Btn variant="secondary" size="sm" disabled={page === 1}
                  onClick={() => setPage(p => Math.max(1, p - 1))}>Prev</Btn>
                <Btn variant="secondary" size="sm" disabled={page >= totalPages}
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}>Next</Btn>
              </div>
            </div>
          )}
        </Card>

        {/* Create / Edit Modal */}
        <Modal open={modal !== "none"} onClose={() => setModal("none")}
               title={modal === "create" ? "New Service Option" : "Edit Service Option"}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14, maxHeight: "75vh", overflowY: "auto", paddingRight: 4 }}>
            {(createAction.error || editAction.error) && (
              <div style={{ padding: "10px 14px", borderRadius: 9, background: "var(--danger-bg)",
                border: "1px solid var(--danger-border)" }}>
                <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>
                  {createAction.error || editAction.error}
                </p>
              </div>
            )}
            <Input label="Name *" placeholder="Wall Mounting" value={form.name}
              onChange={v => setForm(f => ({ ...f, name: v }))}/>
            <Input label="Code *" placeholder="WALL_MOUNT" value={form.code}
              onChange={v => setForm(f => ({ ...f, code: v.toUpperCase() }))}/>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Option Type *</label>
                <select value={form.option_type} onChange={e => setForm(f => ({ ...f, option_type: e.target.value }))}
                  style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)",
                    background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, outline: "none" }}>
                  {OPTION_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Unit *</label>
                <select value={form.unit} onChange={e => setForm(f => ({ ...f, unit: e.target.value }))}
                  style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)",
                    background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, outline: "none" }}>
                  <option value="per_unit">Per Unit</option>
                  <option value="per_hour">Per Hour</option>
                  <option value="flat">Flat</option>
                  <option value="per_sqft">Per Sq.Ft</option>
                  <option value="per_kg">Per Kg</option>
                  <option value="per_item">Per Item</option>
                  <option value="per_visit">Per Visit</option>
                  <option value="none">None</option>
                </select>
              </div>
            </div>
            <Input label="Default Price (₹)" type="number" placeholder="0" value={form.default_price}
              onChange={v => setForm(f => ({ ...f, default_price: v }))}/>
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Description</label>
              <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Brief description…" rows={2}
                style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)",
                  background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, fontFamily: "inherit",
                  resize: "vertical", outline: "none", boxSizing: "border-box" }}/>
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
              <input type="checkbox" checked={form.is_customer_selectable}
                onChange={e => setForm(f => ({ ...f, is_customer_selectable: e.target.checked }))}/>
              <span style={{ fontSize: 13, color: "var(--text-primary)" }}>Customer can select this option</span>
            </label>
            <Input label="Display Order" type="number" value={String(form.display_order)}
              onChange={v => setForm(f => ({ ...f, display_order: Number(v) || 0 }))}/>
            {modal === "create" && (
              <div style={{ padding: "10px 14px", borderRadius: 8, background: "var(--surface-sunken)",
                border: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)" }}>
                After creating, go to <strong>Catalog → Master Services → [Service] → Options</strong> to map this option to services.
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
                {modal === "create" ? "Create Option" : "Save Changes"}
              </Btn>
            </div>
          </div>
        </Modal>
      </PageShell>
    </AdminLayout>
  );
}

function Chip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12,
      background: "var(--primary-muted, rgba(99,102,241,0.1))", color: "var(--primary)",
      border: "1px solid var(--primary-border, rgba(99,102,241,0.3))",
      borderRadius: 20, padding: "3px 10px 3px 12px" }}>
      {label}
      <button onClick={onRemove} style={{ background: "none", border: "none", cursor: "pointer",
        color: "inherit", padding: 0, display: "flex", alignItems: "center" }}>
        <X size={10}/>
      </button>
    </span>
  );
}
