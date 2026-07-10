"use client";
import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  staffQuoteApi, QuoteRecord, QuoteItemRecord,
} from "../../../../../lib/api";

const ITEM_TYPES = ["labour", "part", "material", "service", "visit_charge", "discount", "tax", "other"];
const QUOTE_TYPES = ["repair_quote", "parts_quote", "additional_work_quote", "inspection_quote"];

const STATUS_COLORS: Record<string, string> = {
  draft:                 "#6b7280",
  sent_to_customer:      "#2563eb",
  customer_approved:     "#16a34a",
  customer_rejected:     "#dc2626",
  revision_requested:    "#d97706",
  cancelled:             "#6b7280",
};

export default function ServiceJobQuotesPage() {
  const params = useParams();
  const jobId = params.id as string;

  const [quotes, setQuotes]     = useState<QuoteRecord[]>([]);
  const [selected, setSelected] = useState<QuoteRecord | null>(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState("");

  // Create quote form
  const [quoteType, setQuoteType]   = useState("repair_quote");
  const [notes, setNotes]           = useState("");
  const [creating, setCreating]     = useState(false);

  // Add item form
  const [showAddItem, setShowAddItem] = useState(false);
  const [newItem, setNewItem] = useState({
    item_type: "labour", item_name: "", item_description: "",
    quantity: "1", unit_price: "0", is_customer_visible: true,
  });
  const [addingItem, setAddingItem] = useState(false);

  // Send to customer
  const [showSend, setShowSend]         = useState(false);
  const [customerNotes, setCustomerNotes] = useState("");
  const [sending, setSending]           = useState(false);

  const loadQuotes = useCallback(async () => {
    try {
      const data = await staffQuoteApi.listForJob(jobId);
      setQuotes(data);
      if (data.length > 0 && !selected) {
        const full = await staffQuoteApi.get(data[0].id);
        setSelected(full);
      } else if (selected) {
        const full = await staffQuoteApi.get(selected.id);
        setSelected(full);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load quotes");
    } finally {
      setLoading(false);
    }
  }, [jobId, selected?.id]);

  useEffect(() => { loadQuotes(); }, [jobId]);

  async function createQuote() {
    setCreating(true);
    try {
      const q = await staffQuoteApi.create(jobId, quoteType, notes || undefined);
      setQuotes(prev => [q, ...prev]);
      const full = await staffQuoteApi.get(q.id);
      setSelected(full);
      setNotes("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create quote");
    } finally {
      setCreating(false);
    }
  }

  async function addItem() {
    if (!selected || !newItem.item_name.trim()) return;
    setAddingItem(true);
    try {
      await staffQuoteApi.addItem(selected.id, {
        item_type: newItem.item_type,
        item_name: newItem.item_name,
        item_description: newItem.item_description || undefined,
        quantity: parseFloat(newItem.quantity),
        unit_price: parseFloat(newItem.unit_price),
        is_customer_visible: newItem.is_customer_visible,
      });
      setShowAddItem(false);
      setNewItem({ item_type: "labour", item_name: "", item_description: "", quantity: "1", unit_price: "0", is_customer_visible: true });
      const full = await staffQuoteApi.get(selected.id);
      setSelected(full);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to add item");
    } finally {
      setAddingItem(false);
    }
  }

  async function removeItem(itemId: string) {
    if (!selected) return;
    try {
      await staffQuoteApi.removeItem(selected.id, itemId);
      const full = await staffQuoteApi.get(selected.id);
      setSelected(full);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to remove item");
    }
  }

  async function sendToCustomer() {
    if (!selected) return;
    setSending(true);
    try {
      const updated = await staffQuoteApi.sendToCustomer(selected.id, customerNotes || undefined);
      setSelected(updated);
      setShowSend(false);
      setCustomerNotes("");
      await loadQuotes();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to send quote");
    } finally {
      setSending(false);
    }
  }

  async function cancelQuote() {
    if (!selected) return;
    if (!confirm("Cancel this quote?")) return;
    try {
      const updated = await staffQuoteApi.cancel(selected.id, "Cancelled by provider");
      setSelected(updated);
      await loadQuotes();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to cancel");
    }
  }

  const isEditable = selected?.status === "draft" || selected?.status === "revision_requested" || selected?.status === "revised";

  if (loading) return <div style={{ padding: 32 }}>Loading quotes...</div>;

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Quote Builder</h1>
        <a href={`/service-jobs/${jobId}`} style={{ color: "#6366f1", textDecoration: "none", fontSize: 14 }}>
          ← Back to Job
        </a>
      </div>

      {error && (
        <div style={{ background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: 6, padding: 12, marginBottom: 16, color: "#dc2626" }}>
          {error}
          <button onClick={() => setError("")} style={{ float: "right", background: "none", border: "none", cursor: "pointer" }}>×</button>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 20 }}>
        {/* Left: Quote list + create */}
        <div>
          <div style={{ background: "white", border: "1px solid #e5e7eb", borderRadius: 8, padding: 16, marginBottom: 16 }}>
            <div style={{ fontWeight: 600, marginBottom: 12 }}>Create New Quote</div>
            <select
              value={quoteType}
              onChange={(e) => setQuoteType(e.target.value)}
              style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: 6, padding: "6px 8px", marginBottom: 8, fontSize: 13 }}
            >
              {QUOTE_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </select>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Internal notes (optional)"
              rows={2}
              style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: 6, padding: 8, fontSize: 13, boxSizing: "border-box", marginBottom: 8 }}
            />
            <button
              onClick={createQuote}
              disabled={creating}
              style={{ width: "100%", background: "#6366f1", color: "white", border: "none", borderRadius: 6, padding: "8px 0", cursor: "pointer", fontWeight: 600 }}
            >
              {creating ? "Creating..." : "Create Quote"}
            </button>
          </div>

          <div style={{ background: "white", border: "1px solid #e5e7eb", borderRadius: 8, padding: 16 }}>
            <div style={{ fontWeight: 600, marginBottom: 12 }}>Quotes ({quotes.length})</div>
            {quotes.length === 0 ? (
              <div style={{ color: "#9ca3af", fontSize: 13 }}>No quotes yet.</div>
            ) : (
              quotes.map(q => (
                <div
                  key={q.id}
                  onClick={() => staffQuoteApi.get(q.id).then(setSelected)}
                  style={{
                    padding: "8px 10px", borderRadius: 6, marginBottom: 6, cursor: "pointer",
                    background: selected?.id === q.id ? "#f0f9ff" : "#f9fafb",
                    border: selected?.id === q.id ? "1px solid #6366f1" : "1px solid #e5e7eb",
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{q.quote_number}</div>
                  <div style={{ fontSize: 11, color: STATUS_COLORS[q.status] || "#6b7280", marginTop: 2 }}>
                    {q.status.replace(/_/g, " ")}
                  </div>
                  <div style={{ fontSize: 12, color: "#374151" }}>₹{q.total_amount}</div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Quote detail */}
        {selected ? (
          <div>
            {/* Header */}
            <div style={{ background: "white", border: "1px solid #e5e7eb", borderRadius: 8, padding: 16, marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{selected.quote_number}</div>
                  <div style={{ color: STATUS_COLORS[selected.status] || "#6b7280", fontWeight: 600, marginTop: 4 }}>
                    {selected.status.replace(/_/g, " ")}
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  {isEditable && (
                    <button
                      onClick={() => setShowSend(true)}
                      style={{ background: "#16a34a", color: "white", border: "none", borderRadius: 6, padding: "8px 14px", cursor: "pointer", fontWeight: 600, fontSize: 13 }}
                    >
                      Send to Customer
                    </button>
                  )}
                  {["draft", "revision_requested"].includes(selected.status) && (
                    <button
                      onClick={cancelQuote}
                      style={{ background: "white", color: "#dc2626", border: "1px solid #dc2626", borderRadius: 6, padding: "8px 14px", cursor: "pointer", fontSize: 13 }}
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </div>

              {/* Totals */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginTop: 16 }}>
                {[
                  ["Labour",    selected.labour_amount],
                  ["Parts",     selected.parts_amount],
                  ["Discount",  selected.discount_amount],
                  ["Total",     selected.total_amount],
                ].map(([label, val]) => (
                  <div key={label} style={{ background: "#f9fafb", borderRadius: 6, padding: "8px 12px", textAlign: "center" }}>
                    <div style={{ fontSize: 11, color: "#6b7280" }}>{label}</div>
                    <div style={{ fontSize: 16, fontWeight: 700 }}>₹{parseFloat(val as string).toFixed(2)}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Items */}
            <div style={{ background: "white", border: "1px solid #e5e7eb", borderRadius: 8, padding: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div style={{ fontWeight: 600 }}>Line Items</div>
                {isEditable && (
                  <button
                    onClick={() => setShowAddItem(true)}
                    style={{ background: "#6366f1", color: "white", border: "none", borderRadius: 6, padding: "6px 12px", cursor: "pointer", fontSize: 13 }}
                  >
                    + Add Item
                  </button>
                )}
              </div>

              {(!selected.items || selected.items.length === 0) ? (
                <div style={{ color: "#9ca3af", fontSize: 13, padding: "20px 0", textAlign: "center" }}>
                  No items yet. Add line items to build the quote.
                </div>
              ) : (
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: "#f9fafb" }}>
                      <th style={{ padding: "8px 10px", textAlign: "left", fontWeight: 600 }}>Item</th>
                      <th style={{ padding: "8px 10px", textAlign: "left", fontWeight: 600 }}>Type</th>
                      <th style={{ padding: "8px 10px", textAlign: "right", fontWeight: 600 }}>Qty</th>
                      <th style={{ padding: "8px 10px", textAlign: "right", fontWeight: 600 }}>Unit Price</th>
                      <th style={{ padding: "8px 10px", textAlign: "right", fontWeight: 600 }}>Total</th>
                      {isEditable && <th style={{ padding: "8px 10px" }}></th>}
                    </tr>
                  </thead>
                  <tbody>
                    {selected.items!.map((item: QuoteItemRecord) => (
                      <tr key={item.id} style={{ borderTop: "1px solid #f3f4f6" }}>
                        <td style={{ padding: "8px 10px" }}>
                          <div style={{ fontWeight: 500 }}>{item.item_name}</div>
                          {item.item_description && <div style={{ color: "#6b7280", fontSize: 11 }}>{item.item_description}</div>}
                        </td>
                        <td style={{ padding: "8px 10px", color: "#6b7280" }}>{item.item_type}</td>
                        <td style={{ padding: "8px 10px", textAlign: "right" }}>{parseFloat(item.quantity).toFixed(1)}</td>
                        <td style={{ padding: "8px 10px", textAlign: "right" }}>₹{parseFloat(item.unit_price).toFixed(2)}</td>
                        <td style={{ padding: "8px 10px", textAlign: "right", fontWeight: 600 }}>₹{parseFloat(item.line_total).toFixed(2)}</td>
                        {isEditable && (
                          <td style={{ padding: "8px 10px", textAlign: "center" }}>
                            <button
                              onClick={() => removeItem(item.id)}
                              style={{ background: "none", border: "none", cursor: "pointer", color: "#dc2626", fontSize: 16 }}
                            >
                              ×
                            </button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", color: "#9ca3af", fontSize: 15 }}>
            Select or create a quote to get started.
          </div>
        )}
      </div>

      {/* Add Item Modal */}
      {showAddItem && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "white", borderRadius: 8, padding: 24, width: 460, maxWidth: "90%" }}>
            <h3 style={{ margin: "0 0 16px" }}>Add Line Item</h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
              <div>
                <label style={{ fontSize: 12, color: "#6b7280" }}>Type</label>
                <select
                  value={newItem.item_type}
                  onChange={(e) => setNewItem(p => ({ ...p, item_type: e.target.value }))}
                  style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: 6, padding: "6px 8px", marginTop: 4 }}
                >
                  {ITEM_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, color: "#6b7280" }}>Item Name *</label>
                <input
                  value={newItem.item_name}
                  onChange={(e) => setNewItem(p => ({ ...p, item_name: e.target.value }))}
                  placeholder="e.g. Compressor repair"
                  style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: 6, padding: "6px 8px", marginTop: 4, boxSizing: "border-box" }}
                />
              </div>
              <div>
                <label style={{ fontSize: 12, color: "#6b7280" }}>Quantity</label>
                <input
                  type="number" min="0.001" step="0.5"
                  value={newItem.quantity}
                  onChange={(e) => setNewItem(p => ({ ...p, quantity: e.target.value }))}
                  style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: 6, padding: "6px 8px", marginTop: 4, boxSizing: "border-box" }}
                />
              </div>
              <div>
                <label style={{ fontSize: 12, color: "#6b7280" }}>Unit Price (₹)</label>
                <input
                  type="number" min="0" step="0.5"
                  value={newItem.unit_price}
                  onChange={(e) => setNewItem(p => ({ ...p, unit_price: e.target.value }))}
                  style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: 6, padding: "6px 8px", marginTop: 4, boxSizing: "border-box" }}
                />
              </div>
            </div>
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: "#6b7280" }}>Description (optional)</label>
              <input
                value={newItem.item_description}
                onChange={(e) => setNewItem(p => ({ ...p, item_description: e.target.value }))}
                style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: 6, padding: "6px 8px", marginTop: 4, boxSizing: "border-box" }}
              />
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, marginBottom: 16 }}>
              <input
                type="checkbox"
                checked={newItem.is_customer_visible}
                onChange={(e) => setNewItem(p => ({ ...p, is_customer_visible: e.target.checked }))}
              />
              Visible to customer
            </label>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button onClick={() => setShowAddItem(false)} style={{ padding: "8px 16px", border: "1px solid #d1d5db", borderRadius: 6, cursor: "pointer" }}>Cancel</button>
              <button
                onClick={addItem}
                disabled={addingItem || !newItem.item_name.trim()}
                style={{ background: "#6366f1", color: "white", border: "none", borderRadius: 6, padding: "8px 16px", cursor: "pointer", fontWeight: 600 }}
              >
                {addingItem ? "Adding..." : "Add Item"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Send to Customer Modal */}
      {showSend && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "white", borderRadius: 8, padding: 24, width: 420, maxWidth: "90%" }}>
            <h3 style={{ margin: "0 0 12px" }}>Send Quote to Customer</h3>
            <p style={{ color: "#6b7280", fontSize: 14, marginBottom: 12 }}>
              Total: <strong>₹{parseFloat(selected?.total_amount || "0").toFixed(2)}</strong> ({selected?.quote_number})
            </p>
            <textarea
              value={customerNotes}
              onChange={(e) => setCustomerNotes(e.target.value)}
              placeholder="Notes for customer (optional)"
              rows={3}
              style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: 6, padding: 8, boxSizing: "border-box", marginBottom: 12 }}
            />
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button onClick={() => setShowSend(false)} style={{ padding: "8px 16px", border: "1px solid #d1d5db", borderRadius: 6, cursor: "pointer" }}>Cancel</button>
              <button
                onClick={sendToCustomer}
                disabled={sending}
                style={{ background: "#16a34a", color: "white", border: "none", borderRadius: 6, padding: "8px 16px", cursor: "pointer", fontWeight: 600 }}
              >
                {sending ? "Sending..." : "Send to Customer"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
