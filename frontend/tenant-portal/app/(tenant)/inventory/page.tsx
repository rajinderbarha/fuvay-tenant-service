"use client";
import React, { useState, useCallback, useMemo } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Modal, SectionHeader, StatCard, DataTable, Btn, EditBtn, DeleteBtn } from "../../../components/shared/ui";
import { useApi, useAction } from "../../../hooks/useApi";
import {
  inventoryApi,
  engineApi,
  entitlementApi,
  type InventoryItem,
  type InventoryDraftItem,
} from "../../../lib/api";
import { Boxes, Tags, IndianRupee, FileStack, Upload, Plus } from "lucide-react";

// Stock-level tracking (balances/receipts/low-stock alerts) is not
// maintained by this tenant -- removed per explicit request.
const EXTRACTION_ENGINE_KEY = "inventory_document_extraction";

// Real units used for home-service accessories/spare parts (compressors,
// filters, wiring, pipes, fasteners, chemicals, etc.) -- covers the
// physical unit types genuinely needed for this domain. Not sourced from
// a backend table (none exists for this), a fixed curated list per request
// "add all the units that exist for home service accessories".
const HOME_SERVICE_UNITS = [
  "pcs", "set", "pair", "box", "carton", "packet", "bundle", "roll",
  "coil", "sheet", "bag", "dozen",
  "meter", "feet", "cm",
  "kg", "gram", "liter", "ml",
  "unit",
] as const;

function UnitField({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)}
      style={{ ...fieldInputStyle, cursor: "pointer" }}>
      {HOME_SERVICE_UNITS.map(u => <option key={u} value={u}>{u}</option>)}
    </select>
  );
}

// Shared labeled-field styling for the clean modal forms below.
const fieldLabelStyle: React.CSSProperties = {
  fontSize: 11, color: "var(--text-secondary)", display: "block", marginBottom: 3,
  fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.03em",
};
const fieldInputStyle: React.CSSProperties = {
  width: "100%", height: 34, padding: "0 9px", borderRadius: 7,
  border: "1px solid var(--border)", background: "var(--surface)",
  color: "var(--text-primary)", fontSize: 13, fontFamily: "inherit",
  boxSizing: "border-box",
};

/** Category select strictly limited to this provider's real active service
 * categories -- no free-text entry, since a provider cannot stock inventory
 * for a category they don't offer as a service. */
function CategoryField({ value, onChange, options }: {
  value: string; onChange: (v: string) => void; options: string[];
}) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)}
      style={{ ...fieldInputStyle, cursor: "pointer" }}>
      <option value="">— None —</option>
      {options.map(o => <option key={o} value={o}>{o}</option>)}
    </select>
  );
}

export default function InventoryPage() {
  // ── Items tab ────────────────────────────────────────────────────────────
  const [showCreate, setShowCreate] = useState(false);
  const emptyNewItem = { name:"", sku:"", unit:"pcs", unit_cost:"", category:"", min_quantity:"0", gst:"", warranty:"" };
  const [newItem, setNewItem] = useState(emptyNewItem);
  const { execute: createItem, loading: creating, error: createError } = useAction(
    useCallback(async () => {
      const res = await inventoryApi.createItem(
        newItem.name, newItem.sku, newItem.unit,
        parseFloat(newItem.unit_cost) || 0,
        newItem.category || undefined,
        parseInt(newItem.min_quantity) || 0,
        newItem.gst !== "" ? parseFloat(newItem.gst) : null,
        newItem.warranty || null,
      );
      if (res) { setShowCreate(false); setNewItem(emptyNewItem); itemList.refetch(); }
      return res;
    }, [newItem]) // eslint-disable-line react-hooks/exhaustive-deps
  );

  const itemList = useApi(
    useCallback(() => inventoryApi.listItems(), []),
    []
  );

  // ── Edit/Delete published items ──────────────────────────────────────────
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [itemPatch, setItemPatch] = useState<Partial<InventoryItem>>({});
  const [itemBusy, setItemBusy] = useState<Record<string, boolean>>({});
  const [itemActionError, setItemActionError] = useState<string | null>(null);

  function openEditItem(item: InventoryItem) {
    setEditingItemId(item.item_id);
    setItemPatch({ ...item });
    setItemActionError(null);
  }

  async function handleSaveItemEdit() {
    if (!editingItemId) return;
    setItemBusy(p => ({ ...p, [editingItemId]: true }));
    setItemActionError(null);
    try {
      await inventoryApi.updateItem(editingItemId, {
        name: itemPatch.name, sku: itemPatch.sku, unit: itemPatch.unit,
        unit_cost: itemPatch.unit_cost, category: itemPatch.category ?? null,
        min_quantity: itemPatch.min_quantity, gst: itemPatch.gst ?? null,
        warranty: itemPatch.warranty ?? null,
      });
      setEditingItemId(null);
      itemList.refetch();
    } catch (e) {
      setItemActionError(e instanceof Error ? e.message : "Update failed.");
    } finally {
      setItemBusy(p => ({ ...p, [editingItemId]: false }));
    }
  }

  async function handleDeleteItem(itemId: string) {
    if (!window.confirm("Delete this inventory item? This cannot be undone.")) return;
    setItemBusy(p => ({ ...p, [itemId]: true }));
    setItemActionError(null);
    try {
      await inventoryApi.deleteItem(itemId);
      itemList.refetch();
    } catch (e) {
      setItemActionError(e instanceof Error ? e.message : "Delete failed.");
    } finally {
      setItemBusy(p => ({ ...p, [itemId]: false }));
    }
  }

  // Category dropdown is restricted to the real service categories this
  // provider is actively entitled/enabled for -- per explicit request
  // "category will show in dropdown only in which provider providing
  // service. no other category should show." Not derived from inventory
  // data, and no free-text "add new" option (a provider cannot stock
  // inventory for a category they don't offer as a service).
  const myCategories = useApi(useCallback(() => entitlementApi.getMyCategories(), []), []);
  const knownCategories = useMemo(() => {
    return (myCategories.data?.categories ?? [])
      .filter(c => c.status === "ACTIVE" && c.category_label)
      .map(c => c.category_label as string)
      .filter((v, i, arr) => arr.indexOf(v) === i)
      .sort();
  }, [myCategories.data]);

  // ── PDF -> AI extraction (draft review + publish) ───────────────────────
  // Only shown/usable if the inventory_document_extraction plugin engine is
  // enabled for this tenant -- checked via the same effective-engines
  // endpoint other engine-gated frontend features use.
  const effectiveEngines = useApi(useCallback(() => engineApi.getEffectiveEngines(), []), []);
  const extractionEnabled = !!effectiveEngines.data?.engines?.some(
    e => e.engine_key === EXTRACTION_ENGINE_KEY && e.effective_enabled
  );

  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadNotice, setUploadNotice] = useState<string | null>(null);

  const drafts = useApi(useCallback(() => inventoryApi.listDrafts(), []), []);
  const [editingDraft, setEditingDraft] = useState<Record<string, Partial<InventoryDraftItem>>>({});
  const [draftBusy, setDraftBusy] = useState<Record<string, boolean>>({});
  // item_id of the draft currently open in the edit modal (one modal at a time).
  const [openDraftModalId, setOpenDraftModalId] = useState<string | null>(null);

  async function handleUploadPdf(file: File) {
    setUploading(true); setUploadError(null); setUploadNotice(null);
    try {
      const res = await inventoryApi.uploadForExtraction(file);
      setUploadNotice(
        res.idempotent
          ? `This file was already processed (${res.extracted_item_count} item(s)).`
          : `Extracted ${res.extracted_item_count} item(s) — review below before publishing.`
      );
      drafts.refetch();
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handlePublishDraft(itemId: string) {
    setDraftBusy(p => ({ ...p, [itemId]: true }));
    try {
      await inventoryApi.publishItem(itemId);
      drafts.refetch(); itemList.refetch();
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Publish failed.");
    } finally {
      setDraftBusy(p => ({ ...p, [itemId]: false }));
    }
  }

  async function handleDeleteDraft(itemId: string) {
    setDraftBusy(p => ({ ...p, [itemId]: true }));
    try {
      await inventoryApi.deleteDraft(itemId);
      drafts.refetch();
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Delete failed.");
    } finally {
      setDraftBusy(p => ({ ...p, [itemId]: false }));
    }
  }

  async function handleSaveDraftEdit(itemId: string) {
    const patch = editingDraft[itemId];
    if (!patch) return;
    setDraftBusy(p => ({ ...p, [itemId]: true }));
    try {
      await inventoryApi.updateDraft(itemId, patch);
      setEditingDraft(p => { const n = { ...p }; delete n[itemId]; return n; });
      setOpenDraftModalId(id => id === itemId ? null : id);
      drafts.refetch();
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Save failed.");
    } finally {
      setDraftBusy(p => ({ ...p, [itemId]: false }));
    }
  }

  async function handlePublishAllDrafts() {
    const ids = (drafts.data?.items ?? []).map(i => i.item_id);
    if (ids.length === 0) return;
    setUploading(true);
    try {
      await inventoryApi.publishBulk(ids);
      drafts.refetch(); itemList.refetch();
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Bulk publish failed.");
    } finally {
      setUploading(false);
    }
  }

  // ── KPIs ──────────────────────────────────────────────────────────────────
  const items = itemList.data?.items ?? [];
  const totalItems = items.length;
  const distinctCategories = useMemo(
    () => new Set(items.map(i => i.category).filter(Boolean)).size,
    [items],
  );
  const inventoryValue = useMemo(
    () => items.reduce((sum, i) => sum + (i.unit_cost ?? 0) * (i.min_quantity ?? 0), 0),
    [items],
  );
  const pendingDraftCount = drafts.data?.items?.length ?? 0;

  return (
    <TenantLayout activeNav="inventory">
      <div style={{ maxWidth:1200 }}>
        <SectionHeader
          title="Inventory"
          subtitle="Manage your stocked items, pricing, and AI-extracted price lists."
          icon={<Boxes/>}
          actions={
            <>
              {extractionEnabled && (
                <label style={{ display:"inline-flex" }}>
                  <Btn variant="secondary" icon={<Upload size={14}/>} disabled={uploading}>
                    {uploading ? "Uploading…" : "Upload Inventory PDF"}
                  </Btn>
                  <input type="file" accept="application/pdf" disabled={uploading} style={{ display:"none" }}
                    onChange={e => { const f = e.target.files?.[0]; if (f) handleUploadPdf(f); e.target.value = ""; }}/>
                </label>
              )}
              <Btn onClick={() => setShowCreate(p => !p)} icon={<Plus size={14}/>}>
                New Item
              </Btn>
            </>
          }
        />

        <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(200px,1fr))", gap:14, marginBottom:24 }}>
          <StatCard label="Total Items" value={totalItems} icon={<Boxes/>}/>
          <StatCard label="Categories Stocked" value={distinctCategories} icon={<Tags/>}/>
          <StatCard label="Inventory Value" value={`₹${inventoryValue.toLocaleString("en-IN")}`} icon={<IndianRupee/>}/>
          <StatCard label="Drafts Awaiting Review" value={pendingDraftCount} icon={<FileStack/>}
            alert={pendingDraftCount > 0}/>
        </div>

        <div>
            {!extractionEnabled && !effectiveEngines.loading && (
              <p style={{ fontSize:12, color:"var(--text-tertiary)", marginBottom:16 }}>
                AI PDF extraction is not enabled for your account. Ask your platform admin to enable the
                &quot;Inventory Document Extraction&quot; engine to upload a price list/stock sheet PDF here.
              </p>
            )}

            {(uploadError || uploadNotice) && (
              <div style={{ marginBottom:16, padding:"10px 14px", borderRadius:"var(--radius-md)",
                background: uploadError ? "var(--danger-bg, #fef2f2)" : "var(--success-bg, #f0fdf4)",
                border: `1px solid ${uploadError ? "var(--danger-border, #fecaca)" : "var(--success-border, #bbf7d0)"}`,
                color: uploadError ? "var(--danger-text, #991b1b)" : "var(--success-text, #166534)", fontSize:13 }}>
                {uploadError ?? uploadNotice}
              </div>
            )}

            {extractionEnabled && (drafts.data?.items?.length ?? 0) > 0 && (
              <div style={{ background:"var(--surface)", border:"1px solid var(--border)",
                borderRadius:"var(--radius-lg)", padding:"16px 18px", marginBottom:20 }}>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:12 }}>
                  <h3 style={{ margin:0, fontSize:14, fontWeight:600, color:"var(--text-primary)" }}>
                    Draft items awaiting review ({drafts.data?.items?.length})
                  </h3>
                  <button onClick={handlePublishAllDrafts} disabled={uploading}
                    style={{ padding:"6px 14px", borderRadius:"var(--radius-md)", border:"none",
                      background:"var(--success, #16a34a)", color:"white", fontWeight:600, fontSize:12,
                      cursor:"pointer", fontFamily:"inherit" }}>
                    Publish All
                  </button>
                </div>
                <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                  {drafts.data?.items?.map(d => {
                    const busy = !!draftBusy[d.item_id];
                    return (
                      <div key={d.item_id} style={{ display:"flex", justifyContent:"space-between",
                        alignItems:"center", gap:12, padding:"10px 12px", background:"var(--surface-sunken)",
                        borderRadius:8 }}>
                        <div style={{ minWidth:0 }}>
                          <p style={{ margin:"0 0 2px", fontSize:13, fontWeight:600, color:"var(--text-primary)" }}>
                            {d.name} <span style={{ fontWeight:400, color:"var(--text-tertiary)" }}>({d.sku})</span>
                          </p>
                          <p style={{ margin:0, fontSize:11, color:"var(--text-secondary)" }}>
                            {d.category ?? "No category"} · {d.unit} · ₹{d.unit_cost} · Min qty {d.min_quantity}
                            {d.gst != null ? ` · GST ${d.gst}%` : ""}
                            {d.warranty ? ` · Warranty ${d.warranty}` : ""}
                          </p>
                        </div>
                        <div style={{ display:"flex", gap:6, flexShrink:0 }}>
                          <button onClick={() => setOpenDraftModalId(d.item_id)} disabled={busy}
                            style={{ height:28, padding:"0 10px", borderRadius:6, border:"1px solid var(--border)",
                              background:"var(--surface)", color:"var(--text-primary)", fontSize:11, fontWeight:600,
                              cursor:"pointer", fontFamily:"inherit" }}>Edit</button>
                          <button onClick={() => handlePublishDraft(d.item_id)} disabled={busy}
                            style={{ height:28, padding:"0 10px", borderRadius:6, border:"none",
                              background:"var(--success, #16a34a)", color:"white", fontSize:11, fontWeight:600,
                              cursor:"pointer", fontFamily:"inherit" }}>Publish</button>
                          <button onClick={() => handleDeleteDraft(d.item_id)} disabled={busy}
                            style={{ height:28, padding:"0 10px", borderRadius:6, border:"1px solid var(--border)",
                              background:"transparent", color:"var(--danger, #dc2626)", fontSize:11, fontWeight:600,
                              cursor:"pointer", fontFamily:"inherit" }}>Delete</button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Draft edit modal — one draft item at a time. Keeps
                Publish/Delete on the row itself (outside the modal) for
                quick access without opening it. */}
            {openDraftModalId && (() => {
              const d = drafts.data?.items?.find(x => x.item_id === openDraftModalId);
              if (!d) return null;
              const busy = !!draftBusy[d.item_id];
              const patch = editingDraft[d.item_id] ?? {};
              const set = (field: keyof InventoryDraftItem, value: unknown) =>
                setEditingDraft(p => ({ ...p, [d.item_id]: { ...p[d.item_id], [field]: value } }));
              return (
                <Modal open onClose={() => setOpenDraftModalId(null)} title={`Edit draft — ${d.name}`} size="md">
                  <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
                    <div>
                      <label style={fieldLabelStyle}>Name *</label>
                      <input aria-label="Item Name" value={patch.name ?? d.name}
                        onChange={e => set("name", e.target.value)} style={fieldInputStyle}/>
                    </div>
                    <div>
                      <label style={fieldLabelStyle}>SKU *</label>
                      <input aria-label="SKU" value={patch.sku ?? d.sku}
                        onChange={e => set("sku", e.target.value)} style={fieldInputStyle}/>
                    </div>
                    <div>
                      <label style={fieldLabelStyle}>Unit</label>
                      <UnitField value={patch.unit ?? d.unit} onChange={v => set("unit", v)}/>
                    </div>
                    <div>
                      <label style={fieldLabelStyle}>Category</label>
                      <CategoryField value={String(patch.category ?? d.category ?? "")}
                        onChange={v => set("category", v)} options={knownCategories}/>
                    </div>
                    <div>
                      <label style={fieldLabelStyle}>Unit Cost (₹)</label>
                      <input aria-label="Unit Cost" type="number" value={patch.unit_cost ?? d.unit_cost}
                        onChange={e => set("unit_cost", parseFloat(e.target.value) || 0)} style={fieldInputStyle}/>
                    </div>
                    <div>
                      <label style={fieldLabelStyle}>Min Quantity</label>
                      <input aria-label="Min Quantity" type="number" value={patch.min_quantity ?? d.min_quantity}
                        onChange={e => set("min_quantity", parseInt(e.target.value) || 0)} style={fieldInputStyle}/>
                    </div>
                    <div>
                      <label style={fieldLabelStyle}>GST %</label>
                      <input aria-label="GST Percent" type="number" step="0.01"
                        value={patch.gst ?? d.gst ?? ""}
                        onChange={e => set("gst", e.target.value === "" ? null : parseFloat(e.target.value))}
                        style={fieldInputStyle}/>
                    </div>
                    <div>
                      <label style={fieldLabelStyle}>Warranty</label>
                      <input aria-label="Warranty" placeholder="e.g. 12 months"
                        value={patch.warranty ?? d.warranty ?? ""}
                        onChange={e => set("warranty", e.target.value)} style={fieldInputStyle}/>
                    </div>
                  </div>
                  <div style={{ display:"flex", gap:8, marginTop:20, justifyContent:"flex-end" }}>
                    <button onClick={() => setOpenDraftModalId(null)}
                      style={{ padding:"8px 14px", borderRadius:"var(--radius-md)", border:"1px solid var(--border)",
                        background:"transparent", color:"var(--text-secondary)", fontSize:13,
                        cursor:"pointer", fontFamily:"inherit" }}>
                      Cancel
                    </button>
                    <button onClick={() => handleSaveDraftEdit(d.item_id)} disabled={busy}
                      style={{ padding:"8px 18px", borderRadius:"var(--radius-md)", border:"none",
                        background:"var(--accent)", color:"white", fontWeight:600, fontSize:13,
                        cursor:"pointer", fontFamily:"inherit" }}>
                      {busy ? "Saving…" : "Save"}
                    </button>
                  </div>
                </Modal>
              );
            })()}

            {/* Edit published item modal */}
            {editingItemId && (
              <Modal open onClose={() => setEditingItemId(null)} title="Edit Item" size="md">
                {itemActionError && <p style={{ color:"var(--danger)", fontSize:12, marginBottom:10 }}>{itemActionError}</p>}
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
                  <div>
                    <label style={fieldLabelStyle}>Name *</label>
                    <input value={itemPatch.name ?? ""} onChange={e => setItemPatch(p => ({ ...p, name:e.target.value }))}
                      style={fieldInputStyle}/>
                  </div>
                  <div>
                    <label style={fieldLabelStyle}>SKU *</label>
                    <input value={itemPatch.sku ?? ""} onChange={e => setItemPatch(p => ({ ...p, sku:e.target.value }))}
                      style={fieldInputStyle}/>
                  </div>
                  <div>
                    <label style={fieldLabelStyle}>Unit *</label>
                    <UnitField value={itemPatch.unit ?? "unit"} onChange={v => setItemPatch(p => ({ ...p, unit:v }))}/>
                  </div>
                  <div>
                    <label style={fieldLabelStyle}>Category</label>
                    <CategoryField value={itemPatch.category ?? ""}
                      onChange={v => setItemPatch(p => ({ ...p, category:v }))} options={knownCategories}/>
                  </div>
                  <div>
                    <label style={fieldLabelStyle}>Unit Cost (₹) *</label>
                    <input type="number" value={itemPatch.unit_cost ?? 0}
                      onChange={e => setItemPatch(p => ({ ...p, unit_cost:parseFloat(e.target.value) || 0 }))}
                      style={fieldInputStyle}/>
                  </div>
                  <div>
                    <label style={fieldLabelStyle}>Min Qty</label>
                    <input type="number" value={itemPatch.min_quantity ?? 0}
                      onChange={e => setItemPatch(p => ({ ...p, min_quantity:parseInt(e.target.value) || 0 }))}
                      style={fieldInputStyle}/>
                  </div>
                  <div>
                    <label style={fieldLabelStyle}>GST %</label>
                    <input type="number" step="0.01" value={itemPatch.gst ?? ""}
                      onChange={e => setItemPatch(p => ({ ...p, gst: e.target.value === "" ? null : parseFloat(e.target.value) }))}
                      style={fieldInputStyle}/>
                  </div>
                  <div>
                    <label style={fieldLabelStyle}>Warranty</label>
                    <input placeholder="e.g. 12 months" value={itemPatch.warranty ?? ""}
                      onChange={e => setItemPatch(p => ({ ...p, warranty:e.target.value }))} style={fieldInputStyle}/>
                  </div>
                </div>
                <div style={{ display:"flex", gap:8, marginTop:20, justifyContent:"flex-end" }}>
                  <button onClick={() => setEditingItemId(null)}
                    style={{ padding:"8px 14px", borderRadius:"var(--radius-md)", border:"1px solid var(--border)",
                      background:"transparent", color:"var(--text-secondary)", fontSize:13,
                      cursor:"pointer", fontFamily:"inherit" }}>
                    Cancel
                  </button>
                  <button onClick={handleSaveItemEdit} disabled={!!itemBusy[editingItemId]}
                    style={{ padding:"8px 18px", borderRadius:"var(--radius-md)", border:"none",
                      background:"var(--accent)", color:"white", fontWeight:600, fontSize:13,
                      cursor:"pointer", fontFamily:"inherit" }}>
                    {itemBusy[editingItemId] ? "Saving…" : "Save"}
                  </button>
                </div>
              </Modal>
            )}

            {/* Create Item modal — modalized (was inline) for consistency
                with the draft-edit modal above, per "make form bit clean
                and should open in modal". */}
            {showCreate && (
              <Modal open onClose={() => setShowCreate(false)} title="Create Item" size="md">
                {createError && <p style={{ color:"var(--danger)", fontSize:12, marginBottom:10 }}>{createError}</p>}
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
                  <div>
                    <label style={fieldLabelStyle}>Name *</label>
                    <input value={newItem.name} onChange={e => setNewItem(p => ({ ...p, name:e.target.value }))}
                      style={fieldInputStyle}/>
                  </div>
                  <div>
                    <label style={fieldLabelStyle}>SKU *</label>
                    <input value={newItem.sku} onChange={e => setNewItem(p => ({ ...p, sku:e.target.value }))}
                      style={fieldInputStyle}/>
                  </div>
                  <div>
                    <label style={fieldLabelStyle}>Unit *</label>
                    <UnitField value={newItem.unit} onChange={v => setNewItem(p => ({ ...p, unit:v }))}/>
                  </div>
                  <div>
                    <label style={fieldLabelStyle}>Category</label>
                    <CategoryField value={newItem.category}
                      onChange={v => setNewItem(p => ({ ...p, category:v }))} options={knownCategories}/>
                  </div>
                  <div>
                    <label style={fieldLabelStyle}>Unit Cost (₹) *</label>
                    <input type="number" value={newItem.unit_cost}
                      onChange={e => setNewItem(p => ({ ...p, unit_cost:e.target.value }))} style={fieldInputStyle}/>
                  </div>
                  <div>
                    <label style={fieldLabelStyle}>Min Qty</label>
                    <input type="number" value={newItem.min_quantity}
                      onChange={e => setNewItem(p => ({ ...p, min_quantity:e.target.value }))} style={fieldInputStyle}/>
                  </div>
                  <div>
                    <label style={fieldLabelStyle}>GST %</label>
                    <input type="number" step="0.01" value={newItem.gst}
                      onChange={e => setNewItem(p => ({ ...p, gst:e.target.value }))} style={fieldInputStyle}/>
                  </div>
                  <div>
                    <label style={fieldLabelStyle}>Warranty</label>
                    <input placeholder="e.g. 12 months" value={newItem.warranty}
                      onChange={e => setNewItem(p => ({ ...p, warranty:e.target.value }))} style={fieldInputStyle}/>
                  </div>
                </div>
                <div style={{ display:"flex", gap:8, marginTop:20, justifyContent:"flex-end" }}>
                  <button onClick={() => setShowCreate(false)}
                    style={{ padding:"8px 14px", borderRadius:"var(--radius-md)", border:"1px solid var(--border)",
                      background:"transparent", color:"var(--text-secondary)", fontSize:13,
                      cursor:"pointer", fontFamily:"inherit" }}>
                    Cancel
                  </button>
                  <button onClick={() => createItem()} disabled={creating || !newItem.name || !newItem.sku}
                    style={{ padding:"8px 18px", borderRadius:"var(--radius-md)", border:"none",
                      background:"var(--accent)", color:"white", fontWeight:600, fontSize:13,
                      cursor:"pointer", fontFamily:"inherit",
                      opacity:(!newItem.name || !newItem.sku) ? 0.5 : 1 }}>
                    {creating ? "Creating…" : "Create"}
                  </button>
                </div>
              </Modal>
            )}

            {itemList.error && <p style={{ color:"var(--danger)", fontSize:13, marginBottom:12 }}>{itemList.error}</p>}

            <DataTable<InventoryItem & Record<string, unknown>>
              loading={itemList.loading}
              emptyText="No items yet."
              columns={[
                { key:"name", label:"Name", render:(_v, row) => (
                    <span style={{ fontWeight:600, color:"var(--text-primary)" }}>{row.name}</span>
                  )},
                { key:"sku", label:"SKU" },
                { key:"category", label:"Category", render:(_v, row) => row.category ?? "—" },
                { key:"unit", label:"Unit" },
                { key:"unit_cost", label:"Unit Cost (₹)", render:(_v, row) =>
                    row.unit_cost != null ? `₹${row.unit_cost}` : "—" },
                { key:"min_quantity", label:"Min Qty" },
                { key:"gst", label:"GST %", render:(_v, row) => row.gst != null ? `${row.gst}%` : "—" },
                { key:"warranty", label:"Warranty", render:(_v, row) => row.warranty ?? "—" },
                { key:"actions", label:"", render:(_v, row) => (
                    <div style={{ display:"flex", gap:6, justifyContent:"flex-end" }}>
                      <EditBtn onClick={() => openEditItem(row)} tooltip="Edit item" size="sm"/>
                      <DeleteBtn onClick={() => handleDeleteItem(row.item_id)} tooltip="Delete item" size="sm"/>
                    </div>
                  )},
              ]}
              rows={items as (InventoryItem & Record<string, unknown>)[]}
            />
          </div>
      </div>
    </TenantLayout>
  );
}
