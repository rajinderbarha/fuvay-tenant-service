"use client";
import React, { useCallback, useState } from "react";
import { Card, Btn, Badge, Modal, Input, Skeleton, StarRating } from "../../../../components/shared/ui";
import { serviceJobAssignmentApi, reviewsApi } from "../../../../lib/api";
import type { EligibleStaffRecord } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { CheckCircle, XCircle, Clock, RefreshCw, Users, Calendar } from "lucide-react";

type AssignVariant = "default"|"success"|"warning"|"danger"|"info"|"muted";

function assignVariant(status: string): AssignVariant {
  const m: Record<string, AssignVariant> = {
    unassigned: "warning", assigned: "info", accepted: "success",
    rejected: "danger", cancelled: "muted", scheduled: "info",
  };
  return m[status] ?? "muted";
}

const EVENT_LABELS: Record<string, string> = {
  job_received:          "Job received",
  assignment_created:    "Technician assigned",
  assignment_reassigned: "Technician reassigned",
  assignment_cancelled:  "Assignment cancelled",
  technician_accepted:   "Technician accepted",
  technician_rejected:   "Technician rejected",
  job_scheduled:         "Visit scheduled",
};

export default function ServiceJobDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);

  const ctx      = useApi(useCallback(() => serviceJobAssignmentApi.getContext(id), [id]));
  const staff    = useApi(useCallback(() => serviceJobAssignmentApi.getEligibleStaff(id), [id]));
  const timeline = useApi(useCallback(() => serviceJobAssignmentApi.getTimeline(id), [id]));

  const [showAssign,   setShowAssign]   = useState(false);
  const [showSchedule, setShowSchedule] = useState(false);
  const [showCancel,   setShowCancel]   = useState(false);
  const [staffId,      setStaffId]      = useState("");
  const [schedDate,    setSchedDate]    = useState("");
  const [schedWindow,  setSchedWindow]  = useState("");
  const [cancelReason, setCancelReason] = useState("");
  const [notes,        setNotes]        = useState("");

  const doAssign   = useAction(serviceJobAssignmentApi.assign,   { onSuccess: () => { setShowAssign(false);   ctx.refetch(); timeline.refetch(); } });
  const doCancel   = useAction(serviceJobAssignmentApi.cancelAssignment, { onSuccess: () => { setShowCancel(false);   ctx.refetch(); timeline.refetch(); } });
  const doSchedule = useAction(serviceJobAssignmentApi.schedule, { onSuccess: () => { setShowSchedule(false); ctx.refetch(); } });

  const job        = ctx.data?.job;
  const assignment = ctx.data?.current_assignment;
  const eligible   = staff.data?.eligible_staff ?? [];
  const isJobDone  = job?.status === "completed";

  const jobReviews = useApi(useCallback(
    () => reviewsApi.list({ limit: "50" }),
    []
  ));
  const jobReview = (jobReviews.data?.reviews ?? []).find(r => r.job_id === id) ?? null;

  if (ctx.loading) {
    return <Skeleton height={200} />;
  }

  if (!job) {
    return <Card><div style={{ padding: 32, textAlign: "center", color: "#888" }}>Job not found.</div></Card>;
  }

  const canAssign   = ["unassigned", "rejected"].includes(job.assignment_status);
  const canCancel   = job.assignment_status === "assigned";
  const canSchedule = ["assigned", "accepted"].includes(job.assignment_status);

  return (
    <>
      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: "#111", margin: 0 }}>{job.job_number}</h1>
            <p style={{ color: "#888", fontSize: 13, marginTop: 2 }}>{job.city || "No city"}</p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <Badge variant={assignVariant(job.assignment_status)}>{job.assignment_status}</Badge>
            <Badge variant="muted">{job.status}</Badge>
          </div>
        </div>

        {/* Actions */}
        <Card>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" as const }}>
            {canAssign && (
              <Btn variant="primary" size="sm" onClick={() => { setShowAssign(true); staff.refetch(); }}>
                <Users size={14} style={{ marginRight: 4, display: "inline" }} />
                {job.assignment_status === "rejected" ? "Reassign Technician" : "Assign Technician"}
              </Btn>
            )}
            {canSchedule && (
              <Btn variant="secondary" size="sm" onClick={() => setShowSchedule(true)}>
                <Calendar size={14} style={{ marginRight: 4, display: "inline" }} /> Schedule Visit
              </Btn>
            )}
            {canCancel && (
              <Btn variant="danger" size="sm" onClick={() => setShowCancel(true)}>
                <XCircle size={14} style={{ marginRight: 4, display: "inline" }} /> Cancel Assignment
              </Btn>
            )}
            <Btn variant="ghost" size="sm" onClick={() => { ctx.refetch(); timeline.refetch(); }}>
              <RefreshCw size={14} style={{ marginRight: 4, display: "inline" }} /> Refresh
            </Btn>
          </div>
        </Card>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          {/* Job Summary */}
          <Card>
            <h2 style={{ fontWeight: 600, color: "#333", marginBottom: 12 }}>Job Details</h2>
            <dl style={{ display: "flex", flexDirection: "column" as const, gap: 8, fontSize: 13 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <dt style={{ color: "#888" }}>Job Number</dt>
                <dd style={{ fontFamily: "monospace", fontWeight: 600 }}>{job.job_number}</dd>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <dt style={{ color: "#888" }}>Status</dt>
                <dd><Badge variant="muted">{job.status}</Badge></dd>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <dt style={{ color: "#888" }}>Assignment</dt>
                <dd><Badge variant={assignVariant(job.assignment_status)}>{job.assignment_status}</Badge></dd>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <dt style={{ color: "#888" }}>City</dt>
                <dd>{job.city || "—"}</dd>
              </div>
              {job.scheduled_date && (
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <dt style={{ color: "#888" }}>Scheduled</dt>
                  <dd>{job.scheduled_date} {job.scheduled_time_window || ""}</dd>
                </div>
              )}
            </dl>
          </Card>

          {/* Current Assignment */}
          <Card>
            <h2 style={{ fontWeight: 600, color: "#333", marginBottom: 12 }}>Current Assignment</h2>
            {!assignment ? (
              <p style={{ color: "#888", fontSize: 13 }}>No active assignment.</p>
            ) : (
              <dl style={{ display: "flex", flexDirection: "column" as const, gap: 8, fontSize: 13 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <dt style={{ color: "#888" }}>Status</dt>
                  <dd><Badge variant={assignVariant(assignment.assignment_status)}>{assignment.assignment_status}</Badge></dd>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <dt style={{ color: "#888" }}>Type</dt>
                  <dd>{assignment.assignment_type}</dd>
                </div>
                {assignment.scheduled_date && (
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <dt style={{ color: "#888" }}>Scheduled</dt>
                    <dd>{assignment.scheduled_date} {assignment.scheduled_time_window || ""}</dd>
                  </div>
                )}
                {assignment.accepted_at && (
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <dt style={{ color: "#888", display: "flex", alignItems: "center", gap: 4 }}>
                      <CheckCircle size={12} style={{ color: "var(--success)" }} /> Accepted
                    </dt>
                    <dd style={{ fontSize: 11 }}>{new Date(assignment.accepted_at).toLocaleString()}</dd>
                  </div>
                )}
                {assignment.rejected_at && (
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <dt style={{ color: "#888", display: "flex", alignItems: "center", gap: 4 }}>
                      <XCircle size={12} style={{ color: "var(--danger)" }} /> Rejected
                    </dt>
                    <dd style={{ fontSize: 11 }}>{new Date(assignment.rejected_at).toLocaleString()}</dd>
                  </div>
                )}
                {assignment.rejection_reason && (
                  <div>
                    <dt style={{ color: "#888", marginBottom: 4 }}>Rejection Reason</dt>
                    <dd style={{ background: "#fef2f2", color: "#b91c1c", borderRadius: 6, padding: "6px 8px", fontSize: 12 }}>
                      {assignment.rejection_reason}
                    </dd>
                  </div>
                )}
                {assignment.notes && (
                  <div>
                    <dt style={{ color: "#888", marginBottom: 4 }}>Notes</dt>
                    <dd style={{ background: "#f9fafb", borderRadius: 6, padding: "6px 8px", fontSize: 12 }}>
                      {assignment.notes}
                    </dd>
                  </div>
                )}
              </dl>
            )}
          </Card>
        </div>

        {/* Customer Review — only meaningful once the job is completed */}
        {isJobDone && (
          <Card>
            <h2 style={{ fontWeight: 600, color: "#333", marginBottom: 12 }}>Customer Review</h2>
            {jobReviews.loading ? (
              <Skeleton height={60} />
            ) : jobReview ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <StarRating score={jobReview.composite_score} size={16}/>
                  <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
                    {jobReview.composite_score.toFixed(1)}
                  </span>
                </div>
                {jobReview.comment && (
                  <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>
                    &ldquo;{jobReview.comment}&rdquo;
                  </p>
                )}
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
                  Reviewed on {new Date(jobReview.created_at).toLocaleDateString()}
                  {jobReview.has_reply ? " · You replied" : ""}
                </p>
              </div>
            ) : (
              <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>
                No review yet for this job.
              </p>
            )}
          </Card>
        )}

        {/* Assignment Timeline */}
        <Card>
          <h2 style={{ fontWeight: 600, color: "#333", marginBottom: 16 }}>Assignment Timeline</h2>
          {timeline.loading && <Skeleton height={60} />}
          {!timeline.loading && (timeline.data?.events ?? []).length === 0 && (
            <p style={{ color: "#888", fontSize: 13 }}>No assignment events yet.</p>
          )}
          {!timeline.loading && (timeline.data?.events ?? []).length > 0 && (
            <ol style={{ borderLeft: "2px solid #e5e7eb", marginLeft: 12, paddingLeft: 0, listStyle: "none" }}>
              {(timeline.data?.events ?? []).map((ev, i) => (
                <li key={ev.id || i} style={{ marginBottom: 20, marginLeft: 20, position: "relative" }}>
                  <Clock size={12} style={{ position: "absolute", left: -28, top: 2, color: "#6366f1" }} />
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <p style={{ fontWeight: 600, fontSize: 13, color: "#111", margin: 0 }}>
                      {EVENT_LABELS[ev.event_type] || ev.event_type}
                    </p>
                    <time style={{ fontSize: 11, color: "#9ca3af" }}>
                      {ev.created_at ? new Date(ev.created_at).toLocaleString() : "—"}
                    </time>
                  </div>
                  {ev.actor_role && <p style={{ fontSize: 12, color: "#6b7280", margin: "2px 0 0" }}>by {ev.actor_role}</p>}
                  {ev.reason && <p style={{ fontSize: 12, color: "var(--danger)", margin: "2px 0 0" }}>Reason: {ev.reason}</p>}
                </li>
              ))}
            </ol>
          )}
        </Card>
      </div>

      {/* Assign Modal */}
      <Modal open={showAssign} onClose={() => setShowAssign(false)} title="Assign Technician">
        <div style={{ display: "flex", flexDirection: "column" as const, gap: 16 }}>
          {staff.loading && <Skeleton height={40} />}
          {!staff.loading && eligible.length === 0 && (
            <p style={{ color: "#888", fontSize: 13 }}>No eligible technicians found.</p>
          )}
          {!staff.loading && eligible.length > 0 && (
            <div>
              <label style={{ fontSize: 13, fontWeight: 500, color: "#374151", display: "block", marginBottom: 4 }}>
                Select Technician
              </label>
              <select
                style={{ width: "100%", border: "1px solid #d1d5db", borderRadius:"var(--radius-md)", padding: "8px 12px", fontSize: 13 }}
                value={staffId}
                onChange={(e) => setStaffId(e.target.value)}
              >
                <option value="">— Select technician —</option>
                {eligible.map((s: EligibleStaffRecord) => (
                  <option key={s.staff_member_id} value={s.staff_member_id}>
                    {s.name} ({s.role})
                  </option>
                ))}
              </select>
            </div>
          )}
          <Input label="Scheduled Date (optional)" type="date"
                 value={schedDate} onChange={(v) => setSchedDate(v)} />
          <Input label="Time Window (optional)" placeholder="e.g. 10:00-12:00"
                 value={schedWindow} onChange={(v) => setSchedWindow(v)} />
          <Input label="Notes (optional)" placeholder="Any notes for the technician"
                 value={notes} onChange={(v) => setNotes(v)} />
          {doAssign.error && <p style={{ color: "var(--danger)", fontSize: 13 }}>{doAssign.error}</p>}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Btn variant="ghost" onClick={() => setShowAssign(false)}>Cancel</Btn>
            <Btn variant="primary" loading={doAssign.loading} disabled={!staffId}
                 onClick={() => doAssign.execute(id, {
                   staff_member_id: staffId,
                   scheduled_date: schedDate || undefined,
                   scheduled_time_window: schedWindow || undefined,
                   notes: notes || undefined,
                 })}>
              Assign
            </Btn>
          </div>
        </div>
      </Modal>

      {/* Schedule Modal */}
      <Modal open={showSchedule} onClose={() => setShowSchedule(false)} title="Schedule Visit">
        <div style={{ display: "flex", flexDirection: "column" as const, gap: 16 }}>
          <Input label="Date" type="date" value={schedDate} onChange={(v) => setSchedDate(v)} />
          <Input label="Time Window" placeholder="e.g. 10:00-12:00"
                 value={schedWindow} onChange={(v) => setSchedWindow(v)} />
          {doSchedule.error && <p style={{ color: "var(--danger)", fontSize: 13 }}>{doSchedule.error}</p>}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Btn variant="ghost" onClick={() => setShowSchedule(false)}>Cancel</Btn>
            <Btn variant="primary" loading={doSchedule.loading}
                 disabled={!schedDate || !schedWindow}
                 onClick={() => doSchedule.execute(id, { scheduled_date: schedDate, scheduled_time_window: schedWindow })}>
              Schedule
            </Btn>
          </div>
        </div>
      </Modal>

      {/* Cancel Modal */}
      <Modal open={showCancel} onClose={() => setShowCancel(false)} title="Cancel Assignment">
        <div style={{ display: "flex", flexDirection: "column" as const, gap: 16 }}>
          <p style={{ fontSize: 13, color: "#6b7280" }}>
            The technician will be unassigned and the job returns to unassigned status.
          </p>
          <Input label="Reason (required)" placeholder="Why are you cancelling this assignment?"
                 value={cancelReason} onChange={(v) => setCancelReason(v)} />
          {doCancel.error && <p style={{ color: "var(--danger)", fontSize: 13 }}>{doCancel.error}</p>}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Btn variant="ghost" onClick={() => setShowCancel(false)}>Back</Btn>
            <Btn variant="danger" loading={doCancel.loading}
                 disabled={!cancelReason.trim()}
                 onClick={() => doCancel.execute(id, cancelReason)}>
              Cancel Assignment
            </Btn>
          </div>
        </div>
      </Modal>
    </>
  );
}
