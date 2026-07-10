"use client";
import React, { useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { TenantLayout } from "../../../../../../components/layout/TenantLayout";
import { Card, SectionHeader, Btn, Badge, Spinner } from "../../../../../../components/shared/ui";
import { providerComplianceApi } from "../../../../../../lib/api";
import { useApi, useAction } from "../../../../../../hooks/useApi";
import Link from "next/link";

type BV = "default" | "success" | "warning" | "danger" | "info" | "muted" | "golden" | "terra";

const STATUS_COLOR: Record<string, BV> = {
  submitted:                    "info",
  identity_verification_pending:"warning",
  under_review:                 "warning",
  approved:                     "success",
  partially_approved:           "warning",
  rejected:                     "danger",
  processing:                   "info",
  completed:                    "success",
  failed:                       "danger",
  cancelled:                    "muted",
  sla_breached:                 "danger",
};

const SLA_COLOR: Record<string, BV> = {
  on_track:  "success",
  at_risk:   "warning",
  breached:  "danger",
  completed: "muted",
};

const REQUEST_TYPE_LABELS: Record<string, string> = {
  business_data_export:    "Business Data Export",
  business_profile_erasure:"Business Profile Erasure",
  owner_data_export:       "Owner Data Export",
  owner_data_erasure:      "Owner Data Erasure",
  staff_data_export:       "Staff Data Export",
  staff_data_erasure:      "Staff Data Erasure",
  consent_withdrawal:      "Consent Withdrawal",
  data_correction:         "Data Correction",
  processing_objection:    "Processing Objection",
  grievance:               "Grievance",
};

const WHAT_NEXT: Record<string, string> = {
  submitted:                    "Your request has been received and will be reviewed within 72 hours.",
  identity_verification_pending:"Identity verification required. Please check your email.",
  under_review:                 "Our compliance team is reviewing your request.",
  approved:                     "Request approved. Processing is underway.",
  processing:                   "Your request is actively being processed.",
  completed:                    "Your request has been completed.",
  rejected:                     "Your request was rejected. See reason below.",
  partially_approved:           "Partially approved. Some records are legally exempt.",
  cancelled:                    "This request was cancelled.",
  sla_breached:                 "This request is overdue. Our team is resolving it.",
};

const EXPORT_TYPES = new Set([
  "business_data_export", "owner_data_export", "staff_data_export",
]);

export default function TenantComplianceRequestDetailPage() {
  const params = useParams<{ id: string }>();
  const requestId = params?.id ?? "";

  const req = useApi(
    useCallback(() => providerComplianceApi.getRequest(requestId), [requestId]),
    [requestId]);

  const [toast, setToast] = useState("");
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [generateLoading, setGenerateLoading] = useState(false);

  const cancelAction = useAction(useCallback(
    () => providerComplianceApi.cancelRequest(requestId), [requestId]));

  async function handleCancel() {
    await cancelAction.execute();
    setToast("Request cancelled.");
    req.refetch();
  }

  async function handleGenerateExport() {
    setGenerateLoading(true);
    try {
      const result = await providerComplianceApi.generateExport(requestId);
      setToast(result.message || "Export generation started.");
      req.refetch();
    } catch (e: unknown) {
      setToast("Error: " + ((e as { message?: string })?.message || "Failed to generate export."));
    } finally {
      setGenerateLoading(false);
    }
  }

  async function handleDownload(exportId: string) {
    setDownloadLoading(true);
    try {
      const result = await providerComplianceApi.downloadExport(exportId);
      if (result?.download_url) {
        window.open(result.download_url, "_blank");
        setToast("Download started.");
        req.refetch();
      }
    } catch (e: unknown) {
      setToast("Error: " + ((e as { message?: string })?.message || "Download failed."));
    } finally {
      setDownloadLoading(false);
    }
  }

  const detail = req.data;

  return (
    <TenantLayout>
      <div style={{ padding: "var(--space-6)" }}>
        <SectionHeader
          title={detail ? `Request ${detail.request_number}` : "Compliance Request"}
          subtitle={detail ? REQUEST_TYPE_LABELS[detail.request_type] ?? detail.request_type : "Loading..."}
        />

        {toast && (
          <div style={{
            background: "var(--color-success-subtle)", color: "var(--color-success)",
            border: "1px solid var(--color-success)", borderRadius: "var(--radius-md)",
            padding: "var(--space-3) var(--space-4)", marginBottom: "var(--space-4)",
          }}>
            {toast}
            <button onClick={() => setToast("")} style={{ marginLeft: 8 }}>✕</button>
          </div>
        )}

        {req.loading && <Spinner />}
        {req.error && <p style={{ color: "var(--color-error)" }}>Could not load request.</p>}

        {detail && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
            {/* Summary */}
            <Card>
              <h3 style={{ margin: "0 0 var(--space-4)", fontWeight: 600, fontSize: "var(--font-size-base)" }}>
                Request Summary
              </h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "var(--space-4)" }}>
                {[
                  { label: "Request Number",  value: detail.request_number },
                  { label: "Type",             value: REQUEST_TYPE_LABELS[detail.request_type] ?? detail.request_type },
                  { label: "Subject",          value: detail.subject_type?.replace(/_/g, " ") ?? "—" },
                  { label: "Submitted",        value: detail.submitted_at ? new Date(detail.submitted_at).toLocaleDateString() : "—" },
                  { label: "Due Date",         value: detail.due_at ? new Date(detail.due_at).toLocaleDateString() : "—" },
                  { label: "Completed",        value: detail.completed_at ? new Date(detail.completed_at).toLocaleDateString() : "—" },
                ].map(({ label, value }) => (
                  <div key={label}>
                    <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</p>
                    <p style={{ margin: "var(--space-1) 0 0", fontWeight: 600, fontSize: "var(--font-size-sm)" }}>{value}</p>
                  </div>
                ))}
              </div>
              <div style={{ display: "flex", gap: "var(--space-3)", marginTop: "var(--space-4)" }}>
                <div>
                  <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>Status</span><br />
                  <Badge variant={STATUS_COLOR[detail.status] ?? "muted"}>{detail.status_label}</Badge>
                </div>
                <div>
                  <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>SLA</span><br />
                  <Badge variant={SLA_COLOR[detail.sla_status] ?? "muted"}>{detail.sla_label}</Badge>
                </div>
              </div>
            </Card>

            {/* What Happens Next */}
            <Card style={{ background: "var(--color-info-subtle)" }}>
              <h3 style={{ margin: "0 0 var(--space-2)", fontWeight: 600, fontSize: "var(--font-size-sm)" }}>What Happens Next</h3>
              <p style={{ margin: 0, fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
                {WHAT_NEXT[detail.status] ?? "Our team is processing your request."}
              </p>
            </Card>

            {/* Rejection Reason */}
            {detail.rejection_reason && (
              <Card style={{ background: "var(--color-error-subtle)", border: "1px solid var(--color-error)" }}>
                <h3 style={{ margin: "0 0 var(--space-2)", fontWeight: 600, fontSize: "var(--font-size-sm)", color: "var(--color-error)" }}>
                  Rejection Reason
                </h3>
                <p style={{ margin: 0, fontSize: "var(--font-size-sm)" }}>{detail.rejection_reason}</p>
              </Card>
            )}

            {/* Export section */}
            {EXPORT_TYPES.has(detail.request_type) && (
              <Card>
                <h3 style={{ margin: "0 0 var(--space-3)", fontWeight: 600, fontSize: "var(--font-size-base)" }}>Data Export</h3>
                {!detail.export && detail.status === "approved" && (
                  <div>
                    <p style={{ margin: "0 0 var(--space-3)", fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
                      Your request is approved. Click below to generate your data export.
                    </p>
                    <Btn variant="primary" loading={generateLoading} onClick={handleGenerateExport}
                      data-testid="generate-export-btn">
                      Generate Export
                    </Btn>
                  </div>
                )}
                {detail.export && (
                  detail.export.is_expired ? (
                    <div>
                      <p style={{ color: "var(--color-error)", margin: "0 0 var(--space-3)" }}>
                        This export has expired. Please submit a new export request.
                      </p>
                      <Link href="/provider/compliance">
                        <Btn variant="secondary">Back to Compliance</Btn>
                      </Link>
                    </div>
                  ) : detail.export.status === "processing" ? (
                    <p style={{ margin: 0, fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
                      Export is being generated. Check back shortly.
                    </p>
                  ) : (
                    <div>
                      <p style={{ margin: "0 0 var(--space-3)", fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
                        Your export is ready.
                        {detail.export.expires_at && (
                          <> Expires: {new Date(detail.export.expires_at).toLocaleDateString()}</>
                        )}
                      </p>
                      <Btn variant="primary" loading={downloadLoading}
                        onClick={() => handleDownload(detail.export!.export_id)}
                        data-testid="export-download-btn">
                        Download Business Data
                      </Btn>
                    </div>
                  )
                )}
                {!detail.export && detail.status !== "approved" && (
                  <p style={{ margin: 0, fontSize: "var(--font-size-sm)", color: "var(--color-text-muted)" }}>
                    Export will be available once your request is approved.
                  </p>
                )}
              </Card>
            )}

            {/* Audit Trail */}
            {detail.audit_trail && detail.audit_trail.length > 0 && (
              <Card>
                <h3 style={{ margin: "0 0 var(--space-3)", fontWeight: 600, fontSize: "var(--font-size-base)" }}>Request Timeline</h3>
                <ol style={{ listStyle: "none", padding: 0, margin: 0 }}>
                  {detail.audit_trail.map((entry, i) => (
                    <li key={i} style={{
                      display: "flex", gap: "var(--space-3)", paddingBottom: "var(--space-3)",
                      borderLeft: i < detail.audit_trail!.length - 1 ? "2px solid var(--color-border)" : "none",
                      paddingLeft: "var(--space-3)", marginLeft: "var(--space-2)",
                    }}>
                      <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--color-primary)", flexShrink: 0, marginTop: 4 }} />
                      <div>
                        <p style={{ margin: 0, fontSize: "var(--font-size-sm)", fontWeight: 500 }}>
                          {entry.action.replace(/\./g, " › ").replace(/_/g, " ")}
                        </p>
                        <p style={{ margin: "2px 0 0", fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
                          {new Date(entry.created_at).toLocaleString()}
                        </p>
                      </div>
                    </li>
                  ))}
                </ol>
              </Card>
            )}

            {/* Actions */}
            <div style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
              <Link href="/provider/compliance">
                <Btn variant="ghost">← Back to Compliance</Btn>
              </Link>
              {["submitted", "identity_verification_pending"].includes(detail.status) && (
                <Btn variant="danger" loading={cancelAction.loading} onClick={handleCancel}
                  data-testid="cancel-request-btn">
                  Cancel Request
                </Btn>
              )}
            </div>
          </div>
        )}
      </div>
    </TenantLayout>
  );
}
