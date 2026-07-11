"use client";
/**
 * Jobs Board — FINAL-L5-01D: migrated off legacy jobsApi (/v1/jobs, field_ops
 * table) onto serviceJobsApi (/v1/provider/my-records/jobs, canonical
 * service_jobs table). See docs/final-l5-01d/FINAL_L5_01D_TENANT_JOBS_API_MIGRATION_REPORT.md.
 *
 * The canonical endpoint returns raw customer_id/assigned_staff_id (no
 * resolved display names) — shown as short IDs rather than fabricated
 * names, per the no-mock-data rule.
 */
import React, { useState, useMemo, useCallback } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Card, Badge, JobStatusBadge, Btn, Select, Input, SectionHeader, Skeleton } from "../../../components/shared/ui";
import { serviceJobsApi, getUserRole } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import type { ServiceJobRecord } from "../../../lib/api";
import { ClipboardList, RefreshCw, Search } from "lucide-react";
import ReadOnlyBanner from "../../../components/shared/ReadOnlyBanner";

const shortId = (id?: string | null) => (id ? `${id.slice(0, 8)}…` : "—");

export default function JobsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");

  const jobs = useApi(useCallback(() => serviceJobsApi.list({ limit: 50 }), []));

  const filtered: ServiceJobRecord[] = useMemo(() => {
    const all = jobs.data?.items ?? [];
    return all.filter((j) => {
      const matchStatus = !statusFilter || j.status === statusFilter;
      const q = search.toLowerCase();
      const matchSearch = !q || j.job_number.toLowerCase().includes(q) || (j.zipcode ?? "").includes(q);
      return matchStatus && matchSearch;
    });
  }, [jobs.data, statusFilter, search]);

  return (
    <TenantLayout activeNav="jobs">
      <ReadOnlyBanner role={getUserRole()}/>
      <SectionHeader
        title="Jobs"
        subtitle={jobs.loading ? "Loading..." : `${filtered.length} of ${jobs.data?.total ?? 0} jobs`}
        icon={<ClipboardList/>}
        actions={
          <Btn variant="secondary" size="sm" icon={<RefreshCw size={14}/>} onClick={() => jobs.refetch()}>Refresh</Btn>
        }
      />

      {/* Filters */}
      <Card padding={14} style={{ marginBottom:16 }}>
        <div style={{ display:"grid", gridTemplateColumns:"1fr auto auto", gap:12, alignItems:"end" }}>
          <Input placeholder="Search job number, zipcode..." value={search} onChange={setSearch} icon={<Search/>}/>
          <Select label="" value={statusFilter} onChange={setStatusFilter} placeholder="All statuses" options={[
            {value:"new",label:"New"},{value:"assigned",label:"Assigned"},
            {value:"in_progress",label:"In Progress"},{value:"completed",label:"Completed"},
            {value:"cancelled",label:"Cancelled"},
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
              {["Job","Zipcode","Status","Assignment","Staff","Scheduled"].map(h => (
                <th key={h} style={{ padding:"11px 16px", textAlign:"left", fontSize:11,
                  fontWeight:700, color:"var(--text-tertiary)",
                  letterSpacing:"0.06em", textTransform:"uppercase" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {jobs.loading ? [...Array(6)].map((_,i) => (
              <tr key={i}><td colSpan={6} style={{ padding:"10px 16px" }}><Skeleton height={18}/></td></tr>
            )) : filtered.length === 0 ? (
              <tr><td colSpan={6} style={{ padding:"48px", textAlign:"center", color:"var(--text-tertiary)", fontSize:13 }}>
                No jobs match your filters
              </td></tr>
            ) : filtered.map((j, i) => (
                <tr key={j.id} onClick={() => window.location.href=`/jobs/${j.id}`}
                  style={{ borderBottom:i<filtered.length-1?"1px solid var(--border)":"none", cursor:"pointer" }}
                  onMouseEnter={e=>(e.currentTarget as HTMLTableRowElement).style.background="var(--surface-sunken)"}
                  onMouseLeave={e=>(e.currentTarget as HTMLTableRowElement).style.background="transparent"}>
                  <td style={{ padding:"11px 16px", fontSize:12, fontWeight:600, color:"var(--text-link)" }}>
                    {j.job_number}
                  </td>
                  <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-secondary)" }}>
                    {j.zipcode ?? j.city ?? "—"}
                  </td>
                  <td style={{ padding:"11px 16px" }}><JobStatusBadge status={j.status}/></td>
                  <td style={{ padding:"11px 16px" }}>
                    <Badge variant={j.assignment_status === "unassigned" ? "warning" : "success"}>
                      {j.assignment_status.replace(/_/g," ")}
                    </Badge>
                  </td>
                  <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-secondary)" }}>
                    {shortId(j.assigned_staff_id)}
                  </td>
                  <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-tertiary)" }}>
                    {j.scheduled_date ? `${j.scheduled_date} ${j.scheduled_time_window ?? ""}` : "—"}
                  </td>
                </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </TenantLayout>
  );
}
