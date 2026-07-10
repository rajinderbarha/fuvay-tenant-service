"use client";
import { useState, useEffect } from "react";
import { adminChecklistTemplateApi, ChecklistTemplateRecord, ChecklistTemplateItemRecord } from "../../../lib/api";

const TEMPLATE_TYPES = ["inspection", "repair", "installation", "completion", "safety", "quality"];
const INPUT_TYPES    = ["checkbox", "text", "number", "photo", "select"];
const APPLIES_TO     = ["global", "category", "offering", "tenant"];

export default function ChecklistTemplatesPage() {
  const [templates, setTemplates] = useState<ChecklistTemplateRecord[]>([]);
  const [selected,  setSelected]  = useState<ChecklistTemplateRecord | null>(null);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ template_name: "", template_type: "inspection", applies_to: "global", is_required: false });
  const [creating, setCreating]    = useState(false);

  const [showAddItem, setShowAddItem] = useState(false);
  const [newItemForm, setNewItemForm] = useState({ item_label: "", input_type: "checkbox", is_required: false, sort_order: "0" });
  const [addingItem, setAddingItem]  = useState(false);

  async function load() {
    try {
      const data = await adminChecklistTemplateApi.list();
      setTemplates(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function selectTemplate(t: ChecklistTemplateRecord) {
    try {
      const full = await adminChecklistTemplateApi.get(t.id);
      setSelected(full);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load template");
    }
  }

  async function createTemplate() {
    setCreating(true);
    try {
      const t = await adminChecklistTemplateApi.create({ ...form });
      setTemplates(prev => [t, ...prev]);
      setSelected(t);
      setShowCreate(false);
      setForm({ template_name: "", template_type: "inspection", applies_to: "global", is_required: false });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create");
    } finally {
      setCreating(false);
    }
  }

  async function addItem() {
    if (!selected || !newItemForm.item_label.trim()) return;
    setAddingItem(true);
    try {
      await adminChecklistTemplateApi.addItem(selected.id, {
        ...newItemForm,
        sort_order: parseInt(newItemForm.sort_order),
      });
      const full = await adminChecklistTemplateApi.get(selected.id);
      setSelected(full);
      setShowAddItem(false);
      setNewItemForm({ item_label: "", input_type: "checkbox", is_required: false, sort_order: "0" });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to add item");
    } finally {
      setAddingItem(false);
    }
  }

  if (loading) return <div style={{ padding: 32 }}>Loading checklist templates...</div>;

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Checklist Templates</h1>
        <button
          onClick={() => setShowCreate(true)}
          style={{ background: "#6366f1", color: "white", border: "none", borderRadius: 6, padding: "8px 16px", cursor: "pointer", fontWeight: 600 }}
        >
          + New Template
        </button>
      </div>

      {error && (
        <div style={{ background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: 6, padding: 12, marginBottom: 16, color: "#dc2626" }}>
          {error}
          <button onClick={() => setError("")} style={{ float: "right", background: "none", border: "none", cursor: "pointer" }}>×</button>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 20 }}>
        {/* Template list */}
        <div style={{ background: "white", border: "1px solid #e5e7eb", borderRadius: 8, padding: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>Templates ({templates.length})</div>
          {templates.length === 0 ? (
            <div style={{ color: "#9ca3af", fontSize: 13 }}>No templates yet.</div>
          ) : (
            templates.map(t => (
              <div
                key={t.id}
                onClick={() => selectTemplate(t)}
                style={{
                  padding: "8px 10px", borderRadius: 6, marginBottom: 6, cursor: "pointer",
                  background: selected?.id === t.id ? "#f0f9ff" : "#f9fafb",
                  border: selected?.id === t.id ? "1px solid #6366f1" : "1px solid #e5e7eb",
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 13 }}>{t.template_name}</div>
                <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
                  {t.template_type} · {t.applies_to}
                  {t.is_required && <span style={{ color: "#dc2626", marginLeft: 4 }}>required</span>}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Template detail */}
        {selected ? (
          <div>
            <div style={{ background: "white", border: "1px solid #e5e7eb", borderRadius: 8, padding: 16, marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>{selected.template_name}</h2>
                  <div style={{ color: "#6b7280", fontSize: 13, marginTop: 4 }}>
                    Type: <strong>{selected.template_type}</strong> · Applies to: <strong>{selected.applies_to}</strong>
                    {selected.is_required && <span style={{ color: "#dc2626", marginLeft: 8 }}>Required</span>}
                  </div>
                </div>
                <button
                  onClick={() => setShowAddItem(true)}
                  style={{ background: "#6366f1", color: "white", border: "none", borderRadius: 6, padding: "6px 12px", cursor: "pointer", fontSize: 13 }}
                >
                  + Add Item
                </button>
              </div>
            </div>

            <div style={{ background: "white", border: "1px solid #e5e7eb", borderRadius: 8, padding: 16 }}>
              <div style={{ fontWeight: 600, marginBottom: 12 }}>
                Checklist Items ({(selected.items || []).length})
              </div>
              {(!selected.items || selected.items.length === 0) ? (
                <div style={{ color: "#9ca3af", fontSize: 13, padding: "20px 0", textAlign: "center" }}>
                  No items yet. Add checklist items.
                </div>
              ) : (
                <div>
                  {selected.items!
                    .sort((a: ChecklistTemplateItemRecord, b: ChecklistTemplateItemRecord) => a.sort_order - b.sort_order)
                    .map((item: ChecklistTemplateItemRecord, idx: number) => (
                    <div key={item.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 0", borderBottom: "1px solid #f3f4f6" }}>
                      <div style={{ color: "#9ca3af", fontSize: 12, minWidth: 24 }}>{idx + 1}</div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 500, fontSize: 14 }}>{item.item_label}</div>
                        <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
                          Input: {item.input_type} {item.is_required && <span style={{ color: "#dc2626" }}>· required</span>}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", color: "#9ca3af" }}>
            Select a template to view or edit items.
          </div>
        )}
      </div>

      {/* Create Template Modal */}
      {showCreate && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "white", borderRadius: 8, padding: 24, width: 420, maxWidth: "90%" }}>
            <h3 style={{ margin: "0 0 16px" }}>New Checklist Template</h3>
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: "#6b7280" }}>Template Name *</label>
              <input
                value={form.template_name}
                onChange={(e) => setForm(p => ({ ...p, template_name: e.target.value }))}
                style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: 6, padding: "6px 8px", marginTop: 4, boxSizing: "border-box" }}
              />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
              <div>
                <label style={{ fontSize: 12, color: "#6b7280" }}>Type</label>
                <select
                  value={form.template_type}
                  onChange={(e) => setForm(p => ({ ...p, template_type: e.target.value }))}
                  style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: 6, padding: "6px 8px", marginTop: 4 }}
                >
                  {TEMPLATE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, color: "#6b7280" }}>Applies To</label>
                <select
                  value={form.applies_to}
                  onChange={(e) => setForm(p => ({ ...p, applies_to: e.target.value }))}
                  style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: 6, padding: "6px 8px", marginTop: 4 }}
                >
                  {APPLIES_TO.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, marginBottom: 16 }}>
              <input type="checkbox" checked={form.is_required} onChange={(e) => setForm(p => ({ ...p, is_required: e.target.checked }))} />
              Required checklist
            </label>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button onClick={() => setShowCreate(false)} style={{ padding: "8px 16px", border: "1px solid #d1d5db", borderRadius: 6, cursor: "pointer" }}>Cancel</button>
              <button
                onClick={createTemplate}
                disabled={creating || !form.template_name.trim()}
                style={{ background: "#6366f1", color: "white", border: "none", borderRadius: 6, padding: "8px 16px", cursor: "pointer", fontWeight: 600 }}
              >
                {creating ? "Creating..." : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Item Modal */}
      {showAddItem && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "white", borderRadius: 8, padding: 24, width: 400, maxWidth: "90%" }}>
            <h3 style={{ margin: "0 0 16px" }}>Add Checklist Item</h3>
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: "#6b7280" }}>Item Label *</label>
              <input
                value={newItemForm.item_label}
                onChange={(e) => setNewItemForm(p => ({ ...p, item_label: e.target.value }))}
                placeholder="e.g. Check filter condition"
                style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: 6, padding: "6px 8px", marginTop: 4, boxSizing: "border-box" }}
              />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
              <div>
                <label style={{ fontSize: 12, color: "#6b7280" }}>Input Type</label>
                <select
                  value={newItemForm.input_type}
                  onChange={(e) => setNewItemForm(p => ({ ...p, input_type: e.target.value }))}
                  style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: 6, padding: "6px 8px", marginTop: 4 }}
                >
                  {INPUT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, color: "#6b7280" }}>Sort Order</label>
                <input
                  type="number" min="0"
                  value={newItemForm.sort_order}
                  onChange={(e) => setNewItemForm(p => ({ ...p, sort_order: e.target.value }))}
                  style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: 6, padding: "6px 8px", marginTop: 4, boxSizing: "border-box" }}
                />
              </div>
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, marginBottom: 16 }}>
              <input type="checkbox" checked={newItemForm.is_required} onChange={(e) => setNewItemForm(p => ({ ...p, is_required: e.target.checked }))} />
              Required item
            </label>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button onClick={() => setShowAddItem(false)} style={{ padding: "8px 16px", border: "1px solid #d1d5db", borderRadius: 6, cursor: "pointer" }}>Cancel</button>
              <button
                onClick={addItem}
                disabled={addingItem || !newItemForm.item_label.trim()}
                style={{ background: "#6366f1", color: "white", border: "none", borderRadius: 6, padding: "8px 16px", cursor: "pointer", fontWeight: 600 }}
              >
                {addingItem ? "Adding..." : "Add Item"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
