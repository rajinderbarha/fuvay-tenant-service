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
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { Card, Badge, JobStatusBadge, Btn, Modal, Input, Skeleton } from "../../../../components/shared/ui";
import { serviceJobsApi, serviceJobAssignmentApi, getUserRole } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import ReadOnlyBanner, { isReadOnly } from "../../../../components/shared/ReadOnlyBanner";

export default function JobDetailPage({ params }:{ params: Promise<{ id:string }> }) {
  const { id } = React.use(params);
  const job      = useApi(useCallback(() => serviceJobsApi.get(id), [id]));
  const timeline = useApi(useCallback(() => serviceJobAssignmentApi.getTimeline(id), [id]));
  const eligible = useApi(useCallback(() => serviceJobAssignmentApi.getEligibleStaff(id), [id]));

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
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:16,
        fontSize:12, color:"var(--text-tertiary)" }}>
        <a href="/jobs" style={{ color:"var(--text-link)", textDecoration:"none" }}>Jobs</a>
        <span>›</span>
        <span style={{ color:"var(--text-primary)", fontWeight:500 }}>
          {job.loading ? "Loading..." : j?.job_number}
        </span>
      </div>

      <ReadOnlyBanner role={getUserRole()}/>

      {job.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <Skeleton height={140} style={{ borderRadius:14 }}/>
          <Skeleton height={200} style={{ borderRadius:14 }}/>
        </div>
      ) : !j ? (
        <div style={{ textAlign:"center", padding:60 }}>
          <p style={{ color:"var(--text-tertiary)" }}>Job not found</p>
        </div>
      ) : (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          {/* Hero */}
          <Card padding={24}>
            <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", flexWrap:"wrap", gap:16 }}>
              <div>
                <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:8 }}>
                  <h1 style={{ fontSize:20, fontWeight:700, color:"var(--text-primary)", margin:0 }}>{j.job_number}</h1>
                  <JobStatusBadge status={j.status}/>
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
                  <Btn variant="secondary" size="sm" onClick={() => setScheduleModal(true)}>Schedule</Btn>
                  <Btn variant="primary" size="sm" onClick={() => setAssignModal(true)}>
                    {j.assignment_status === "unassigned" ? "Assign" : "Reassign"}
                  </Btn>
                  <Btn variant="danger" size="sm" onClick={() => setCancelModal(true)}>Cancel</Btn>
                </div>
              )}
            </div>
          </Card>

          {/* Real canonical fields */}
          <Card padding={20}>
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
            <Card padding={20}>
              <h3 style={{ fontSize:14, fontWeight:700, margin:"0 0 12px" }}>Completion Proof</h3>
              <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(200px,1fr))", gap:14 }}>
                <Field label="Technician" value={j.completion_data.technician ?? "—"}/>
                <Field label="Collected Amount" value={j.completion_data.collected_amount != null ? `₹${j.completion_data.collected_amount}` : "—"}/>
                <Field label="Completed At" value={j.completion_data.completed_at ? new Date(j.completion_data.completed_at).toLocaleString() : "—"}/>
              </div>
              {j.completion_data.work_summary && (
                <p style={{ marginTop:12, fontSize:12, color:"var(--text-secondary)" }}>{j.completion_data.work_summary}</p>
              )}
            </Card>
          )}

          {/* Assignment timeline — real data from serviceJobAssignmentApi */}
          <Card padding={20}>
            <h3 style={{ fontSize:14, fontWeight:700, margin:"0 0 12px" }}>Assignment Timeline</h3>
            {timeline.loading ? <Skeleton height={60}/> : (timeline.data?.events?.length ?? 0) === 0 ? (
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
        {eligible.loading ? <Skeleton height={80}/> : (
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
            <Btn variant="primary" size="sm" onClick={handleAssign} disabled={!selectedStaff}
              style={{ marginTop:8 }}>Confirm Assignment</Btn>
          </div>
        )}
      </Modal>

      {/* Cancel modal */}
      <Modal open={cancelModal} onClose={() => setCancelModal(false)} title="Cancel Assignment">
        <Input label="Reason" value={cancelReason} onChange={setCancelReason} placeholder="Reason for cancellation"/>
        <Btn variant="danger" size="sm" onClick={handleCancel} style={{ marginTop:12 }}>Confirm Cancel</Btn>
      </Modal>

      {/* Schedule modal */}
      <Modal open={scheduleModal} onClose={() => setScheduleModal(false)} title="Schedule Job">
        <Input label="Date (YYYY-MM-DD)" value={schedDate} onChange={setSchedDate} placeholder="2026-07-15"/>
        <Input label="Time Window" value={schedWindow} onChange={setSchedWindow} placeholder="10:00-12:00"/>
        <Btn variant="primary" size="sm" onClick={handleSchedule} style={{ marginTop:12 }}>Confirm Schedule</Btn>
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
