"use client";
import { useCallback, useState } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import EnterpriseDataGrid, { GridColumn, GridData } from "../../../components/enterprise/EnterpriseDataGrid";
import { FilterDef } from "../../../components/enterprise/EnterpriseFilterBar";
import { apiFetchPaginatedRaw } from "../../../lib/api";

type LogSource = "engine" | "security" | "auth";

const TABS: { id: LogSource; label: string }[] = [
  { id: "engine",   label: "Engine Audit" },
  { id: "security", label: "Security Audit" },
  { id: "auth",     label: "Auth Audit" },
];

const ENGINE_COLUMNS: GridColumn[] = [
  { key: "event_type",  label: "Event",    width: 180 },
  { key: "engine_key",  label: "Engine",   width: 160 },
  { key: "actor_type",  label: "Actor",    width: 120 },
  { key: "reason",      label: "Reason",   width: 260 },
  { key: "created_at",  label: "Time",     width: 180,
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
  { key: "user_id",        label: "User",    width: 140,
    render: v => String(v ?? "").slice(0, 8) },
  { key: "ip_address",     label: "IP",      width: 130 },
  { key: "success",        label: "OK",      width: 70,
    render: v => v ? "✓" : "✗" },
  { key: "failure_reason", label: "Reason",  width: 220 },
  { key: "created_at",     label: "Time",    width: 180,
    render: v => v ? String(v).replace("T", " ").slice(0, 19) : "—" },
];

const DATE_FILTER: FilterDef = { key: "created", label: "Date Range", type: "date_range" };

const ENGINE_FILTERS: FilterDef[] = [
  {
    key: "event_type", label: "Event Type", type: "select",
    options: [
      { value: "enabled",       label: "Enabled" },
      { value: "disabled",      label: "Disabled" },
      { value: "updated",       label: "Updated" },
      { value: "health_check",  label: "Health Check" },
    ],
  },
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
  auth:     { endpoint: "/v1/auth/audit-log",      columns: AUTH_COLUMNS,     filters: AUTH_FILTERS,     resourceKey: "admin_auth_audit" },
};

function wrapLegacy(d: unknown, params: Record<string, unknown>) {
  const raw   = (d as Record<string, unknown>)?.logs
             ?? (d as Record<string, unknown>)?.items
             ?? d;
  const items = Array.isArray(raw) ? raw : [];
  const page     = Number(params.page ?? 1);
  const pageSize = Number(params.page_size ?? 25);
  const total    = (d as Record<string, unknown>)?.total ?? items.length;
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

  const fetchFn = useCallback(async (params: Record<string, unknown>) => {
    const d = await apiFetchPaginatedRaw(TAB_CONFIG[tab].endpoint, params);
    if (d?.pagination) return d as unknown as GridData;
    return wrapLegacy(d, params);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  return (
    <AdminLayout>
    <div style={{ padding: "24px 32px", maxWidth: 1280, margin: "0 auto",
      display: "flex", flexDirection: "column", gap: 20 }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
        Audit Logs
      </h1>

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
      />
    </div>
    </AdminLayout>
  );
}
