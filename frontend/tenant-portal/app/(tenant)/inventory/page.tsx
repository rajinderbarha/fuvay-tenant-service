"use client";

import React, { useCallback, useMemo, useState } from "react";
import {
  Boxes, Building2, CircleDollarSign, FileStack, History,
  IndianRupee, PackageCheck, Plus, RefreshCw, Search, ShieldCheck,
  SlidersHorizontal, Truck, Upload,
} from "lucide-react";
import {
  Badge, Btn, Card, CardHeader, DataTable, DeleteBtn, EditBtn, EmptyState,
  Input, KpiGrid, Modal, Pagination, SectionHeader, Select, SummaryCard,
} from "../../../components/shared/ui";
import { useApi } from "../../../hooks/useApi";
import {
  engineApi, entitlementApi, inventoryApi,
  type InventoryDraftItem, type InventoryItem,
} from "../../../lib/api";

const EXTRACTION_ENGINE_KEY = "inventory_document_extraction";
const PAGE_SIZE = 20;
const UNITS = [
  "pcs", "set", "pair", "box", "carton", "packet", "bundle", "roll",
  "coil", "sheet", "bag", "dozen", "meter", "feet", "cm", "kg",
  "gram", "liter", "ml", "unit",
];

type Tab = "catalog" | "stock" | "imports";
type ItemForm = {
  name: string; sku: string; unit: string; serviceGroupId: string;
  unitCost: string; sellingPrice: string; minQuantity: string;
  gst: string; warranty: string;
};

const EMPTY_ITEM: ItemForm = {
  name: "", sku: "", unit: "pcs", serviceGroupId: "",
  unitCost: "", sellingPrice: "", minQuantity: "5", gst: "18", warranty: "",
};

const money = (value: number | null | undefined) =>
  `₹${Number(value ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;

const inputStyle: React.CSSProperties = {
  width: "100%", height: 38, borderRadius: 10, padding: "0 12px",
  border: "1px solid var(--border)", background: "var(--surface)",
  color: "var(--text-primary)", boxSizing: "border-box", fontFamily: "inherit",
};

function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return <label style={{ display: "grid", gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
    <span style={{ fontWeight: 600 }}>{label}</span>
    {children}
    {hint && <span style={{ color: "var(--text-tertiary)", fontSize: 11 }}>{hint}</span>}
  </label>;
}

function stockBadge(item: InventoryItem) {
  if (item.available_qty <= 0) return <Badge variant="danger" dot>Out of stock</Badge>;
  if (item.below_minimum) return <Badge variant="warning" dot>Reorder</Badge>;
  return <Badge variant="success" dot>Healthy</Badge>;
}

export default function InventoryPage() {
  const [tab, setTab] = useState<Tab>("catalog");
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [stockStatus, setStockStatus] = useState<"all" | "healthy" | "low" | "out">("all");
  const [sort, setSort] = useState("name_asc");
  const [showArchived, setShowArchived] = useState(false);
  const [notice, setNotice] = useState<{ tone: "success" | "danger"; text: string } | null>(null);

  const categories = useApi(useCallback(() => entitlementApi.getMyCategories(), []), []);
  const categoryOptions = useMemo(() => (categories.data?.categories ?? [])
    .filter(c => c.status === "ACTIVE" && c.category_id && c.category_label)
    .map(c => ({ value: c.category_id, label: c.category_label as string })), [categories.data]);

  const items = useApi(useCallback(() => inventoryApi.listItems({
    search, categoryId: categoryId || undefined, stockStatus, sort,
    offset: (page - 1) * PAGE_SIZE, limit: PAGE_SIZE, includeArchived: showArchived,
  }), [search, categoryId, stockStatus, sort, page, showArchived]),
  [search, categoryId, stockStatus, sort, page, showArchived]);

  const summary = useApi(useCallback(() => inventoryApi.getWorkspaceSummary(), []), []);
  const locations = useApi(useCallback(() => inventoryApi.listLocations(), []), []);
  const engines = useApi(useCallback(() => engineApi.getEffectiveEngines(), []), []);
  const extractionEnabled = !!engines.data?.engines?.some(
    e => e.engine_key === EXTRACTION_ENGINE_KEY && e.effective_enabled,
  );
  const drafts = useApi(useCallback(
    () => extractionEnabled ? inventoryApi.listDrafts() : Promise.resolve({ items: [], total: 0 }),
    [extractionEnabled]), [extractionEnabled]);

  const [itemModal, setItemModal] = useState<"create" | "edit" | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [itemForm, setItemForm] = useState<ItemForm>(EMPTY_ITEM);
  const [saving, setSaving] = useState(false);
  const [locationModal, setLocationModal] = useState(false);
  const [locationName, setLocationName] = useState("");
  const [locationType, setLocationType] = useState("warehouse");
  const [receiveModal, setReceiveModal] = useState(false);
  const [selectedItem, setSelectedItem] = useState("");
  const [selectedLocation, setSelectedLocation] = useState("");
  const [receiveQuantity, setReceiveQuantity] = useState("");
  const [receiveNotes, setReceiveNotes] = useState("");
  const [stockAction, setStockAction] = useState<"count" | "transfer" | null>(null);
  const [countedQuantity, setCountedQuantity] = useState("");
  const [transferLocation, setTransferLocation] = useState("");
  const [transferQuantity, setTransferQuantity] = useState("");
  const [stockReason, setStockReason] = useState("");
  const [uploading, setUploading] = useState(false);
  const [draftBusy, setDraftBusy] = useState<string | null>(null);
  const [draftCategories, setDraftCategories] = useState<Record<string, string>>({});

  const balance = useApi(useCallback(() => selectedItem && selectedLocation
    ? inventoryApi.getBalance(selectedItem, selectedLocation)
    : Promise.resolve(null), [selectedItem, selectedLocation]), [selectedItem, selectedLocation]);
  const transactions = useApi(useCallback(() => selectedItem && selectedLocation
    ? inventoryApi.listTransactions(selectedItem, selectedLocation)
    : Promise.resolve({ transactions: [], has_next: false }),
  [selectedItem, selectedLocation]), [selectedItem, selectedLocation]);

  const refresh = () => {
    items.refetch(); summary.refetch(); locations.refetch();
    if (selectedItem && selectedLocation) { balance.refetch(); transactions.refetch(); }
  };

  const openCreate = () => {
    setEditingId(null); setItemForm({ ...EMPTY_ITEM, serviceGroupId: categoryOptions[0]?.value ?? "" });
    setItemModal("create"); setNotice(null);
  };
  const openEdit = (item: InventoryItem) => {
    setEditingId(item.item_id);
    setItemForm({
      name: item.name, sku: item.sku, unit: item.unit,
      serviceGroupId: item.service_group_id ?? "",
      unitCost: String(item.unit_cost ?? 0), sellingPrice: String(item.selling_price ?? item.unit_cost ?? 0),
      minQuantity: String(item.min_quantity), gst: item.gst == null ? "" : String(item.gst),
      warranty: item.warranty ?? "",
    });
    setItemModal("edit"); setNotice(null);
  };

  async function saveItem() {
    const category = categoryOptions.find(c => c.value === itemForm.serviceGroupId);
    if (!itemForm.name.trim() || !itemForm.sku.trim() || !category) {
      setNotice({ tone: "danger", text: "Name, SKU, and an enabled service category are required." }); return;
    }
    const unitCost = Number(itemForm.unitCost);
    const sellingPrice = Number(itemForm.sellingPrice);
    if (unitCost < 0 || sellingPrice < 0) {
      setNotice({ tone: "danger", text: "Cost and customer price cannot be negative." }); return;
    }
    setSaving(true); setNotice(null);
    try {
      if (itemModal === "create") {
        await inventoryApi.createItem(itemForm.name.trim(), itemForm.sku.trim(), itemForm.unit,
          unitCost, category.label, Number(itemForm.minQuantity) || 0,
          itemForm.gst === "" ? null : Number(itemForm.gst), itemForm.warranty || null,
          sellingPrice, category.value);
      } else if (editingId) {
        await inventoryApi.updateItem(editingId, {
          name: itemForm.name.trim(), sku: itemForm.sku.trim(), unit: itemForm.unit,
          unit_cost: unitCost, selling_price: sellingPrice,
          category: category.label, service_group_id: category.value,
          min_quantity: Number(itemForm.minQuantity) || 0,
          gst: itemForm.gst === "" ? null : Number(itemForm.gst), warranty: itemForm.warranty || null,
        });
      }
      const wasCreate = itemModal === "create";
      setItemModal(null); refresh();
      setNotice({ tone: "success", text: wasCreate ? "Inventory item created." : "Inventory item updated." });
    } catch (error) {
      setNotice({ tone: "danger", text: error instanceof Error ? error.message : "Could not save the item." });
    } finally { setSaving(false); }
  }

  async function archiveItem(item: InventoryItem) {
    if (!window.confirm(`Archive ${item.name}? Historical stock ledger entries will be retained.`)) return;
    try {
      await inventoryApi.deleteItem(item.item_id); refresh();
      setNotice({ tone: "success", text: `${item.name} was archived. Its ledger remains available for audit.` });
    } catch (error) {
      setNotice({ tone: "danger", text: error instanceof Error ? error.message : "Archive failed." });
    }
  }

  async function restoreItem(item: InventoryItem) {
    try {
      await inventoryApi.updateItem(item.item_id, { is_active: true }); refresh();
      setNotice({ tone: "success", text: `${item.name} was restored to the active catalogue.` });
    } catch (error) {
      setNotice({ tone: "danger", text: error instanceof Error ? error.message : "Restore failed." });
    }
  }

  async function createLocation() {
    if (!locationName.trim()) return;
    setSaving(true);
    try {
      const created = await inventoryApi.createLocation(locationName.trim(), locationType);
      setLocationModal(false); setLocationName(""); locations.refetch(); summary.refetch();
      setSelectedLocation(created.location_id);
      setNotice({ tone: "success", text: "Stock location created." });
    } catch (error) {
      setNotice({ tone: "danger", text: error instanceof Error ? error.message : "Could not create location." });
    } finally { setSaving(false); }
  }

  async function receiveStock() {
    const qty = Number(receiveQuantity);
    if (!selectedItem || !selectedLocation || qty <= 0) {
      setNotice({ tone: "danger", text: "Select an item and location, then enter a positive quantity." }); return;
    }
    setSaving(true);
    try {
      await inventoryApi.receiveStock(selectedItem, selectedLocation, qty, receiveNotes || undefined);
      setReceiveModal(false); setReceiveQuantity(""); setReceiveNotes(""); refresh();
      setNotice({ tone: "success", text: `${qty} unit(s) received into stock.` });
    } catch (error) {
      setNotice({ tone: "danger", text: error instanceof Error ? error.message : "Stock receipt failed." });
    } finally { setSaving(false); }
  }

  async function submitStockControl() {
    if (!selectedItem || !selectedLocation || !stockReason.trim()) {
      setNotice({ tone: "danger", text: "Select an item and location and enter an audit reason." }); return;
    }
    setSaving(true);
    try {
      if (stockAction === "count") {
        const counted = Number(countedQuantity);
        if (counted < 0) throw new Error("Counted quantity cannot be negative.");
        await inventoryApi.countStock(selectedItem, selectedLocation, counted, stockReason.trim());
        setNotice({ tone: "success", text: "Cycle count posted to the immutable stock ledger." });
      } else if (stockAction === "transfer") {
        const qty = Number(transferQuantity);
        if (!transferLocation || transferLocation === selectedLocation || qty <= 0) {
          throw new Error("Choose a different destination and a positive quantity.");
        }
        await inventoryApi.transferStock(selectedItem, selectedLocation, transferLocation, qty, stockReason.trim());
        setNotice({ tone: "success", text: "Stock transfer posted at both locations." });
      }
      setStockAction(null); setCountedQuantity(""); setTransferQuantity(""); setStockReason(""); refresh();
    } catch (error) {
      setNotice({ tone: "danger", text: error instanceof Error ? error.message : "Stock control failed." });
    } finally { setSaving(false); }
  }

  async function handlePdf(file: File) {
    setUploading(true); setNotice(null);
    try {
      const result = await inventoryApi.uploadForExtraction(file);
      drafts.refetch(); setTab("imports");
      setNotice({ tone: "success", text: `Extracted ${result.extracted_item_count} draft item(s). Review before publishing.` });
    } catch (error) {
      setNotice({ tone: "danger", text: error instanceof Error ? error.message : "PDF extraction failed." });
    } finally { setUploading(false); }
  }

  async function publishDraft(id: string) {
    const draft = drafts.data?.items.find(item => item.item_id === id);
    const mappedId = draftCategories[id] ?? draft?.service_group_id ?? "";
    const mappedCategory = categoryOptions.find(option => option.value === mappedId);
    if (!mappedCategory) {
      setNotice({ tone: "danger", text: "Map the draft to an enabled setup category before publishing." });
      return;
    }
    setDraftBusy(id);
    try {
      await inventoryApi.updateDraft(id, {
        category: mappedCategory.label, service_group_id: mappedCategory.value,
      });
      await inventoryApi.publishItem(id); drafts.refetch(); refresh();
    }
    catch (error) { setNotice({ tone: "danger", text: error instanceof Error ? error.message : "Publish failed." }); }
    finally { setDraftBusy(null); }
  }

  const rows = items.data?.items ?? [];
  const locationRows = locations.data?.locations ?? [];

  return <div style={{ width: "100%", maxWidth: 1500 }}>
    <SectionHeader
      title="Inventory & parts"
      subtitle="Control provider-owned parts, customer prices, stock locations, and the job reservation ledger."
      icon={<Boxes />}
      actions={<>
        <Btn variant="secondary" icon={<RefreshCw size={14}/>} onClick={refresh}>Refresh</Btn>
        {extractionEnabled && <label style={{ display: "inline-flex" }}>
          <Btn variant="secondary" icon={<Upload size={14}/>} loading={uploading}>Import PDF</Btn>
          <input hidden type="file" accept="application/pdf" onChange={e => {
            const file = e.target.files?.[0]; if (file) handlePdf(file); e.target.value = "";
          }}/>
        </label>}
        <Btn icon={<Plus size={14}/>} onClick={openCreate}>New item</Btn>
      </>}
    />

    {notice && <div role="alert" style={{
      marginBottom: 16, padding: "11px 14px", borderRadius: 10, fontSize: 13,
      color: notice.tone === "danger" ? "var(--danger-text)" : "var(--success-text)",
      background: notice.tone === "danger" ? "var(--danger-bg)" : "var(--success-bg)",
      border: `1px solid ${notice.tone === "danger" ? "var(--danger-border)" : "var(--success-border)"}`,
    }}>{notice.text}</div>}

    <KpiGrid minCardWidth={190} style={{ marginBottom: 18 }}>
      <SummaryCard label="Active items" value={summary.data?.total_items ?? "—"} sub="Published provider catalogue" icon={<PackageCheck/>}/>
      <SummaryCard label="Available units" value={summary.data?.available_units ?? "—"} sub={`${summary.data?.reserved_units ?? 0} reserved for jobs`} icon={<Boxes/>}/>
      <SummaryCard label="Inventory cost value" value={summary.data ? money(summary.data.inventory_value) : "—"} sub="Acquisition cost × on-hand" icon={<IndianRupee/>}/>
      <SummaryCard label="Potential retail value" value={summary.data ? money(summary.data.retail_value) : "—"} sub="Customer price × available" icon={<CircleDollarSign/>} accent/>
      <SummaryCard label="Needs reorder" value={summary.data?.low_stock_items ?? "—"} sub={`${summary.data?.active_locations ?? 0} active locations`} tone={summary.data?.low_stock_items ? "warning" : "success"} icon={<Truck/>}/>
    </KpiGrid>

    <div role="tablist" aria-label="Inventory sections" style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 18, overflowX: "auto" }}>
      {([
        ["catalog", "Item catalogue", <Boxes key="i" size={14}/>],
        ["stock", "Stock & ledger", <History key="s" size={14}/>],
        ["imports", `Import review${drafts.data?.total ? ` (${drafts.data.total})` : ""}`, <FileStack key="d" size={14}/>],
      ] as const).map(([id, label, icon]) => <button key={id} role="tab" aria-selected={tab === id}
        onClick={() => setTab(id)} style={{
          display: "inline-flex", gap: 7, alignItems: "center", height: 42, padding: "0 14px",
          border: 0, borderBottom: tab === id ? "2px solid var(--accent)" : "2px solid transparent",
          background: "transparent", color: tab === id ? "var(--accent)" : "var(--text-secondary)",
          fontWeight: tab === id ? 700 : 500, cursor: "pointer", whiteSpace: "nowrap",
        }}>{icon}{label}</button>)}
    </div>

    {tab === "catalog" && <Card padding={0}>
      <div style={{ padding: 16, borderBottom: "1px solid var(--border)", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 10, alignItems: "end" }}>
        <Input label="Search inventory" icon={<Search/>} value={searchInput} placeholder="Name, SKU, or category"
          onChange={setSearchInput}/>
        <Select label="Service category" value={categoryId} onChange={v => { setCategoryId(v); setPage(1); }}
          placeholder="All enabled categories" options={categoryOptions}/>
        <Select label="Stock status" value={stockStatus} onChange={v => { setStockStatus(v as typeof stockStatus); setPage(1); }} options={[
          { value: "all", label: "All stock states" }, { value: "healthy", label: "Healthy" },
          { value: "low", label: "Below reorder level" }, { value: "out", label: "Out of stock" },
        ]}/>
        <Select label="Sort" value={sort} onChange={v => { setSort(v); setPage(1); }} options={[
          { value: "name_asc", label: "Name A–Z" }, { value: "name_desc", label: "Name Z–A" },
          { value: "stock_asc", label: "Lowest stock" }, { value: "stock_desc", label: "Highest stock" },
          { value: "value_desc", label: "Highest stock value" },
        ]}/>
        <Btn variant="secondary" icon={<SlidersHorizontal size={14}/>} onClick={() => { setSearch(searchInput.trim()); setPage(1); }}>Apply</Btn>
      </div>
      <div style={{ padding: "10px 16px", display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border)" }}>
        <label style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--text-secondary)" }}>
          <input type="checkbox" checked={showArchived} onChange={e => { setShowArchived(e.target.checked); setPage(1); }}/>
          View archived items
        </label>
        {(search || categoryId || stockStatus !== "all") && <Btn size="xs" variant="ghost" onClick={() => {
          setSearch(""); setSearchInput(""); setCategoryId(""); setStockStatus("all"); setPage(1);
        }}>Clear filters</Btn>}
      </div>
      <DataTable<InventoryItem & Record<string, unknown>> loading={items.loading} emptyText="No inventory items match these filters."
        rows={rows as Array<InventoryItem & Record<string, unknown>>} columns={[
          { key: "name", label: "Item", render: (_v, row) => <div><strong style={{ color: "var(--text-primary)" }}>{row.name}</strong><div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{row.sku} · {row.unit}</div></div> },
          { key: "category", label: "Setup category", render: (_v, row) => row.category ?? "Unmapped" },
          { key: "quantity", label: "On hand", render: (_v, row) => <div><strong>{row.quantity}</strong><div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{row.reserved_qty} reserved</div></div> },
          { key: "available_qty", label: "Available", render: (_v, row) => <div>{row.available_qty} {row.unit}<div style={{ marginTop: 4 }}>{stockBadge(row)}</div></div> },
          { key: "unit_cost", label: "Provider cost", render: (_v, row) => money(row.unit_cost) },
          { key: "selling_price", label: "Customer price", render: (_v, row) => <div><strong>{money(row.selling_price)}</strong><div style={{ fontSize: 11, color: row.margin < 0 ? "var(--danger-text)" : "var(--success-text)" }}>{row.margin >= 0 ? "+" : ""}{money(row.margin)} margin</div></div> },
          { key: "gst", label: "Tax", render: (_v, row) => row.gst == null ? "—" : `${row.gst}% GST` },
          { key: "actions", label: "", render: (_v, row) => showArchived
            ? <Btn size="xs" variant="success" onClick={() => restoreItem(row)}>Restore</Btn>
            : <div style={{ display: "flex", justifyContent: "flex-end", gap: 3 }}>
                <Btn size="xs" variant="ghost" onClick={() => { setSelectedItem(row.item_id); setSelectedLocation(locationRows[0]?.location_id ?? ""); setTab("stock"); }}>Ledger</Btn>
                <EditBtn onClick={() => openEdit(row)} tooltip="Edit catalogue and pricing"/><DeleteBtn onClick={() => archiveItem(row)} tooltip="Archive item"/>
              </div> },
        ]}/>
      <Pagination page={page} total={items.data?.total ?? 0} pageSize={PAGE_SIZE} onPage={setPage} alwaysShow/>
    </Card>}

    {tab === "stock" && <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 360px), 1fr))", gap: 16 }}>
      <Card>
        <CardHeader icon={<Building2/>} title="Stock locations" subtitle="Warehouses, stores, and service vans"
          actions={<Btn size="xs" icon={<Plus size={12}/>} onClick={() => setLocationModal(true)}>Add</Btn>}/>
        {locationRows.length === 0 ? <EmptyState title="No stock location" description="Create a location before receiving parts." icon={<Building2/>} action={<Btn size="sm" onClick={() => setLocationModal(true)}>Create location</Btn>}/>
          : <div style={{ display: "grid", gap: 8 }}>{locationRows.map(location => <button key={location.location_id}
            onClick={() => setSelectedLocation(location.location_id)} style={{
              textAlign: "left", padding: 12, borderRadius: 10, cursor: "pointer",
              border: `1px solid ${selectedLocation === location.location_id ? "var(--accent)" : "var(--border)"}`,
              background: selectedLocation === location.location_id ? "var(--accent-muted)" : "var(--surface)",
              color: "var(--text-primary)",
            }}><strong>{location.location_name}</strong><div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 3, textTransform: "capitalize" }}>{location.location_type}</div></button>)}</div>}
      </Card>
      <Card>
        <CardHeader icon={<History/>} title="Stock ledger" subtitle="Append-only receipts, reservations, consumption, and releases"
          actions={<>
            <Btn size="xs" variant="secondary" disabled={!selectedItem || !selectedLocation} onClick={() => { setCountedQuantity(String(balance.data?.quantity ?? 0)); setStockAction("count"); }}>Cycle count</Btn>
            <Btn size="xs" variant="secondary" disabled={!selectedItem || !selectedLocation || locationRows.length < 2} onClick={() => { setTransferLocation(locationRows.find(l => l.location_id !== selectedLocation)?.location_id ?? ""); setStockAction("transfer"); }}>Transfer</Btn>
            <Btn size="sm" icon={<Plus size={13}/>} disabled={!selectedItem || !selectedLocation} onClick={() => setReceiveModal(true)}>Receive stock</Btn>
          </>}/>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 16 }}>
          <Select label="Item" value={selectedItem} onChange={setSelectedItem} placeholder="Select inventory item"
            options={rows.map(i => ({ value: i.item_id, label: `${i.name} (${i.sku})` }))}/>
          <Select label="Location" value={selectedLocation} onChange={setSelectedLocation} placeholder="Select stock location"
            options={locationRows.map(l => ({ value: l.location_id, label: l.location_name }))}/>
        </div>
        {selectedItem && selectedLocation ? <>
          <KpiGrid minCardWidth={130} style={{ marginBottom: 14 }}>
            <SummaryCard label="On hand" value={balance.data?.quantity ?? "—"}/>
            <SummaryCard label="Reserved" value={balance.data?.reserved_qty ?? "—"} tone="warning"/>
            <SummaryCard label="Available" value={balance.data?.available_qty ?? "—"} tone={balance.data?.below_minimum ? "danger" : "success"}/>
          </KpiGrid>
          {balance.data && !balance.data.reconciliation_ok && <div role="alert" style={{ padding: 10, marginBottom: 12, borderRadius: 8, background: "var(--danger-bg)", color: "var(--danger-text)", fontSize: 12 }}>Ledger reconciliation failed. Stock mutations are blocked until support resolves the mismatch.</div>}
          <DataTable<Record<string, unknown>> loading={transactions.loading} emptyText="No stock movements for this item and location."
            rows={(transactions.data?.transactions ?? []) as unknown as Array<Record<string, unknown>>} columns={[
              { key: "created_at", label: "Time", render: v => v ? new Date(String(v)).toLocaleString() : "—" },
              { key: "txn_type", label: "Movement", render: v => <Badge variant={String(v) === "receipt" ? "success" : String(v) === "confirmation" ? "warning" : "info"}>{String(v).replaceAll("_", " ")}</Badge> },
              { key: "quantity", label: "Quantity", render: v => <strong style={{ color: Number(v) < 0 ? "var(--danger-text)" : Number(v) > 0 ? "var(--success-text)" : "var(--text-primary)" }}>{Number(v) > 0 ? "+" : ""}{String(v)}</strong> },
              { key: "balance_after", label: "Balance" }, { key: "job_id", label: "Job", render: v => v ? String(v) : "—" },
              { key: "notes", label: "Reference", render: v => v ? String(v) : "—" },
            ]}/>
        </> : (
          <EmptyState title="Select stock context" description="Choose an item and location to inspect its reconciled balance and immutable ledger." icon={<ShieldCheck/>}/>
        )}
      </Card>
    </div>}

    {tab === "imports" && <Card>
      <CardHeader icon={<FileStack/>} title="Import review" subtitle="AI extraction creates drafts only; a provider must publish each item."/>
      {!extractionEnabled ? <EmptyState title="Document extraction is not enabled" description="Inventory works normally without AI import. An administrator can enable the optional extraction engine for this tenant." icon={<FileStack/>}/>
        : (drafts.data?.items ?? []).length === 0 ? <EmptyState title="No drafts awaiting review" description="Upload a supplier PDF to create reviewable inventory drafts." icon={<Upload/>}/>
        : <DataTable<InventoryDraftItem & Record<string, unknown>> loading={drafts.loading} emptyText="No import drafts."
          rows={(drafts.data?.items ?? []) as Array<InventoryDraftItem & Record<string, unknown>>} columns={[
            { key: "name", label: "Draft item", render: (_v, row) => <div><strong>{row.name}</strong><div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{row.sku}</div></div> },
            { key: "category", label: "Setup category", render: (_v, row) => <select
              aria-label={`Map ${row.name} to service category`}
              value={draftCategories[row.item_id] ?? row.service_group_id ?? ""}
              onChange={e => setDraftCategories(current => ({ ...current, [row.item_id]: e.target.value }))}
              style={{ ...inputStyle, minWidth: 170 }}>
              <option value="">Map category</option>
              {categoryOptions.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select> },
            { key: "unit_cost", label: "Detected price", render: v => money(Number(v)) },
            { key: "min_quantity", label: "Reorder level" },
            { key: "actions", label: "", render: (_v, row) => <Btn size="xs" variant="success"
              disabled={!(draftCategories[row.item_id] ?? row.service_group_id)}
              loading={draftBusy === row.item_id} onClick={() => publishDraft(row.item_id)}>Publish</Btn> },
          ]}/>
        }
    </Card>}

    <Modal open={!!itemModal} onClose={() => setItemModal(null)} title={itemModal === "create" ? "Create inventory item" : "Edit inventory item"} size="lg">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
        <Field label="Item name"><input style={inputStyle} value={itemForm.name} onChange={e => setItemForm(p => ({ ...p, name: e.target.value }))}/></Field>
        <Field label="SKU"><input style={inputStyle} value={itemForm.sku} onChange={e => setItemForm(p => ({ ...p, sku: e.target.value }))}/></Field>
        <Field label="Enabled service category" hint="Sourced from the provider setup entitlement; admin catalog remains read-only."><select style={inputStyle} value={itemForm.serviceGroupId} onChange={e => setItemForm(p => ({ ...p, serviceGroupId: e.target.value }))}><option value="">Select category</option>{categoryOptions.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}</select></Field>
        <Field label="Unit"><select style={inputStyle} value={itemForm.unit} onChange={e => setItemForm(p => ({ ...p, unit: e.target.value }))}>{UNITS.map(u => <option key={u}>{u}</option>)}</select></Field>
        <Field label="Provider acquisition cost" hint="Private; used for inventory valuation and margin."><input style={inputStyle} type="number" min="0" step="0.01" value={itemForm.unitCost} onChange={e => setItemForm(p => ({ ...p, unitCost: e.target.value }))}/></Field>
        <Field label="Customer part price" hint="Customer-facing part price before GST. Service commission rules remain separate."><input style={inputStyle} type="number" min="0" step="0.01" value={itemForm.sellingPrice} onChange={e => setItemForm(p => ({ ...p, sellingPrice: e.target.value }))}/></Field>
        <Field label="Reorder level"><input style={inputStyle} type="number" min="0" value={itemForm.minQuantity} onChange={e => setItemForm(p => ({ ...p, minQuantity: e.target.value }))}/></Field>
        <Field label="GST percentage"><input style={inputStyle} type="number" min="0" max="100" step="0.01" value={itemForm.gst} onChange={e => setItemForm(p => ({ ...p, gst: e.target.value }))}/></Field>
        <Field label="Part warranty"><input style={inputStyle} placeholder="Example: 12 months" value={itemForm.warranty} onChange={e => setItemForm(p => ({ ...p, warranty: e.target.value }))}/></Field>
      </div>
      <div style={{ marginTop: 18, padding: 12, borderRadius: 10, background: "var(--info-bg)", color: "var(--info-text)", fontSize: 12 }}>
        Pricing ownership: the provider sets part cost and customer price here. Admin service commission and completion-credit policies are applied by Home Services Finance, not duplicated in inventory.
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 20 }}><Btn variant="secondary" onClick={() => setItemModal(null)}>Cancel</Btn><Btn loading={saving} onClick={saveItem}>{itemModal === "create" ? "Create item" : "Save changes"}</Btn></div>
    </Modal>

    <Modal open={locationModal} onClose={() => setLocationModal(false)} title="Add stock location" size="sm">
      <div style={{ display: "grid", gap: 14 }}><Field label="Location name"><input style={inputStyle} value={locationName} placeholder="Main warehouse" onChange={e => setLocationName(e.target.value)}/></Field><Field label="Location type"><select style={inputStyle} value={locationType} onChange={e => setLocationType(e.target.value)}><option value="warehouse">Warehouse</option><option value="store">Store</option><option value="van">Service van</option><option value="technician">Technician stock</option></select></Field></div>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 20 }}><Btn variant="secondary" onClick={() => setLocationModal(false)}>Cancel</Btn><Btn loading={saving} disabled={!locationName.trim()} onClick={createLocation}>Create location</Btn></div>
    </Modal>

    <Modal open={receiveModal} onClose={() => setReceiveModal(false)} title="Receive stock" size="sm">
      <div style={{ display: "grid", gap: 14 }}><Field label="Quantity received"><input style={inputStyle} type="number" min="1" value={receiveQuantity} onChange={e => setReceiveQuantity(e.target.value)}/></Field><Field label="Receipt reference / notes"><input style={inputStyle} value={receiveNotes} placeholder="Supplier invoice or delivery note" onChange={e => setReceiveNotes(e.target.value)}/></Field></div>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 20 }}><Btn variant="secondary" onClick={() => setReceiveModal(false)}>Cancel</Btn><Btn loading={saving} onClick={receiveStock}>Post receipt</Btn></div>
    </Modal>

    <Modal open={!!stockAction} onClose={() => setStockAction(null)} title={stockAction === "count" ? "Post cycle count" : "Transfer stock"} size="sm">
      <div style={{ display: "grid", gap: 14 }}>
        {stockAction === "count" ? <Field label="Counted on-hand quantity" hint={`Reserved units: ${balance.data?.reserved_qty ?? 0}. The physical count cannot be below active job reservations.`}><input style={inputStyle} type="number" min="0" value={countedQuantity} onChange={e => setCountedQuantity(e.target.value)}/></Field>
          : <>
            <Field label="Destination location"><select style={inputStyle} value={transferLocation} onChange={e => setTransferLocation(e.target.value)}><option value="">Select destination</option>{locationRows.filter(l => l.location_id !== selectedLocation).map(l => <option key={l.location_id} value={l.location_id}>{l.location_name}</option>)}</select></Field>
            <Field label="Transfer quantity"><input style={inputStyle} type="number" min="1" value={transferQuantity} onChange={e => setTransferQuantity(e.target.value)}/></Field>
          </>}
        <Field label="Audit reason"><input style={inputStyle} placeholder="Count variance, van replenishment, etc." value={stockReason} onChange={e => setStockReason(e.target.value)}/></Field>
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 20 }}><Btn variant="secondary" onClick={() => setStockAction(null)}>Cancel</Btn><Btn loading={saving} disabled={!stockReason.trim()} onClick={submitStockControl}>{stockAction === "count" ? "Post count" : "Transfer stock"}</Btn></div>
    </Modal>
  </div>;
}
