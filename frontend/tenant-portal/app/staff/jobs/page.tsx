"use client";
import { TableSurface } from "@serviceos/design-system";
import React, { useCallback, useState } from "react";
import Link from "next/link";
import { StaffLayout } from "../../../components/layout/StaffLayout";
import { Card, StatCard, Badge, Skeleton, EmptyState } from "../../../components/shared/ui";
import { useApi } from "../../../hooks/useApi";
import { homeServiceStaffJobsApi } from "../../../lib/api";
import { ClipboardList } from "lucide-react";

// MODULE-L5-38: this page (and the detail + dashboard below) called
// staffSelfApi.getMyJobs -> /v1/staff/me/jobs, the dead field_ops staff
// router whose `jobs` table has 0 rows platform-wide -- a technician logging
// into the web portal saw zero jobs and all-disabled actions with stale
// "not certified yet" copy. Repointed to the real, live-verified
// home_service_assignment + execution pipeline (/v1/staff/service-jobs),
// the same one the staff-app mobile was moved to in MODULE-L5-36.
const ACTIVE_STATUSES = new Set([
  "accepted", "on_the_way", "reached_site", "inspection_started",
  "inspection_done", "quote_required", "service_started", "work_done",
]);
const TABS = [
  { id: "assigned", label: "Assigned", match: (s: string) => s === "assigned" },
  { id: "active", label: "Active", match: (s: string) => ACTIVE_STATUSES.has(s) },
  { id: "completed", label: "Completed", match: (s: string) => s === "completed" },
  // Phase 2A.1: closed_estimate_declined (customer declined the estimate) is
  // terminal like cancelled/failed -- without this it fell into no tab at
  // all and vanished from the staff job list entirely.
  { id: "cancelled", label: "Cancelled", match: (s: string) => s === "cancelled" || s === "failed" || s === "closed_estimate_declined" },
] as const;

export default function StaffJobsPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("assigned");

  const jobs = useApi(useCallback(() => homeServiceStaffJobsApi.list(), []));
  const match = TABS.find(t => t.id === tab)!.match;
  const list = (jobs.data?.jobs ?? []).filter(j => match(j.status));

  return (
    <StaffLayout activeNav="jobs">
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>Assigned Work</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
          Jobs assigned to you. Open a job to accept it and run it through to completion.
        </p>
      </div>

      <div style={{ marginBottom: 20 }}>
        {jobs.loading ? <Skeleton height={92}/> : <StatCard label={`${TABS.find(t => t.id === tab)!.label} Jobs`} value={list.length} icon={<ClipboardList/>}/>}
      </div>

      <div style={{ display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap" }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            style={{
              padding: "6px 14px", borderRadius:"var(--radius-md)", fontSize: 12, fontWeight: 600, cursor: "pointer",
              border: "1px solid var(--border)",
              background: tab === t.id ? "var(--accent, var(--brand))" : "var(--card-bg)",
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
            description="New jobs assigned to you will appear here."/>
        ) : (
          <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["Job #", "City", "Status", "Scheduled", ""].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {list.map(j => (
                <tr key={j.id} style={{ borderBottom: "1px solid var(--border-subtle, var(--border))" }}>
                  <td style={{ padding: "10px 16px" }}>{j.job_number || j.id.slice(0, 8)}</td>
                  <td style={{ padding: "10px 16px" }}>{[j.city, j.zipcode].filter(Boolean).join(", ") || "—"}</td>
                  <td style={{ padding: "10px 16px" }}><Badge variant="info" size="sm">{j.status}</Badge></td>
                  <td style={{ padding: "10px 16px", color: "var(--text-tertiary)" }}>{j.scheduled_date ? `${j.scheduled_date}${j.scheduled_time_window ? ` · ${j.scheduled_time_window}` : ""}` : "—"}</td>
                  <td style={{ padding: "10px 16px" }}>
                    <Link href={`/staff/jobs/${j.id}`} style={{ fontSize: 12, fontWeight: 600, color: "var(--accent, var(--brand))" }}>View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </TableSurface>
        )}
      </Card>
    </StaffLayout>
  );
}
