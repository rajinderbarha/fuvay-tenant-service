"use client";
import React, { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import { StaffLayout } from "../../../../components/layout/StaffLayout";
import { Card, Badge, Skeleton } from "../../../../components/shared/ui";
import { useApi, useAction } from "../../../../hooks/useApi";
import { homeServiceStaffJobsApi } from "../../../../lib/api";

// MODULE-L5-38: repointed from the dead field_ops /v1/staff/me/jobs detail
// (0 rows, all-actions-disabled with stale "not certified" copy) to the real,
// live-verified /v1/staff/service-jobs detail + execution lifecycle -- the
// same pipeline the staff-app mobile JobDetailScreen uses (MODULE-L5-36).
// Detail is {job, assignment, booking}; ServiceJob carries no customer
// phone/price (the safe booking view deliberately excludes them from staff).

// Each status offers a distinct next action (one endpoint each, not a generic
// status update). Mirrors mobile's transitions map.
const NEXT_ACTIONS: Record<string, { key: string; label: string }[]> = {
  assigned:           [{ key: "accept", label: "Accept Job" }, { key: "reject", label: "Reject Job" }],
  accepted:           [{ key: "onTheWay", label: "On The Way" }],
  on_the_way:         [{ key: "reachedSite", label: "Reached Site" }],
  reached_site:       [{ key: "startInspection", label: "Start Inspection" }],
  inspection_started: [{ key: "completeInspection", label: "Complete Inspection" }],
  inspection_done:    [{ key: "startService", label: "Start Service" }],
  service_started:    [{ key: "markWorkDone", label: "Work Done" }, { key: "complete", label: "Complete & Submit" }],
  work_done:          [{ key: "complete", label: "Complete & Submit" }],
  quote_required:     [{ key: "complete", label: "Complete & Submit" }],
};

export default function StaffJobDetailPage() {
  const params = useParams<{ job_id: string }>();
  const jobId = params.job_id;
  const detail = useApi(useCallback(() => homeServiceStaffJobsApi.get(jobId), [jobId]), [jobId]);

  const [rejectReason, setRejectReason] = useState("");
  const [showReject, setShowReject] = useState(false);
  const [workSummary, setWorkSummary] = useState("");
  const [collected, setCollected] = useState("");
  const [showComplete, setShowComplete] = useState(false);

  const act = useAction(
    async (fn: () => Promise<unknown>) => fn(),
    { onSuccess: () => detail.refetch() },
  );

  const j = detail.data?.job;
  const booking = detail.data?.booking;
  const assignment = detail.data?.assignment;
  const actions = j ? (NEXT_ACTIONS[j.status] ?? []) : [];

  function runAction(key: string) {
    if (key === "reject") { setShowReject(true); return; }
    if (key === "complete") { setShowComplete(true); return; }
    const map: Record<string, () => Promise<unknown>> = {
      accept: () => homeServiceStaffJobsApi.accept(jobId),
      onTheWay: () => homeServiceStaffJobsApi.onTheWay(jobId),
      reachedSite: () => homeServiceStaffJobsApi.reachedSite(jobId),
      startInspection: () => homeServiceStaffJobsApi.startInspection(jobId),
      completeInspection: () => homeServiceStaffJobsApi.completeInspection(jobId),
      startService: () => homeServiceStaffJobsApi.startService(jobId),
      markWorkDone: () => homeServiceStaffJobsApi.markWorkDone(jobId),
    };
    if (map[key]) act.execute(map[key]);
  }

  function submitReject() {
    if (!rejectReason.trim()) return;
    act.execute(() => homeServiceStaffJobsApi.reject(jobId, rejectReason.trim()));
    setShowReject(false); setRejectReason("");
  }

  function submitComplete() {
    const amount = parseFloat(collected);
    if (!workSummary.trim() || isNaN(amount)) return;
    act.execute(() => homeServiceStaffJobsApi.complete(jobId, {
      work_summary: workSummary.trim(), collected_amount: amount,
      payment_mode: "customer_pays_provider_directly",
    }));
    setShowComplete(false); setWorkSummary(""); setCollected("");
  }

  return (
    <StaffLayout activeNav="jobs">
      {detail.loading ? <Skeleton height={300}/> : detail.error ? (
        <Card><p style={{ color: "var(--danger-text)", fontSize: 13 }}>{detail.error}{detail.requestId && ` — Request ID: ${detail.requestId}`}</p></Card>
      ) : j ? (
        <>
          <div style={{ marginBottom: 20, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>{j.job_number || `Job ${j.id.slice(0, 8)}`}</h1>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
                {[j.city, j.zipcode].filter(Boolean).join(", ") || "—"}
              </p>
            </div>
            <Badge variant="info" size="sm">{j.status}</Badge>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 16 }}>
            <Card>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Job Details</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13 }}>
                <Row label="Booking" value={booking ? `#${booking.booking_number}` : undefined}/>
                <Row label="Customer" value={booking?.customer_name}/>
                <Row label="Issue" value={booking?.issue_summary}/>
                <Row label="City / Zip" value={[j.city, j.zipcode].filter(Boolean).join(" / ") || undefined}/>
                <Row label="Scheduled" value={j.scheduled_date ? `${j.scheduled_date}${j.scheduled_time_window ? ` · ${j.scheduled_time_window}` : ""}` : undefined}/>
                {assignment?.rejection_reason && <Row label="Rejection Reason" value={assignment.rejection_reason}/>}
              </div>
              {j.completion_data && (
                <div style={{ marginTop: 16, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
                  <h4 style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 8px" }}>Completion</h4>
                  <p style={{ fontSize: 13, margin: 0 }}>{String((j.completion_data as Record<string, unknown>).work_summary ?? "")}</p>
                  <p style={{ fontSize: 13, fontWeight: 700, margin: "4px 0 0" }}>₹{Number((j.completion_data as Record<string, unknown>).collected_amount ?? 0).toLocaleString("en-IN")} collected</p>
                </div>
              )}
            </Card>

            <Card>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Job Actions</h3>
              {act.error && <p style={{ fontSize: 12, color: "var(--danger-text)", marginBottom: 8 }}>{act.error}</p>}
              {actions.length === 0 ? (
                <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>No actions available for this status.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {actions.map(a => (
                    <button key={a.key} disabled={act.loading} onClick={() => runAction(a.key)}
                      style={{
                        padding: "9px 12px", borderRadius: 8, fontSize: 13, fontWeight: 600,
                        border: "1px solid var(--border)",
                        background: a.key === "reject" ? "var(--danger-bg, #fef2f2)" : a.key === "complete" ? "var(--success-bg, #ecfdf5)" : "var(--accent, #2563eb)",
                        color: a.key === "reject" ? "var(--danger-text, #991b1b)" : a.key === "complete" ? "var(--success-text, #065f46)" : "#fff",
                        cursor: act.loading ? "wait" : "pointer", textAlign: "left",
                      }}>
                      {a.label}
                    </button>
                  ))}
                </div>
              )}

              {showReject && (
                <div style={{ marginTop: 12 }}>
                  <textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)} rows={3}
                    placeholder="Reason for rejection (required)"
                    style={{ width: "100%", padding: 8, fontSize: 13, borderRadius: 8, border: "1px solid var(--border)" }}/>
                  <button onClick={submitReject} disabled={!rejectReason.trim() || act.loading}
                    style={{ marginTop: 8, padding: "8px 12px", borderRadius: 8, fontSize: 13, fontWeight: 600, border: "none", background: "var(--danger-text, #991b1b)", color: "#fff", cursor: "pointer" }}>
                    Submit Rejection
                  </button>
                </div>
              )}

              {showComplete && (
                <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
                  <textarea value={workSummary} onChange={e => setWorkSummary(e.target.value)} rows={3}
                    placeholder="Work summary (required)"
                    style={{ width: "100%", padding: 8, fontSize: 13, borderRadius: 8, border: "1px solid var(--border)" }}/>
                  <input value={collected} onChange={e => setCollected(e.target.value)} inputMode="decimal"
                    placeholder="Amount collected (₹, required)"
                    style={{ width: "100%", padding: 8, fontSize: 13, borderRadius: 8, border: "1px solid var(--border)" }}/>
                  <button onClick={submitComplete} disabled={!workSummary.trim() || !collected || act.loading}
                    style={{ padding: "8px 12px", borderRadius: 8, fontSize: 13, fontWeight: 600, border: "none", background: "var(--success-text, #065f46)", color: "#fff", cursor: "pointer" }}>
                    Submit &amp; Complete
                  </button>
                </div>
              )}
            </Card>
          </div>
        </>
      ) : null}
    </StaffLayout>
  );
}

function Row({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 2 }}>{label}</div>
      <div>{value || "—"}</div>
    </div>
  );
}
