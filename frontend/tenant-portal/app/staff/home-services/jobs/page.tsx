"use client";
import React, { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import { StaffLayout } from "../../../../components/layout/StaffLayout";
import { Card, StatCard, Badge, Skeleton, EmptyState } from "../../../../components/shared/ui";
import { useApi } from "../../../../hooks/useApi";
import { homeServiceStaffJobsApi } from "../../../../lib/api";
import { ClipboardList } from "lucide-react";

const TABS = [
  { id: "today",       label: "Today" },
  { id: "in_progress",  label: "In Progress" },
  { id: "needs_parts",  label: "Needs Parts" },
  { id: "completed",    label: "Completed" },
  { id: "all",          label: "All" },
] as const;

const IN_PROGRESS_STATUSES = new Set([
  "accepted", "scheduled", "on_the_way", "reached_site",
  "inspection_started", "inspection_done", "service_started",
]);

export default function StaffHomeServiceJobsPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("today");
  const jobs = useApi(useCallback(() => homeServiceStaffJobsApi.list(), []), []);
  const list = jobs.data?.jobs ?? [];

  const filtered = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10);
    switch (tab) {
      case "today":       return list.filter(j => j.scheduled_date === today || IN_PROGRESS_STATUSES.has(j.status));
      case "in_progress":  return list.filter(j => IN_PROGRESS_STATUSES.has(j.status));
      case "needs_parts":  return list.filter(j => j.status === "quote_required");
      case "completed":    return list.filter(j => j.status === "completed" || j.status === "work_done");
      default:              return list;
    }
  }, [list, tab]);

  return (
    <StaffLayout activeNav="jobs">
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>Assigned Jobs</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
          Home Services jobs assigned to you — accept, update status, request parts, and complete jobs here.
        </p>
      </div>

      <div style={{ marginBottom: 20 }}>
        {jobs.loading ? <Skeleton height={92}/> : <StatCard label="Total Assigned" value={list.length} icon={<ClipboardList/>}/>}
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
        ) : filtered.length === 0 ? (
          <EmptyState icon={<ClipboardList/>} title="No jobs in this category yet."
            description="New assigned jobs will appear here."/>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["Job #", "City", "Status", "Scheduled", ""].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(j => (
                <tr key={j.id} style={{ borderBottom: "1px solid var(--border-subtle, var(--border))" }}>
                  <td style={{ padding: "10px 16px" }}>{j.job_number}</td>
                  <td style={{ padding: "10px 16px" }}>{j.city ?? "—"}</td>
                  <td style={{ padding: "10px 16px" }}><Badge variant="info" size="sm">{j.status}</Badge></td>
                  <td style={{ padding: "10px 16px", color: "var(--text-tertiary)" }}>{j.scheduled_date ?? "—"}</td>
                  <td style={{ padding: "10px 16px" }}>
                    <Link href={`/staff/home-services/jobs/${j.id}`} style={{ fontSize: 12, fontWeight: 600, color: "var(--accent, #2563eb)" }}>View</Link>
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
