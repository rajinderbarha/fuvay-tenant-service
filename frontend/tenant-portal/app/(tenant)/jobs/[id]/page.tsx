"use client";
/**
 * Job Detail — FINAL-L5-01D: migrated off legacy jobsApi/quotesApi (field_ops
 * job_type-aware repair/service/consultation workflow) onto serviceJobsApi +
 * serviceJobAssignmentApi (canonical service_jobs + service_job_assignments).
 *
 * The legacy detail page's quote/checklist/assessment/spawn-repair sections
 * have NO equivalent in the canonical service_jobs model — rather than point
 * those actions at the wrong table or fabricate the missing concepts, this
 * page shows only real canonical fields and wires actions (assign/reassign/
 * schedule/cancel) to the real assignment API. See
 * docs/final-l5-01d/FINAL_L5_01D_TENANT_JOBS_API_MIGRATION_REPORT.md.
 */
import React, { useCallback, useState } from "react";
import Link from "next/link";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { PageHeader, Card, StatusBadge, Button, Modal, Input, Skeleton } from "@serviceos/design-system";
import { Badge } from "../../../../components/shared/ui";
import { serviceJobsApi, serviceJobAssignmentApi, mediaAssetApi, getUserRole } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import ReadOnlyBanner, { isReadOnly } from "../../../../components/shared/ReadOnlyBanner";
import { MediaUploader } from "../../../../components/media/MediaUploader";
import { MediaGallery } from "../../../../components/media/MediaGallery";

export default function JobDetailPage({ params }:{ params: Promise<{ id:string }> }) {
  const { id } = React.use(params);
  const job      = useApi(useCallback(() => serviceJobsApi.get(id), [id]));
  const timeline = useApi(useCallback(() => serviceJobAssignmentApi.getTimeline(id), [id]));
  const eligible = useApi(useCallback(() => serviceJobAssignmentApi.getEligibleStaff(id), [id]));
  const beforePhotos = useApi(useCallback(
    () => mediaAssetApi.listAssets({ owner_type: "service_job", owner_id: id, media_context: "job_before_photo" }), [id]));
  const afterPhotos = useApi(useCallback(
    () => mediaAssetApi.listAssets({ owner_type: "service_job", owner_id: id, media_context: "job_after_photo" }), [id]));

  const assignAction = useAction(useCallback(
    (staffId: string) => serviceJobAssignmentApi.assign(id, { staff_member_id: staffId }), [id]));
  const cancelAction = useAction(useCallback(
    (reason: string) => serviceJobAssignmentApi.cancelAssignment(id, reason), [id]));
  const scheduleAction = useAction(useCallback(
    (date: string, window: string) => serviceJobAssignmentApi.schedule(id, { scheduled_date: date, scheduled_time_window: window }), [id]));

  const [assignModal, setAssignModal] = useState(false);
  const [cancelModal, setCancelModal] = useState(false);
  const [scheduleModal, setScheduleModal] = useState(false);
  const [selectedStaff, setSelectedStaff] = useState("");
  const [cancelReason, setCancelReason] = useState("");
  const [schedDate, setSchedDate] = useState("");
  const [schedWindow, setSchedWindow] = useState("");

  const j = job.data;
  const readOnly = isReadOnly(getUserRole());

  async function handleAssign() {
    if (!selectedStaff) return;
    const res = await assignAction.execute(selectedStaff);
    if (res) { job.refetch(); timeline.refetch(); setAssignModal(false); setSelectedStaff(""); }
  }
  async function handleCancel() {
    const res = await cancelAction.execute(cancelReason || "Cancelled by tenant");
    if (res) { job.refetch(); timeline.refetch(); setCancelModal(false); setCancelReason(""); }
  }
  async function handleSchedule() {
    if (!schedDate || !schedWindow) return;
    const res = await scheduleAction.execute(schedDate, schedWindow);
    if (res) { job.refetch(); setScheduleModal(false); }
  }

  return (
    <TenantLayout activeNav="jobs">
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8,
        fontSize:12, color:"var(--text-tertiary)" }}>
        <Link href="/jobs" style={{ color:"var(--text-link)", textDecoration:"none" }}>Jobs</Link>
        <span>›</span>
        <span style={{ color:"var(--text-primary)", fontWeight:500 }}>
          {job.loading ? "Loading..." : j?.job_number}
        </span>
      </div>

      <PageHeader title={job.loading ? "Loading..." : (j?.job_number ?? "Job")} description="ServiceBooking -> ServiceJob pipeline" />

      <ReadOnlyBanner role={getUserRole()}/>

      {job.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:16, marginTop:16 }}>
          <Skeleton height="8.75rem"/>
          <Skeleton height="12.5rem"/>
        </div>
      ) : !j ? (
        <div style={{ textAlign:"center", padding:60 }}>
          <p style={{ color:"var(--text-tertiary)" }}>Job not found</p>
        </div>
      ) : (
        <div style={{ display:"flex", flexDirection:"column", gap:16, marginTop:16 }}>
          {/* Hero */}
          <Card padding="lg">
            <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", flexWrap:"wrap", gap:16 }}>
              <div>
                <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:8 }}>
                  <h1 style={{ fontSize:20, fontWeight:700, color:"var(--text-primary)", margin:0 }}>{j.job_number}</h1>
                  <StatusBadge status={j.status}/>
                  <Badge variant={j.assignment_status === "unassigned" ? "warning" : "success"}>
                    {j.assignment_status.replace(/_/g," ")}
                  </Badge>
                </div>
                <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 4px" }}>
                  {j.address_snapshot?.line1 ?? ""} {j.city ?? ""} {j.zipcode ?? ""}
                </p>
                <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:0 }}>
                  Scheduled: {j.scheduled_date ? `${j.scheduled_date} ${j.scheduled_time_window ?? ""}` : "Not scheduled"}
                </p>
              </div>
              {!readOnly && (
                <div style={{ display:"flex", gap:8 }}>
                  <Button variant="secondary" size="sm" onClick={() => setScheduleModal(true)}>Schedule</Button>
                  <Button variant="primary" size="sm" onClick={() => setAssignModal(true)}>
                    {j.assignment_status === "unassigned" ? "Assign" : "Reassign"}
                  </Button>
                  <Button variant="destructive" size="sm" onClick={() => setCancelModal(true)}>Cancel</Button>
                </div>
              )}
            </div>
          </Card>

          {/* Real canonical fields */}
          <Card padding="md">
            <h3 style={{ fontSize:14, fontWeight:700, margin:"0 0 12px" }}>Job Details</h3>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(180px,1fr))", gap:14 }}>
              <Field label="Job ID" value={j.id}/>
              <Field label="Booking ID" value={j.booking_id}/>
              <Field label="Customer ID" value={j.customer_id ?? "—"}/>
              <Field label="Assigned Staff ID" value={j.assigned_staff_id ?? "Unassigned"}/>
              <Field label="Created" value={j.created_at ? new Date(j.created_at).toLocaleString() : "—"}/>
              <Field label="Updated" value={j.updated_at ? new Date(j.updated_at).toLocaleString() : "—"}/>
            </div>
            {j.failure_reason && (
              <p style={{ marginTop:12, fontSize:12, color:"var(--danger-text)" }}>Failure: {j.failure_reason}</p>
            )}
          </Card>

          {/* Completion proof — only for completed jobs, real data only */}
          {j.completion_data && (
            <Card padding="md">
              <h3 style={{ fontSize:14, fontWeight:700, margin:"0 0 12px" }}>Completion Proof</h3>
              <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(200px,1fr))", gap:14 }}>
                <Field label="Technician" value={j.completion_data.technician ?? "—"}/>
                <Field label="Completed At" value={j.completion_data.completed_at ? new Date(j.completion_data.completed_at).toLocaleString() : "—"}/>
              </div>
              {j.completion_data.work_summary && (
                <p style={{ marginTop:12, fontSize:12, color:"var(--text-secondary)" }}>{j.completion_data.work_summary}</p>
              )}
            </Card>
          )}

          {/* Payment Collection — Customer Pays Provider Directly; Usage Credit
              Deduction is tracked in the ledger (per-job drill-down not returned
              by this canonical endpoint yet), linked below rather than fabricated. */}
          {j.completion_data && (
            <Card padding="md">
              <h3 style={{ fontSize:14, fontWeight:700, margin:"0 0 12px" }}>Payment Collection</h3>
              <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(200px,1fr))", gap:14 }}>
                <Field label="Collected Amount" value={j.completion_data.collected_amount != null ? `₹${j.completion_data.collected_amount}` : "—"}/>
                <Field label="Payment Mode" value="Customer Pays Provider Directly"/>
              </div>
              <Link href="/packages"
                style={{ display:"inline-block", marginTop:12, fontSize:12, fontWeight:600, color:"var(--text-link)" }}>
                View Usage Credit Deduction (Completed Job Deduction) for this job →
              </Link>
            </Card>
          )}

          {/* Job Photos — real MediaUploader/MediaGallery, wired to /v1/media
              (owner_type=service_job), previously orphaned dead code. */}
          <Card padding="md">
            <h3 style={{ fontSize:14, fontWeight:700, margin:"0 0 16px" }}>Job Photos</h3>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:20 }}>
              <div>
                <p style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)", margin:"0 0 8px" }}>Before</p>
                {!readOnly && (
                  <MediaUploader
                    mediaContext="job_before_photo"
                    ownerType="service_job"
                    ownerId={j.id}
                    multiple
                    label="Upload before photo"
                    onUploaded={() => beforePhotos.refetch()}
                  />
                )}
                <div style={{ marginTop:10 }}>
                  <MediaGallery assets={beforePhotos.data?.items ?? []} emptyMessage="No before photos uploaded yet."/>
                </div>
              </div>
              <div>
                <p style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)", margin:"0 0 8px" }}>After</p>
                {!readOnly && (
                  <MediaUploader
                    mediaContext="job_after_photo"
                    ownerType="service_job"
                    ownerId={j.id}
                    multiple
                    label="Upload after photo"
                    onUploaded={() => afterPhotos.refetch()}
                  />
                )}
                <div style={{ marginTop:10 }}>
                  <MediaGallery assets={afterPhotos.data?.items ?? []} emptyMessage="No after photos uploaded yet."/>
                </div>
              </div>
            </div>
          </Card>

          {/* Assignment timeline — real data from serviceJobAssignmentApi */}
          <Card padding="md">
            <h3 style={{ fontSize:14, fontWeight:700, margin:"0 0 12px" }}>Assignment Timeline</h3>
            {timeline.loading ? <Skeleton height="3.75rem"/> : (timeline.data?.events?.length ?? 0) === 0 ? (
              <p style={{ fontSize:12, color:"var(--text-tertiary)" }}>No assignment events yet.</p>
            ) : (
              <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                {timeline.data!.events.map(ev => (
                  <div key={ev.id} style={{ fontSize:12, color:"var(--text-secondary)" }}>
                    <strong>{ev.event_type}</strong> {ev.reason ? `— ${ev.reason}` : ""}
                    {ev.created_at ? ` (${new Date(ev.created_at).toLocaleString()})` : ""}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Assign modal */}
      <Modal open={assignModal} onClose={() => setAssignModal(false)} title="Assign Technician">
        {eligible.loading ? <Skeleton height="5rem"/> : (
          <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
            {(eligible.data?.eligible_staff ?? []).map(s => (
              <label key={s.staff_member_id} style={{ display:"flex", alignItems:"center", gap:8, fontSize:13 }}>
                <input type="radio" name="staff" value={s.staff_member_id}
                  checked={selectedStaff === s.staff_member_id}
                  onChange={() => setSelectedStaff(s.staff_member_id)}/>
                {s.name} ({s.role})
              </label>
            ))}
            {(eligible.data?.eligible_staff ?? []).length === 0 && (
              <p style={{ fontSize:12, color:"var(--text-tertiary)" }}>No eligible staff found.</p>
            )}
            <Button variant="primary" size="sm" onClick={handleAssign} disabled={!selectedStaff}
              style={{ marginTop:8 }}>Confirm Assignment</Button>
          </div>
        )}
      </Modal>

      {/* Cancel modal */}
      <Modal open={cancelModal} onClose={() => setCancelModal(false)} title="Cancel Assignment">
        <Input label="Reason" value={cancelReason} onChange={e => setCancelReason(e.target.value)} placeholder="Reason for cancellation"/>
        <Button variant="destructive" size="sm" onClick={handleCancel} style={{ marginTop:12 }}>Confirm Cancel</Button>
      </Modal>

      {/* Schedule modal */}
      <Modal open={scheduleModal} onClose={() => setScheduleModal(false)} title="Schedule Job">
        <Input label="Date (YYYY-MM-DD)" value={schedDate} onChange={e => setSchedDate(e.target.value)} placeholder="2026-07-15"/>
        <Input label="Time Window" value={schedWindow} onChange={e => setSchedWindow(e.target.value)} placeholder="10:00-12:00"/>
        <Button variant="primary" size="sm" onClick={handleSchedule} style={{ marginTop:12 }}>Confirm Schedule</Button>
      </Modal>
    </TenantLayout>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p style={{ fontSize:10, fontWeight:700, color:"var(--text-tertiary)", textTransform:"uppercase",
        letterSpacing:"0.06em", margin:"0 0 4px" }}>{label}</p>
      <p style={{ fontSize:13, color:"var(--text-primary)", margin:0, wordBreak:"break-all" }}>{value}</p>
    </div>
  );
}
