"use client";
/**
 * Phase 1B — Admin Roles page.
 * ServiceOS RBAC is code-defined (app/core/permissions.py), not a DB CRUD
 * system — this page renders the real, live-computed role data (permission
 * counts, assigned user counts) rather than a fake editable table.
 */
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, StatCard, SectionHeader, Skeleton, EmptyState } from "../../../../components/shared/ui";
import { Shield, Users, AlertTriangle, CheckCircle2 } from "lucide-react";
import { rolesPermissionsApi, RoleListItem } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import { RequirePermission } from "../../../../components/shared/PermissionGate";

const SCOPE_BADGE: Record<string, "info" | "success" | "muted"> = {
  platform: "info", tenant: "success", customer: "muted", public: "muted",
};

export default function RolesPage() {
  const [detailRole, setDetailRole] = useState<string | null>(null);
  const roles = useApi(useCallback(() => rolesPermissionsApi.listRoles(), []));
  const detail = useApi(useCallback(
    () => detailRole ? rolesPermissionsApi.getRole(detailRole) : Promise.resolve(null),
    [detailRole]), [detailRole]);

  const s = roles.data?.summary;

  return (
    <AdminLayout activeNav="users">
      <RequirePermission requiredPermission="platform:roles:read" parentLabel="Dashboard">
      {detailRole && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 200,
          display: "flex", justifyContent: "flex-end" }} onClick={() => setDetailRole(null)}>
          <div style={{ width: "min(560px,95vw)", background: "var(--surface)", overflowY: "auto",
            boxShadow: "-4px 0 32px rgba(0,0,0,0.25)" }} onClick={e => e.stopPropagation()}>
            <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border)",
              display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>{detail.data?.label ?? detailRole}</h2>
              <Btn variant="ghost" size="sm" onClick={() => setDetailRole(null)}>✕</Btn>
            </div>
            <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 20 }}>
              {detail.loading ? <Skeleton height={200}/> : detail.data && (
                <>
                  {!detail.data.is_implemented && (
                    <Card style={{ padding: 14, background: "var(--warning-bg)", border: "1px solid var(--warning-border)" }}>
                      <p style={{ fontSize: 12, color: "var(--warning-text)", margin: 0 }}>
                        This role is named in the certification spec but not yet implemented in
                        <code> app/core/permissions.py</code>. No users can currently be assigned
                        this role, and it grants no permissions.
                      </p>
                    </Card>
                  )}
                  <div>
                    <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                      textTransform: "uppercase", margin: "0 0 8px" }}>Overview</p>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <Badge variant={detail.data.type === "system" ? "info" : "muted"}>{detail.data.type}</Badge>
                      <Badge variant={SCOPE_BADGE[detail.data.scope] ?? "muted"}>{detail.data.scope}</Badge>
                      <Badge variant={detail.data.is_implemented ? "success" : "danger"}>
                        {detail.data.is_implemented ? "Implemented" : "Not Implemented"}
                      </Badge>
                    </div>
                  </div>
                  <div>
                    <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                      textTransform: "uppercase", margin: "0 0 8px" }}>
                      Permission Matrix ({detail.data.permission_count})
                    </p>
                    <div style={{ maxHeight: 240, overflowY: "auto", display: "flex", flexDirection: "column", gap: 4 }}>
                      {detail.data.permissions.map((p, i) => (
                        <p key={i} style={{ fontSize: 12, fontFamily: "monospace", color: "var(--text-secondary)", margin: 0 }}>{p}</p>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                      textTransform: "uppercase", margin: "0 0 8px" }}>
                      Assigned Users ({detail.data.assigned_user_count})
                    </p>
                    {detail.data.assigned_users.length === 0 ? (
                      <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>No users assigned.</p>
                    ) : detail.data.assigned_users.map(u => (
                      <div key={u.id} style={{ display: "flex", justifyContent: "space-between",
                        padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                        <span style={{ fontSize: 12 }}>{u.email}</span>
                        <Badge variant={u.is_active ? "success" : "muted"} size="sm">
                          {u.is_active ? "active" : "inactive"}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      <SectionHeader title="Roles" subtitle="Platform RBAC roles — code-defined in app/core/permissions.py, enriched with live assignment data."
        actions={<Btn size="sm" variant="ghost" onClick={() => roles.refetch()}>Refresh</Btn>}/>

      {roles.loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))", gap: 12, marginBottom: 20 }}>
          {[...Array(6)].map((_, i) => <Skeleton key={i} height={88} style={{ borderRadius:"var(--radius-lg)" }}/>)}
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))", gap: 12, marginBottom: 20 }}>
          <StatCard label="Total Roles" value={s?.total_roles ?? 0} icon={<Shield size={16}/>}/>
          <StatCard label="System Roles" value={s?.system_roles ?? 0} icon={<Shield size={16}/>}/>
          <StatCard label="Custom Roles" value={s?.custom_roles ?? 0} icon={<Shield size={16}/>}/>
          <StatCard label="Active Roles" value={s?.active_roles ?? 0} icon={<CheckCircle2 size={16}/>}/>
          <StatCard label="Users Assigned" value={s?.users_assigned ?? 0} icon={<Users size={16}/>}/>
          <StatCard label="Permission Gaps" value={s?.permission_gaps ?? 0} icon={<AlertTriangle size={16}/>}
            alert={(s?.permission_gaps ?? 0) > 0}/>
        </div>
      )}

      {roles.error ? (
        <EmptyState icon={<AlertTriangle/>} title="Could not load roles."
          description={`${roles.error}${roles.requestId ? ` — Request ID: ${roles.requestId}` : ""}`}
          action={<Btn size="sm" onClick={() => roles.refetch()}>Retry</Btn>}/>
      ) : roles.loading ? (
        <Skeleton height={300} style={{ borderRadius:"var(--radius-lg)" }}/>
      ) : (roles.data?.items.length ?? 0) === 0 ? (
        <EmptyState icon={<Shield/>} title="No roles found."/>
      ) : (
        <Card style={{ padding: 0, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "var(--surface-sunken)" }}>
                {["Role", "Type", "Scope", "Users", "Permissions", "Status", "Actions"].map(h => (
                  <th key={h} style={{ padding: "8px 16px", textAlign: "left", fontSize: 11,
                    fontWeight: 700, color: "var(--text-tertiary)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(roles.data?.items ?? []).map((role: RoleListItem, i, arr) => (
                <tr key={role.role_id} style={{ borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <td style={{ padding: "10px 16px", fontWeight: 600 }}>{role.label}</td>
                  <td style={{ padding: "10px 16px" }}><Badge variant={role.type === "system" ? "info" : "muted"} size="sm">{role.type}</Badge></td>
                  <td style={{ padding: "10px 16px" }}><Badge variant={SCOPE_BADGE[role.scope] ?? "muted"} size="sm">{role.scope}</Badge></td>
                  <td style={{ padding: "10px 16px" }}>{role.user_count}</td>
                  <td style={{ padding: "10px 16px" }}>{role.permission_count}</td>
                  <td style={{ padding: "10px 16px" }}>
                    <Badge variant={role.is_implemented ? "success" : "danger"} size="sm">
                      {role.is_implemented ? "Implemented" : "Not Implemented"}
                    </Badge>
                  </td>
                  <td style={{ padding: "10px 16px" }}>
                    <Btn size="xs" variant="secondary" onClick={() => setDetailRole(role.role_key)}>View</Btn>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      </RequirePermission>
    </AdminLayout>
  );
}
