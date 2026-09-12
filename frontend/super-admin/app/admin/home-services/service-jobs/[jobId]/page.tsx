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
import { formatPriceSnapshotValue } from "../../../../../lib/price-snapshot-format";
import { useApi, useAction } from "../../../../../hooks/useApi";
import { usePermissions } from "../../../../../hooks/usePermissions";
import { ReviewFeedbackTab } from "../../../../../components/home-services/ReviewFeedbackTab";
import { TableSurface } from "@serviceos/design-system";
import styles from "./jobDetail.module.css";

function copyText(t: string) { if (typeof navigator !== "undefined") navigator.clipboard?.writeText(t).catch(() => {}); }

function humanize(value: unknown) {
  if (value == null || value === "") return "—";
  const text = String(value).replace(/_/g, " ").trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : "—";
}

function money(value: unknown) {
  return formatPriceSnapshotValue("service_total", value);
}

function credits(value: unknown) {
  const amount = Number(value);
  return Number.isFinite(amount) ? `${amount.toLocaleString("en-IN", { maximumFractionDigits: 2 })} usage credits` : "—";
}

function formatAddress(snapshot: Record<string, unknown> | null | undefined) {
  if (!snapshot) return null;
  return [snapshot.address_line_1 ?? snapshot.address_line1 ?? snapshot.line1,
    snapshot.address_line_2 ?? snapshot.address_line2, snapshot.locality, snapshot.landmark,
    snapshot.city, snapshot.state, snapshot.zipcode ?? snapshot.postal_code]
    .filter(value => typeof value === "string" && value.trim())
    .join(", ") || null;
}

const STATUS_VARIANT: Record<string, "success" | "warning" | "muted" | "danger"> = {
  completed: "success", cancelled: "danger", failed: "danger", force_closed: "danger", voided: "muted",
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
  const targets = useApi(useCallback(() => adminExecutionApi.getAllowedServiceJobOverrideTargets(jobId), [jobId]), [jobId]);
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
        <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 14px" }}>{["cancelled", "failed"].includes(currentStatus) ? "Reopen Job" : "Override Job Status"}</p>
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
            placeholder={["cancelled", "failed"].includes(currentStatus) ? "Why should this job return to dispatch?" : "Why is this status being overridden?"} />
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
            {override.loading ? "Submitting…" : ["cancelled", "failed"].includes(currentStatus) ? "Reopen Job" : "Confirm Override"}
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
  const technicians = useApi(useCallback(() => adminServiceJobAssignmentApi.getEligibleTechnicians(jobId), [jobId]), [jobId]);
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
  const job = useApi(useCallback(() => finalRecordsAdminApi.getJob(jobId), [jobId]), [jobId]);
  // FINAL-L5-05B — these two admin timeline endpoints (assignment + execution)
  // plus the notes endpoint already existed as real, working backend routes
  // and typed API-client methods, but were never wired into this page (dead
  // code). Wiring them here closes part of the real feature-parity gap this
  // sprint found between this canonical page and the legacy /admin/operations
  // page (which shows a rendered timeline) — see FINAL_L5_05_JOBS_MIGRATION.md.
  const assignmentTimeline = useApi(useCallback(() => adminServiceJobAssignmentApi.getJobTimeline(jobId), [jobId]), [jobId]);
  const executionTimeline = useApi(useCallback(() => adminExecutionApi.getJobTimeline(jobId), [jobId]), [jobId]);
  const jobNotes = useApi(useCallback(() => adminExecutionApi.getJobNotes(jobId), [jobId]), [jobId]);
  const perm = usePermissions();
  const [showReassign, setShowReassign] = useState(false);
  const [showOverride, setShowOverride] = useState(false);
  const [showForceClose, setShowForceClose] = useState(false);
  const [showVoid, setShowVoid] = useState(false);

  const d = job.data;
  const priceSnapshot = (d?.price_summary ?? d?.booking?.price_snapshot ?? {}) as Record<string, any>;
  const providerSnapshot = (d?.booking?.provider_snapshot ?? {}) as Record<string, any>;
  const deduction = d?.usage_credit_deduction;
  const platformChargeRecovery = d?.platform_charge_recovery;
  const commissionAmount = d?.charge_summary?.commission_amount ?? (deduction ? Math.abs(deduction.credit_delta) : null);
  const platformChargeAmount = d?.charge_summary?.platform_charge_amount
    ?? (platformChargeRecovery ? Math.abs(platformChargeRecovery.credit_delta) : priceSnapshot.platform_fee);
  const totalProviderDeduction = d?.charge_summary?.total_provider_credit_deduction;
  const bookingAddress = formatAddress(d?.booking?.address_snapshot);

  return (
    <AdminLayout activeNav="home-services-operations">
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
            {!['completed', 'force_closed', 'voided'].includes(d.status) && perm.has("admin:jobs:status_override") && (
              <button onClick={() => setShowOverride(true)}
                style={{ padding: "8px 14px", fontSize: 13, fontWeight: 600, borderRadius: 6,
                  border: "1px solid var(--border)", background: "var(--surface)", cursor: "pointer",
                  whiteSpace: "nowrap" }}>
                {['cancelled', 'failed'].includes(d.status) ? 'Reopen Job' : 'Override Status'}
              </button>
            )}
            {!['completed', 'cancelled', 'failed', 'force_closed', 'voided'].includes(d.status) && perm.has("admin:jobs:void") && (
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
        <div className={styles.detailGrid}>
          <div className={styles.column}>
            <Section title="Complete Job Details">
              <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
                <Field label="Job Number" value={d.job_number} />
                <Field label="Status" value={<Badge variant={STATUS_VARIANT[d.status] ?? "muted"}>{d.status}</Badge>} />
                <Field label="Assignment Status" value={humanize(d.assignment_status)} />
                <Field label="Technician" value={d.technician?.full_name ?? "Unassigned"} />
                {d.technician?.designation && <Field label="Technician Role" value={d.technician.designation} />}
                <Field label="Scheduled Date" value={d.scheduled_date ? new Date(`${d.scheduled_date}T00:00:00`).toLocaleDateString() : "—"} />
                <Field label="Time Window" value={d.scheduled_time_window ?? "—"} />
                <Field label="Priority" value={d.is_emergency ? <Badge variant="danger">Emergency</Badge> : "Standard"} />
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
                {d.warranty_days_snapshot != null && <Field label="Warranty" value={`${d.warranty_days_snapshot} days`} />}
                {d.warranty_expires_at && <Field label="Warranty Expires" value={new Date(d.warranty_expires_at).toLocaleDateString()} />}
                {d.failure_reason && <Field label="Failure Reason" value={d.failure_reason} />}
              </div>
            </Section>

            <Section title="Service & Booking Details">
              <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
                <Field label="Service" value={d.service_context?.service_name ?? "—"} />
                <Field label="Job Type" value={d.service_context?.job_type ?? humanize(d.service_context?.legacy_job_type)} />
                <Field label="Reported Problem" value={d.service_context?.problem_name ?? "—"} />
                <Field label="Issue Summary" value={d.booking?.issue_summary} />
                {d.booking?.customer_note && <Field label="Customer Note" value={d.booking.customer_note} />}
                <Field label="Customer Total" value={
                  (priceSnapshot.customer_total ?? priceSnapshot.display_price ?? priceSnapshot.selected_price_amount) != null
                    ? formatPriceSnapshotValue("customer_total", priceSnapshot.customer_total ?? priceSnapshot.display_price ?? priceSnapshot.selected_price_amount)
                    : "—"
                } />
                {priceSnapshot.service_total != null && (
                  <Field label="Service Amount" value={formatPriceSnapshotValue("service_total", priceSnapshot.service_total)} />
                )}
                {priceSnapshot.platform_fee != null && (
                  <Field label="Platform Charge" value={formatPriceSnapshotValue("platform_fee", priceSnapshot.platform_fee)} />
                )}
                <Field label="Payment Mode" value={
                  priceSnapshot.payment_mode === "customer_pays_provider_directly"
                    ? "Customer Pays Provider Directly"
                    : (priceSnapshot.payment_mode ?? "—")
                } />
                {priceSnapshot.payment_status && <Field label="Payment Status" value={humanize(priceSnapshot.payment_status)} />}
                {priceSnapshot.invoice_number && <Field label="Invoice Number" value={priceSnapshot.invoice_number} />}
              </div>
            </Section>

            <Section title="Technician Estimate & Customer Approval">
              {d.current_quote ? (
                <>
                  <div style={{ display: "flex", gap: 24, flexWrap: "wrap", marginBottom: 12 }}>
                    <Field label="Estimate Number" value={d.current_quote.quote_number} />
                    <Field label="Version" value={d.current_quote.version_number} />
                    <Field label="Approval Status" value={
                      <Badge variant={d.current_quote.status === "customer_approved" ? "success" : "warning"}>
                        {humanize(d.current_quote.status)}
                      </Badge>
                    } />
                    <Field label="Sent to Customer" value={d.current_quote.sent_to_customer_at
                      ? new Date(d.current_quote.sent_to_customer_at).toLocaleString() : "—"} />
                    <Field label="Customer Approved At" value={d.current_quote.approved_at
                      ? new Date(d.current_quote.approved_at).toLocaleString() : "—"} />
                  </div>
                  {d.current_quote.customer_visible_notes && (
                    <div style={{ padding: 10, marginBottom: 12, borderRadius: 8, background: "var(--surface-secondary)" }}>
                      <Field label="Notes Shown to Customer" value={d.current_quote.customer_visible_notes} />
                    </div>
                  )}
                  {(d.quote_items?.length ?? 0) > 0 ? (
                    <div style={{ overflowX: "auto" }}>
                      <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                        <thead>
                          <tr style={{ color: "var(--text-tertiary)", textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                            <th style={{ padding: "8px 6px" }}>Item / Service</th>
                            <th style={{ padding: "8px 6px" }}>Type</th>
                            <th style={{ padding: "8px 6px", textAlign: "right" }}>Qty</th>
                            <th style={{ padding: "8px 6px", textAlign: "right" }}>Unit Price</th>
                            <th style={{ padding: "8px 6px", textAlign: "right" }}>Total</th>
                          </tr>
                        </thead>
                        <tbody>
                          {d.quote_items!.map(item => (
                            <tr key={item.id} style={{ borderBottom: "1px solid var(--border)" }}>
                              <td style={{ padding: "10px 6px" }}>
                                <strong>{item.item_name}</strong>
                                {item.item_description && <div style={{ color: "var(--text-tertiary)", marginTop: 2 }}>{item.item_description}</div>}
                              </td>
                              <td style={{ padding: "10px 6px" }}>{humanize(item.item_type)}</td>
                              <td style={{ padding: "10px 6px", textAlign: "right" }}>{item.quantity}</td>
                              <td style={{ padding: "10px 6px", textAlign: "right" }}>{money(item.unit_price)}</td>
                              <td style={{ padding: "10px 6px", textAlign: "right", fontWeight: 700 }}>{money(item.line_total)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </TableSurface>
                    </div>
                  ) : (
                    <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No technician-added estimate items were recorded.</p>
                  )}
                  <div style={{ display: "flex", gap: 24, flexWrap: "wrap", marginTop: 14 }}>
                    <Field label="Labour" value={money(d.current_quote.labour_amount)} />
                    <Field label="Parts" value={money(d.current_quote.parts_amount)} />
                    <Field label="Services" value={money(d.current_quote.service_amount)} />
                    <Field label="Discount" value={money(d.current_quote.discount_amount)} />
                    <Field label="Tax" value={money(d.current_quote.tax_amount)} />
                    <Field label="Approved Service Total" value={money(d.current_quote.total_amount)} />
                  </div>
                </>
              ) : (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No technician estimate was created for this job.</p>
              )}
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

            <Section title="Platform & Commission Charges">
              {(deduction || platformChargeRecovery) ? (
                <>
                  <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 14px" }}>
                    The customer pays the provider directly. Platform and commission charges are recorded separately against the provider&apos;s usage credits.
                  </p>
                  <div style={{ display: "flex", gap: 24, flexWrap: "wrap", marginBottom: 12 }}>
                    <Field label="Platform Charge" value={money(priceSnapshot.platform_fee ?? platformChargeAmount)} />
                    <Field label="Platform Charge Recovery" value={credits(platformChargeAmount)} />
                    <Field label="Commission Charge" value={credits(commissionAmount)} />
                    <Field label="Total Provider Credit Deduction" value={credits(totalProviderDeduction)} />
                    {platformChargeRecovery && <Field label="Platform Balance" value={`${platformChargeRecovery.balance_before} → ${platformChargeRecovery.balance_after}`} />}
                    {deduction && <Field label="Commission Balance" value={`${deduction.balance_before} → ${deduction.balance_after}`} />}
                    <Field label="Recorded At" value={
                      (deduction?.created_at ?? platformChargeRecovery?.created_at)
                        ? new Date(deduction?.created_at ?? platformChargeRecovery!.created_at).toLocaleString()
                        : "—"
                    } />
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
                    View job entries in Usage Credit Ledger <ExternalLink size={12} />
                  </a>
                </>
              ) : (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
                  No platform or commission charge record found for this job
                  {d.status === "completed"
                    ? " — this completed job predates the current charge flow, or the charge genuinely failed."
                    : " — job is not completed yet, so no charge is expected."}
                </p>
              )}
            </Section>
          </div>

          <div className={styles.column}>
            <Section title="Customer">
              <Field label="Customer ID" value={
                <span style={{ display: "flex", alignItems: "center", gap: 6, fontFamily: "monospace", fontSize: 12 }}>
                  {d.customer_id}
                  {d.customer_id && <Copy size={12} style={{ cursor: "pointer" }} onClick={() => copyText(d.customer_id!)} />}
                </span>
              } />
              <Field label="Name" value={d.booking?.customer_name ?? "Not captured"} />
              <Field label="Phone" value={d.booking?.customer_phone ?? "Not captured"} />
              <Field label="Service Address" value={bookingAddress ?? `${d.city ?? "—"} · ${d.zipcode ?? "—"}`} />
              {(d.booking?.customer_photo_urls?.length ?? 0) > 0 && (
                <Field label="Customer Attachments" value={
                  <span style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {d.booking!.customer_photo_urls.map((url, index) => (
                      <a key={url} href={url} target="_blank" rel="noreferrer"
                        style={{ color: "var(--brand)", textDecoration: "none" }}>
                        Photo {index + 1} <ExternalLink size={11} style={{ display: "inline" }} />
                      </a>
                    ))}
                  </span>
                } />
              )}
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
              <Field label="Assigned Technician" value={d.technician?.full_name ?? "Unassigned"} />
              {d.technician?.phone && <Field label="Technician Phone" value={d.technician.phone} />}
              {d.technician?.email && <Field label="Technician Email" value={d.technician.email} />}
            </Section>

            <Section title="Booking">
              <Field label="Booking Number" value={d.booking?.booking_number} />
              <Field label="Booking Status" value={d.booking?.status} />
              <Field label="Preferred Visit" value={
                [d.booking?.preferred_date, d.booking?.preferred_time_window].filter(Boolean).join(" · ") || "—"
              } />
              <Field label="Emergency Booking" value={d.booking?.is_emergency ? "Yes" : "No"} />
              <Field label="Booking ID" value={<span style={{ fontFamily: "monospace", fontSize: 12 }}>{d.booking_id}</span>} />
            </Section>
          </div>

          <div className={styles.fullRow}>
            <Section title="Review & Feedback">
              <ReviewFeedbackTab jobId={d.id} jobStatus={d.status} />
            </Section>
          </div>

          <div className={styles.fullRow}>
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
