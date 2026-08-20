"use client";
import { useCallback, useState } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { PageShell, PageHeader } from "@serviceos/design-system";
import EnterpriseDataGrid, { GridColumn, GridData } from "../../../components/enterprise/EnterpriseDataGrid";
import { FilterDef } from "../../../components/enterprise/EnterpriseFilterBar";
import { apiFetchPaginatedRaw, sprint27AdminApi, AuditLogRecord } from "../../../lib/api";

type LogSource = "engine" | "security" | "auth";

const TABS: { id: LogSource; label: string }[] = [
  { id: "engine",   label: "Engine Audit" },
  { id: "security", label: "Security Audit" },
  { id: "auth",     label: "Auth Audit" },
];

const ENGINE_COLUMNS: GridColumn[] = [
  { key: "action",        label: "Action",    width: 220 },
  { key: "engine_key",    label: "Engine",    width: 170 },
  { key: "actor_role",    label: "Actor",     width: 120 },
  { key: "resource_type", label: "Resource",  width: 160 },
  { key: "resource_id",   label: "Resource ID", width: 180,
    render: v => v ? String(v).slice(0, 12) : "—" },
  { key: "created_at",    label: "Time",      width: 180,
    render: v => v ? String(v).replace("T", " ").slice(0, 19) : "—" },
];

const SECURITY_COLUMNS: GridColumn[] = [
  { key: "event_type",  label: "Event",      width: 180 },
  { key: "actor_type",  label: "Actor",      width: 120 },
  { key: "ip_address",  label: "IP",         width: 130 },
  { key: "user_agent",  label: "User Agent", width: 200, visible: false },
  { key: "description", label: "Details",    width: 280 },
  { key: "created_at",  label: "Time",       width: 180,
    render: v => v ? String(v).replace("T", " ").slice(0, 19) : "—" },
];

const AUTH_COLUMNS: GridColumn[] = [
  { key: "event_type",     label: "Event",   width: 180 },
  { key: "email_attempted", label: "Email",   width: 220 },
  { key: "user_id",        label: "User",    width: 140,
    render: v => String(v ?? "").slice(0, 8) },
  { key: "ip_address",     label: "IP",      width: 130 },
  { key: "failure_reason", label: "Reason",  width: 220 },
  { key: "created_at",     label: "Time",    width: 180,
    render: v => v ? String(v).replace("T", " ").slice(0, 19) : "—" },
];

const DATE_FILTER: FilterDef = { key: "created", label: "Date Range", type: "date_range" };

const ENGINE_FILTERS: FilterDef[] = [
  {
    key: "action", label: "Action", type: "select",
    options: [
      { value: "created",       label: "Created" },
      { value: "updated",       label: "Updated" },
      { value: "deleted",       label: "Deleted" },
      { value: "approved",      label: "Approved" },
      { value: "rejected",      label: "Rejected" },
      { value: "export",        label: "Export" },
    ],
  },
  { key: "engine_key", label: "Engine", type: "text" },
  { key: "resource_type", label: "Resource Type", type: "text" },
  DATE_FILTER,
];

const SECURITY_FILTERS: FilterDef[] = [
  {
    key: "event_type", label: "Event Type", type: "select",
    options: [
      { value: "rate_limit_hit",  label: "Rate Limit Hit" },
      { value: "suspicious_ip",   label: "Suspicious IP" },
      { value: "blocked_attempt", label: "Blocked Attempt" },
    ],
  },
  DATE_FILTER,
];

const AUTH_FILTERS: FilterDef[] = [
  {
    key: "event_type", label: "Event Type", type: "select",
    options: [
      { value: "login_success",  label: "Login Success" },
      { value: "login_failed",   label: "Login Failed" },
      { value: "logout",         label: "Logout" },
      { value: "token_refresh",  label: "Token Refresh" },
      { value: "password_reset", label: "Password Reset" },
    ],
  },
  DATE_FILTER,
];

const TAB_CONFIG: Record<LogSource, {
  endpoint: string;
  columns: GridColumn[];
  filters: FilterDef[];
  resourceKey: string;
}> = {
  engine:   { endpoint: "/v1/admin/audit-logs",    columns: ENGINE_COLUMNS,   filters: ENGINE_FILTERS,   resourceKey: "admin_engine_audit" },
  security: { endpoint: "/v1/security/audit-log",  columns: SECURITY_COLUMNS, filters: SECURITY_FILTERS, resourceKey: "admin_security_audit" },
  auth:     { endpoint: "/v1/admin/audit-logs/login-events", columns: AUTH_COLUMNS, filters: AUTH_FILTERS, resourceKey: "admin_auth_audit" },
};

function wrapLegacy(d: unknown, params: Record<string, unknown>) {
  const raw   = (d as Record<string, unknown>)?.logs
             ?? (d as Record<string, unknown>)?.items
             ?? (d as Record<string, unknown>)?.audit_logs
             ?? d;
  const items = Array.isArray(raw) ? raw : [];
  const pageSize = Number((d as Record<string, unknown>)?.limit ?? params.limit ?? params.page_size ?? 25);
  const offset   = Number((d as Record<string, unknown>)?.offset ?? ((Number(params.page ?? 1) - 1) * pageSize));
  const page     = Math.floor(offset / pageSize) + 1;
  const hasNext  = Boolean((d as Record<string, unknown>)?.has_next);
  const total    = (d as Record<string, unknown>)?.total
                ?? (hasNext ? offset + items.length + 1 : offset + items.length);
  return {
    items: items as Record<string, unknown>[],
    pagination: {
      page, page_size: pageSize, total_items: Number(total),
      total_pages: Math.ceil(Number(total) / pageSize) || 1,
      has_next: page * pageSize < Number(total), has_previous: page > 1,
    },
    sort:            { sort_by: String(params.sort_by), sort_direction: String(params.sort_direction) },
    filters_applied: params as Record<string, unknown>,
    available_columns: [],
  };
}

export default function AuditLogsPage() {
  const [tab, setTab] = useState<LogSource>("engine");
  const cfg = TAB_CONFIG[tab];

  // MODULE-L5-11: the record-timeline endpoint (full audit history of one record)
  // had a client method but was reachable from no UI. Wire it as a row-action
  // drill-in: "View record timeline" opens the complete trail for that resource.
  const [timeline, setTimeline] = useState<{
    open: boolean; loading: boolean; type: string; id: string; rows: AuditLogRecord[];
  } | null>(null);

  const openTimeline = useCallback(async (resourceType: string, resourceId: string) => {
    setTimeline({ open: true, loading: true, type: resourceType, id: resourceId, rows: [] });
    try {
      const r = await sprint27AdminApi.getAuditTimeline(resourceType, resourceId);
      setTimeline({ open: true, loading: false, type: resourceType, id: resourceId, rows: r.timeline ?? [] });
    } catch {
      setTimeline({ open: true, loading: false, type: resourceType, id: resourceId, rows: [] });
    }
  }, []);

  const fetchFn = useCallback(async (params: Record<string, unknown>) => {
    const endpointParams = { ...params };
    if (tab === "engine" || tab === "auth") {
      endpointParams.limit = params.page_size ?? 25;
      endpointParams.offset = (Number(params.page ?? 1) - 1) * Number(params.page_size ?? 25);
      delete endpointParams.page;
      delete endpointParams.page_size;
      if (tab === "engine") {
        if (params.created_from) endpointParams.date_from = params.created_from;
        if (params.created_to) endpointParams.date_to = params.created_to;
        delete endpointParams.created_from;
        delete endpointParams.created_to;
      }
      if (params.sort_by || params.sort_direction) {
        delete endpointParams.sort_by;
        delete endpointParams.sort_direction;
      }
    }
    const d = await apiFetchPaginatedRaw(TAB_CONFIG[tab].endpoint, endpointParams);
    if (d?.pagination) return d as unknown as GridData;
    return wrapLegacy(d, params);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  return (
    <AdminLayout>
    <PageShell>
      <PageHeader title="Audit Logs" description="Engine, security, and auth audit trails across the platform." />

      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)" }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            padding: "8px 16px", fontSize: 13, fontWeight: 600, borderRadius: "8px 8px 0 0",
            border: tab === t.id ? "1px solid var(--border)" : "1px solid transparent",
            borderBottom: tab === t.id ? "1px solid var(--surface)" : "1px solid transparent",
            marginBottom: tab === t.id ? -1 : 0,
            background: tab === t.id ? "var(--surface)" : "none",
            color: tab === t.id ? "var(--brand)" : "var(--text-tertiary)",
            cursor: "pointer", fontFamily: "inherit", transition: "color 0.12s",
          }}>
            {t.label}
          </button>
        ))}
      </div>

      <EnterpriseDataGrid
        key={tab}
        resourceKey={cfg.resourceKey}
        fetchFn={fetchFn}
        columns={cfg.columns}
        filters={cfg.filters}
        defaultSort={{ sort_by: "created_at", sort_direction: "desc" }}
        enableColumnPrefs
        emptyMessage="No audit logs found."
        rowActions={tab === "engine" ? (row) => {
          const rt = String(row.resource_type ?? row.entity_type ?? "");
          const ri = String(row.resource_id ?? row.entity_id ?? "");
          if (!rt || !ri) return [];
          return [{ label: "View record timeline", onClick: () => openTimeline(rt, ri) }];
        } : undefined}
      />

      {timeline?.open && (
        <div onClick={() => setTimeline(null)} style={{ position: "fixed", inset: 0,
          background: "rgba(0,0,0,0.45)", zIndex: 300, display: "flex", justifyContent: "flex-end" }}>
          <div onClick={e => e.stopPropagation()} style={{ width: "min(520px, 96vw)",
            background: "var(--surface)", height: "100%", overflowY: "auto",
            boxShadow: "-4px 0 32px rgba(0,0,0,0.25)" }}>
            <div style={{ padding: "18px 22px", borderBottom: "1px solid var(--border)",
              display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>Record timeline</h2>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "3px 0 0" }}>
                  {timeline.type} · {timeline.id}
                </p>
              </div>
              <button onClick={() => setTimeline(null)} style={{ background: "none", border: "none",
                fontSize: 20, cursor: "pointer", color: "var(--text-tertiary)" }}>✕</button>
            </div>
            <div style={{ padding: "16px 22px" }}>
              {timeline.loading ? (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Loading…</p>
              ) : timeline.rows.length === 0 ? (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No audit entries for this record.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
                  {timeline.rows.map((e, i) => (
                    <div key={e.id ?? i} style={{ display: "flex", gap: 12,
                      paddingBottom: 14, position: "relative" }}>
                      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                        <span style={{ width: 9, height: 9, borderRadius: "50%", background: "var(--brand)", marginTop: 4 }} />
                        {i < timeline.rows.length - 1 && (
                          <span style={{ width: 2, flex: 1, background: "var(--border)", marginTop: 2 }} />
                        )}
                      </div>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                          {e.action}{e.is_high_risk ? " ⚠" : ""}
                        </div>
                        <div style={{ fontSize: 12, color: "var(--text-secondary)", margin: "2px 0" }}>
                          {e.actor_role ?? "system"}{e.engine_key ? ` · ${e.engine_key}` : ""}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                          {String(e.created_at ?? "").replace("T", " ").slice(0, 19)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </PageShell>
    </AdminLayout>
  );
}
