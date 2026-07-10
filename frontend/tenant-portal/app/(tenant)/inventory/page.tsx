"use client";
import React, { useState, useCallback } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { useApi, useAction } from "../../../hooks/useApi";
import {
  inventoryApi,
  type InventoryItem,
  type LowStockItem,
  type StockTransaction,
} from "../../../lib/api";

type Tab = "items" | "stock" | "low";

export default function InventoryPage() {
  const [tab, setTab] = useState<Tab>("items");

  // ── Items tab ────────────────────────────────────────────────────────────
  const [showCreate, setShowCreate] = useState(false);
  const [newItem, setNewItem] = useState({ name:"", sku:"", unit:"pcs", unit_cost:"", category:"", min_quantity:"0" });
  const { execute: createItem, loading: creating, error: createError } = useAction(
    useCallback(async () => {
      const res = await inventoryApi.createItem(
        newItem.name, newItem.sku, newItem.unit,
        parseFloat(newItem.unit_cost) || 0,
        newItem.category || undefined,
        parseInt(newItem.min_quantity) || 0,
      );
      if (res) { setShowCreate(false); setNewItem({ name:"", sku:"", unit:"pcs", unit_cost:"", category:"", min_quantity:"0" }); itemList.refetch(); }
      return res;
    }, [newItem]) // eslint-disable-line react-hooks/exhaustive-deps
  );

  const itemList = useApi(
    useCallback(() => inventoryApi.listItems(), []),
    []
  );

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
    receive:"#10b981", consume:"#ef4444", adjust:"#f59e0b",
    reserve:"#8b5cf6", release:"#3b82f6",
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
              style={{ padding:"8px 18px", borderRadius:8,
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
              <button onClick={() => setShowCreate(p => !p)}
                style={{ padding:"8px 16px", borderRadius:8, border:"none",
                  background:"var(--accent)", color:"white", fontWeight:600, fontSize:13,
                  cursor:"pointer", fontFamily:"inherit" }}>
                + New Item
              </button>
            </div>

            {showCreate && (
              <div style={{ background:"var(--surface)", border:"1px solid var(--border)",
                borderRadius:12, padding:"18px 20px", marginBottom:20, maxWidth:480 }}>
                <h3 style={{ margin:"0 0 14px", fontSize:15, fontWeight:600, color:"var(--text-primary)" }}>
                  Create Item
                </h3>
                {createError && <p style={{ color:"var(--danger)", fontSize:12, marginBottom:10 }}>{createError}</p>}
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10 }}>
                  {[
                    ["name","Name *","text"],
                    ["sku","SKU *","text"],
                    ["unit","Unit *","text"],
                    ["unit_cost","Unit Cost (₹) *","number"],
                    ["category","Category","text"],
                    ["min_quantity","Min Qty","number"],
                  ].map(([key, label, type]) => (
                    <div key={key}>
                      <label style={{ fontSize:11, color:"var(--text-secondary)", display:"block", marginBottom:3 }}>
                        {label}
                      </label>
                      <input type={type} value={newItem[key as keyof typeof newItem]}
                        onChange={e => setNewItem(p => ({ ...p, [key]:e.target.value }))}
                        style={{ width:"100%", height:34, padding:"0 9px", borderRadius:7,
                          border:"1px solid var(--border)", background:"var(--surface)",
                          color:"var(--text-primary)", fontSize:12, fontFamily:"inherit",
                          boxSizing:"border-box" }}/>
                    </div>
                  ))}
                </div>
                <div style={{ display:"flex", gap:8, marginTop:14 }}>
                  <button onClick={() => createItem()} disabled={creating || !newItem.name || !newItem.sku}
                    style={{ padding:"8px 18px", borderRadius:8, border:"none",
                      background:"var(--accent)", color:"white", fontWeight:600, fontSize:13,
                      cursor:"pointer", fontFamily:"inherit",
                      opacity:(!newItem.name || !newItem.sku) ? 0.5 : 1 }}>
                    {creating ? "Creating…" : "Create"}
                  </button>
                  <button onClick={() => setShowCreate(false)}
                    style={{ padding:"8px 14px", borderRadius:8, border:"1px solid var(--border)",
                      background:"transparent", color:"var(--text-secondary)", fontSize:13,
                      cursor:"pointer", fontFamily:"inherit" }}>
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {itemList.loading && <p style={{ color:"var(--text-tertiary)", fontSize:13 }}>Loading…</p>}
            {itemList.error  && <p style={{ color:"var(--danger)", fontSize:13 }}>{itemList.error}</p>}
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(280px,1fr))", gap:10 }}>
              {itemList.data?.items.map((item: InventoryItem) => (
                <div key={item.item_id}
                  style={{ background:"var(--surface)", border:"1px solid var(--border)",
                    borderRadius:12, padding:"14px 16px" }}>
                  <div style={{ display:"flex", justifyContent:"space-between" }}>
                    <p style={{ margin:"0 0 3px", fontWeight:600, fontSize:14, color:"var(--text-primary)" }}>
                      {item.name}
                    </p>
                    <span style={{ fontSize:11, color:"var(--text-tertiary)" }}>{item.sku}</span>
                  </div>
                  <p style={{ margin:"0 0 6px", fontSize:12, color:"var(--text-secondary)" }}>
                    {item.category ?? "—"} · {item.unit} · ₹{item.unit_cost}
                  </p>
                  <p style={{ margin:0, fontSize:11, color:"var(--text-tertiary)" }}>
                    Min qty: {item.min_quantity}
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
                style={{ height:36, padding:"0 10px", borderRadius:8, width:220,
                  border:"1px solid var(--border)", background:"var(--surface)",
                  color:"var(--text-primary)", fontSize:13, fontFamily:"inherit" }}/>
              <input value={stockLocId} onChange={e => setStockLocId(e.target.value)}
                placeholder="Location UUID"
                style={{ height:36, padding:"0 10px", borderRadius:8, width:220,
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
                        ["Available", balance.data.available],
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
                    borderRadius:12, padding:"16px 18px", maxWidth:400, marginBottom:20 }}>
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
                style={{ height:34, padding:"0 14px", borderRadius:8, border:"1px solid var(--border)",
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
                      On hand: <strong>{item.current_quantity}</strong> · Reserved: {item.reserved_qty} ·
                      Min: {item.min_quantity} · Shortfall: <strong style={{ color:"#ef4444" }}>{item.shortfall}</strong>
                    </p>
                  </div>
                  <button onClick={() => replenish(item.item_id, item.shortfall)} disabled={replenishing}
                    style={{ padding:"7px 14px", borderRadius:8, border:"none",
                      background:"var(--accent)", color:"white", fontWeight:600, fontSize:12,
                      cursor:"pointer", fontFamily:"inherit", whiteSpace:"nowrap" }}>
                    {replenishing ? "…" : `Request +${item.shortfall}`}
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
