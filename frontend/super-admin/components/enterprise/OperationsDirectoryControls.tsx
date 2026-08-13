"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Bookmark, Check, Columns3, Download, Loader2, Save, Trash2 } from "lucide-react";
import { enterpriseApi, EnterpriseSavedView } from "../../lib/api";
import EnterpriseColumnManager, { ColumnDef } from "./EnterpriseColumnManager";

interface Props {
  resourceKey: "admin_customers" | "admin_staff" | "admin_complaints" | "admin_categories" | "admin_verticals" | "admin_service_groups";
  filters: Record<string, unknown>;
  sort?: { sort_by: string; sort_direction: string };
  columns: ColumnDef[];
  onApplyView: (filters: Record<string, unknown>, sort: Record<string, unknown>) => void;
  onColumnsChange: (columns: ColumnDef[]) => void;
}

const EXPORT_FIELDS: Record<Props["resourceKey"], Set<string>> = {
  admin_customers: new Set(["full_name", "phone", "email", "city", "state", "zipcode", "health_band", "total_bookings", "completed_bookings", "cancelled_bookings", "complaints_count", "reviews_count", "average_rating", "last_booking_at", "created_at"]),
  admin_staff: new Set(["full_name", "email", "phone", "role", "tenant_name", "tenant_city", "availability_status", "is_active", "is_verified", "total_jobs", "completed_jobs", "active_jobs", "average_rating", "last_job_at", "created_at"]),
  admin_complaints: new Set(["complaint_number", "status", "priority", "complaint_type", "created_at"]),
  admin_categories: new Set(["name", "slug", "vertical_type", "finance_model", "customer_flow_type", "status", "is_customer_visible", "tenant_selectable", "pricing_supported", "display_order", "created_at", "updated_at"]),
  admin_verticals: new Set(["label", "key", "status", "finance_model", "lifecycle_status", "release_stage", "registration_allowed", "is_beta", "sort_order", "updated_at"]),
  admin_service_groups: new Set(["name", "code", "slug", "category_name", "status", "display_order", "created_at", "updated_at", "deleted_at"]),
};

const buttonStyle: React.CSSProperties = {
  height: 34, padding: "0 11px", borderRadius: 8, border: "1px solid var(--border)",
  background: "var(--surface)", color: "var(--text-secondary)", fontSize: 12,
  fontWeight: 600, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6,
};

export default function OperationsDirectoryControls({
  resourceKey, filters, sort = { sort_by: "created_at", sort_direction: "desc" },
  columns, onApplyView, onColumnsChange,
}: Props) {
  const [views, setViews] = useState<EnterpriseSavedView[]>([]);
  const [selectedView, setSelectedView] = useState("");
  const [savingView, setSavingView] = useState(false);
  const [viewName, setViewName] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const signature = useMemo(() => columns.map(c => c.key).join("|"), [columns]);

  useEffect(() => {
    let active = true;
    Promise.all([
      enterpriseApi.listSavedViews(resourceKey),
      enterpriseApi.getColumnPrefs(resourceKey).catch(() => null),
    ]).then(([saved, prefs]) => {
      if (!active) return;
      setViews(saved ?? []);
      const stored = Array.isArray(prefs?.columns) ? prefs.columns as ColumnDef[] : [];
      if (stored.length) {
        const byKey = new Map(stored.map(c => [c.key, c]));
        onColumnsChange(columns.map((column, index) => ({
          ...column, ...(byKey.get(column.key) ?? {}), order: byKey.get(column.key)?.order ?? index,
        })));
      }
    }).catch(() => setMessage("Personalization is temporarily unavailable."));
    return () => { active = false; };
    // Column keys form the schema; visibility changes must not re-fetch prefs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resourceKey, signature]);

  async function changeColumns(next: ColumnDef[]) {
    if (!next.some(c => c.visible)) return;
    onColumnsChange(next);
    try {
      await enterpriseApi.saveColumnPrefs(resourceKey, next);
      setMessage("Columns saved");
    } catch {
      setMessage("Columns changed for this session; saving failed.");
    }
  }

  async function resetColumns() {
    setBusy(true);
    try {
      const prefs = await enterpriseApi.resetColumnPrefs(resourceKey);
      const defaults = prefs.columns as ColumnDef[];
      onColumnsChange(defaults.length ? defaults : columns.map((c, order) => ({ ...c, visible: true, order })));
      setMessage("Default columns restored");
    } finally { setBusy(false); }
  }

  async function createView() {
    if (!viewName.trim()) return;
    setBusy(true);
    try {
      const view = await enterpriseApi.createSavedView({
        resource_key: resourceKey, view_name: viewName.trim(), scope: "admin",
        filters, sort, columns: columns.filter(c => c.visible).map(c => c.key), page_size: 25,
        visibility: "private",
      });
      setViews(current => [...current, view]);
      setSelectedView(view.id); setViewName(""); setSavingView(false);
      setMessage("View saved");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save this view.");
    } finally { setBusy(false); }
  }

  async function removeView() {
    if (!selectedView) return;
    setBusy(true);
    try {
      await enterpriseApi.deleteSavedView(selectedView);
      setViews(current => current.filter(v => v.id !== selectedView));
      setSelectedView(""); setMessage("View deleted");
    } finally { setBusy(false); }
  }

  function applySelected(id: string) {
    setSelectedView(id);
    const view = views.find(v => v.id === id);
    if (view) onApplyView(view.filters ?? {}, view.sort ?? {});
  }

  async function queueExport() {
    setBusy(true);
    try {
      const job = await enterpriseApi.createExport({
        resource_key: resourceKey, filters,
        columns: columns.filter(c => c.visible && EXPORT_FIELDS[resourceKey].has(c.key)).map(c => c.key), export_format: "csv",
      }, `${resourceKey}-${Date.now()}`);
      setMessage(`Export ${job.status}. Open Export center to track it.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Export could not be queued.");
    } finally { setBusy(false); }
  }

  return (
    <div className="operations-directory-controls" style={{
      display: "flex", gap: 7, alignItems: "center", flexWrap: "wrap",
      padding: "9px 12px", border: "1px solid var(--border)", borderRadius: 10,
      background: "var(--surface)", boxShadow: "var(--shadow-xs)",
    }}>
      <Bookmark size={14} color="var(--text-tertiary)" />
      <select aria-label="Saved views" value={selectedView} onChange={e => applySelected(e.target.value)}
        style={{ ...buttonStyle, minWidth: 150, appearance: "auto" }}>
        <option value="">Saved views</option>
        {views.map(view => <option key={view.id} value={view.id}>{view.view_name}{view.is_default ? " · default" : ""}</option>)}
      </select>
      {savingView ? <>
        <input autoFocus value={viewName} onChange={e => setViewName(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") createView(); if (e.key === "Escape") setSavingView(false); }}
          placeholder="View name" aria-label="View name"
          style={{ ...buttonStyle, cursor: "text", width: 160 }} />
        <button style={buttonStyle} disabled={busy || !viewName.trim()} onClick={createView}><Check size={14} />Save</button>
      </> : <button style={buttonStyle} onClick={() => setSavingView(true)}><Save size={14} />Save view</button>}
      {selectedView && <button aria-label="Delete saved view" title="Delete saved view" style={buttonStyle} disabled={busy} onClick={removeView}><Trash2 size={14} /></button>}
      <span style={{ width: 1, height: 22, background: "var(--border)" }} />
      <EnterpriseColumnManager columns={columns} onChange={changeColumns} onReset={resetColumns} />
      <button style={buttonStyle} disabled={busy} onClick={queueExport}>
        {busy ? <Loader2 size={14} className="spin" /> : <Download size={14} />}Queue export
      </button>
      <Link href="/admin/exports" style={{ ...buttonStyle, textDecoration: "none" }}>Export center</Link>
      {message && <span role="status" style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-tertiary)" }}>{message}</span>}
      <span className="sr-only"><Columns3 size={1} /></span>
    </div>
  );
}
