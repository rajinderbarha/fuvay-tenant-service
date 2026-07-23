"use client";
import React, { useState, useCallback, useMemo } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Modal } from "../../../components/shared/ui";
import { useApi, useAction } from "../../../hooks/useApi";
import {
  inventoryApi,
  engineApi,
  type InventoryItem,
  type InventoryDraftItem,
  type LowStockItem,
  type StockTransaction,
} from "../../../lib/api";

type Tab = "items" | "stock" | "low";
const EXTRACTION_ENGINE_KEY = "inventory_document_extraction";

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

/** Combo box: pick from known values (real distinct categories already in
 * use for this tenant) or type a new one. Kept intentionally simple (no
 * extra dependency) — a native <select> with an "+ Add new…" sentinel that
 * reveals a free-text input. */
function CategoryField({ value, onChange, options }: {
  value: string; onChange: (v: string) => void; options: string[];
}) {
  const [customMode, setCustomMode] = useState(() => !!value && !options.includes(value));
  if (customMode) {
    return (
      <div style={{ display: "flex", gap: 6 }}>
        <input value={value} onChange={e => onChange(e.target.value)}
          placeholder="New category name" style={fieldInputStyle} />
        {options.length > 0 && (
          <button type="button" onClick={() => { setCustomMode(false); onChange(""); }}
            style={{ height: 34, padding: "0 10px", borderRadius: 7, border: "1px solid var(--border)",
              background: "transparent", color: "var(--text-secondary)", fontSize: 12, cursor: "pointer",
              fontFamily: "inherit", whiteSpace: "nowrap" }}>
            Choose existing
          </button>
        )}
      </div>
    );
  }
  return (
    <select value={value}
      onChange={e => { if (e.target.value === "__new__") { setCustomMode(true); onChange(""); } else { onChange(e.target.value); } }}
      style={{ ...fieldInputStyle, cursor: "pointer" }}>
      <option value="">— None —</option>
      {options.map(o => <option key={o} value={o}>{o}</option>)}
      <option value="__new__">+ Add new category…</option>
    </select>
  );
}

export default function InventoryPage() {
  const [tab, setTab] = useState<Tab>("items");

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

  // Real distinct categories already in use for this tenant's inventory —
  // used to pre-populate the Category combo (per user request "category
  // data we have so show that as well"), not a fabricated taxonomy.
  const knownCategories = useMemo(() => {
    const set = new Set<string>();
    for (const i of itemList.data?.items ?? []) { if (i.category) set.add(i.category); }
    return Array.from(set).sort();
  }, [itemList.data]);

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

  // ── Stock tab ────────────────────────────────────────────────────────────
  const [stockItemId,   setStockItemId]   = useState("");
  const [stockLocId,    setStockLocId]    = useState("");
  const [receiveQty,    setReceiveQty]    = useState("");
  const [receiveNotes,  setReceiveNotes]  = useState("");

  const balance = useApi(
    useCallback(async () => {
      if (!stockItemId || !stockLocId) return null;
      return inventoryApi.getBalance(stockItemId, stockLocId);
    }, [stockItemId, stockLocId]),
    [stockItemId, stockLocId]
  );

  const transactions = useApi(
    useCallback(async () => {
      if (!stockItemId || !stockLocId) return null;
      return inventoryApi.listTransactions(stockItemId, stockLocId);
    }, [stockItemId, stockLocId]),
    [stockItemId, stockLocId]
  );

  const { execute: receive, loading: receiving, error: receiveError } = useAction(
    useCallback(async () => {
      if (!stockItemId || !stockLocId || !receiveQty) return null;
      const res = await inventoryApi.receiveStock(
        stockItemId, stockLocId, parseFloat(receiveQty),
        receiveNotes || undefined
      );
      if (res) { setReceiveQty(""); setReceiveNotes(""); balance.refetch(); transactions.refetch(); }
      return res;
    }, [stockItemId, stockLocId, receiveQty, receiveNotes, balance, transactions])
  );

  // ── Low stock tab ─────────────────────────────────────────────────────────
  const lowStock = useApi(
    useCallback(() => inventoryApi.getLowStock(), []),
    []
  );

  const { execute: replenish, loading: replenishing } = useAction(
    useCallback(async (itemId: string, qty: number) => {
      const res = await inventoryApi.replenish(itemId, qty);
      if (res) lowStock.refetch();
      return res;
    }, [lowStock])
  );

  const txnTypeColor: Record<string, string> = {
    receive:"var(--success)", consume:"#ef4444", adjust:"var(--warning)",
    reserve:"#8b5cf6", release:"var(--brand)",
  };

  return (
    <TenantLayout activeNav="inventory">
      <div style={{ maxWidth:1100 }}>
        <h1 style={{ fontSize:22, fontWeight:700, margin:"0 0 20px", color:"var(--text-primary)" }}>
          Inventory
        </h1>

        {/* Tabs */}
        <div style={{ display:"flex", gap:4, marginBottom:24 }}>
          {(["items","stock","low"] as Tab[]).map(t => (
            <button key={t} onClick={() => setTab(t)}
              style={{ padding:"8px 18px", borderRadius:"var(--radius-md)",
                border: tab === t ? "2px solid var(--accent)" : "1px solid var(--border)",
                background: tab === t ? "var(--accent-bg)" : "var(--surface)",
                color: tab === t ? "var(--accent)" : "var(--text-secondary)",
                fontWeight: tab === t ? 600 : 400, fontSize:13, cursor:"pointer",
                fontFamily:"inherit" }}>
              {{ items:"Items", stock:"Stock Levels", low:"Low Stock Alerts" }[t]}
            </button>
          ))}
        </div>

        {/* ── Items Tab ── */}
        {tab === "items" && (
          <div>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:16 }}>
              <span style={{ fontSize:13, color:"var(--text-secondary)" }}>
                {itemList.data ? `${itemList.data.items.length} items` : ""}
              </span>
              <div style={{ display:"flex", gap:8 }}>
                {extractionEnabled && (
                  <label style={{ padding:"8px 16px", borderRadius:"var(--radius-md)",
                    border:"1px solid var(--border)", background:"var(--surface)",
                    color:"var(--text-primary)", fontWeight:600, fontSize:13,
                    cursor: uploading ? "wait" : "pointer", fontFamily:"inherit", opacity: uploading ? 0.6 : 1 }}>
                    {uploading ? "Uploading…" : "Upload Inventory PDF"}
                    <input type="file" accept="application/pdf" disabled={uploading} style={{ display:"none" }}
                      onChange={e => { const f = e.target.files?.[0]; if (f) handleUploadPdf(f); e.target.value = ""; }}/>
                  </label>
                )}
                <button onClick={() => setShowCreate(p => !p)}
                  style={{ padding:"8px 16px", borderRadius:"var(--radius-md)", border:"none",
                    background:"var(--accent)", color:"white", fontWeight:600, fontSize:13,
                    cursor:"pointer", fontFamily:"inherit" }}>
                  + New Item
                </button>
              </div>
            </div>

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
                    Draft items awaiting review ({drafts.data?.items.length})
                  </h3>
                  <button onClick={handlePublishAllDrafts} disabled={uploading}
                    style={{ padding:"6px 14px", borderRadius:"var(--radius-md)", border:"none",
                      background:"var(--success, #16a34a)", color:"white", fontWeight:600, fontSize:12,
                      cursor:"pointer", fontFamily:"inherit" }}>
                    Publish All
                  </button>
                </div>
                <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                  {drafts.data?.items.map(d => {
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
              const d = drafts.data?.items.find(x => x.item_id === openDraftModalId);
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
                      <input aria-label="Unit" value={patch.unit ?? d.unit}
                        onChange={e => set("unit", e.target.value)} style={fieldInputStyle}/>
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
                    <input value={newItem.unit} onChange={e => setNewItem(p => ({ ...p, unit:e.target.value }))}
                      style={fieldInputStyle}/>
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

            {itemList.loading && <p style={{ color:"var(--text-tertiary)", fontSize:13 }}>Loading…</p>}
            {itemList.error  && <p style={{ color:"var(--danger)", fontSize:13 }}>{itemList.error}</p>}
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(280px,1fr))", gap:10 }}>
              {itemList.data?.items.map((item: InventoryItem) => (
                <div key={item.item_id}
                  style={{ background:"var(--surface)", border:"1px solid var(--border)",
                    borderRadius:"var(--radius-lg)", padding:"14px 16px" }}>
                  <div style={{ display:"flex", justifyContent:"space-between" }}>
                    <p style={{ margin:"0 0 3px", fontWeight:600, fontSize:14, color:"var(--text-primary)" }}>
                      {item.name}
                    </p>
                    <span style={{ fontSize:11, color:"var(--text-tertiary)" }}>{item.sku}</span>
                  </div>
                  <p style={{ margin:"0 0 6px", fontSize:12, color:"var(--text-secondary)" }}>
                    {item.category ?? "—"} · {item.unit}{item.unit_cost != null ? ` · ₹${item.unit_cost}` : ""}
                  </p>
                  <p style={{ margin:0, fontSize:11, color:"var(--text-tertiary)" }}>
                    Min qty: {item.min_quantity}
                    {item.gst != null ? ` · GST ${item.gst}%` : ""}
                    {item.warranty ? ` · Warranty ${item.warranty}` : ""}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Stock Tab ── */}
        {tab === "stock" && (
          <div>
            <div style={{ display:"flex", gap:8, marginBottom:20, flexWrap:"wrap" }}>
              <input value={stockItemId} onChange={e => setStockItemId(e.target.value)}
                placeholder="Item UUID"
                style={{ height:36, padding:"0 10px", borderRadius:"var(--radius-md)", width:220,
                  border:"1px solid var(--border)", background:"var(--surface)",
                  color:"var(--text-primary)", fontSize:13, fontFamily:"inherit" }}/>
              <input value={stockLocId} onChange={e => setStockLocId(e.target.value)}
                placeholder="Location UUID"
                style={{ height:36, padding:"0 10px", borderRadius:"var(--radius-md)", width:220,
                  border:"1px solid var(--border)", background:"var(--surface)",
                  color:"var(--text-primary)", fontSize:13, fontFamily:"inherit" }}/>
            </div>

            {!stockItemId || !stockLocId
              ? <p style={{ color:"var(--text-tertiary)", fontSize:13 }}>Enter item and location IDs above.</p>
              : <>
                  {/* Balance card */}
                  {balance.loading && <p style={{ color:"var(--text-tertiary)", fontSize:13 }}>Loading balance…</p>}
                  {balance.data && (
                    <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:12,
                      marginBottom:20, maxWidth:500 }}>
                      {[
                        ["On Hand", balance.data.quantity],
                        ["Reserved", balance.data.reserved_qty],
                        ["Available", balance.data.available_qty],
                      ].map(([label, val]) => (
                        <div key={label as string} style={{ background:"var(--surface)",
                          border:"1px solid var(--border)", borderRadius:10, padding:"14px 16px",
                          textAlign:"center" }}>
                          <p style={{ margin:"0 0 4px", fontSize:22, fontWeight:700, color:"var(--text-primary)" }}>
                            {val}
                          </p>
                          <p style={{ margin:0, fontSize:11, color:"var(--text-tertiary)" }}>{label}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Receive form */}
                  <div style={{ background:"var(--surface)", border:"1px solid var(--border)",
                    borderRadius:"var(--radius-lg)", padding:"16px 18px", maxWidth:400, marginBottom:20 }}>
                    <h3 style={{ margin:"0 0 12px", fontSize:14, fontWeight:600, color:"var(--text-primary)" }}>
                      Receive Stock
                    </h3>
                    {receiveError && <p style={{ color:"var(--danger)", fontSize:12, marginBottom:8 }}>{receiveError}</p>}
                    <div style={{ display:"flex", gap:8, marginBottom:8 }}>
                      <input type="number" value={receiveQty} onChange={e => setReceiveQty(e.target.value)}
                        placeholder="Quantity *"
                        style={{ flex:1, height:34, padding:"0 9px", borderRadius:7,
                          border:"1px solid var(--border)", background:"var(--surface)",
                          color:"var(--text-primary)", fontSize:13, fontFamily:"inherit" }}/>
                      <input value={receiveNotes} onChange={e => setReceiveNotes(e.target.value)}
                        placeholder="Notes"
                        style={{ flex:2, height:34, padding:"0 9px", borderRadius:7,
                          border:"1px solid var(--border)", background:"var(--surface)",
                          color:"var(--text-primary)", fontSize:13, fontFamily:"inherit" }}/>
                    </div>
                    <button onClick={() => receive()} disabled={receiving || !receiveQty}
                      style={{ height:34, padding:"0 16px", borderRadius:7, border:"none",
                        background:"var(--accent)", color:"white", fontWeight:600, fontSize:13,
                        cursor:(!receiveQty) ? "not-allowed" : "pointer",
                        opacity:!receiveQty ? 0.5 : 1, fontFamily:"inherit" }}>
                      {receiving ? "Recording…" : "Record Receipt"}
                    </button>
                  </div>

                  {/* Transaction ledger */}
                  <h3 style={{ fontSize:14, fontWeight:600, color:"var(--text-primary)", margin:"0 0 10px" }}>
                    Transaction Ledger
                  </h3>
                  {transactions.loading && <p style={{ color:"var(--text-tertiary)", fontSize:13 }}>Loading…</p>}
                  {transactions.data?.transactions.length === 0 && (
                    <p style={{ color:"var(--text-tertiary)", fontSize:13 }}>No transactions yet.</p>
                  )}
                  <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
                    {transactions.data?.transactions.map((txn: StockTransaction) => (
                      <div key={txn.txn_id}
                        style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                          background:"var(--surface)", border:"1px solid var(--border)",
                          borderRadius:9, padding:"10px 14px" }}>
                        <div>
                          <span style={{ fontSize:12, fontWeight:600,
                            color: txnTypeColor[txn.txn_type] ?? "var(--text-primary)" }}>
                            {txn.txn_type.toUpperCase()}
                          </span>
                          {txn.notes && <span style={{ fontSize:12, color:"var(--text-tertiary)", marginLeft:8 }}>{txn.notes}</span>}
                        </div>
                        <div style={{ textAlign:"right" }}>
                          <p style={{ margin:"0 0 1px", fontSize:13, fontWeight:600, color:"var(--text-primary)" }}>
                            {txn.quantity > 0 ? "+" : ""}{txn.quantity}
                          </p>
                          <p style={{ margin:0, fontSize:11, color:"var(--text-tertiary)" }}>
                            {txn.balance_before} → {txn.balance_after}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
            }
          </div>
        )}

        {/* ── Low Stock Tab ── */}
        {tab === "low" && (
          <div>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:16 }}>
              <span style={{ fontSize:13, color:"var(--text-secondary)" }}>
                Items below minimum quantity
              </span>
              <button onClick={lowStock.refetch}
                style={{ height:34, padding:"0 14px", borderRadius:"var(--radius-md)", border:"1px solid var(--border)",
                  background:"var(--surface)", color:"var(--text-secondary)", fontSize:13,
                  cursor:"pointer", fontFamily:"inherit" }}>
                Refresh
              </button>
            </div>
            {lowStock.loading && <p style={{ color:"var(--text-tertiary)", fontSize:13 }}>Loading…</p>}
            {lowStock.error  && <p style={{ color:"var(--danger)", fontSize:13 }}>{lowStock.error}</p>}
            {lowStock.data?.items.length === 0 && (
              <div style={{ textAlign:"center", padding:"40px 0" }}>
                <p style={{ fontSize:32, margin:"0 0 8px" }}>✅</p>
                <p style={{ fontSize:14, color:"var(--text-secondary)" }}>All items are adequately stocked.</p>
              </div>
            )}
            <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
              {lowStock.data?.items.map((item: LowStockItem) => (
                <div key={item.item_id}
                  style={{ background:"var(--surface)", border:"1px solid #ef444444",
                    borderLeft:"3px solid #ef4444",
                    borderRadius:10, padding:"14px 18px",
                    display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                  <div>
                    <p style={{ margin:"0 0 3px", fontWeight:600, fontSize:14, color:"var(--text-primary)" }}>
                      {item.name}
                    </p>
                    <p style={{ margin:0, fontSize:12, color:"var(--text-secondary)" }}>
                      On hand: <strong>{item.current_qty}</strong> ·
                      Min: {item.min_quantity} · Shortfall: <strong style={{ color:"#ef4444" }}>{item.deficit}</strong>
                    </p>
                  </div>
                  <button onClick={() => replenish(item.item_id, item.deficit)} disabled={replenishing}
                    style={{ padding:"7px 14px", borderRadius:"var(--radius-md)", border:"none",
                      background:"var(--accent)", color:"white", fontWeight:600, fontSize:12,
                      cursor:"pointer", fontFamily:"inherit", whiteSpace:"nowrap" }}>
                    {replenishing ? "…" : `Request +${item.deficit}`}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </TenantLayout>
  );
}
