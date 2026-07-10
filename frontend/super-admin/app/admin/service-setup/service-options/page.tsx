"use client";
import { useEffect, useState } from "react";
import { serviceOptionApi, ServiceOption34E } from "../../../../lib/api";
import { PageHeader } from "../../../../components/shared/layout";
import { Btn } from "../../../../components/shared/ui";

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  inactive: "bg-yellow-100 text-yellow-800",
  archived: "bg-gray-100 text-gray-500",
  deprecated: "bg-red-100 text-red-700",
  pending_review: "bg-blue-100 text-blue-700",
};

const STATUSES = ["", "active", "inactive", "archived", "deprecated", "pending_review"];

export default function ServiceOptionsPage() {
  const [items, setItems] = useState<ServiceOption34E[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    name: "", code: "", description: "", option_type: "add_on",
    unit: "per_unit", default_price: "0", vertical_type: "",
    is_customer_selectable: true,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [actionMsg, setActionMsg] = useState("");

  async function load() {
    setLoading(true);
    try {
      const res = await serviceOptionApi.listOptions({
        status: statusFilter || undefined,
        search: search || undefined,
        page_size: 100,
      });
      const d = res as unknown as { items: ServiceOption34E[]; total: number };
      setItems(d.items ?? []);
      setTotal(d.total ?? 0);
    } catch { /* ignore */ }
    setLoading(false);
  }

  useEffect(() => { load(); }, [statusFilter, search]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name) { setError("Name is required"); return; }
    setSaving(true); setError("");
    try {
      await serviceOptionApi.createOption(form);
      setShowCreate(false);
      setForm({ name: "", code: "", description: "", option_type: "add_on",
                unit: "per_unit", default_price: "0", vertical_type: "",
                is_customer_selectable: true });
      await load();
    } catch (err: unknown) {
      setError((err as Error).message ?? "Failed to create");
    }
    setSaving(false);
  }

  async function setStatus(opt: ServiceOption34E, newStatus: "activate" | "deactivate" | "archive") {
    try {
      if (newStatus === "activate") await serviceOptionApi.activateOption(opt.id);
      else if (newStatus === "deactivate") await serviceOptionApi.deactivateOption(opt.id);
      else await serviceOptionApi.archiveOption(opt.id);
      setActionMsg(`Option ${newStatus}d`);
      await load();
      setTimeout(() => setActionMsg(""), 2000);
    } catch { /* ignore */ }
  }

  return (
    <div className="page-root">
      <PageHeader
        title="Service Options"
        description={`${total} options — types and variants customers can select during booking`}
        primaryAction={<Btn onClick={() => setShowCreate(true)}>+ New Option</Btn>}
      />

      <div className="flex gap-3 mb-4 flex-wrap">
        <input
          className="form-input w-64"
          placeholder="Search options…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select className="form-input w-48" value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}>
          {STATUSES.map(s => (
            <option key={s} value={s}>{s === "" ? "All Statuses" : s}</option>
          ))}
        </select>
      </div>

      {actionMsg && <p className="text-green-600 text-sm mb-3">{actionMsg}</p>}

      {loading ? (
        <p className="body-text text-muted">Loading…</p>
      ) : items.length === 0 ? (
        <p className="body-text text-muted">No service options found.</p>
      ) : (
        <div className="card overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Code</th>
                <th>Type</th>
                <th>Vertical</th>
                <th>Status</th>
                <th>Customer</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map(opt => (
                <tr key={opt.id}>
                  <td className="font-medium">{opt.name}</td>
                  <td><code className="text-xs">{opt.code}</code></td>
                  <td className="text-sm text-muted">{opt.option_type}</td>
                  <td className="text-sm text-muted">{opt.vertical_type ?? "—"}</td>
                  <td>
                    <span className={`badge ${STATUS_COLORS[opt.status] ?? "bg-gray-100 text-gray-600"}`}>
                      {opt.status}
                    </span>
                  </td>
                  <td className="text-sm">{opt.is_customer_selectable ? "Yes" : "No"}</td>
                  <td>
                    <div className="flex gap-1">
                      {opt.status !== "active" && (
                        <button className="text-xs text-green-600 hover:underline"
                          onClick={() => setStatus(opt, "activate")}>Activate</button>
                      )}
                      {opt.status === "active" && (
                        <button className="text-xs text-yellow-600 hover:underline"
                          onClick={() => setStatus(opt, "deactivate")}>Deactivate</button>
                      )}
                      {opt.status !== "archived" && (
                        <button className="text-xs text-gray-500 hover:underline"
                          onClick={() => setStatus(opt, "archive")}>Archive</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <div className="modal-overlay">
          <div className="modal">
            <h2 className="section-title mb-4">New Service Option</h2>
            {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
            <form onSubmit={handleCreate} className="form-stack">
              <label className="form-label">
                Name <span className="text-red-500">*</span>
                <input className="form-input" value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="Split AC" />
              </label>
              <label className="form-label">
                Code
                <input className="form-input" value={form.code}
                  onChange={e => setForm(f => ({ ...f, code: e.target.value }))}
                  placeholder="split_ac" />
              </label>
              <label className="form-label">
                Description
                <textarea className="form-input" value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  rows={2} />
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="form-label">
                  Option Type
                  <select className="form-input" value={form.option_type}
                    onChange={e => setForm(f => ({ ...f, option_type: e.target.value }))}>
                    {["add_on", "upgrade", "material", "tool", "visit_fee", "equipment_type"].map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </label>
                <label className="form-label">
                  Vertical Type
                  <input className="form-input" value={form.vertical_type}
                    onChange={e => setForm(f => ({ ...f, vertical_type: e.target.value }))}
                    placeholder="home_service" />
                </label>
              </div>
              <label className="form-label">
                Default Price
                <input className="form-input" type="number" value={form.default_price}
                  onChange={e => setForm(f => ({ ...f, default_price: e.target.value }))} />
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={form.is_customer_selectable}
                  onChange={e => setForm(f => ({ ...f, is_customer_selectable: e.target.checked }))} />
                Customer selectable
              </label>
              <div className="flex gap-3 mt-4">
                <Btn type="submit" disabled={saving}>{saving ? "Saving…" : "Create"}</Btn>
                <Btn variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Btn>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
