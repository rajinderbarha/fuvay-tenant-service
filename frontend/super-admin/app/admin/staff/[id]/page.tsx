"use client";
import React, { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader, DataTable } from "../../../../components/shared/ui";
import { adminStaffApi, AdminStaffMember } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import { ArrowLeft, ExternalLink } from "lucide-react";
import Link from "next/link";

const AVAIL_BADGE: Record<string, "success" | "warning" | "danger" | "muted"> = {
  available: "success", busy: "warning", inactive: "muted",
};

const JOB_STATUS_BADGE: Record<string, "success" | "warning" | "danger" | "info" | "muted"> = {
  completed: "success", in_progress: "info", assigned: "info",
  pending_start: "warning", on_the_way: "warning", cancelled: "danger",
};

function InfoRow({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div style={{ display: "flex", gap: 12, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
      <div style={{ width: 160, fontSize: 12, color: "var(--muted-text)", flexShrink: 0 }}>{label}</div>
      <div style={{ fontSize: 13, color: "var(--text)", fontWeight: 500 }}>{value ?? "—"}</div>
    </div>
  );
}

export default function StaffDetailPage() {
  const params = useParams<{ id: string }>();
  const staffId = params?.id ?? "";
  const [tab, setTab] = useState<"overview" | "jobs">("overview");

  const staffFetch = useApi(useCallback(() => adminStaffApi.get(staffId), [staffId]));
  const staff: AdminStaffMember | null =
    (staffFetch.data as { data?: AdminStaffMember } | null)?.data ?? null;

  const jobsFetch = useApi(useCallback(() => adminStaffApi.jobs(staffId, { page: 1 }), [staffId]));
  type JobRow = { id: string; booking_number: string; tenant_name: string; service_category: string; status: string; customer_rating: number | null; city: string; completed_at: string | null; created_at: string | null };
  type JobsData = { jobs: JobRow[]; meta: { page: number; total: number; total_pages: number } };
  const jobsData: JobsData | undefined =
    (jobsFetch.data as { data?: JobsData } | null)?.data;
  const jobs = jobsData?.jobs ?? [];
  const jobsMeta = jobsData?.meta;

  const jobColumns = [
    {
      key: "booking_number", label: "Job #", width: 130,
      render: (_: unknown, row: JobRow) => (
        <span style={{ fontFamily: "monospace", fontSize: 12, fontWeight: 600 }}>{row.booking_number || "—"}</span>
      ),
    },
    {
      key: "tenant_name", label: "Provider",
      render: (_: unknown, row: JobRow) => <span style={{ fontSize: 13 }}>{row.tenant_name || "—"}</span>,
    },
    {
      key: "service_category", label: "Category",
      render: (_: unknown, row: JobRow) => <span style={{ fontSize: 12 }}>{row.service_category || "—"}</span>,
    },
    {
      key: "status", label: "Status", width: 140,
      render: (_: unknown, row: JobRow) => (
        <Badge variant={JOB_STATUS_BADGE[row.status] ?? "muted"}>{row.status.replace(/_/g, " ")}</Badge>
      ),
    },
    {
      key: "city", label: "City", width: 100,
      render: (_: unknown, row: JobRow) => <span style={{ fontSize: 12, color: "var(--muted-text)" }}>{row.city || "—"}</span>,
    },
    {
      key: "customer_rating", label: "Rating", width: 80,
      render: (_: unknown, row: JobRow) => (
        <span style={{ fontSize: 13 }}>
          {row.customer_rating != null
            ? <><span style={{ color: "#f59e0b" }}>★</span> {row.customer_rating}</>
            : <span style={{ color: "var(--muted-text)" }}>—</span>}
        </span>
      ),
    },
    {
      key: "created_at", label: "Date", width: 100,
      render: (_: unknown, row: JobRow) => {
        const d = row.created_at ? new Date(row.created_at) : null;
        return <span style={{ fontSize: 12, color: "var(--muted-text)" }}>{d ? d.toLocaleDateString("en-IN") : "—"}</span>;
      },
    },
  ];

  const tabStyle = (t: typeof tab): React.CSSProperties => ({
    padding: "8px 18px", border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600,
    borderBottom: `2px solid ${tab === t ? "var(--primary)" : "transparent"}`,
    color: tab === t ? "var(--primary)" : "var(--muted-text)",
    background: "transparent",
  });

  return (
    <AdminLayout activeNav="staff">
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
        <Link href="/admin/staff" style={{ color: "var(--muted-text)", display: "flex", alignItems: "center", gap: 4, fontSize: 13, textDecoration: "none" }}>
          <ArrowLeft size={15} /> Staff
        </Link>
      </div>

      <SectionHeader
        title={staffFetch.loading ? "Loading…" : (staff?.full_name ?? "Staff Member")}
        subtitle={staff ? `Staff ID: ${staffId}` : ""}
      />

      {staffFetch.error ? (
        <Card padding={32} style={{ textAlign: "center" }}>
          <p style={{ color: "var(--danger-text,#b91c1c)", fontSize: 14 }}>
            Could not load staff member. {staffFetch.error}
          </p>
          <Btn variant="secondary" size="sm" onClick={() => staffFetch.refetch()} style={{ marginTop: 12 }}>
            Retry
          </Btn>
        </Card>
      ) : staffFetch.loading ? (
        <Card padding={32}><div style={{ color: "var(--muted-text)", fontSize: 13 }}>Loading…</div></Card>
      ) : staff ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Quick stats */}
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {[
              { label: "Availability", value: <Badge variant={AVAIL_BADGE[staff.availability_status] ?? "muted"}>{staff.availability_status}</Badge> },
              { label: "Role", value: <Badge variant="muted">{staff.role.replace(/_/g, " ")}</Badge> },
              { label: "Total Jobs", value: staff.total_jobs },
              { label: "Completed", value: staff.completed_jobs },
              { label: "Active Jobs", value: staff.active_jobs },
              { label: "Avg Rating", value: staff.average_rating != null ? `★ ${staff.average_rating.toFixed(1)}` : "—" },
              { label: "Reviews", value: staff.total_reviews },
            ].map(({ label, value }) => (
              <div key={label} style={{
                background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: 8,
                padding: "12px 16px", flex: 1, minWidth: 90,
              }}>
                <div style={{ fontSize: 11, color: "var(--muted-text)", marginBottom: 4 }}>{label}</div>
                <div style={{ fontSize: 15, fontWeight: 700 }}>{value}</div>
              </div>
            ))}
          </div>

          {/* Tabs */}
          <Card padding={0}>
            <div style={{ display: "flex", borderBottom: "1px solid var(--border)", padding: "0 8px" }}>
              <button style={tabStyle("overview")} onClick={() => setTab("overview")}>Overview</button>
              <button style={tabStyle("jobs")} onClick={() => setTab("jobs")}>
                Jobs {jobsMeta?.total != null ? `(${jobsMeta.total})` : ""}
              </button>
            </div>

            {tab === "overview" && (
              <div style={{ padding: 20 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
                      Contact Details
                    </div>
                    <InfoRow label="Full Name" value={staff.full_name} />
                    <InfoRow label="Phone" value={staff.phone} />
                    <InfoRow label="Email" value={staff.email} />
                    <InfoRow label="Role" value={staff.role} />
                    <InfoRow label="Verified" value={staff.is_verified ? "Yes" : "Pending"} />
                    <InfoRow label="Active" value={staff.is_active ? "Active" : "Deactivated"} />
                    <InfoRow label="Joined" value={staff.created_at ? new Date(staff.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" }) : undefined} />
                  </div>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
                      Provider
                    </div>
                    <InfoRow label="Tenant" value={staff.tenant_name} />
                    <InfoRow label="Business" value={staff.business_name} />
                    <InfoRow label="City" value={staff.tenant_city} />
                    <InfoRow label="Last Job" value={staff.last_job_at ? new Date(staff.last_job_at).toLocaleDateString("en-IN") : undefined} />
                    <InfoRow label="Last Category" value={staff.last_category} />
                    <InfoRow label="Avg Rating" value={staff.average_rating != null ? `${staff.average_rating.toFixed(2)} (${staff.total_reviews} reviews)` : undefined} />
                  </div>
                </div>
              </div>
            )}

            {tab === "jobs" && (
              <div>
                <DataTable
                  columns={jobColumns as unknown as Parameters<typeof DataTable>[0]["columns"]}
                  rows={jobs as unknown as Record<string, unknown>[]}
                  loading={jobsFetch.loading}
                  emptyText="No jobs found for this staff member."
                />
                {jobsMeta && jobsMeta.total_pages > 1 && (
                  <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", textAlign: "center", color: "var(--muted-text)", fontSize: 12 }}>
                    Showing page 1 of {jobsMeta.total_pages} ({jobsMeta.total} total jobs)
                  </div>
                )}
              </div>
            )}
          </Card>
        </div>
      ) : null}
    </AdminLayout>
  );
}
