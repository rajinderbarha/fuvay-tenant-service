"use client";

import React, { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import { CheckCircle, ChevronLeft, ChevronRight, FlaskConical, Globe, Layers, RefreshCw, Search, Settings, ShieldAlert, ToggleLeft, ToggleRight, UserPlus, XCircle, Zap } from "lucide-react";
import { AdminLayout, useAdminMenuRefresh } from "../../../components/layout/AdminLayout";
import OperationsDirectoryControls from "../../../components/enterprise/OperationsDirectoryControls";
import type { ColumnDef } from "../../../components/enterprise/EnterpriseColumnManager";
import { Badge, Btn, Modal, SectionHeader } from "../../../components/shared/ui";
import { verticalCatalogApi, type VerticalDetail, type VerticalItem } from "../../../lib/api";
import { useAction, useApi } from "../../../hooks/useApi";

type Filters = { q: string; status: string; finance_model: string; lifecycle_status: string; release_stage: string; registration_allowed: string; is_beta: string };
const EMPTY: Filters = { q: "", status: "", finance_model: "", lifecycle_status: "", release_stage: "", registration_allowed: "", is_beta: "" };
const DEFAULT_COLUMNS: ColumnDef[] = [
  { key: "label", label: "Vertical", visible: true, order: 0 },
  { key: "status", label: "Status", visible: true, order: 1 },
  { key: "release_stage", label: "Release", visible: true, order: 2 },
  { key: "finance_model", label: "Finance model", visible: true, order: 3 },
  { key: "lifecycle_status", label: "Lifecycle", visible: true, order: 4 },
  { key: "registration_allowed", label: "Registration", visible: true, order: 5 },
  { key: "modules", label: "Modules", visible: true, order: 6 },
  { key: "enrollments", label: "Enrollments", visible: true, order: 7 },
  { key: "actions", label: "Actions", visible: true, order: 8 },
];

function ModulesModal({ vertical, onClose, onChanged }: { vertical: VerticalItem; onClose: () => void; onChanged: () => void }) {
  const [pendingDisable, setPendingDisable] = useState<{ key: string; label: string } | null>(null);
  const [reason, setReason] = useState("");
  const detail = useApi(() => verticalCatalogApi.getVertical(vertical.key), [vertical.key]);
  const enable = useAction((key: string) => verticalCatalogApi.enableModule(vertical.key, key));
  const disable = useAction((key: string, auditReason: string) => verticalCatalogApi.disableModule(vertical.key, key, auditReason));
  const allModules = (detail.data as VerticalDetail | null)?.modules ?? [];
  const modules = allModules.filter(module => module.navigation_status === "available");
  const hiddenCount = allModules.length - modules.length;
  const groups = modules.reduce<Record<string, typeof modules>>((all, item) => {
    (all[item.module_group ?? "Other"] ??= []).push(item); return all;
  }, {});
  const activeCount = modules.filter(module => module.is_enabled).length;
  return <Modal open title={`${vertical.label} · Admin navigation`} size="lg" onClose={onClose}>
    <div style={{ padding: 12, marginBottom: 14, borderRadius: 10, border: "1px solid var(--info-border)", background: "var(--info-bg)", color: "var(--text-secondary)", fontSize: 12, lineHeight: 1.55 }}>
      These switches only control current pages shown in the super-admin sidebar. They do not enable or disable tenant entitlements, native-app features, booking engines, or finance policy.
      {!detail.loading && <strong style={{ display: "block", marginTop: 4, color: "var(--text-primary)" }}>{activeCount} enabled of {modules.length} current admin workspaces{hiddenCount ? ` · ${hiddenCount} retired or unavailable hidden` : ""}</strong>}
    </div>
    {(detail.error || enable.error || disable.error) && <div style={{ padding: 10, marginBottom: 12, borderRadius: 8, background: "var(--danger-bg)", color: "var(--danger)", fontSize: 12 }}>{detail.error || enable.error || disable.error}</div>}
    {detail.loading ? <div className="skeleton" style={{ height: 180 }} /> : modules.length === 0 ? <div style={{ padding: 28, textAlign: "center", color: "var(--text-tertiary)" }}>No current admin navigation modules are assigned to this vertical.</div> : Object.entries(groups).map(([group, rows]) => <section key={group} style={{ marginBottom: 16 }}>
      <p style={{ fontSize: 11, fontWeight: 800, textTransform: "uppercase", color: "var(--text-tertiary)", letterSpacing: ".07em" }}>{group}</p>
      {rows.map(row => <div key={row.key} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", border: "1px solid var(--border)", background: "var(--surface-sunken)", borderRadius: 9, marginBottom: 5 }}>
        <Layers size={14} color="var(--brand)" /><div style={{ flex: 1, minWidth: 0 }}><div style={{ fontSize: 13, fontWeight: 650 }}>{row.label}</div><div style={{ fontSize: 10.5, color: "var(--text-tertiary)", marginTop: 2 }}>{row.navigation_status_reason || row.description || row.admin_path || "Admin navigation page"}</div></div>
        {row.is_required && <Badge variant="warning">Required</Badge>}
        <button aria-label={`${row.is_enabled ? "Disable" : "Enable"} ${row.label}`} disabled={(row.is_required && row.is_enabled) || enable.loading || disable.loading}
          onClick={async () => { if (row.is_enabled) { setPendingDisable({ key: row.key, label: row.label }); setReason(""); } else { const result = await enable.execute(row.key); if (result) { detail.refetch(); onChanged(); } } }}
          style={{ border: 0, background: "none", color: row.is_enabled ? "var(--success)" : "var(--text-tertiary)", cursor: (row.is_required && row.is_enabled) ? "not-allowed" : "pointer" }}>
          {row.is_enabled ? <ToggleRight size={23} /> : <ToggleLeft size={23} />}
        </button>
      </div>)}
    </section>)}
    {pendingDisable && <div style={{ marginTop: 12, padding: 14, borderRadius: 10, border: "1px solid var(--warning-border)", background: "var(--warning-bg)" }}>
      <div style={{ fontWeight: 750, fontSize: 13 }}>Hide {pendingDisable.label} from admin navigation?</div>
      <p style={{ margin: "4px 0 9px", fontSize: 11.5, color: "var(--text-secondary)" }}>This does not disable the underlying engine or tenant capability. Add a reason for the audit trail.</p>
      <textarea aria-label="Module disable reason" value={reason} onChange={event => setReason(event.target.value)} rows={2} placeholder="Explain why this page should be hidden…" style={{ width: "100%", boxSizing: "border-box", padding: 9, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }} />
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 9 }}><Btn size="xs" variant="ghost" onClick={() => setPendingDisable(null)}>Cancel</Btn><Btn size="xs" variant="danger" disabled={reason.trim().length < 10} loading={disable.loading} onClick={async () => { const result = await disable.execute(pendingDisable.key, reason.trim()); if (result) { setPendingDisable(null); setReason(""); detail.refetch(); onChanged(); } }}>Hide module</Btn></div>
    </div>}
  </Modal>;
}

function DisableModal({ vertical, onClose, onDisabled }: { vertical: VerticalItem; onClose: () => void; onDisabled: () => void }) {
  const [reason, setReason] = useState("");
  const impact = useApi(() => verticalCatalogApi.getDisableImpact(vertical.key), [vertical.key]);
  const action = useAction(() => verticalCatalogApi.disableVertical(vertical.key, reason.trim()));
  const data = impact.data ?? {};
  return <Modal open title={`Disable ${vertical.label}?`} size="md" onClose={onClose}>
    <div style={{ padding: 14, border: "1px solid var(--warning-border)", background: "var(--warning-bg)", borderRadius: 10, marginBottom: 15 }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", fontWeight: 750, fontSize: 13 }}><ShieldAlert size={16} />Operational impact</div>
      {impact.loading ? <p style={{ fontSize: 12 }}>Calculating impact…</p> : <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 8, marginTop: 10 }}>
        {[['Active tenants', data.active_tenant_enrollments], ['Under review', data.under_review_enrollments], ['Active jobs', data.active_jobs], ['Booking drafts', data.draft_bookings_in_progress]].map(([label, value]) => <div key={String(label)}><strong>{String(value ?? 0)}</strong><div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{label}</div></div>)}
      </div>}
    </div>
    <label style={{ fontSize: 12, fontWeight: 700 }}>Audit reason <span style={{ color: "var(--danger)" }}>*</span></label>
    <textarea value={reason} onChange={event => setReason(event.target.value)} rows={3} placeholder="Explain why registration and new access must be disabled…"
      style={{ width: "100%", marginTop: 6, padding: 10, borderRadius: 9, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", boxSizing: "border-box" }} />
    {action.error && <p style={{ color: "var(--danger)", fontSize: 12 }}>{action.error}</p>}
    <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 14 }}><Btn variant="ghost" onClick={onClose}>Cancel</Btn><Btn variant="danger" disabled={reason.trim().length < 10 || impact.loading} loading={action.loading} onClick={async () => { const result = await action.execute(); if (result) onDisabled(); }}>Disable vertical</Btn></div>
  </Modal>;
}

export default function VerticalsPage() {
  const refreshMenu = useAdminMenuRefresh();
  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [page, setPage] = useState(1);
  const [columns, setColumns] = useState(DEFAULT_COLUMNS);
  const [modules, setModules] = useState<VerticalItem | null>(null);
  const [disabling, setDisabling] = useState<VerticalItem | null>(null);
  const pageSize = 25;
  const query = useApi(useCallback(() => verticalCatalogApi.listVerticalsDirectory({ include_disabled: true, ...filters,
    registration_allowed: filters.registration_allowed === "" ? undefined : filters.registration_allowed === "true",
    is_beta: filters.is_beta === "" ? undefined : filters.is_beta === "true", page, page_size: pageSize,
  }), [filters, page]));
  const summary = useApi(useCallback(() => verticalCatalogApi.summary(), []));
  const enable = useAction((key: string) => verticalCatalogApi.enableVertical(key));
  const visible = useMemo(() => new Set(columns.filter(c => c.visible).map(c => c.key)), [columns]);
  const data = query.data;
  const items = data?.items ?? [];
  const setFilter = (key: keyof Filters, value: string) => { setFilters(current => ({ ...current, [key]: value })); setPage(1); };
  const refresh = () => { query.refetch(); summary.refetch(); refreshMenu(); };
  const controlsFilters = Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== ""));
  const selectStyle: React.CSSProperties = { height: 36, border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface)", color: "var(--text-primary)", padding: "0 10px", fontSize: 12 };

  return <AdminLayout activeNav="verticals">
    <style>{`
      .vertical-summary-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:14px}
      .vertical-summary-card{position:relative;overflow:hidden;min-height:92px;padding:15px 17px;border:1px solid var(--border);border-radius:13px;background:var(--surface);box-shadow:var(--shadow-xs)}
      .vertical-summary-icon{position:absolute;right:14px;top:14px;width:31px;height:31px;border-radius:9px;display:grid;place-items:center;background:var(--surface-sunken)}
      .vertical-summary-value{font-size:25px;line-height:1;font-weight:760;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
      .vertical-summary-label{margin-top:9px;font-size:11.5px;font-weight:700;color:var(--text-secondary)}
      .vertical-summary-note{margin-top:3px;font-size:10px;color:var(--text-tertiary)}
      .vertical-filterbar{display:grid;grid-template-columns:minmax(270px,1fr) auto auto auto auto;gap:8px;align-items:center;padding:10px;border:1px solid var(--border);border-radius:12px;background:var(--surface);box-shadow:var(--shadow-xs);margin-bottom:9px}
      .vertical-table-shell{border:1px solid var(--border);border-radius:13px;overflow:hidden;background:var(--surface);box-shadow:var(--shadow-xs);margin-top:9px}
      .vertical-table-scroll{overflow-x:auto}
      .vertical-table{width:100%;min-width:1020px;border-collapse:separate;border-spacing:0}
      .vertical-table th{height:42px;padding:0 14px;border-bottom:1px solid var(--border);background:var(--surface-sunken);color:var(--text-tertiary);font-size:10.5px;font-weight:760;letter-spacing:.055em;text-align:left;text-transform:uppercase;white-space:nowrap}
      .vertical-table td{height:62px;padding:8px 14px;border-bottom:1px solid var(--border);color:var(--text-secondary);font-size:12px;vertical-align:middle;white-space:nowrap}
      .vertical-table tbody tr{transition:background .14s ease}.vertical-table tbody tr:hover{background:var(--surface-sunken)}.vertical-table tbody tr:last-child td{border-bottom:0}
      .vertical-name{display:flex;align-items:center;gap:11px;min-width:185px}.vertical-icon{width:36px;height:36px;flex:0 0 36px;border-radius:10px;display:grid;place-items:center}
      .vertical-link{color:var(--text-primary);font-size:13px;font-weight:720;text-decoration:none}.vertical-link:hover{color:var(--brand)}
      .vertical-code{margin-top:2px;color:var(--text-tertiary);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10px}
      .vertical-actions{display:flex;justify-content:flex-end;align-items:center;gap:5px}.vertical-count{color:var(--text-primary);font-size:13px;font-weight:720}.vertical-count-sub{margin-top:2px;color:var(--text-tertiary);font-size:10px}
      .vertical-table-footer{min-height:45px;padding:0 14px;border-top:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;color:var(--text-secondary);font-size:11.5px}
      @media(max-width:1100px){.vertical-summary-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.vertical-filterbar{grid-template-columns:minmax(240px,1fr) auto auto}.vertical-filter-optional{display:none}}
      @media(max-width:680px){.vertical-summary-grid{grid-template-columns:1fr 1fr}.vertical-summary-card{min-height:84px;padding:13px}.vertical-filterbar{grid-template-columns:1fr}.vertical-filterbar>*{width:100%}.operations-directory-controls{overflow-x:auto;flex-wrap:nowrap!important}}
    `}</style>
    <SectionHeader title="Business Verticals" subtitle="Control platform availability, registration, capabilities, and release lifecycle." icon={<Globe size={20} />} actions={<Btn variant="ghost" size="sm" icon={<RefreshCw size={13} />} onClick={refresh}>Refresh</Btn>} />
    <div className="vertical-summary-grid">
      {[
        ["All verticals", summary.data?.total, "Platform registry", <Globe size={16} />, "var(--brand)"],
        ["Enabled", summary.data?.enabled, "Available to operate", <Zap size={16} />, "var(--success)"],
        ["Registration open", summary.data?.registration_open, "Accepting new tenants", <UserPlus size={16} />, "var(--info)"],
        ["Needs attention", (summary.data?.disabled ?? 0) + (summary.data?.beta ?? 0), `${summary.data?.disabled ?? 0} disabled · ${summary.data?.beta ?? 0} beta`, <XCircle size={16} />, "var(--warning)"],
      ].map(([label, value, note, icon, color]) => <div key={String(label)} className="vertical-summary-card"><span className="vertical-summary-icon" style={{ color: String(color) }}>{icon}</span><div className="vertical-summary-value">{summary.loading ? "…" : String(value ?? "—")}</div><div className="vertical-summary-label">{label}</div><div className="vertical-summary-note">{note}</div></div>)}
    </div>
    <div className="vertical-filterbar">
      <div style={{ position: "relative", flex: "1 1 250px" }}><Search size={14} style={{ position: "absolute", left: 11, top: 11, color: "var(--text-tertiary)" }} /><input aria-label="Search verticals" value={filters.q} onChange={e => setFilter("q", e.target.value)} placeholder="Search name, key, slug or description" style={{ ...selectStyle, width: "100%", paddingLeft: 33 }} /></div>
      <select aria-label="Status" value={filters.status} onChange={e => setFilter("status", e.target.value)} style={selectStyle}><option value="">All statuses</option><option value="enabled">Enabled</option><option value="disabled">Disabled</option></select>
      <select aria-label="Release stage" value={filters.release_stage} onChange={e => setFilter("release_stage", e.target.value)} style={selectStyle}><option value="">All releases</option><option value="production">Production</option><option value="beta">Beta</option><option value="alpha">Alpha</option></select>
      <select className="vertical-filter-optional" aria-label="Registration" value={filters.registration_allowed} onChange={e => setFilter("registration_allowed", e.target.value)} style={selectStyle}><option value="">Any registration</option><option value="true">Open</option><option value="false">Closed</option></select>
      {Object.values(filters).some(Boolean) && <Btn size="sm" variant="ghost" onClick={() => { setFilters(EMPTY); setPage(1); }}>Clear</Btn>}
    </div>
    <OperationsDirectoryControls resourceKey="admin_verticals" filters={controlsFilters} sort={{ sort_by: "sort_order", sort_direction: "asc" }} columns={columns} onColumnsChange={setColumns}
      onApplyView={(next) => { setFilters({ ...EMPTY, ...next } as Filters); setPage(1); }} />
    {query.error && <div style={{ padding: 12, color: "var(--danger)", background: "var(--danger-bg)", borderRadius: 9, marginTop: 9 }}>{query.error}</div>}
    <div className="vertical-table-shell">
      <div className="vertical-table-scroll"><table className="vertical-table"><thead><tr>
        {visible.has("label") && <th>Vertical</th>}{visible.has("status") && <th>Status</th>}{visible.has("release_stage") && <th>Release</th>}{visible.has("finance_model") && <th>Finance model</th>}{visible.has("lifecycle_status") && <th>Lifecycle</th>}{visible.has("registration_allowed") && <th>Registration</th>}{visible.has("modules") && <th>Modules</th>}{visible.has("enrollments") && <th>Enrollments</th>}{visible.has("actions") && <th style={{ textAlign: "right" }}>Actions</th>}
      </tr></thead><tbody>
        {query.loading ? Array.from({ length: 5 }).map((_, i) => <tr key={i}><td colSpan={9}><div className="skeleton" style={{ height: 38, margin: 7 }} /></td></tr>) : items.map(v => <tr key={v.id}>
          {visible.has("label") && <td><div className="vertical-name"><span className="vertical-icon" style={{ color: v.color ?? "var(--brand)", background: `${v.color ?? "#2563eb"}16` }}><Globe size={16} /></span><div><Link className="vertical-link" href={`/admin/verticals/${v.key}`}>{v.label}</Link><div className="vertical-code">{v.key}</div></div></div></td>}
          {visible.has("status") && <td><Badge variant={v.is_enabled ? "success" : "muted"}>{v.is_enabled ? "Enabled" : "Disabled"}</Badge></td>}
          {visible.has("release_stage") && <td><Badge variant={v.is_beta ? "warning" : "info"}>{v.release_stage || (v.is_beta ? "beta" : "ga")}</Badge></td>}
          {visible.has("finance_model") && <td style={{ textTransform: "capitalize" }}>{v.finance_model?.replaceAll("_", " ") || "—"}</td>}
          {visible.has("lifecycle_status") && <td style={{ textTransform: "capitalize" }}>{v.lifecycle_status?.replaceAll("_", " ") || "—"}</td>}
          {visible.has("registration_allowed") && <td><Badge variant={v.registration_allowed ? "success" : "muted"}>{v.registration_allowed ? "Open" : "Closed"}</Badge></td>}
          {visible.has("modules") && <td><span className="vertical-count">{v.enabled_module_count ?? 0}</span><div className="vertical-count-sub">of {v.module_count ?? 0} enabled</div></td>}
          {visible.has("enrollments") && <td><span className="vertical-count">{v.active_enrollment_count ?? 0}</span><div className="vertical-count-sub">{v.enrollment_count ?? 0} total</div></td>}
          {visible.has("actions") && <td><div className="vertical-actions"><Btn variant="ghost" size="xs" icon={<Settings size={12} />} onClick={() => setModules(v)}>Modules</Btn><Link href={`/admin/verticals/${v.key}?tab=capabilities`} style={{ textDecoration: "none" }}><Btn variant="secondary" size="xs">Manage</Btn></Link>{v.is_enabled ? <button aria-label={`Disable ${v.label}`} title="Disable vertical" onClick={() => setDisabling(v)} style={{ width: 28, height: 28, display: "grid", placeItems: "center", border: "1px solid var(--border)", borderRadius: 7, background: "transparent", color: "var(--text-tertiary)", cursor: "pointer" }}><XCircle size={13} /></button> : <Btn variant="success" size="xs" loading={enable.loading} onClick={async () => { await enable.execute(v.key); refresh(); }}>Enable</Btn>}</div></td>}
        </tr>)}
      </tbody></table></div>
      {!query.loading && !items.length && <div style={{ textAlign: "center", padding: 45, color: "var(--text-tertiary)" }}>No verticals match these filters.</div>}
      <div className="vertical-table-footer"><span>{data?.total ?? 0} verticals · Page {page} of {data?.pages ?? 1}</span><div style={{ display: "flex", gap: 5 }}><Btn size="xs" variant="ghost" disabled={page <= 1} onClick={() => setPage(p => p - 1)}><ChevronLeft size={14} /></Btn><Btn size="xs" variant="ghost" disabled={page >= (data?.pages ?? 1)} onClick={() => setPage(p => p + 1)}><ChevronRight size={14} /></Btn></div></div>
    </div>
    {modules && <ModulesModal vertical={modules} onClose={() => setModules(null)} onChanged={refresh} />}
    {disabling && <DisableModal vertical={disabling} onClose={() => setDisabling(null)} onDisabled={() => { setDisabling(null); refresh(); }} />}
  </AdminLayout>;
}
