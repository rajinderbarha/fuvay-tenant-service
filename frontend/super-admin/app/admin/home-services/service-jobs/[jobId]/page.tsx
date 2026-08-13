"use client";
/**
 * Home Services Job Detail (Super Admin) — E2E-04B.
 * Real job + booking (price/payment/provider) + Completed Job Deduction
 * ledger link, all from GET /v1/admin/final-records/jobs/{job_id}.
 */
import React, { useCallback, useState } from "react";
import Link from "next/link";
import { AdminLayout } from "../../../../../components/layout/AdminLayout";
import { Card, Badge, SectionHeader, Skeleton } from "../../../../../components/shared/ui";
import { ChevronRight, Copy, ExternalLink } from "lucide-react";
import { finalRecordsAdminApi, adminServiceJobAssignmentApi, adminExecutionApi } from "../../../../../lib/api";
import { useApi, useAction } from "../../../../../hooks/useApi";
import { usePermissions } from "../../../../../hooks/usePermissions";

function copyText(t: string) { if (typeof navigator !== "undefined") navigator.clipboard?.writeText(t).catch(() => {}); }

const STATUS_VARIANT: Record<string, "success" | "warning" | "muted" | "danger"> = {
  completed: "success", cancelled: "danger", failed: "danger",
  pending_assignment: "muted", assigned: "warning", accepted: "warning",
  on_the_way: "warning", reached_site: "warning", inspection_started: "warning",
  inspection_done: "warning", service_started: "warning", work_done: "warning",
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card style={{ marginBottom: 16 }}>
      <p style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em",
        color: "var(--text-tertiary)", margin: "0 0 12px" }}>{title}</p>
      {children}
    </Card>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>{value ?? "—"}</div>
    </div>
  );
}

// FINAL-L5-05D: exceptional admin mutations — status override, force-close,
// void. Each is a distinct, explicit operation (not one generic "change
// status" endpoint), requires a reason, requires confirmation, and states
// its real financial consequence rather than hiding it.
function StatusOverrideModal({ jobId, currentStatus, onClose, onDone }: {
  jobId: string; currentStatus: string; onClose: () => void; onDone: () => void;
}) {
  const targets = useApi(useCallback(() => adminExecutionApi.getAllowedServiceJobOverrideTargets(jobId), [jobId]));
  const override = useAction(adminExecutionApi.overrideServiceJobStatus);
  const [targetStatus, setTargetStatus] = useState("");
  const [reason, setReason] = useState("");

  const submit = async () => {
    if (!targetStatus || !reason.trim()) return;
    const result = await override.execute(jobId, {
      target_status: targetStatus, expected_current_status: currentStatus,
      reason_code: "admin_override", reason: reason.trim(),
    });
    if (result) onDone();
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex",
      alignItems: "center", justifyContent: "center", zIndex: 1000 }} onClick={onClose}>
      <div style={{ background: "var(--surface)", borderRadius:"var(--radius-md)", padding: 20, width: 420, maxWidth: "90vw" }}
        onClick={e => e.stopPropagation()}>
        <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 14px" }}>Override Job Status</p>
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>New status</div>
          {targets.loading ? <Skeleton height={32} /> : (
            <select value={targetStatus} onChange={e => setTargetStatus(e.target.value)}
              style={{ width: "100%", padding: 8, fontSize: 13, border: "1px solid var(--border)", borderRadius: 6 }}>
              <option value="">Select a target status…</option>
              {(targets.data?.allowed_targets ?? []).map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          )}
          {!targets.loading && (targets.data?.allowed_targets?.length ?? 0) === 0 && (
            <p style={{ fontSize: 12, color: "var(--danger-text)", marginTop: 4 }}>
              No admin override is available from this job's current status ({currentStatus}).
            </p>
          )}
        </div>
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Reason (required)</div>
          <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3}
            style={{ width: "100%", padding: 8, fontSize: 13, border: "1px solid var(--border)", borderRadius: 6 }}
            placeholder="Why is this status being overridden?" />
        </div>
        {override.error && <p style={{ fontSize: 12, color: "var(--danger-text)", marginBottom: 10 }}>
          {override.error} {override.requestId && `(Request ID: ${override.requestId})`}
        </p>}
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button onClick={onClose} style={{ padding: "8px 14px", fontSize: 13, borderRadius: 6,
            border: "1px solid var(--border)", background: "transparent" }}>Cancel</button>
          <button onClick={submit} disabled={!targetStatus || !reason.trim() || override.loading}
            style={{ padding: "8px 14px", fontSize: 13, borderRadius: 6, border: "none",
              background: "var(--brand)", color: "#fff",
              opacity: (!targetStatus || !reason.trim() || override.loading) ? 0.5 : 1 }}>
            {override.loading ? "Submitting…" : "Confirm Override"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ForceCloseModal({ jobId, currentStatus, onClose, onDone }: {
  jobId: string; currentStatus: string; onClose: () => void; onDone: () => void;
}) {
  const forceClose = useAction(adminExecutionApi.forceCloseServiceJob);
  const [reason, setReason] = useState("");

  const submit = async () => {
    if (!reason.trim()) return;
    const result = await forceClose.execute(jobId, {
      expected_current_status: currentStatus, reason_code: "admin_force_close", reason: reason.trim(),
    });
    if (result) onDone();
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex",
      alignItems: "center", justifyContent: "center", zIndex: 1000 }} onClick={onClose}>
      <div style={{ background: "var(--surface)", borderRadius:"var(--radius-md)", padding: 20, width: 440, maxWidth: "90vw" }}
        onClick={e => e.stopPropagation()}>
        <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 10px" }}>Force-Close Job</p>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 14px" }}>
          This makes the job terminal (status: force_closed). It does <strong>not</strong> create a Completed
          Job Deduction automatically — if real completion evidence exists, a finance review must apply it
          manually afterward.
        </p>
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Reason (required)</div>
          <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3}
            style={{ width: "100%", padding: 8, fontSize: 13, border: "1px solid var(--border)", borderRadius: 6 }}
            placeholder="Why is this job being force-closed?" />
        </div>
        {forceClose.error && <p style={{ fontSize: 12, color: "var(--danger-text)", marginBottom: 10 }}>
          {forceClose.error} {forceClose.requestId && `(Request ID: ${forceClose.requestId})`}
        </p>}
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button onClick={onClose} style={{ padding: "8px 14px", fontSize: 13, borderRadius: 6,
            border: "1px solid var(--border)", background: "transparent" }}>Cancel</button>
          <button onClick={submit} disabled={!reason.trim() || forceClose.loading}
            style={{ padding: "8px 14px", fontSize: 13, borderRadius: 6, border: "none",
              background: "var(--danger-text, var(--danger))", color: "#fff",
              opacity: (!reason.trim() || forceClose.loading) ? 0.5 : 1 }}>
            {forceClose.loading ? "Force-closing…" : "Confirm Force-Close"}
          </button>
        </div>
      </div>
    </div>
  );
}

function VoidModal({ jobId, currentStatus, onClose, onDone }: {
  jobId: string; currentStatus: string; onClose: () => void; onDone: () => void;
}) {
  const voidAction = useAction(adminExecutionApi.voidServiceJob);
  const [reason, setReason] = useState("");

  const submit = async () => {
    if (!reason.trim()) return;
    const result = await voidAction.execute(jobId, {
      expected_current_status: currentStatus, reason_code: "admin_void", reason: reason.trim(),
    });
    if (result) onDone();
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex",
      alignItems: "center", justifyContent: "center", zIndex: 1000 }} onClick={onClose}>
      <div style={{ background: "var(--surface)", borderRadius:"var(--radius-md)", padding: 20, width: 440, maxWidth: "90vw" }}
        onClick={e => e.stopPropagation()}>
        <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 10px" }}>Void Job</p>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 14px" }}>
          The job remains permanently visible in history, timeline, and audit — voiding is not deletion. It no
          longer counts as a valid active or completed record. If this job already has a Completed Job
          Deduction, voiding is blocked until a manual finance reversal is recorded.
        </p>
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Reason (required)</div>
          <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3}
            style={{ width: "100%", padding: 8, fontSize: 13, border: "1px solid var(--border)", borderRadius: 6 }}
            placeholder="Why is this job being voided?" />
        </div>
        {voidAction.error && <p style={{ fontSize: 12, color: "var(--danger-text)", marginBottom: 10 }}>
          {voidAction.error} {voidAction.requestId && `(Request ID: ${voidAction.requestId})`}
        </p>}
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button onClick={onClose} style={{ padding: "8px 14px", fontSize: 13, borderRadius: 6,
            border: "1px solid var(--border)", background: "transparent" }}>Cancel</button>
          <button onClick={submit} disabled={!reason.trim() || voidAction.loading}
            style={{ padding: "8px 14px", fontSize: 13, borderRadius: 6, border: "none",
              background: "var(--danger-text, var(--danger))", color: "#fff",
              opacity: (!reason.trim() || voidAction.loading) ? 0.5 : 1 }}>
            {voidAction.loading ? "Voiding…" : "Confirm Void"}
          </button>
        </div>
      </div>
    </div>
  );
}

// FINAL-L5-05C Part 15: real reassignment UI action — permission-aware
// (super_admin only, enforced server-side too), requires a reason, confirms
// before submitting. Technician list comes from the live eligible-technicians
// endpoint, not a hardcoded/mocked list.
function ReassignModal({ jobId, onClose, onDone }: { jobId: string; onClose: () => void; onDone: () => void }) {
  const technicians = useApi(useCallback(() => adminServiceJobAssignmentApi.getEligibleTechnicians(jobId), [jobId]));
  const reassign = useAction(adminServiceJobAssignmentApi.reassignJob);
  const [technicianId, setTechnicianId] = useState("");
  const [reason, setReason] = useState("");

  const submit = async () => {
    if (!technicianId || !reason.trim()) return;
    const result = await reassign.execute(jobId, { technician_id: technicianId, reason: reason.trim() });
    if (result) onDone();
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex",
      alignItems: "center", justifyContent: "center", zIndex: 1000 }} onClick={onClose}>
      <div style={{ background: "var(--surface)", borderRadius:"var(--radius-md)", padding: 20, width: 420, maxWidth: "90vw" }}
        onClick={e => e.stopPropagation()}>
        <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 14px" }}>Reassign Technician</p>

        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Technician</div>
          {technicians.loading ? (
            <Skeleton height={32} />
          ) : (
            <select value={technicianId} onChange={e => setTechnicianId(e.target.value)}
              style={{ width: "100%", padding: 8, fontSize: 13, border: "1px solid var(--border)", borderRadius: 6 }}>
              <option value="">Select a technician…</option>
              {(technicians.data?.technicians ?? []).map(t => (
                <option key={t.id} value={t.id}>{t.full_name}</option>
              ))}
            </select>
          )}
          {!technicians.loading && (technicians.data?.technicians?.length ?? 0) === 0 && (
            <p style={{ fontSize: 12, color: "var(--danger-text)", marginTop: 4 }}>
              No active technicians found for this job's tenant.
            </p>
          )}
        </div>

        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Reason (required)</div>
          <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3}
            style={{ width: "100%", padding: 8, fontSize: 13, border: "1px solid var(--border)", borderRadius: 6 }}
            placeholder="Why is this job being reassigned?" />
        </div>

        {reassign.error && (
          <p style={{ fontSize: 12, color: "var(--danger-text)", marginBottom: 10 }}>
            {reassign.error} {reassign.requestId && `(Request ID: ${reassign.requestId})`}
          </p>
        )}

        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button onClick={onClose} style={{ padding: "8px 14px", fontSize: 13, borderRadius: 6,
            border: "1px solid var(--border)", background: "transparent" }}>Cancel</button>
          <button onClick={submit} disabled={!technicianId || !reason.trim() || reassign.loading}
            style={{ padding: "8px 14px", fontSize: 13, borderRadius: 6, border: "none",
              background: "var(--brand)", color: "#fff",
              opacity: (!technicianId || !reason.trim() || reassign.loading) ? 0.5 : 1 }}>
            {reassign.loading ? "Reassigning…" : "Confirm Reassignment"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AdminServiceJobDetailPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = React.use(params);
  const job = useApi(useCallback(() => finalRecordsAdminApi.getJob(jobId), [jobId]));
  // FINAL-L5-05B — these two admin timeline endpoints (assignment + execution)
  // plus the notes endpoint already existed as real, working backend routes
  // and typed API-client methods, but were never wired into this page (dead
  // code). Wiring them here closes part of the real feature-parity gap this
  // sprint found between this canonical page and the legacy /admin/operations
  // page (which shows a rendered timeline) — see FINAL_L5_05_JOBS_MIGRATION.md.
  const assignmentTimeline = useApi(useCallback(() => adminServiceJobAssignmentApi.getJobTimeline(jobId), [jobId]));
  const executionTimeline = useApi(useCallback(() => adminExecutionApi.getJobTimeline(jobId), [jobId]));
  const jobNotes = useApi(useCallback(() => adminExecutionApi.getJobNotes(jobId), [jobId]));
  const perm = usePermissions();
  const [showReassign, setShowReassign] = useState(false);
  const [showOverride, setShowOverride] = useState(false);
  const [showForceClose, setShowForceClose] = useState(false);
  const [showVoid, setShowVoid] = useState(false);

  const d = job.data;
  const priceSnapshot = (d?.booking?.price_snapshot ?? {}) as Record<string, any>;
  const providerSnapshot = (d?.booking?.provider_snapshot ?? {}) as Record<string, any>;
  const deduction = d?.usage_credit_deduction;

  return (
    <AdminLayout activeNav="operations">
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 16, fontSize: 12, color: "var(--text-tertiary)" }}>
        <span>Admin</span><ChevronRight size={12}/><span>Home Services</span><ChevronRight size={12}/>
        <Link href="/admin/home-services/bookings-jobs" style={{ color: "var(--text-tertiary)", textDecoration: "none" }}>Service Jobs</Link>
        <ChevronRight size={12}/>
        <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{d?.job_number ?? jobId}</span>
      </div>

      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
        <SectionHeader
          title={d?.job_number ?? "Job Detail"}
          subtitle={d ? `Booking ${d.booking?.booking_number ?? d.booking_id}` : "Loading job detail…"}
        />
        {d && (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 4 }}>
            {!["completed", "cancelled", "failed", "force_closed", "voided"].includes(d.status) && (
              <>
                {perm.has("admin:jobs:reassign") && (
                <button onClick={() => setShowReassign(true)}
                  style={{ padding: "8px 14px", fontSize: 13, fontWeight: 600, borderRadius: 6,
                    border: "1px solid var(--border)", background: "var(--surface)", cursor: "pointer",
                    whiteSpace: "nowrap" }}>
                  Reassign Technician
                </button>
                )}
                {perm.has("admin:jobs:status_override") && (
                <button onClick={() => setShowOverride(true)}
                  style={{ padding: "8px 14px", fontSize: 13, fontWeight: 600, borderRadius: 6,
                    border: "1px solid var(--border)", background: "var(--surface)", cursor: "pointer",
                    whiteSpace: "nowrap" }}>
                  Override Status
                </button>
                )}
                {perm.has("admin:jobs:force_close") && (
                <button onClick={() => setShowForceClose(true)}
                  style={{ padding: "8px 14px", fontSize: 13, fontWeight: 600, borderRadius: 6,
                    border: "1px solid var(--danger-text, var(--danger))", color: "var(--danger-text, var(--danger))",
                    background: "transparent", cursor: "pointer", whiteSpace: "nowrap" }}>
                  Force-Close
                </button>
                )}
              </>
            )}
            {d.status !== "voided" && perm.has("admin:jobs:void") && (
              <button onClick={() => setShowVoid(true)}
                style={{ padding: "8px 14px", fontSize: 13, fontWeight: 600, borderRadius: 6,
                  border: "1px solid var(--danger-text, var(--danger))", color: "var(--danger-text, var(--danger))",
                  background: "transparent", cursor: "pointer", whiteSpace: "nowrap" }}>
                Void Job
              </button>
            )}
          </div>
        )}
      </div>

      {showReassign && d && (
        <ReassignModal
          jobId={jobId}
          onClose={() => setShowReassign(false)}
          onDone={() => { setShowReassign(false); job.refetch(); assignmentTimeline.refetch(); }}
        />
      )}

      {showOverride && d && (
        <StatusOverrideModal
          jobId={jobId} currentStatus={d.status}
          onClose={() => setShowOverride(false)}
          onDone={() => { setShowOverride(false); job.refetch(); executionTimeline.refetch(); }}
        />
      )}

      {showForceClose && d && (
        <ForceCloseModal
          jobId={jobId} currentStatus={d.status}
          onClose={() => setShowForceClose(false)}
          onDone={() => { setShowForceClose(false); job.refetch(); executionTimeline.refetch(); }}
        />
      )}

      {showVoid && d && (
        <VoidModal
          jobId={jobId} currentStatus={d.status}
          onClose={() => setShowVoid(false)}
          onDone={() => { setShowVoid(false); job.refetch(); executionTimeline.refetch(); }}
        />
      )}

      {job.error && (
        <Card style={{ marginBottom: 16 }}>
          <p style={{ color: "var(--danger-text)", fontSize: 13 }}>
            Could not load this job. {job.requestId && `Request ID: ${job.requestId}`}
          </p>
        </Card>
      )}

      {job.loading ? (
        <Skeleton height={300} />
      ) : d && !(d as any).error ? (
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
          <div>
            <Section title="Job Summary">
              <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
                <Field label="Job Number" value={d.job_number} />
                <Field label="Status" value={<Badge variant={STATUS_VARIANT[d.status] ?? "muted"}>{d.status}</Badge>} />
                <Field label="Assignment Status" value={d.assignment_status} />
                <Field label="City / Zipcode" value={`${d.city ?? "—"} / ${d.zipcode ?? "—"}`} />
                <Field label="Created At" value={d.created_at ? new Date(d.created_at).toLocaleString() : "—"} />
                <Field label="Updated At" value={d.updated_at ? new Date(d.updated_at).toLocaleString() : "—"} />
                <Field label="SLA Status" value={
                  d.sla ? (
                    <span style={{
                      fontWeight: 700,
                      color: d.sla.sla_status === "BREACHED" ? "var(--danger-text, var(--danger))"
                        : d.sla.sla_status === "AT_RISK" ? "var(--warning-text, var(--warning))"
                        : d.sla.sla_status === "ON_TRACK" ? "var(--success-text, var(--success))"
                        : "var(--text-tertiary)",
                    }}>
                      {d.sla.sla_status === "NOT_APPLICABLE" ? "—" : d.sla.sla_status.replace("_", " ")}
                    </span>
                  ) : "—"
                } />
                {d.sla?.next_deadline && (
                  <Field label="Next Deadline" value={new Date(d.sla.next_deadline).toLocaleString()} />
                )}
                {d.sla?.minutes_overdue != null && (
                  <Field label="Overdue By" value={`${d.sla.minutes_overdue} min`} />
                )}
              </div>
            </Section>

            <Section title="Service Details">
              <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
                <Field label="Issue Summary" value={d.booking?.issue_summary} />
                <Field label="Selected Price" value={
                  priceSnapshot.selected_price_amount != null
                    ? `₹${priceSnapshot.selected_price_amount} (${priceSnapshot.selected_price_option ?? "—"})`
                    : "—"
                } />
                <Field label="Payment Mode" value={
                  priceSnapshot.payment_mode === "customer_pays_provider_directly"
                    ? "Customer Pays Provider Directly"
                    : (priceSnapshot.payment_mode ?? "—")
                } />
              </div>
            </Section>

            <Section title="Completion">
              {d.completion_data ? (
                <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
                  <Field label="Work Summary" value={String(d.completion_data.work_summary ?? "—")} />
                  <Field label="Collected Amount" value={`₹${d.completion_data.collected_amount ?? "—"}`} />
                  <Field label="Completed At" value={
                    d.completion_data.completed_at ? new Date(String(d.completion_data.completed_at)).toLocaleString() : "—"
                  } />
                </div>
              ) : (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
                  {d.status === "completed"
                    ? "This job is marked completed but has no completion proof recorded (predates the completion flow, or was set outside it)."
                    : "Not completed yet."}
                </p>
              )}
            </Section>

            <Section title="Completed Job Deduction">
              {deduction ? (
                <>
                  <div style={{ display: "flex", gap: 24, flexWrap: "wrap", marginBottom: 12 }}>
                    <Field label="Deduction Status" value={<Badge variant="success">Deducted</Badge>} />
                    <Field label="Deduction Credits" value={`${Math.abs(deduction.credit_delta)} usage credits`} />
                    <Field label="Balance Before" value={deduction.balance_before} />
                    <Field label="Balance After" value={deduction.balance_after} />
                    <Field label="Deducted At" value={deduction.created_at ? new Date(deduction.created_at).toLocaleString() : "—"} />
                  </div>
                  {d.usage_credit_deduction_duplicate_count > 0 && (
                    <p style={{ fontSize: 12, color: "var(--danger-text)" }}>
                      ⚠ {d.usage_credit_deduction_duplicate_count} duplicate ledger entr{d.usage_credit_deduction_duplicate_count === 1 ? "y" : "ies"} found for this job.
                    </p>
                  )}
                  <a
                    href={`/admin/home-services/finance?tab=credits&credits_tab=ledger&tenant_id=${d.tenant_id}&job_id=${d.id}`}
                    style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 600,
                      color: "var(--brand)", textDecoration: "none", marginTop: 4 }}
                  >
                    View exact entry in Usage Credit Ledger <ExternalLink size={12} />
                  </a>
                </>
              ) : (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
                  No deduction record found for this job
                  {d.status === "completed"
                    ? " — this completed job predates the real completion+deduction flow, or the deduction genuinely failed."
                    : " — job is not completed yet, so no deduction is expected."}
                </p>
              )}
            </Section>
          </div>

          <div>
            <Section title="Customer">
              <Field label="Customer ID" value={
                <span style={{ display: "flex", alignItems: "center", gap: 6, fontFamily: "monospace", fontSize: 12 }}>
                  {d.customer_id}
                  {d.customer_id && <Copy size={12} style={{ cursor: "pointer" }} onClick={() => copyText(d.customer_id!)} />}
                </span>
              } />
              <Field label="Name" value={d.booking?.customer_name ?? "Not captured"} />
            </Section>

            <Section title="Provider">
              <Field label="Provider" value={providerSnapshot.provider_name} />
              {/* Real bug fixed here: public_badges is an array of
                  {name, icon, color} objects (see lib/api.ts
                  MatchingDiagnosticsBadge), not strings -- .join(", ") on an
                  array of objects renders "[object Object], [object Object]"
                  rather than crashing, so this silently showed garbage text
                  on every job that had a badge instead of erroring visibly. */}
              <Field label="Badges" value={Array.isArray(providerSnapshot.public_badges)
                ? providerSnapshot.public_badges.map((b: { name?: string } | string) =>
                    typeof b === "string" ? b : b?.name ?? "").filter(Boolean).join(", ") || "—"
                : "—"} />
              <Field label="Tenant ID" value={
                <span style={{ fontFamily: "monospace", fontSize: 12 }}>{d.tenant_id}</span>
              } />
            </Section>

            <Section title="Booking">
              <Field label="Booking Number" value={d.booking?.booking_number} />
              <Field label="Booking Status" value={d.booking?.status} />
              <Field label="Booking ID" value={<span style={{ fontFamily: "monospace", fontSize: 12 }}>{d.booking_id}</span>} />
            </Section>
          </div>

          <div style={{ gridColumn: "1 / -1" }}>
            <Section title="Timeline & Notes">
              {(assignmentTimeline.loading || executionTimeline.loading || jobNotes.loading) ? (
                <Skeleton height={80} />
              ) : (
                <>
                  {[...(assignmentTimeline.data?.events ?? []).map(e => ({
                      key: `a-${e.id}`, at: e.created_at, label: `${e.event_type}${e.old_value != null ? ` (${JSON.stringify(e.old_value)} → ${JSON.stringify(e.new_value)})` : ""}`,
                    })),
                    ...(executionTimeline.data ?? []).map(e => ({
                      key: `e-${e.id}`, at: e.created_at, label: `${e.event_type}${e.old_status ? ` (${e.old_status} → ${e.new_status})` : ""}`,
                    })),
                  ].sort((a, b) => new Date(b.at ?? 0).getTime() - new Date(a.at ?? 0).getTime())
                   .map(ev => (
                    <div key={ev.key} style={{ display: "flex", gap: 10, padding: "6px 0", borderBottom: "1px solid var(--border)", fontSize: 12 }}>
                      <span style={{ color: "var(--text-tertiary)", flexShrink: 0, minWidth: 140 }}>
                        {ev.at ? new Date(ev.at).toLocaleString() : "—"}
                      </span>
                      <span>{ev.label}</span>
                    </div>
                  ))}
                  {(assignmentTimeline.data?.events?.length ?? 0) === 0 && (executionTimeline.data?.length ?? 0) === 0 && (
                    <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No timeline events recorded for this job.</p>
                  )}
                  {(jobNotes.data?.length ?? 0) > 0 && (
                    <div style={{ marginTop: 14 }}>
                      <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 8px" }}>Notes</p>
                      {jobNotes.data!.map(n => (
                        <div key={n.id} style={{ padding: "6px 0", borderBottom: "1px solid var(--border)", fontSize: 12 }}>
                          <span style={{ color: "var(--text-tertiary)", marginRight: 8 }}>
                            {n.created_at ? new Date(n.created_at).toLocaleString() : "—"}
                          </span>
                          {n.note_text}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </Section>
          </div>
        </div>
      ) : (
        <Card>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Job not found.</p>
        </Card>
      )}
    </AdminLayout>
  );
}
