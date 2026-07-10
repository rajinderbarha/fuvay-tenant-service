"use client";
import { useEffect, useState } from "react";
import { serviceOptionApi, IssueType34E } from "../../../../lib/api";
import { PageHeader } from "../../../../components/shared/layout";
import { Btn } from "../../../../components/shared/ui";

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  inactive: "bg-yellow-100 text-yellow-800",
  archived: "bg-gray-100 text-gray-500",
  deprecated: "bg-red-100 text-red-700",
  pending_review: "bg-blue-100 text-blue-700",
};

const SEVERITIES = ["low", "medium", "high", "urgent"];
const STATUSES = ["", "active", "inactive", "archived", "deprecated"];

export default function IssueTypesPage() {
  const [items, setItems] = useState<IssueType34E[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    name: "", code: "", description: "", severity: "medium",
    vertical_type: "", requires_photo: false, requires_description: false,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [actionMsg, setActionMsg] = useState("");

  async function load() {
    setLoading(true);
    try {
      const res = await serviceOptionApi.listIssueTypes({
        status: statusFilter || undefined,
        search: search || undefined,
        page_size: 100,
      });
      const d = res as unknown as { items: IssueType34E[]; total: number };
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
      await serviceOptionApi.createIssueType({
        ...form, severity_default: form.severity,
      } as Parameters<typeof serviceOptionApi.createIssueType>[0]);
      setShowCreate(false);
      setForm({ name: "", code: "", description: "", severity: "medium",
                vertical_type: "", requires_photo: false, requires_description: false });
      await load();
    } catch (err: unknown) {
      setError((err as Error).message ?? "Failed to create");
    }
    setSaving(false);
  }

  async function setStatus(it: IssueType34E, action: "activate" | "deactivate" | "archive") {
    try {
      if (action === "activate") await serviceOptionApi.activateIssueType(it.id);
      else if (action === "deactivate") await serviceOptionApi.deactivateIssueType(it.id);
      else await serviceOptionApi.archiveIssueType(it.id);
      setActionMsg(`Issue type ${action}d`);
      await load();
      setTimeout(() => setActionMsg(""), 2000);
    } catch { /* ignore */ }
  }

  return (
    <div className="page-root">
      <PageHeader
        title="Issue Types"
        description={`${total} issue types — problem categories customers report during booking`}
        primaryAction={<Btn onClick={() => setShowCreate(true)}>+ New Issue Type</Btn>}
      />

      <div className="flex gap-3 mb-4 flex-wrap">
        <input className="form-input w-64" placeholder="Search issue types…"
          value={search} onChange={e => setSearch(e.target.value)} />
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
        <p className="body-text text-muted">No issue types found.</p>
      ) : (
        <div className="card overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Code</th>
                <th>Severity</th>
                <th>Vertical</th>
                <th>Photo</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map(it => (
                <tr key={it.id}>
                  <td className="font-medium">{it.name}</td>
                  <td><code className="text-xs">{it.code}</code></td>
                  <td>
                    <span className={`badge text-xs ${
                      it.severity === "urgent" ? "bg-red-100 text-red-800" :
                      it.severity === "high"   ? "bg-orange-100 text-orange-800" :
                      it.severity === "medium" ? "bg-yellow-100 text-yellow-800" :
                                                 "bg-gray-100 text-gray-600"
                    }`}>{it.severity}</span>
                  </td>
                  <td className="text-sm text-muted">{it.vertical_type ?? "—"}</td>
                  <td className="text-sm">{it.requires_photo ? "📷" : "—"}</td>
                  <td>
                    <span className={`badge ${STATUS_COLORS[it.status] ?? "bg-gray-100 text-gray-600"}`}>
                      {it.status}
                    </span>
                  </td>
                  <td>
                    <div className="flex gap-1">
                      {it.status !== "active" && (
                        <button className="text-xs text-green-600 hover:underline"
                          onClick={() => setStatus(it, "activate")}>Activate</button>
                      )}
                      {it.status === "active" && (
                        <button className="text-xs text-yellow-600 hover:underline"
                          onClick={() => setStatus(it, "deactivate")}>Deactivate</button>
                      )}
                      {it.status !== "archived" && (
                        <button className="text-xs text-gray-500 hover:underline"
                          onClick={() => setStatus(it, "archive")}>Archive</button>
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
            <h2 className="section-title mb-4">New Issue Type</h2>
            {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
            <form onSubmit={handleCreate} className="form-stack">
              <label className="form-label">
                Name <span className="text-red-500">*</span>
                <input className="form-input" value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="Not cooling" />
              </label>
              <label className="form-label">
                Code
                <input className="form-input" value={form.code}
                  onChange={e => setForm(f => ({ ...f, code: e.target.value }))}
                  placeholder="not_cooling" />
              </label>
              <label className="form-label">
                Description
                <textarea className="form-input" value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  rows={2} />
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="form-label">
                  Default Severity
                  <select className="form-input" value={form.severity}
                    onChange={e => setForm(f => ({ ...f, severity: e.target.value }))}>
                    {SEVERITIES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </label>
                <label className="form-label">
                  Vertical Type
                  <input className="form-input" value={form.vertical_type}
                    onChange={e => setForm(f => ({ ...f, vertical_type: e.target.value }))}
                    placeholder="home_service" />
                </label>
              </div>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input type="checkbox" checked={form.requires_photo}
                    onChange={e => setForm(f => ({ ...f, requires_photo: e.target.checked }))} />
                  Requires photo
                </label>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input type="checkbox" checked={form.requires_description}
                    onChange={e => setForm(f => ({ ...f, requires_description: e.target.checked }))} />
                  Requires description
                </label>
              </div>
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
