"use client";
import { useEffect, useState } from "react";
import { serviceOptionApi, ServiceOptionGroup34E } from "../../../../lib/api";
import { PageHeader } from "../../../../components/shared/layout";
import { Btn } from "../../../../components/shared/ui";

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  inactive: "bg-yellow-100 text-yellow-800",
  archived: "bg-gray-100 text-gray-500",
};

export default function OptionGroupsPage() {
  const [groups, setGroups] = useState<ServiceOptionGroup34E[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ code: "", name: "", description: "", vertical_type: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    try {
      const res = await serviceOptionApi.listOptionGroups();
      setGroups((res as unknown as { data: ServiceOptionGroup34E[] }).data ?? (res as unknown as ServiceOptionGroup34E[]));
    } catch { /* ignore */ }
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.code || !form.name) { setError("Code and name are required"); return; }
    setSaving(true); setError("");
    try {
      await serviceOptionApi.createOptionGroup(form);
      setShowCreate(false);
      setForm({ code: "", name: "", description: "", vertical_type: "" });
      await load();
    } catch (err: unknown) {
      setError((err as Error).message ?? "Failed to create");
    }
    setSaving(false);
  }

  return (
    <div className="page-root">
      <PageHeader
        title="Option Groups"
        description="Logical groupings for service options (e.g. AC Type, Washer Type)"
        primaryAction={<Btn onClick={() => setShowCreate(true)}>+ New Group</Btn>}
      />

      {loading ? (
        <p className="body-text text-muted">Loading…</p>
      ) : groups.length === 0 ? (
        <p className="body-text text-muted">No option groups yet.</p>
      ) : (
        <div className="card">
          <table className="data-table">
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Vertical</th>
                <th>Status</th>
                <th>Order</th>
              </tr>
            </thead>
            <tbody>
              {groups.map(g => (
                <tr key={g.id}>
                  <td><code className="text-xs">{g.code}</code></td>
                  <td className="font-medium">{g.name}</td>
                  <td className="text-sm text-muted">{g.vertical_type ?? "—"}</td>
                  <td>
                    <span className={`badge ${STATUS_COLORS[g.status] ?? "bg-gray-100 text-gray-600"}`}>
                      {g.status}
                    </span>
                  </td>
                  <td className="text-sm text-muted">{g.display_order}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <div className="modal-overlay">
          <div className="modal">
            <h2 className="section-title mb-4">New Option Group</h2>
            {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
            <form onSubmit={handleCreate} className="form-stack">
              <label className="form-label">
                Code <span className="text-red-500">*</span>
                <input className="form-input" value={form.code}
                  onChange={e => setForm(f => ({ ...f, code: e.target.value }))}
                  placeholder="ac_type" />
              </label>
              <label className="form-label">
                Name <span className="text-red-500">*</span>
                <input className="form-input" value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="AC Type" />
              </label>
              <label className="form-label">
                Description
                <textarea className="form-input" value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  rows={2} />
              </label>
              <label className="form-label">
                Vertical Type
                <input className="form-input" value={form.vertical_type}
                  onChange={e => setForm(f => ({ ...f, vertical_type: e.target.value }))}
                  placeholder="home_service" />
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
