"use client";
import { TableSurface } from "@serviceos/design-system";
import React, { useCallback, useState } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Card, Badge, Skeleton, Btn, SectionHeader } from "../../../components/shared/ui";
import { authApi } from "../../../lib/api";
import type { UserDetail } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import { Users, RefreshCw, Mail, Phone, ShieldCheck, ShieldOff } from "lucide-react";

const ROLES = ["all", "owner", "manager", "staff", "customer"] as const;
type RoleFilter = typeof ROLES[number];

export default function UsersPage() {
  const [roleFilter, setRoleFilter] = useState<RoleFilter>("all");
  const users = useApi(useCallback(() =>
    authApi.listUsers(roleFilter === "all" ? { limit: 100 } : { role: roleFilter, limit: 100 }),
    [roleFilter]
  ));

  const list: UserDetail[] = users.data?.users ?? [];

  return (
    <TenantLayout activeNav="users">
      <SectionHeader
        title="Team Users"
        subtitle={users.loading ? "Loading..." : `${users.data?.total ?? 0} users`}
        icon={<Users/>}
        actions={
          <Btn variant="ghost" size="sm" icon={<RefreshCw size={14}/>} onClick={users.refetch}>
            Refresh
          </Btn>
        }
      />

      {/* Role filter pills */}
      <div style={{ display:"flex", gap:8, marginBottom:16, flexWrap:"wrap" }}>
        {ROLES.map(r => (
          <button key={r} onClick={() => setRoleFilter(r)}
            style={{ padding:"6px 14px", borderRadius:999, border:"1px solid",
              borderColor: roleFilter === r ? "var(--brand)" : "var(--border)",
              background: roleFilter === r ? "var(--brand)" : "var(--surface)",
              color: roleFilter === r ? "white" : "var(--text-secondary)",
              fontSize:12, fontWeight:600, cursor:"pointer", textTransform:"capitalize" }}>
            {r}
          </button>
        ))}
      </div>

      {users.error && (
        <div style={{ padding:"12px 16px", borderRadius:10, background:"var(--danger-bg)",
          border:"1px solid var(--danger-border)", marginBottom:16 }}>
          <p style={{ fontSize:13, color:"var(--danger-text)", margin:0 }}>{users.error}</p>
        </div>
      )}

      {users.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
          {[...Array(6)].map((_,i) => <Skeleton key={i} height={64} style={{ borderRadius:10 }}/>)}
        </div>
      ) : list.length === 0 ? (
        <Card padding={48} style={{ textAlign:"center" }}>
          <Users size={32} style={{ color:"var(--text-tertiary)", margin:"0 auto 12px", display:"block" }}/>
          <p style={{ fontSize:14, color:"var(--text-secondary)", margin:0 }}>
            No users found{roleFilter !== "all" ? ` with role "${roleFilter}"` : ""}.
          </p>
        </Card>
      ) : (
        <Card padding={0}>
          <TableSurface style={{ width:"100%", borderCollapse:"collapse" }}>
            <thead>
              <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                {["Name","Contact","Role","Status","MFA","Joined"].map(h => (
                  <th key={h} style={{ padding:"10px 16px", textAlign:"left", fontSize:11, fontWeight:700,
                    color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {list.map((u, i) => (
                <tr key={u.user_id}
                  style={{ borderBottom: i < list.length-1 ? "1px solid var(--border)" : "none" }}>
                  <td style={{ padding:"12px 16px" }}>
                    <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0 }}>
                      {u.full_name}
                    </p>
                    {u.is_verified && (
                      <span style={{ fontSize:10, color:"var(--success-text)" }}>✓ Verified</span>
                    )}
                  </td>
                  <td style={{ padding:"12px 16px" }}>
                    <div style={{ display:"flex", flexDirection:"column", gap:3 }}>
                      <div style={{ display:"flex", alignItems:"center", gap:5 }}>
                        <Mail size={10} style={{ color:"var(--text-tertiary)", flexShrink:0 }}/>
                        <span style={{ fontSize:12, color:"var(--text-secondary)" }}>{u.email}</span>
                      </div>
                      {u.phone && (
                        <div style={{ display:"flex", alignItems:"center", gap:5 }}>
                          <Phone size={10} style={{ color:"var(--text-tertiary)", flexShrink:0 }}/>
                          <span style={{ fontSize:12, color:"var(--text-secondary)" }}>{u.phone}</span>
                        </div>
                      )}
                    </div>
                  </td>
                  <td style={{ padding:"12px 16px" }}>
                    <Badge variant="muted" size="sm">{u.role}</Badge>
                  </td>
                  <td style={{ padding:"12px 16px" }}>
                    <Badge variant={u.is_active ? "success" : "danger"} size="sm">
                      {u.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                  <td style={{ padding:"12px 16px" }}>
                    {u.is_mfa_enabled
                      ? <ShieldCheck size={15} style={{ color:"var(--success-text)" }}/>
                      : <ShieldOff size={15} style={{ color:"var(--text-tertiary)" }}/>}
                  </td>
                  <td style={{ padding:"12px 16px", fontSize:12, color:"var(--text-tertiary)" }}>
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </TableSurface>
        </Card>
      )}
    </TenantLayout>
  );
}
