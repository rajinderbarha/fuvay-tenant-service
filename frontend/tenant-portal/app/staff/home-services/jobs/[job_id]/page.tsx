"use client";
import React, { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import { StaffLayout } from "../../../../../components/layout/StaffLayout";
import { Card, Badge, Skeleton, Btn } from "../../../../../components/shared/ui";
import { useApi, useAction } from "../../../../../hooks/useApi";
import { homeServiceStaffJobsApi } from "../../../../../lib/api";

// job.status -> the single next CTA a technician can take. Mirrors
// JOB_TRANSITIONS in app/engines/execution/constants.py — one primary
// action per status, not a free-for-all button list, so an invalid jump
// can never be attempted from this UI (the backend also rejects it with
// a 422 either way, per HS8/HS8B).
const NEXT_ACTION: Record<string, { label: string; fn: keyof typeof homeServiceStaffJobsApi }> = {
  assigned:            { label: "Accept Job",          fn: "accept" },
  accepted:            { label: "Mark On The Way",      fn: "onTheWay" },
  scheduled:           { label: "Mark On The Way",      fn: "onTheWay" },
  on_the_way:          { label: "Reached Site",         fn: "reachedSite" },
  reached_site:        { label: "Start Inspection",     fn: "startInspection" },
  inspection_started:  { label: "Complete Inspection",  fn: "completeInspection" },
  inspection_done:     { label: "Start Service",        fn: "startService" },
  service_started:     { label: "Mark Work Done",        fn: "markWorkDone" },
};

export default function StaffHomeServiceJobDetailPage() {
  const params = useParams<{ job_id: string }>();
  const jobId = params.job_id;

  const job = useApi(useCallback(() => homeServiceStaffJobsApi.get(jobId), [jobId]), [jobId]);
  const parts = useApi(useCallback(() => homeServiceStaffJobsApi.listPartsRequests(jobId), [jobId]), [jobId]);

  const statusAction = useAction(
    useCallback(async (fnName: keyof typeof homeServiceStaffJobsApi) => {
      const fn = homeServiceStaffJobsApi[fnName] as (id: string) => Promise<unknown>;
      return fn(jobId);
    }, [jobId]),
    { onSuccess: () => { job.refetch(); } },
  );

  const [partsForm, setPartsForm] = useState({ part_name: "", quantity: "1", estimated_cost: "", reason: "" });
  const partsAction = useAction(
    useCallback(() => homeServiceStaffJobsApi.createPartsRequest(jobId, {
      part_name: partsForm.part_name, quantity: Number(partsForm.quantity),
      estimated_cost: Number(partsForm.estimated_cost), reason: partsForm.reason,
    }), [jobId, partsForm]),
    { onSuccess: () => { setPartsForm({ part_name: "", quantity: "1", estimated_cost: "", reason: "" }); parts.refetch(); job.refetch(); } },
  );

  const [completeForm, setCompleteForm] = useState({ work_summary: "", collected_amount: "", technician_note: "" });
  const completeAction = useAction(
    useCallback(() => homeServiceStaffJobsApi.complete(jobId, {
      work_summary: completeForm.work_summary,
      collected_amount: Number(completeForm.collected_amount),
      technician_note: completeForm.technician_note || undefined,
    }), [jobId, completeForm]),
    { onSuccess: () => { job.refetch(); } },
  );

  // MODULE-L5-38: GET /v1/staff/service-jobs/{id} returns {job, assignment,
  // booking}, not a flat job -- this page previously read job.data.status /
  // .job_number / etc. directly, which were all undefined at runtime (blank
  // job number, undefined status -> no action ever offered). The api client's
  // .get() type was corrected to HomeServiceJobDetail; derive the job from it.
  const j = job.data?.job;
  const nextAction = j ? NEXT_ACTION[j.status] : undefined;
  const canRequestParts = j && ["inspection_started", "inspection_done", "service_started", "quote_required"].includes(j.status);
  const canComplete = j && ["service_started", "work_done", "quote_required"].includes(j.status);
  const isCompleted = j?.status === "completed";

  return (
    <StaffLayout activeNav="jobs">
      {job.loading ? <Skeleton height={300}/> : job.error ? (
        <Card><p style={{ color: "var(--danger-text)", fontSize: 13 }}>{job.error}{job.requestId && ` — Request ID: ${job.requestId}`}</p></Card>
      ) : j ? (
        <>
          <div style={{ marginBottom: 20, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>{j.job_number}</h1>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>{j.city ?? "—"} {j.zipcode ?? ""}</p>
            </div>
            <Badge variant="info" size="sm">{j.status}</Badge>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 16 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <Card>
                <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Status Action</h3>
                {isCompleted ? (
                  <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>Job completed. No further status actions available.</p>
                ) : nextAction ? (
                  <Btn variant="primary" loading={statusAction.loading} onClick={() => statusAction.execute(nextAction.fn)}>
                    {nextAction.label}
                  </Btn>
                ) : (
                  <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No status action available from &quot;{j.status}&quot;.</p>
                )}
                {statusAction.error && (
                  <p style={{ fontSize: 12, color: "var(--danger-text)", marginTop: 8 }}>
                    {statusAction.error}{statusAction.requestId && ` — Request ID: ${statusAction.requestId}`}
                  </p>
                )}
              </Card>

              {canRequestParts && (
                <Card>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Request Parts</h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <input placeholder="Part name" value={partsForm.part_name}
                      onChange={e => setPartsForm(f => ({ ...f, part_name: e.target.value }))}
                      style={inputStyle}/>
                    <div style={{ display: "flex", gap: 8 }}>
                      <input placeholder="Quantity" type="number" min={1} value={partsForm.quantity}
                        onChange={e => setPartsForm(f => ({ ...f, quantity: e.target.value }))}
                        style={{ ...inputStyle, flex: 1 }}/>
                      <input placeholder="Estimated cost (₹)" type="number" min={0} value={partsForm.estimated_cost}
                        onChange={e => setPartsForm(f => ({ ...f, estimated_cost: e.target.value }))}
                        style={{ ...inputStyle, flex: 1 }}/>
                    </div>
                    <textarea placeholder="Reason" value={partsForm.reason}
                      onChange={e => setPartsForm(f => ({ ...f, reason: e.target.value }))}
                      style={{ ...inputStyle, minHeight: 60 }}/>
                    <Btn variant="secondary" loading={partsAction.loading}
                      disabled={!partsForm.part_name || !partsForm.estimated_cost || !partsForm.reason}
                      onClick={() => partsAction.execute()}>
                      Submit Parts Request
                    </Btn>
                    {partsAction.error && (
                      <p style={{ fontSize: 12, color: "var(--danger-text)" }}>
                        {partsAction.error}{partsAction.requestId && ` — Request ID: ${partsAction.requestId}`}
                      </p>
                    )}
                  </div>
                </Card>
              )}

              {parts.data && parts.data.parts_requests.length > 0 && (
                <Card>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Parts Requests</h3>
                  {parts.data.parts_requests.map(pr => (
                    <div key={pr.parts_request_id} style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ fontSize: 13, fontWeight: 600 }}>{pr.part_name} × {pr.quantity}</span>
                        <Badge variant={pr.status.includes("rejected") ? "danger" : pr.status === "installed" ? "success" : "info"} size="sm">{pr.status}</Badge>
                      </div>
                      <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "2px 0 0" }}>₹{pr.estimated_cost} — {pr.reason}</p>
                    </div>
                  ))}
                </Card>
              )}

              {canComplete && !isCompleted && (
                <Card>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Complete Job</h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <textarea placeholder="Work summary (required)" value={completeForm.work_summary}
                      onChange={e => setCompleteForm(f => ({ ...f, work_summary: e.target.value }))}
                      style={{ ...inputStyle, minHeight: 70 }}/>
                    <input placeholder="Collected amount (₹, required)" type="number" min={0} value={completeForm.collected_amount}
                      onChange={e => setCompleteForm(f => ({ ...f, collected_amount: e.target.value }))}
                      style={inputStyle}/>
                    <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Payment mode: Customer Pays Provider Directly (fixed)</div>
                    <textarea placeholder="Technician note (optional)" value={completeForm.technician_note}
                      onChange={e => setCompleteForm(f => ({ ...f, technician_note: e.target.value }))}
                      style={{ ...inputStyle, minHeight: 50 }}/>
                    <Btn variant="primary" loading={completeAction.loading}
                      disabled={!completeForm.work_summary || !completeForm.collected_amount}
                      onClick={() => completeAction.execute()}>
                      Submit Completion
                    </Btn>
                    {completeAction.error && (
                      <p style={{ fontSize: 12, color: "var(--danger-text)" }}>
                        {completeAction.error}{completeAction.requestId && ` — Request ID: ${completeAction.requestId}`}
                      </p>
                    )}
                  </div>
                </Card>
              )}

              {isCompleted && j.completion_data && (
                <Card>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Completion Proof</h3>
                  <p style={{ fontSize: 13 }}>{String(j.completion_data.work_summary)}</p>
                  <p style={{ fontSize: 13, fontWeight: 700, marginTop: 8 }}>
                    Collected Amount: ₹{Number(j.completion_data.collected_amount).toLocaleString("en-IN")}
                  </p>
                  <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                    Payment Collected On-site — Customer Pays Provider Directly
                  </p>
                </Card>
              )}
            </div>

            <Card>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Job Info</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13 }}>
                <Row label="Booking" value={j.booking_id}/>
                <Row label="Scheduled" value={j.scheduled_date ?? undefined}/>
                <Row label="Time Window" value={j.scheduled_time_window ?? undefined}/>
                <Row label="Assignment Status" value={j.assignment_status}/>
              </div>
            </Card>
          </div>
        </>
      ) : null}
    </StaffLayout>
  );
}

const inputStyle: React.CSSProperties = {
  padding: "8px 10px", borderRadius: 8, fontSize: 13,
  border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text)",
};

function Row({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 2 }}>{label}</div>
      <div>{value || "—"}</div>
    </div>
  );
}
