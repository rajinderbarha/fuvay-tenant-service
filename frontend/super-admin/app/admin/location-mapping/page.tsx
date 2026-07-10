"use client";
import { useCallback, useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  MapPin, Search, RefreshCw, Upload, Download, Plus, ChevronLeft, ChevronRight,
  SlidersHorizontal, CheckSquare, Square, X, AlertTriangle, History,
} from "lucide-react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader,
} from "../../../components/shared/ui";
import { SummaryCardsRow } from "../../../components/pricing/SummaryCard";
import { ResolutionPathTrace } from "../../../components/pricing/ResolutionPathTrace";
import { ImportWizard } from "../../../components/pricing/ImportWizard";
import { catalogApi } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import type { PricingTier, TierLocation, TierLocationsSummary } from "../../../lib/api";

const PAGE_SIZE = 50;

// ─── Helpers ─────────────────────────────────────────────────────────────────
const MAPPING_TYPE_COLORS: Record<string, string> = {
  Zipcode: "#7c3aed", City: "#0891b2", District: "#059669",
  Zone: "#d97706", State: "#dc2626", Country: "#6b7280",
};

function MappingTypeBadge({ type }: { type?: string | null }) {
  const t = type ?? "City";
  const c = MAPPING_TYPE_COLORS[t] ?? "#6b7280";
  return (
    <span style={{
      display: "inline-block", padding: "2px 8px", borderRadius: 10, fontSize: 11,
      fontWeight: 700, background: `${c}18`, color: c, border: `1px solid ${c}40`,
    }}>{t}</span>
  );
}

function ConflictBadge({ has, status }: { has?: boolean; status?: string }) {
  if (has) return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 8px",
      borderRadius: 10, fontSize: 11, fontWeight: 700,
      background: "var(--warning-bg,#fef3c7)", color: "#d97706", border: "1px solid #fcd34d",
    }}>
      <AlertTriangle size={10} /> {status ?? "Conflict"}
    </span>
  );
  return <Badge variant="success">Clean</Badge>;
}

// ─── Detail Drawer ────────────────────────────────────────────────────────────
function DetailDrawer({ row, tiers, onClose, onEdit, onResolve }: {
  row: TierLocation; tiers: PricingTier[];
  onClose: () => void; onEdit: (r: TierLocation) => void; onResolve: (r: TierLocation) => void;
}) {
  const tier = tiers.find(t => t.tier_id === row.tier_id);
  const fields: [string, string][] = [
    ["Country", row.country ?? "India"], ["State", row.state ?? "—"],
    ["District", row.district ?? "—"], ["City", row.city ?? "—"],
    ["Zipcode", row.zipcode ?? "—"], ["Zone", row.zone_name ?? "—"],
    ["Priority", String(row.priority)],
  ];
  return (
    <div style={{
      position: "fixed", right: 0, top: 0, bottom: 0, width: 400, zIndex: 201,
      background: "var(--surface-elevated,var(--surface))", borderLeft: "1px solid var(--border)",
      boxShadow: "var(--shadow-lg,-4px 0 24px rgba(0,0,0,0.14))",
      display: "flex", flexDirection: "column",
    }}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)" }}>Mapping Detail</span>
        <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", display: "flex", padding: 4, borderRadius: 6 }}>
          <X size={17} />
        </button>
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>ID</div>
          <code style={{ fontSize: 11, color: "var(--text-secondary)", wordBreak: "break-all" }}>{row.location_id}</code>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {fields.map(([k, v]) => (
            <div key={k}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 3 }}>{k}</div>
              <div style={{ fontSize: 13, fontWeight: v === "—" ? 400 : 600, color: v === "—" ? "var(--text-tertiary)" : "var(--text-primary)" }}>{v}</div>
            </div>
          ))}
        </div>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>Pricing Tier</div>
          {tier ? (
            <div style={{ padding: "10px 14px", borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
              <div style={{ fontWeight: 700, fontSize: 14 }}>{tier.name}</div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
                {tier.tier_type} · ×{tier.base_multiplier} · {tier.default_commission_percent}% commission
              </div>
            </div>
          ) : <span style={{ color: "var(--text-tertiary)", fontSize: 13 }}>—</span>}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>Type</div>
            <MappingTypeBadge type={row.mapping_type} />
          </div>
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>Status</div>
            <Badge variant={row.is_active ? "success" : "muted"}>{row.is_active ? "Active" : "Inactive"}</Badge>
          </div>
        </div>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>Conflict</div>
          <ConflictBadge has={row.has_conflict} status={row.conflict_status} />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {[["Created", row.created_at], ["Updated", row.updated_at]].map(([k, v]) => (
            <div key={k as string}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 3 }}>{k}</div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{v ? new Date(v as string).toLocaleDateString("en-IN") : "—"}</div>
            </div>
          ))}
        </div>
      </div>
      <div style={{ padding: "14px 20px", borderTop: "1px solid var(--border)", display: "flex", gap: 8 }}>
        <Btn variant="primary" size="sm" onClick={() => onEdit(row)} style={{ flex: 1 }}>Edit</Btn>
        {row.has_conflict && (
          <Btn variant="secondary" size="sm" onClick={() => onResolve(row)} style={{ flex: 1 }}>Resolve Conflict</Btn>
        )}
      </div>
    </div>
  );
}

// ─── Conflict Resolution Drawer ───────────────────────────────────────────────
function ConflictDrawer({ row, tiers, onClose, onDone }: {
  row: TierLocation; tiers: PricingTier[]; onClose: () => void; onDone: () => void;
}) {
  const [resType, setResType] = useState<"keep_this" | "override_tier" | "deactivate">("keep_this");
  const [overrideTier, setOverrideTier] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const options = [
    { val: "keep_this" as const, label: "Keep this mapping, deactivate others", desc: "Makes this the primary mapping — deactivates all other active mappings for the same zipcode." },
    { val: "override_tier" as const, label: "Change tier for this mapping", desc: "Reassign which tier this specific mapping resolves to." },
    { val: "deactivate" as const, label: "Deactivate this mapping", desc: "Remove this mapping from resolution. Other mappings for this zipcode remain." },
  ];

  async function handleResolve() {
    setLoading(true); setErr("");
    try {
      await catalogApi.resolveConflict(row.location_id, resType, overrideTier || undefined);
      onDone();
    } catch (e: unknown) { setErr((e as Error)?.message ?? "Failed to resolve conflict."); }
    finally { setLoading(false); }
  }

  return (
    <div style={{
      position: "fixed", right: 0, top: 0, bottom: 0, width: 400, zIndex: 201,
      background: "var(--surface-elevated,var(--surface))", borderLeft: "1px solid var(--border)",
      boxShadow: "var(--shadow-lg,-4px 0 24px rgba(0,0,0,0.14))",
      display: "flex", flexDirection: "column",
    }}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontWeight: 700, fontSize: 15, color: "#d97706" }}>Resolve Conflict</span>
        <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", display: "flex", padding: 4, borderRadius: 6 }}>
          <X size={17} />
        </button>
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ padding: "10px 14px", borderRadius: 8, background: "var(--warning-bg,#fef3c7)", border: "1px solid #fcd34d", fontSize: 13, color: "#92400e" }}>
          Zipcode <strong>{row.zipcode}</strong> has multiple active mappings. Choose how to resolve:
        </div>
        {options.map(o => (
          <label key={o.val} style={{
            display: "flex", gap: 10, padding: "12px 14px", borderRadius: 8, cursor: "pointer",
            border: `2px solid ${resType === o.val ? "var(--accent,var(--brand))" : "var(--border)"}`,
            background: resType === o.val ? "var(--surface-sunken)" : "var(--surface)",
          }}>
            <input type="radio" name="resType" value={o.val} checked={resType === o.val}
              onChange={() => setResType(o.val)} style={{ marginTop: 2 }} />
            <div>
              <div style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>{o.label}</div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 3 }}>{o.desc}</div>
            </div>
          </label>
        ))}
        {resType === "override_tier" && (
          <Select label="New Pricing Tier" value={overrideTier} onChange={setOverrideTier}
            placeholder="Select tier…" options={tiers.map(t => ({ value: t.tier_id, label: t.name }))} />
        )}
        {err && <p style={{ color: "var(--danger-text)", fontSize: 13, margin: 0 }}>{err}</p>}
      </div>
      <div style={{ padding: "14px 20px", borderTop: "1px solid var(--border)", display: "flex", gap: 8 }}>
        <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
        <Btn variant="primary" size="sm" loading={loading} onClick={handleResolve}
          disabled={resType === "override_tier" && !overrideTier} style={{ flex: 1 }}>
          Resolve Conflict
        </Btn>
      </div>
    </div>
  );
}

// ─── Advanced Filters Drawer ──────────────────────────────────────────────────
interface AdvancedFilters {
  city: string; zipcode: string; district: string; state: string; country: string; zone: string;
  mappingType: string; isActive: string; conflictStatus: string;
  createdFrom: string; createdTo: string; updatedFrom: string; updatedTo: string;
}
const EMPTY_FILTERS: AdvancedFilters = {
  city: "", zipcode: "", district: "", state: "", country: "", zone: "",
  mappingType: "", isActive: "", conflictStatus: "",
  createdFrom: "", createdTo: "", updatedFrom: "", updatedTo: "",
};

function FiltersDrawer({ open, onClose, values, onChange }: {
  open: boolean; onClose: () => void; values: AdvancedFilters; onChange: (v: AdvancedFilters) => void;
}) {
  const [local, setLocal] = useState<AdvancedFilters>(values);
  useEffect(() => { if (open) setLocal(values); }, [open]);

  function L(p: Partial<AdvancedFilters>) { setLocal(prev => ({ ...prev, ...p })); }
  if (!open) return null;

  return (
    <div style={{
      position: "fixed", right: 0, top: 0, bottom: 0, width: 360, zIndex: 201,
      background: "var(--surface-elevated,var(--surface))", borderLeft: "1px solid var(--border)",
      boxShadow: "var(--shadow-lg,-4px 0 24px rgba(0,0,0,0.14))",
      display: "flex", flexDirection: "column",
    }}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)" }}>Advanced Filters</span>
        <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", display: "flex", padding: 4, borderRadius: 6 }}>
          <X size={17} />
        </button>
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
        <Input label="City" placeholder="e.g. Mumbai" value={local.city} onChange={v => L({ city: v })} />
        <Input label="Zipcode" placeholder="e.g. 400001" value={local.zipcode} onChange={v => L({ zipcode: v })} />
        <Input label="District" placeholder="e.g. Dadar" value={local.district} onChange={v => L({ district: v })} />
        <Input label="State" placeholder="e.g. Maharashtra" value={local.state} onChange={v => L({ state: v })} />
        <Input label="Country" placeholder="India" value={local.country} onChange={v => L({ country: v })} />
        <Input label="Zone / Area" placeholder="e.g. Western Suburbs" value={local.zone} onChange={v => L({ zone: v })} />
        <Select label="Mapping Type" value={local.mappingType} onChange={v => L({ mappingType: v })}
          options={[
            { value: "", label: "All types" }, { value: "Zipcode", label: "Zipcode" },
            { value: "City", label: "City" }, { value: "District", label: "District" },
            { value: "Zone", label: "Zone" }, { value: "State", label: "State" },
          ]} />
        <Select label="Status" value={local.isActive} onChange={v => L({ isActive: v })}
          options={[{ value: "", label: "All" }, { value: "true", label: "Active only" }, { value: "false", label: "Inactive only" }]} />
        <Select label="Conflict Status" value={local.conflictStatus} onChange={v => L({ conflictStatus: v })}
          options={[{ value: "", label: "All" }, { value: "true", label: "Has conflict" }, { value: "false", label: "Clean" }]} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <Input label="Created from" placeholder="YYYY-MM-DD" value={local.createdFrom} onChange={v => L({ createdFrom: v })} />
          <Input label="Created to" placeholder="YYYY-MM-DD" value={local.createdTo} onChange={v => L({ createdTo: v })} />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <Input label="Updated from" placeholder="YYYY-MM-DD" value={local.updatedFrom} onChange={v => L({ updatedFrom: v })} />
          <Input label="Updated to" placeholder="YYYY-MM-DD" value={local.updatedTo} onChange={v => L({ updatedTo: v })} />
        </div>
      </div>
      <div style={{ padding: "14px 20px", borderTop: "1px solid var(--border)", display: "flex", gap: 8 }}>
        <Btn variant="ghost" size="sm" onClick={() => { setLocal(EMPTY_FILTERS); onChange(EMPTY_FILTERS); }}>Clear all</Btn>
        <Btn variant="primary" size="sm" onClick={() => { onChange(local); onClose(); }} style={{ flex: 1 }}>Apply Filters</Btn>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
function LocationMappingInner() {
  const searchParams = useSearchParams();
  const initialTierId = searchParams.get("tier_id") ?? "";
  const initialConflict = searchParams.get("has_conflict") === "true";

  const tiersApi = useApi(useCallback(() => catalogApi.listTiers(true), []));
  const allTiers = (tiersApi.data?.tiers ?? []) as PricingTier[];
  const tierOptions = [
    { value: "", label: "All tiers" },
    ...allTiers.map(t => ({ value: t.tier_id, label: t.name })),
  ];

  // Quick filters
  const [search, setSearch]         = useState("");
  const [tierFilter, setTierFilter] = useState(initialTierId);
  const [conflictOnly, setConflictOnly] = useState(initialConflict);
  const [page, setPage]             = useState(1);

  // Advanced filters
  const [advFilters, setAdvFilters] = useState<AdvancedFilters>(EMPTY_FILTERS);
  const [filtersOpen, setFiltersOpen] = useState(false);

  // Bulk selection
  const [selected, setSelected] = useState<Set<string>>(new Set());

  // Drawer state
  const [detailRow, setDetailRow]   = useState<TierLocation | null>(null);
  const [conflictRow, setConflictRow] = useState<TierLocation | null>(null);

  // Import history
  const [showImports, setShowImports] = useState(false);

  // Bulk tier modal
  const [bulkTierModal, setBulkTierModal] = useState(false);
  const [bulkNewTier, setBulkNewTier]     = useState("");
  const [bulkLoading, setBulkLoading]     = useState(false);

  const summary   = useApi(useCallback(() => catalogApi.getTierLocationsSummary(), []));
  const locations = useApi(useCallback(() => catalogApi.listTierLocationsGrid({
    tierId:      tierFilter || undefined,
    q:           search || undefined,
    state:       advFilters.state || undefined,
    district:    advFilters.district || undefined,
    city:        advFilters.city || undefined,
    zipcode:     advFilters.zipcode || undefined,
    isActive:    advFilters.isActive ? advFilters.isActive === "true" : undefined,
    hasConflict: advFilters.conflictStatus
      ? advFilters.conflictStatus === "true"
      : conflictOnly ? true : undefined,
    page, pageSize: PAGE_SIZE,
  }), [tierFilter, search, advFilters, conflictOnly, page]));

  const importBatches = useApi(useCallback(
    () => showImports ? catalogApi.listImportBatches() : Promise.resolve(null),
    [showImports]
  ));

  useEffect(() => { setPage(1); }, [search, tierFilter, advFilters, conflictOnly]);

  const rows: TierLocation[] = locations.data?.items ?? [];
  const pagination = locations.data?.pagination;
  const totalPages = pagination?.total_pages ?? 1;

  // Selection helpers
  const allOnPageSelected = rows.length > 0 && rows.every(r => selected.has(r.location_id));
  const someSelected = selected.size > 0;
  function toggleRow(id: string) {
    setSelected(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s; });
  }
  function toggleAll() {
    setSelected(allOnPageSelected ? new Set() : new Set(rows.map(r => r.location_id)));
  }

  // Create/Edit modal
  const [modalOpen, setModalOpen] = useState(false);
  const [editRow, setEditRow]     = useState<TierLocation | null>(null);
  const [form, setForm] = useState({ tier_id: "", city: "", zipcode: "", state: "", district: "", country: "India", zone_name: "", priority: "100" });
  function F(p: Partial<typeof form>) { setForm(prev => ({ ...prev, ...p })); }

  function openCreate() {
    setEditRow(null);
    setForm({ tier_id: allTiers[0]?.tier_id ?? "", city: "", zipcode: "", state: "", district: "", country: "India", zone_name: "", priority: "100" });
    setModalOpen(true);
  }
  function openEdit(row: TierLocation) {
    setEditRow(row);
    setForm({ tier_id: row.tier_id, city: row.city ?? "", zipcode: row.zipcode ?? "", state: row.state ?? "", district: row.district ?? "", country: row.country ?? "India", zone_name: row.zone_name ?? "", priority: String(row.priority) });
    setModalOpen(true);
  }

  const createAction = useAction(useCallback((d: Record<string, unknown>) => catalogApi.createTierLocation(d as never), []));
  const updateAction = useAction(useCallback((id: string, d: Record<string, unknown>) => catalogApi.updateTierLocation(id, d), []));
  const deleteAction = useAction(useCallback((id: string) => catalogApi.deleteTierLocation(id), []));

  function refetchAll() { locations.refetch(); summary.refetch(); setSelected(new Set()); }

  async function handleSave() {
    const payload = {
      tier_id: form.tier_id, city: form.city || undefined, zipcode: form.zipcode || undefined,
      state: form.state || undefined, district: form.district || undefined,
      country: form.country || "India", zone_name: form.zone_name || undefined,
      priority: parseInt(form.priority) || 100,
    };
    const res = editRow
      ? await updateAction.execute(editRow.location_id, payload)
      : await createAction.execute(payload);
    if (res !== null) { refetchAll(); setModalOpen(false); }
  }

  async function handleDeactivate(id: string) {
    if (!confirm("Deactivate this location mapping?")) return;
    const res = await updateAction.execute(id, { is_active: false });
    if (res !== null) refetchAll();
  }
  async function handleDelete(id: string) {
    if (!confirm("Remove this location mapping? This cannot be undone.")) return;
    const res = await deleteAction.execute(id);
    if (res !== null) refetchAll();
  }

  async function handleBulkDeactivate() {
    if (!confirm(`Deactivate ${selected.size} selected mapping(s)?`)) return;
    setBulkLoading(true);
    try { await catalogApi.bulkDeactivateTierLocations(Array.from(selected)); refetchAll(); }
    finally { setBulkLoading(false); }
  }
  async function handleBulkChangeTier() {
    if (!bulkNewTier) return;
    setBulkLoading(true);
    try {
      await catalogApi.bulkChangeTierLocations(Array.from(selected), bulkNewTier);
      setBulkTierModal(false); setBulkNewTier(""); refetchAll();
    } finally { setBulkLoading(false); }
  }

  // Export
  async function handleExport() {
    const res = await catalogApi.exportTierLocations({
      tierId: tierFilter || undefined, state: advFilters.state || undefined,
      district: advFilters.district || undefined, hasConflict: conflictOnly ? true : undefined,
    });
    const header = "city,zipcode,district,state,country,tier_name,conflict_status,mapping_type\n";
    const body = res.rows.map((r: TierLocation & { tier_name?: string }) =>
      [r.city ?? "", r.zipcode ?? "", r.district ?? "", r.state ?? "", r.country ?? "India",
       r.tier_name ?? "", r.conflict_status ?? "", r.mapping_type ?? ""].join(",")
    ).join("\n");
    const blob = new Blob([header + body], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "tier_mappings.csv"; a.click();
    URL.revokeObjectURL(url);
  }

  // Resolve test
  const [resolveCity, setResolveCity]         = useState("");
  const [resolveZip, setResolveZip]           = useState("");
  const [resolveState, setResolveState]       = useState("");
  const [resolveDistrict, setResolveDistrict] = useState("");
  const [resolveZone, setResolveZone]         = useState("");
  const [resolveResult, setResolveResult] = useState<{
    matched_by: string | null; tier: PricingTier | null; resolution_path: string[];
  } | null>(null);

  const resolveAction = useAction(useCallback(
    (c?: string, z?: string, s?: string, d?: string, zn?: string) =>
      catalogApi.resolveLocation(c, z, s, d, zn),
    []
  ));
  async function handleResolve() {
    const res = await resolveAction.execute(
      resolveCity || undefined, resolveZip || undefined,
      resolveState || undefined, resolveDistrict || undefined, resolveZone || undefined,
    );
    setResolveResult(res ?? null);
  }

  // Summary card filter helpers
  const s = summary.data as TierLocationsSummary | null;

  const activeFilterCount = [
    search, tierFilter, conflictOnly ? "1" : "",
    ...Object.values(advFilters),
  ].filter(Boolean).length;

  // DataTable columns
  type LocRow = TierLocation & { tier_name?: string; tier_code?: string };
  const columns: Parameters<typeof DataTable<Record<string, unknown>>>[0]["columns"] = [
    {
      key: "_sel", label: "",
      render: (_, row) => {
        const id = (row as unknown as LocRow).location_id;
        const sel = selected.has(id);
        return (
          <button
            onClick={e => { e.stopPropagation(); toggleRow(id); }}
            style={{ background: "none", border: "none", cursor: "pointer", padding: "0 2px", color: "var(--text-tertiary)", display: "flex" }}>
            {sel ? <CheckSquare size={15} color="var(--brand)" /> : <Square size={15} />}
          </button>
        );
      },
    },
    {
      key: "mapping_type", label: "Type",
      render: v => <MappingTypeBadge type={v as string} />,
    },
    {
      key: "city", label: "Location",
      render: (v, row) => (
        <span style={{ fontWeight: 600, color: "var(--brand)", cursor: "pointer" }}>
          {(v as string) ?? <span style={{ color: "var(--text-tertiary)", fontWeight: 400 }}>—</span>}
        </span>
      ),
    },
    {
      key: "zipcode", label: "Zipcode",
      render: v => v ? <code style={{ fontSize: 12, background: "var(--surface-sunken)", padding: "1px 5px", borderRadius: 4 }}>{v as string}</code> : <span style={{ color: "var(--text-tertiary)" }}>—</span>,
    },
    { key: "district", label: "District", render: v => (v as string) ?? <span style={{ color: "var(--text-tertiary)" }}>—</span> },
    { key: "state",    label: "State",    render: v => (v as string) ?? <span style={{ color: "var(--text-tertiary)" }}>—</span> },
    {
      key: "tier_name", label: "Tier",
      render: v => v ? <Badge variant="info">{v as string}</Badge> : <span style={{ color: "var(--text-tertiary)" }}>—</span>,
    },
    {
      key: "has_conflict", label: "Conflict",
      render: (v, row) => <ConflictBadge has={v as boolean} status={(row as unknown as LocRow).conflict_status} />,
    },
    {
      key: "is_active", label: "Status",
      render: v => <Badge variant={v ? "success" : "muted"}>{v ? "Active" : "Inactive"}</Badge>,
    },
    {
      key: "updated_at", label: "Updated",
      render: v => v ? <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{new Date(v as string).toLocaleDateString("en-IN")}</span> : <span style={{ color: "var(--text-tertiary)" }}>—</span>,
    },
    {
      key: "_actions", label: "",
      render: (_, row) => {
        const r = row as unknown as LocRow;
        return (
          <div style={{ display: "flex", gap: 4 }} onClick={e => e.stopPropagation()}>
            <Btn variant="ghost" size="xs" onClick={() => openEdit(r)}>Edit</Btn>
            {r.has_conflict && (
              <Btn variant="ghost" size="xs" onClick={() => setConflictRow(r)}>Resolve</Btn>
            )}
            {r.is_active && (
              <Btn variant="ghost" size="xs" onClick={() => handleDeactivate(r.location_id)}>Deactivate</Btn>
            )}
          </div>
        );
      },
    },
  ];

  const [importOpen, setImportOpen] = useState(false);

  return (
    <AdminLayout activeNav="location-mapping">
      <SectionHeader
        title="City / Zipcode → Tier Mapping"
        subtitle="Map cities, zipcodes, districts, states, and zones to pricing tiers. Zipcode takes precedence over city."
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="secondary" size="sm" icon={<Download size={13} />} onClick={handleExport}>Export</Btn>
            <Btn variant="secondary" size="sm" icon={<Upload size={13} />} onClick={() => setImportOpen(true)}>Import CSV</Btn>
            <Btn variant="primary" size="sm" icon={<Plus size={13} />} onClick={openCreate}>Add Mapping</Btn>
          </div>
        }
      />

      <div style={{ padding: "0 28px 32px" }}>
        {/* Summary Cards */}
        {s && (
          <SummaryCardsRow cards={[
            { label: "Total Mappings",      value: s.total_mappings,      onClick: () => { setAdvFilters(EMPTY_FILTERS); setConflictOnly(false); setPage(1); } },
            { label: "Mapped Cities",       value: s.mapped_cities },
            { label: "Mapped Zipcodes",     value: s.mapped_zipcodes,     onClick: () => { setAdvFilters(p => ({ ...p, mappingType: "Zipcode" })); setPage(1); } },
            { label: "Mapped Districts",    value: s.mapped_districts },
            { label: "Mapped States",       value: s.mapped_states },
            { label: "Duplicate Conflicts", value: s.duplicate_zipcodes,  accent: s.duplicate_zipcodes > 0, onClick: () => { setConflictOnly(true); setPage(1); } },
            { label: "Inactive Mappings",   value: s.inactive_mappings,   onClick: () => { setAdvFilters(p => ({ ...p, isActive: "false" })); setPage(1); } },
          ]} />
        )}

        {/* Main Table Card */}
        <Card padding={16}>
          {/* Toolbar */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <MapPin size={18} color="var(--brand)" />
              <span style={{ fontWeight: 700, fontSize: 15 }}>Mapping Table</span>
              <Badge variant="muted">{pagination?.total ?? rows.length} total</Badge>
              {activeFilterCount > 0 && (
                <Badge variant="info">{activeFilterCount} filter{activeFilterCount > 1 ? "s" : ""}</Badge>
              )}
              {someSelected && <Badge variant="warning">{selected.size} selected</Badge>}
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {someSelected && (
                <>
                  <Btn variant="secondary" size="sm" loading={bulkLoading} onClick={handleBulkDeactivate}>Deactivate ({selected.size})</Btn>
                  <Btn variant="secondary" size="sm" onClick={() => setBulkTierModal(true)}>Change Tier ({selected.size})</Btn>
                  <Btn variant="ghost" size="sm" onClick={() => setSelected(new Set())}><X size={12} /></Btn>
                </>
              )}
              <Btn variant="ghost" size="sm" icon={<History size={13} />} onClick={() => setShowImports(v => !v)}>
                Imports
              </Btn>
              <Btn variant="ghost" size="sm" onClick={() => refetchAll()}><RefreshCw size={13} /></Btn>
            </div>
          </div>

          {/* Filter Bar */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 180px 160px auto auto", gap: 10, marginBottom: 12 }}>
            <div style={{ position: "relative" }}>
              <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)", pointerEvents: "none" }} />
              <input
                placeholder="Search city, zipcode, state, district…"
                value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}
                style={{ width: "100%", height: 34, paddingLeft: 32, paddingRight: 12, fontSize: 13, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", outline: "none", fontFamily: "inherit", boxSizing: "border-box" }}
              />
            </div>
            <Select label="" value={tierFilter} onChange={v => { setTierFilter(v); setPage(1); }} placeholder="All tiers" options={tierOptions} />
            <Select label="" value={conflictOnly ? "true" : ""} onChange={v => { setConflictOnly(v === "true"); setPage(1); }}
              options={[{ value: "", label: "All conflicts" }, { value: "true", label: "Conflicts only" }]} />
            <Btn variant={activeFilterCount > 0 ? "primary" : "secondary"} size="sm"
              icon={<SlidersHorizontal size={13} />} onClick={() => setFiltersOpen(true)}>
              {activeFilterCount > 0 ? `Filters (${activeFilterCount})` : "Filters"}
            </Btn>
            {activeFilterCount > 0 && (
              <Btn variant="ghost" size="sm" onClick={() => { setSearch(""); setTierFilter(""); setConflictOnly(false); setAdvFilters(EMPTY_FILTERS); setPage(1); }}>
                Clear
              </Btn>
            )}
          </div>

          {/* Select All Row */}
          {rows.length > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, padding: "4px 0" }}>
              <button onClick={toggleAll} style={{ background: "none", border: "none", cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
                {allOnPageSelected ? <CheckSquare size={14} color="var(--brand)" /> : <Square size={14} />}
                {allOnPageSelected ? "Deselect all on page" : "Select all on page"}
              </button>
            </div>
          )}

          {/* DataTable */}
          <DataTable
            columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
            rows={rows as unknown as Record<string, unknown>[]}
            loading={locations.loading}
            emptyText={activeFilterCount > 0 ? "No mappings match the current filters." : "No location mappings yet. Add your first mapping or import a CSV."}
            onRowClick={row => setDetailRow(row as unknown as TierLocation)}
          />

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ padding: "12px 0 2px", borderTop: "1px solid var(--border)", marginTop: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 12, color: "var(--muted-text)" }}>
                {pagination?.total} total · page {pagination?.page} of {totalPages}
              </span>
              <div style={{ display: "flex", gap: 6 }}>
                <Btn variant="ghost" size="sm" icon={<ChevronLeft size={13} />} onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Prev</Btn>
                <Btn variant="ghost" size="sm" icon={<ChevronRight size={13} />} onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>Next</Btn>
              </div>
            </div>
          )}
        </Card>

        {/* Import History */}
        {showImports && (
          <Card padding={16} style={{ marginTop: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <History size={15} color="var(--brand)" />
                <span style={{ fontWeight: 700, fontSize: 14 }}>Import History</span>
              </div>
              <Btn variant="ghost" size="sm" onClick={() => setShowImports(false)}><X size={13} /></Btn>
            </div>
            {importBatches.loading ? (
              <div style={{ padding: "20px 0", textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</div>
            ) : (
              <DataTable
                columns={[
                  { key: "file_name", label: "File" },
                  { key: "status", label: "Status", render: v => <Badge variant={v === "confirmed" ? "success" : "muted"}>{v as string}</Badge> },
                  { key: "total_rows", label: "Total" },
                  { key: "valid_rows", label: "Valid" },
                  { key: "created_rows", label: "Created" },
                  { key: "updated_rows", label: "Updated" },
                  { key: "skipped_rows", label: "Skipped" },
                  { key: "conflict_rows", label: "Conflicts" },
                  { key: "created_at", label: "Date", render: v => v ? new Date(v as string).toLocaleDateString("en-IN") : "—" },
                ]}
                rows={((importBatches.data as { batches?: Record<string, unknown>[] } | null)?.batches ?? []) as Record<string, unknown>[]}
                emptyText="No imports yet."
              />
            )}
          </Card>
        )}

        {/* Tier Resolve Test */}
        <Card padding={16} style={{ marginTop: 16 }}>
          <h3 style={{ margin: "0 0 4px", fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>Tier Resolve Test</h3>
          <p style={{ margin: "0 0 14px", fontSize: 13, color: "var(--text-secondary)" }}>
            Test which pricing tier a location resolves to. Checks zipcode → city → district → zone → state.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 10 }}>
            <Input label="City" placeholder="e.g. Mumbai" value={resolveCity} onChange={setResolveCity} />
            <Input label="Zipcode" placeholder="e.g. 400001" value={resolveZip} onChange={setResolveZip} />
            <Input label="State" placeholder="e.g. Maharashtra" value={resolveState} onChange={setResolveState} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: 10 }}>
            <Input label="District" placeholder="e.g. Dadar" value={resolveDistrict} onChange={setResolveDistrict} />
            <Input label="Zone" placeholder="e.g. Western Suburbs" value={resolveZone} onChange={setResolveZone} />
            <div style={{ display: "flex", alignItems: "flex-end" }}>
              <Btn variant="primary" size="sm" loading={resolveAction.loading}
                disabled={!resolveCity && !resolveZip && !resolveState && !resolveDistrict && !resolveZone}
                onClick={handleResolve}>Resolve</Btn>
            </div>
          </div>
          {resolveResult && (
            <div style={{ marginTop: 14, padding: "14px 16px", borderRadius: 10, background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
              {resolveResult.tier ? (
                <>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                    <Badge variant="success">Matched</Badge>
                    <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>via <strong>{resolveResult.matched_by}</strong></span>
                  </div>
                  <p style={{ margin: 0, fontSize: 20, fontWeight: 700, color: "var(--brand)" }}>{resolveResult.tier.name}</p>
                  <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--text-tertiary)" }}>
                    {resolveResult.tier.tier_type} · ×{resolveResult.tier.base_multiplier} · {resolveResult.tier.default_commission_percent}% commission
                  </p>
                </>
              ) : (
                <>
                  <Badge variant="muted">No Match</Badge>
                  <p style={{ margin: "8px 0 0", fontSize: 13, color: "var(--text-tertiary)" }}>
                    No tier matched. The location will use the platform default pricing.
                  </p>
                </>
              )}
              <ResolutionPathTrace path={resolveResult.resolution_path} />
            </div>
          )}
        </Card>
      </div>

      {/* Drawers with backdrop */}
      {(filtersOpen || !!detailRow || !!conflictRow) && (
        <div
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", zIndex: 200 }}
          onClick={() => { setFiltersOpen(false); setDetailRow(null); setConflictRow(null); }}
        />
      )}
      <FiltersDrawer open={filtersOpen} onClose={() => setFiltersOpen(false)}
        values={advFilters} onChange={v => { setAdvFilters(v); setPage(1); }} />
      {detailRow && (
        <DetailDrawer row={detailRow} tiers={allTiers}
          onClose={() => setDetailRow(null)}
          onEdit={r => { setDetailRow(null); openEdit(r); }}
          onResolve={r => { setDetailRow(null); setConflictRow(r); }} />
      )}
      {conflictRow && (
        <ConflictDrawer row={conflictRow} tiers={allTiers}
          onClose={() => setConflictRow(null)}
          onDone={() => { setConflictRow(null); refetchAll(); }} />
      )}

      {/* Create/Edit Modal */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)}
        title={editRow ? "Edit Location Mapping" : "Add Location Mapping"}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {(createAction.error || updateAction.error) && (
            <div style={{ padding: "10px 14px", borderRadius: 8, background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{createAction.error || updateAction.error}</p>
            </div>
          )}
          <div style={{ padding: "8px 12px", borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)" }}>
            Provide at least one of: zipcode (highest priority) or city. State/district improve matching.
          </div>
          <Select label="Pricing Tier *" value={form.tier_id} onChange={v => F({ tier_id: v })}
            placeholder="Select tier…" options={tierOptions.filter(o => o.value)} />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <Input label="City" placeholder="e.g. Mumbai" value={form.city} onChange={v => F({ city: v })} />
            <Input label="Zipcode" placeholder="e.g. 400001" value={form.zipcode} onChange={v => F({ zipcode: v })} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
            <Input label="District" placeholder="e.g. Dadar" value={form.district} onChange={v => F({ district: v })} />
            <Input label="State" placeholder="e.g. Maharashtra" value={form.state} onChange={v => F({ state: v })} />
            <Input label="Country" placeholder="India" value={form.country} onChange={v => F({ country: v })} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <Input label="Zone / Area" placeholder="e.g. Western Suburbs" value={form.zone_name} onChange={v => F({ zone_name: v })} />
            <Input label="Priority" placeholder="100" value={form.priority} onChange={v => F({ priority: v })} />
          </div>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", paddingTop: 4 }}>
            <Btn variant="ghost" size="sm" onClick={() => setModalOpen(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={createAction.loading || updateAction.loading}
              disabled={!form.tier_id || (!form.city && !form.zipcode && !form.district && !form.state)}
              onClick={handleSave}>
              {editRow ? "Save Changes" : "Add Mapping"}
            </Btn>
          </div>
        </div>
      </Modal>

      {/* Bulk Change Tier Modal */}
      <Modal open={bulkTierModal} onClose={() => { setBulkTierModal(false); setBulkNewTier(""); }}
        title={`Change Tier for ${selected.size} Mapping(s)`}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)" }}>
            Select the new pricing tier to assign to the {selected.size} selected mapping(s).
          </p>
          <Select label="New Pricing Tier" value={bulkNewTier} onChange={setBulkNewTier}
            placeholder="Select tier…" options={tierOptions.filter(o => o.value)} />
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", paddingTop: 4 }}>
            <Btn variant="ghost" size="sm" onClick={() => { setBulkTierModal(false); setBulkNewTier(""); }}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={bulkLoading} disabled={!bulkNewTier} onClick={handleBulkChangeTier}>
              Apply to {selected.size} Mapping(s)
            </Btn>
          </div>
        </div>
      </Modal>

      <ImportWizard
        open={importOpen}
        onClose={() => setImportOpen(false)}
        previewFn={(fn, csv) => catalogApi.importTierLocationsPreview(fn, csv)}
        confirmFn={(id, res) => catalogApi.importTierLocationsConfirm(id, res)}
        onComplete={() => { refetchAll(); if (showImports) importBatches.refetch(); }}
        columnsHint="Expected columns: country, state, district, city, zipcode, tier_code, zone_code (optional)."
      />
    </AdminLayout>
  );
}

export default function LocationMappingPage() {
  return (
    <Suspense fallback={<div style={{ padding: 40 }}>Loading…</div>}>
      <LocationMappingInner />
    </Suspense>
  );
}
