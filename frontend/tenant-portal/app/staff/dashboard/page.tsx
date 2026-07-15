"use client";
import React, { useCallback } from "react";
import { StaffLayout } from "../../../components/layout/StaffLayout";
import { Card, StatCard, Skeleton, EmptyState, Badge } from "../../../components/shared/ui";
import { useApi } from "../../../hooks/useApi";
import { useStaffContextValue } from "../../../hooks/useStaffContext";
import { staffSelfApi, tenantSetupApi, homeServiceStaffJobsApi } from "../../../lib/api";
import { ClipboardList, Wrench, MapPin, Clock, FileText, Bell, CheckCircle2, AlertTriangle } from "lucide-react";

export default function StaffDashboardPage() {
  return (
    <StaffLayout activeNav="dashboard">
      <StaffDashboardContent/>
    </StaffLayout>
  );
}

/** Renders only once StaffLayout has already resolved auth (loading=false,
 * isTechnician=true) — reads that single resolved context via
 * useStaffContextValue() instead of re-running useStaffContext(), and only
 * fires its data fetches at that point rather than racing them against the
 * layout's own /v1/auth/me call immediately after login. */
function StaffDashboardContent() {
  const ctx = useStaffContextValue();

  const skills   = useApi(useCallback(() => staffSelfApi.getMySkills(), []));
  // MODULE-L5-38: repointed from the dead field_ops /v1/staff/me/jobs to the
  // real /v1/staff/service-jobs list (see /staff/jobs page).
  const jobs     = useApi(useCallback(() => homeServiceStaffJobsApi.list(), []));
  const notifs   = useApi(useCallback(() => staffSelfApi.getNotifications(), []));
  const areas    = useApi(useCallback(() => staffSelfApi.getServiceAreas(), []));
  const status   = useApi(useCallback(() => tenantSetupApi.getStatus(), []));

  const jobCount = jobs.data?.jobs.length ?? 0;
  const skillCount = skills.data?.skills?.length ?? 0;
  const areaCount = areas.data?.total ?? 0;
  const unread = notifs.data?.unread_count ?? notifs.data?.items.filter(n => n.read_status !== "read").length ?? 0;

  const readonlyStatus = status.data as Record<string, unknown> | null;
  const bookable = !!readonlyStatus?.bookable;

  return (
    <>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>My Dashboard</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
          Welcome back, {ctx.user?.full_name || ctx.user?.email}.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 20 }}>
        {jobs.loading || skills.loading || areas.loading || notifs.loading ? (
          Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} height={92}/>)
        ) : (
          <>
            <StatCard label="Today's Assigned Work" value={jobCount} icon={<ClipboardList/>}/>
            <StatCard label="Active Skills" value={skillCount} icon={<Wrench/>}/>
            <StatCard label="Service Areas" value={areaCount} icon={<MapPin/>}/>
            <StatCard label="Availability Status" value="—" icon={<Clock/>}/>
            <StatCard label="Documents Status" value="Not tracked yet" icon={<FileText/>}/>
            <StatCard label="Notifications" value={unread} icon={<Bell/>} alert={unread > 0}/>
          </>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
        <Card>
          <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Assigned Work</h3>
          {jobs.loading ? <Skeleton height={100}/> : jobCount === 0 ? (
            <EmptyState icon={<ClipboardList/>} title="No assigned work yet."
              description="New jobs assigned to you will appear here."/>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {jobs.data!.jobs.map(j => (
                <div key={j.id} style={{ padding: "10px 12px", borderRadius: 8, border: "1px solid var(--border)" }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{j.job_number || `Job ${j.id.slice(0, 8)}`}</div>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{[j.city, j.status].filter(Boolean).join(" · ")}</div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Tenant Status Snapshot (readonly)</h3>
          {status.loading ? <Skeleton height={80}/> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {bookable ? <CheckCircle2 size={14} color="var(--success)"/> : <AlertTriangle size={14} color="var(--warning)"/>}
                Bookable: <Badge variant={bookable ? "success" : "warning"} size="sm">{bookable ? "Yes" : "Not yet"}</Badge>
              </div>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
                Package, usage credits, and security deposit status are managed by your tenant owner/admin — you can view but not change them.
              </p>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
