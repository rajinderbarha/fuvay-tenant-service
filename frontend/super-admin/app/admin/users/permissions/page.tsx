"use client";
/**
 * Phase 1B — Admin Permissions page.
 * Renders live permission constants from app/core/permissions.py::class P,
 * grouped and enriched with real role assignments.
 */
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, StatCard, SectionHeader, Skeleton, EmptyState, Input, Select } from "../../../../components/shared/ui";
import { Key, Shield, Users, AlertTriangle } from "lucide-react";
import { rolesPermissionsApi, PermissionListItem } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

const RISK_BADGE: Record<string, "danger" | "warning" | "muted"> = {
  high: "danger", medium: "warning", low: "muted",
};
const SCOPE_BADGE: Record<string, "info" | "success" | "muted"> = {
  admin: "info", tenant: "success", customer: "muted",
};

const MODULES = [
  "Auth / IAM", "Platform Settings", "Dashboard", "Navigation", "Engines",
  "Verticals", "Users & Roles", "Catalog", "Pricing", "Tenant", "Booking",
  "Finance", "Audit", "Compliance", "Field Ops", "Other",
];

export default function PermissionsPage() {
  const [moduleFilter, setModuleFilter] = useState("");
  const [scopeFilter, setScopeFilter] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [search, setSearch] = useState("");
  const [detailKey, setDetailKey] = useState<PermissionListItem | null>(null);

  const perms = useApi(useCallback(() => rolesPermissionsApi.listPermissions({
    module: moduleFilter || undefined, app_scope: scopeFilter || undefined,
    risk_level: riskFilter || undefined, search: search || undefined,
  }), [moduleFilter, scopeFilter, riskFilter, search]), [moduleFilter, scopeFilter, riskFilter, search]);

  const s = perms.data?.summary;

  return (
    <AdminLayout activeNav="users">
      {detailKey && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 200,
          display: "flex", justifyContent: "flex-end" }} onClick={() => setDetailKey(null)}>
          <div style={{ width: "min(480px,95vw)", background: "var(--surface)", overflowY: "auto",
            boxShadow: "-4px 0 32px rgba(0,0,0,0.25)" }} onClick={e => e.stopPropagation()}>
            <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border)",
              display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, fontFamily: "monospace" }}>{detailKey.permission_key}</h2>
              <Btn variant="ghost" size="sm" onClick={() => setDetailKey(null)}>✕</Btn>
            </div>
            <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Badge variant={SCOPE_BADGE[detailKey.app_scope] ?? "muted"}>{detailKey.app_scope}</Badge>
                <Badge variant={RISK_BADGE[detailKey.risk_level]}>{detailKey.risk_level} risk</Badge>
                <Badge variant="muted">{detailKey.module}</Badge>
              </div>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>{detailKey.description}</p>
              <div>
                <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                  textTransform: "uppercase", margin: "0 0 8px" }}>
                  Assigned Roles ({detailKey.assigned_role_count})
                </p>
                {detailKey.assigned_roles.length === 0 ? (
                  <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>No role currently grants this permission.</p>
                ) : (
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {detailKey.assigned_roles.map(r => <Badge key={r} variant="info" size="sm">{r}</Badge>)}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <SectionHeader title="Permissions" subtitle="Live permission constants from app/core/permissions.py, grouped and filterable."/>

      {perms.loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))", gap: 12, marginBottom: 20 }}>
          {[...Array(6)].map((_, i) => <Skeleton key={i} height={88} style={{ borderRadius: 12 }}/>)}
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))", gap: 12, marginBottom: 20 }}>
          <StatCard label="Total Permissions" value={s?.total_permissions ?? 0} icon={<Key size={16}/>}/>
          <StatCard label="Admin Permissions" value={s?.admin_permissions ?? 0} icon={<Shield size={16}/>}/>
          <StatCard label="Tenant Permissions" value={s?.tenant_permissions ?? 0} icon={<Users size={16}/>}/>
          <StatCard label="Customer Permissions" value={s?.customer_permissions ?? 0} icon={<Users size={16}/>}/>
          <StatCard label="High Risk" value={s?.high_risk_permissions ?? 0} icon={<AlertTriangle size={16}/>} alert={(s?.high_risk_permissions ?? 0) > 0}/>
          <StatCard label="Unassigned" value={s?.unassigned_permissions ?? 0} icon={<AlertTriangle size={16}/>} alert={(s?.unassigned_permissions ?? 0) > 0}/>
        </div>
      )}

      <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
        <Input placeholder="Search permission key…" value={search} onChange={setSearch}/>
        <Select value={moduleFilter} onChange={setModuleFilter} placeholder="All Modules"
          options={MODULES.map(m => ({ value: m, label: m }))}/>
        <Select value={scopeFilter} onChange={setScopeFilter} placeholder="All App Scopes"
          options={[{ value: "admin", label: "Admin" }, { value: "tenant", label: "Tenant" }, { value: "customer", label: "Customer" }]}/>
        <Select value={riskFilter} onChange={setRiskFilter} placeholder="All Risk Levels"
          options={[{ value: "high", label: "High" }, { value: "medium", label: "Medium" }, { value: "low", label: "Low" }]}/>
      </div>

      {perms.error ? (
        <EmptyState icon={<AlertTriangle/>} title="Could not load permissions."
          description={`${perms.error}${perms.requestId ? ` — Request ID: ${perms.requestId}` : ""}`}
          action={<Btn size="sm" onClick={() => perms.refetch()}>Retry</Btn>}/>
      ) : perms.loading ? (
        <Skeleton height={400} style={{ borderRadius: 12 }}/>
      ) : (perms.data?.items.length ?? 0) === 0 ? (
        <EmptyState icon={<Key/>} title="No permissions match these filters."/>
      ) : (
        <Card style={{ padding: 0, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "var(--surface-sunken)" }}>
                {["Permission Key", "Module", "Scope", "Risk", "Assigned Roles", "Status"].map(h => (
                  <th key={h} style={{ padding: "8px 16px", textAlign: "left", fontSize: 11,
                    fontWeight: 700, color: "var(--text-tertiary)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(perms.data?.items ?? []).map((p: PermissionListItem, i, arr) => (
                <tr key={p.permission_key} style={{ borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none",
                  cursor: "pointer" }} onClick={() => setDetailKey(p)}>
                  <td style={{ padding: "10px 16px", fontFamily: "monospace", fontSize: 12 }}>{p.permission_key}</td>
                  <td style={{ padding: "10px 16px", fontSize: 12 }}>{p.module}</td>
                  <td style={{ padding: "10px 16px" }}><Badge variant={SCOPE_BADGE[p.app_scope] ?? "muted"} size="sm">{p.app_scope}</Badge></td>
                  <td style={{ padding: "10px 16px" }}><Badge variant={RISK_BADGE[p.risk_level]} size="sm">{p.risk_level}</Badge></td>
                  <td style={{ padding: "10px 16px", fontSize: 12 }}>{p.assigned_role_count}</td>
                  <td style={{ padding: "10px 16px" }}><Badge variant="success" size="sm">{p.status}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </AdminLayout>
  );
}
