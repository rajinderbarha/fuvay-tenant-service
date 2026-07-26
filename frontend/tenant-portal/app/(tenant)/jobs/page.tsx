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
import Link from "next/link";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { PageHeader, Card, StatusBadge, DataTable, Button, type DataTableColumn } from "@serviceos/design-system";
import { Badge, Select, Input } from "../../../components/shared/ui";
import { serviceJobsApi, getUserRole } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import type { ServiceJobRecord } from "../../../lib/api";
import { RefreshCw, Search } from "lucide-react";
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

  const columns: DataTableColumn<ServiceJobRecord>[] = [
    { key: "job_number", header: "Job", render: (j) => (
      <Link href={`/jobs/${j.id}`} style={{ fontWeight: 600, color: "var(--text-link)" }}>{j.job_number}</Link>
    ) },
    { key: "location", header: "Zipcode", accessor: (j) => j.zipcode ?? j.city ?? "—" },
    { key: "status", header: "Status", render: (j) => <StatusBadge status={j.status} /> },
    { key: "assignment_status", header: "Assignment", render: (j) => (
      <Badge variant={j.assignment_status === "unassigned" ? "warning" : "success"}>
        {j.assignment_status.replace(/_/g, " ")}
      </Badge>
    ) },
    { key: "assigned_staff_id", header: "Staff", accessor: (j) => shortId(j.assigned_staff_id) },
    { key: "scheduled_date", header: "Scheduled", accessor: (j) => j.scheduled_date ? `${j.scheduled_date} ${j.scheduled_time_window ?? ""}` : "—" },
  ];

  return (
    <TenantLayout activeNav="jobs">
      <ReadOnlyBanner role={getUserRole()}/>
      <PageHeader
        title="Jobs"
        description={jobs.loading ? "Loading..." : `${filtered.length} of ${jobs.data?.total ?? 0} jobs — ServiceBooking -> ServiceJob pipeline`}
        actions={
          <Button variant="secondary" size="sm" leftIcon={<RefreshCw size={14}/>} onClick={() => jobs.refetch()}>Refresh</Button>
        }
      />

      {/* Filters */}
      <Card padding="sm" style={{ marginBottom: 16 }}>
        <div style={{ display:"grid", gridTemplateColumns:"1fr auto auto", gap:12, alignItems:"end" }}>
          <Input placeholder="Search job number, zipcode..." value={search} onChange={setSearch} icon={<Search/>}/>
          <Select label="" value={statusFilter} onChange={setStatusFilter} placeholder="All statuses" options={[
            {value:"new",label:"New"},{value:"assigned",label:"Assigned"},
            {value:"in_progress",label:"In Progress"},{value:"completed",label:"Completed"},
            {value:"cancelled",label:"Cancelled"},
          ]}/>
        </div>
      </Card>

      {/* Jobs table */}
      <DataTable<ServiceJobRecord>
        columns={columns}
        rows={filtered}
        rowKey={(j) => j.id}
        loading={jobs.loading}
        error={jobs.error ?? undefined}
        emptyTitle="No jobs match your filters"
      />
    </TenantLayout>
  );
}
