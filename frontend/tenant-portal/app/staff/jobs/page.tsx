"use client";
import React, { useCallback, useState } from "react";
import Link from "next/link";
import { StaffLayout } from "../../../components/layout/StaffLayout";
import { Card, StatCard, Badge, Skeleton, EmptyState } from "../../../components/shared/ui";
import { useApi } from "../../../hooks/useApi";
import { staffSelfApi, getTenantId } from "../../../lib/api";
import { ClipboardList } from "lucide-react";

const TABS = [
  { id: "assigned", label: "Assigned", status: "assigned" },
  { id: "scheduled", label: "Scheduled", status: "scheduled" },
  { id: "pending", label: "Pending Acceptance", status: "pending_acceptance" },
  { id: "completed", label: "Completed", status: "completed" },
  { id: "cancelled", label: "Cancelled", status: "cancelled" },
] as const;

export default function StaffJobsPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("assigned");
  const tenantId = getTenantId() || "";
  const activeStatus = TABS.find(t => t.id === tab)!.status;

  const jobs = useApi(
    useCallback(() => (tenantId ? staffSelfApi.getMyJobs(tenantId, activeStatus) : Promise.resolve({ jobs: [], has_next: false, next_cursor: null })), [tenantId, activeStatus]),
    [tenantId, activeStatus]
  );
  const list = jobs.data?.jobs ?? [];

  return (
    <StaffLayout activeNav="jobs">
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>Assigned Work</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
          Jobs assigned to you. Job execution runtime (start, on-the-way, in-progress, completion, payment) is not certified for this app yet.
        </p>
      </div>

      <div style={{ marginBottom: 20 }}>
        {jobs.loading ? <Skeleton height={92}/> : <StatCard label={`${TABS.find(t => t.id === tab)!.label} Jobs`} value={list.length} icon={<ClipboardList/>}/>}
      </div>

      <div style={{ display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap" }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            style={{
              padding: "6px 14px", borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: "pointer",
              border: "1px solid var(--border)",
              background: tab === t.id ? "var(--accent, #2563eb)" : "var(--card-bg)",
              color: tab === t.id ? "#fff" : "var(--text)",
            }}>
            {t.label}
          </button>
        ))}
      </div>

      <Card padding={0}>
        {jobs.loading ? <Skeleton height={160}/> : jobs.error ? (
          <div style={{ padding: 20 }}>
            <p style={{ color: "var(--danger-text)", fontSize: 13 }}>{jobs.error}{jobs.requestId && ` — Request ID: ${jobs.requestId}`}</p>
          </div>
        ) : list.length === 0 ? (
          <EmptyState icon={<ClipboardList/>} title="No jobs in this category yet."
            description="New assigned jobs will appear here when booking assignment runtime is enabled."/>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["Job #", "Service", "City", "Status", "Scheduled", ""].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {list.map(j => (
                <tr key={j.job_id} style={{ borderBottom: "1px solid var(--border-subtle, var(--border))" }}>
                  <td style={{ padding: "10px 16px" }}>{j.job_number || j.job_id.slice(0, 8)}</td>
                  <td style={{ padding: "10px 16px" }}>{j.service_category || j.job_type || "—"}</td>
                  <td style={{ padding: "10px 16px" }}>{j.city || "—"}</td>
                  <td style={{ padding: "10px 16px" }}><Badge variant="info" size="sm">{j.status}</Badge></td>
                  <td style={{ padding: "10px 16px", color: "var(--text-tertiary)" }}>{j.scheduled_at ? new Date(j.scheduled_at).toLocaleString() : "—"}</td>
                  <td style={{ padding: "10px 16px" }}>
                    <Link href={`/staff/jobs/${j.job_id}`} style={{ fontSize: 12, fontWeight: 600, color: "var(--accent, #2563eb)" }}>View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </StaffLayout>
  );
}
