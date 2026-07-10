"use client";
import React, { useCallback } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Card, Badge, Avatar, Skeleton, Btn } from "../../../components/shared/ui";
import { PageShell, PageHeader, SearchBar } from "../../../components/shared/layout";
import { staffApi, dsApi } from "../../../lib/api";
import type { UserDetail } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import { useState } from "react";
import { Plus, RefreshCw, Mail, Phone } from "lucide-react";

export default function StaffPage() {
  const staff  = useApi(useCallback(() => staffApi.list(), []));
  const scores = useApi(useCallback(() => dsApi.staffRankings(), []));
  const [search, setSearch] = useState("");

  const scoreMap = Object.fromEntries(
    (scores.data?.rankings ?? []).map((s: { staff_id:string; composite_score:number }) => [s.staff_id, s.composite_score])
  );

  const allList: UserDetail[] = staff.data?.users ?? [];
  const list = search
    ? allList.filter(s =>
        s.full_name.toLowerCase().includes(search.toLowerCase()) ||
        s.email.toLowerCase().includes(search.toLowerCase())
      )
    : allList;

  return (
    <TenantLayout activeNav="staff">
      <PageShell>
      <PageHeader
        title="Staff"
        description={staff.loading ? "Loading…" : `${staff.data?.total ?? 0} team members`}
        primaryAction={
          <Btn variant="primary" size="sm" icon={<Plus size={14}/>}
            onClick={() => window.location.href="/staff/invite"}>
            Add Staff
          </Btn>
        }
        secondaryActions={[
          { label: "Refresh", onClick: staff.refetch },
        ]}
      />
      <SearchBar value={search} onChange={setSearch} placeholder="Search by name or email…" />

      {staff.error && (
        <div style={{ padding:"12px 16px", borderRadius:10, background:"var(--danger-bg)",
          border:"1px solid var(--danger-border)", marginBottom:16 }}>
          <p style={{ fontSize:13, color:"var(--danger-text)", margin:0 }}>{staff.error}</p>
        </div>
      )}

      {staff.loading ? (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(280px,1fr))", gap:14 }}>
          {[...Array(6)].map((_,i) => <Skeleton key={i} height={140} style={{ borderRadius:14 }}/>)}
        </div>
      ) : list.length === 0 ? (
        <Card padding={48} style={{ textAlign:"center" }}>
          <p style={{ fontSize:14, color:"var(--text-secondary)", margin:0 }}>
            No staff members yet. Invite someone to get started.
          </p>
        </Card>
      ) : (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(280px,1fr))", gap:14 }}>
          {list.map((s: UserDetail) => {
            const score = scoreMap[s.user_id] ?? 0;
            return (
              <Card key={s.user_id} padding={18} hover
                onClick={() => window.location.href=`/staff/${s.user_id}`}>
                <div style={{ display:"flex", alignItems:"center", gap:12, marginBottom:14 }}>
                  <div style={{ position:"relative" }}>
                    <Avatar name={s.full_name} size={44}/>
                    <span style={{ position:"absolute", bottom:0, right:0,
                      width:12, height:12, borderRadius:"50%",
                      background: s.is_active ? "var(--success)" : "var(--border-strong)",
                      border:"2px solid var(--surface)" }}/>
                  </div>
                  <div style={{ flex:1, minWidth:0 }}>
                    <p style={{ fontSize:14, fontWeight:600, color:"var(--text-primary)",
                      margin:0, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                      {s.full_name}
                    </p>
                    <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0" }}>
                      {s.role}
                    </p>
                  </div>
                  <Badge variant={s.is_active ? "success" : "muted"} size="sm">
                    {s.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>

                {/* Contact */}
                <div style={{ display:"flex", flexDirection:"column", gap:5, marginBottom:12 }}>
                  <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                    <Mail size={11} style={{ color:"var(--text-tertiary)", flexShrink:0 }}/>
                    <span style={{ fontSize:11, color:"var(--text-secondary)",
                      overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                      {s.email}
                    </span>
                  </div>
                  {s.phone && (
                    <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                      <Phone size={11} style={{ color:"var(--text-tertiary)", flexShrink:0 }}/>
                      <span style={{ fontSize:11, color:"var(--text-secondary)" }}>{s.phone}</span>
                    </div>
                  )}
                </div>

                {/* Performance score bar (from DS engine) */}
                {!scores.loading && score > 0 && (
                  <div>
                    <div style={{ display:"flex", justifyContent:"space-between", marginBottom:5 }}>
                      <span style={{ fontSize:11, color:"var(--text-tertiary)", fontWeight:600,
                        textTransform:"uppercase", letterSpacing:"0.05em" }}>Performance</span>
                      <span style={{ fontSize:13, fontWeight:700,
                        color: score >= 80 ? "var(--success-text)" : score >= 60 ? "var(--warning-text)" : "var(--danger-text)" }}>
                        {score.toFixed(0)}%
                      </span>
                    </div>
                    <div style={{ height:6, background:"var(--border)", borderRadius:999, overflow:"hidden" }}>
                      <div style={{ height:"100%", width:`${Math.min(100,score)}%`,
                        background: score >= 80 ? "var(--success)" : score >= 60 ? "var(--warning)" : "var(--danger)",
                        borderRadius:999, transition:"width 0.5s ease" }}/>
                    </div>
                  </div>
                )}

                {/* Verification status */}
                <div style={{ display:"flex", gap:6, marginTop:10 }}>
                  {s.is_verified && <Badge variant="info" size="sm">Verified</Badge>}
                  {s.is_mfa_enabled && <Badge variant="muted" size="sm">MFA On</Badge>}
                </div>
              </Card>
            );
          })}
        </div>
      )}
      </PageShell>
    </TenantLayout>
  );
}
