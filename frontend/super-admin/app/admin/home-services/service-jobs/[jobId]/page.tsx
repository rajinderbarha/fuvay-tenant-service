"use client";
/**
 * Home Services Job Detail (Super Admin) — E2E-04B.
 * Real job + booking (price/payment/provider) + Completed Job Deduction
 * ledger link, all from GET /v1/admin/final-records/jobs/{job_id}.
 */
import React, { useCallback } from "react";
import { AdminLayout } from "../../../../../components/layout/AdminLayout";
import { Card, Badge, SectionHeader, Skeleton } from "../../../../../components/shared/ui";
import { ChevronRight, Copy, ExternalLink } from "lucide-react";
import { finalRecordsAdminApi } from "../../../../../lib/api";
import { useApi } from "../../../../../hooks/useApi";

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

export default function AdminServiceJobDetailPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = React.use(params);
  const job = useApi(useCallback(() => finalRecordsAdminApi.getJob(jobId), [jobId]));

  const d = job.data;
  const priceSnapshot = (d?.booking?.price_snapshot ?? {}) as Record<string, any>;
  const providerSnapshot = (d?.booking?.provider_snapshot ?? {}) as Record<string, any>;
  const deduction = d?.usage_credit_deduction;

  return (
    <AdminLayout activeNav="hs-bookings">
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 16, fontSize: 12, color: "var(--text-tertiary)" }}>
        <span>Admin</span><ChevronRight size={12}/><span>Home Services</span><ChevronRight size={12}/>
        <a href="/admin/home-services/service-jobs" style={{ color: "var(--text-tertiary)", textDecoration: "none" }}>Service Jobs</a>
        <ChevronRight size={12}/>
        <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{d?.job_number ?? jobId}</span>
      </div>

      <SectionHeader
        title={d?.job_number ?? "Job Detail"}
        subtitle={d ? `Booking ${d.booking?.booking_number ?? d.booking_id}` : "Loading job detail…"}
      />

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
                    href={`/admin/finance/usage-credits?tenant_id=${d.tenant_id}&job_id=${d.id}`}
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
              <Field label="Badges" value={Array.isArray(providerSnapshot.public_badges) ? providerSnapshot.public_badges.join(", ") : "—"} />
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
        </div>
      ) : (
        <Card>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Job not found.</p>
        </Card>
      )}
    </AdminLayout>
  );
}
