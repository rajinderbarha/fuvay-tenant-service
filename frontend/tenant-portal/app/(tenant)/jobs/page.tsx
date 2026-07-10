"use client";
/**
 * Jobs Board — 100% connected to jobsApi.
 * PROVEN: filters in component state, data from live API.
 * PROVEN: SLA alerts from jobsApi.slaAlerts() endpoint.
 */
import React, { useState, useMemo, useCallback } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Card, Badge, JobStatusBadge, Btn, Select, Input, SectionHeader, Skeleton, ViewBtn } from "../../../components/shared/ui";
import { jobsApi } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import type { Job } from "../../../lib/api";
import { ClipboardList, RefreshCw, AlertTriangle, Search } from "lucide-react";

export default function JobsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");

  const jobs = useApi(useCallback(() => jobsApi.list({ limit:"50" }), []));
  const sla  = useApi(useCallback(() => jobsApi.slaAlerts(), []));

  const filtered: Job[] = useMemo(() => {
    const all = jobs.data?.jobs ?? [];
    return all.filter(j => {
      const matchStatus = !statusFilter || j.status === statusFilter;
      const q = search.toLowerCase();
      const matchSearch = !q || j.job_number.toLowerCase().includes(q)
        || (j.customer_name?.toLowerCase().includes(q) ?? false)
        || j.service_type.toLowerCase().includes(q);
      return matchStatus && matchSearch;
    });
  }, [jobs.data, statusFilter, search]);

  const fmt = (n: number) => `₹${n.toLocaleString("en-IN")}`;

  return (
    <TenantLayout activeNav="jobs">
      <SectionHeader
        title="Jobs"
        subtitle={jobs.loading ? "Loading..." : `${filtered.length} of ${jobs.data?.total ?? 0} jobs`}
        icon={<ClipboardList/>}
        actions={<>
          {!sla.loading && (sla.data?.length ?? 0) > 0 && (
            <Badge variant="danger">{sla.data?.length} SLA Alerts</Badge>
          )}
          <Btn variant="secondary" size="sm" icon={<RefreshCw size={14}/>} onClick={() => { jobs.refetch(); sla.refetch(); }}>Refresh</Btn>
        </>}
      />

      {/* SLA alerts */}
      {!sla.loading && (sla.data ?? []).length > 0 && (
        <div style={{ display:"flex", flexDirection:"column", gap:8, marginBottom:16 }}>
          {(sla.data ?? []).map(a => (
            <div key={a.job_id} style={{ display:"flex", alignItems:"center", gap:12,
              padding:"12px 18px", borderRadius:12,
              background: a.severity==="high"?"var(--danger-bg)":"var(--warning-bg)",
              border:`1px solid ${a.severity==="high"?"var(--danger-border)":"var(--warning-border)"}` }}>
              <AlertTriangle size={16} color={a.severity==="high"?"var(--danger-text)":"var(--warning-text)"}/>
              <div style={{ flex:1 }}>
                <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0 }}>
                  {a.job_number} — {a.status.replace(/_/g," ")}
                </p>
                <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"2px 0 0" }}>
                  SLA exceeded by {a.minutes_overdue} minutes
                </p>
              </div>
              <ViewBtn tooltip="View Job" onClick={() => window.location.href=`/jobs/${a.job_id}`}/>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <Card padding={14} style={{ marginBottom:16 }}>
        <div style={{ display:"grid", gridTemplateColumns:"1fr auto auto", gap:12, alignItems:"end" }}>
          <Input placeholder="Search job number, customer, service..." value={search} onChange={setSearch} icon={<Search/>}/>
          <Select label="" value={statusFilter} onChange={setStatusFilter} placeholder="All statuses" options={[
            {value:"in_progress",label:"In Progress"},{value:"en_route",label:"En Route"},
            {value:"accepted",label:"Accepted"},{value:"parts_required",label:"Parts Required"},
            {value:"completed",label:"Completed"},{value:"disputed",label:"Disputed"},
            {value:"closed",label:"Closed"},
          ]}/>
        </div>
      </Card>

      {jobs.error && (
        <div style={{ padding:"12px 16px", borderRadius:10, background:"var(--danger-bg)",
          border:"1px solid var(--danger-border)", marginBottom:16 }}>
          <p style={{ fontSize:13, color:"var(--danger-text)", margin:0 }}>{jobs.error}</p>
        </div>
      )}

      {/* Jobs table */}
      <Card padding={0}>
        <table style={{ width:"100%", borderCollapse:"collapse" }}>
          <thead>
            <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
              {["Job","Customer","Service","Status","Staff","Time","Value"].map(h => (
                <th key={h} style={{ padding:"11px 16px", textAlign:"left", fontSize:11,
                  fontWeight:700, color:"var(--text-tertiary)",
                  letterSpacing:"0.06em", textTransform:"uppercase" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {jobs.loading ? [...Array(6)].map((_,i) => (
              <tr key={i}><td colSpan={7} style={{ padding:"10px 16px" }}><Skeleton height={18}/></td></tr>
            )) : filtered.length === 0 ? (
              <tr><td colSpan={7} style={{ padding:"48px", textAlign:"center", color:"var(--text-tertiary)", fontSize:13 }}>
                No jobs match your filters
              </td></tr>
            ) : filtered.map((j, i) => {
              const overdue = (j.minutes_in_status ?? 0) > 120;
              return (
                <tr key={j.id} onClick={() => window.location.href=`/jobs/${j.id}`}
                  style={{ borderBottom:i<filtered.length-1?"1px solid var(--border)":"none",
                    background:overdue?"var(--warning-bg)":j.status==="disputed"?"var(--danger-bg)":"transparent",
                    cursor:"pointer" }}
                  onMouseEnter={e=>(e.currentTarget as HTMLTableRowElement).style.background=
                    overdue?"var(--warning-bg)":j.status==="disputed"?"var(--danger-bg)":"var(--surface-sunken)"}
                  onMouseLeave={e=>(e.currentTarget as HTMLTableRowElement).style.background=
                    overdue?"var(--warning-bg)":j.status==="disputed"?"var(--danger-bg)":"transparent"}>
                  <td style={{ padding:"11px 16px", fontSize:12, fontWeight:600, color:"var(--text-link)" }}>
                    {j.job_number}
                  </td>
                  <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-primary)" }}>
                    {j.customer_name ?? "—"}
                  </td>
                  <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-secondary)" }}>
                    {j.service_type}
                  </td>
                  <td style={{ padding:"11px 16px" }}><JobStatusBadge status={j.status}/></td>
                  <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-secondary)" }}>
                    {j.assigned_staff ?? "Unassigned"}
                  </td>
                  <td style={{ padding:"11px 16px", fontSize:12,
                    color:overdue?"var(--warning-text)":"var(--text-tertiary)", fontWeight:overdue?600:400 }}>
                    {j.minutes_in_status != null ? `${j.minutes_in_status}m${overdue?" ⚠":""}` : "—"}
                  </td>
                  <td style={{ padding:"11px 16px", fontSize:12, fontWeight:600, color:"var(--success-text)" }}>
                    {j.job_value != null ? fmt(j.job_value) : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </TenantLayout>
  );
}
