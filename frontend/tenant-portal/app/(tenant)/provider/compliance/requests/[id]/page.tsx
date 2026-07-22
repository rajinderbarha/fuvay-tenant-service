"use client";
import React, { useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { TenantLayout } from "../../../../../../components/layout/TenantLayout";
import { Card, PageHeader, Button, Spinner } from "@serviceos/design-system";
import { Badge } from "../../../../../../components/shared/ui";
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
      <PageHeader
        title={detail ? `Request ${detail.request_number}` : "Compliance Request"}
        description={detail ? REQUEST_TYPE_LABELS[detail.request_type] ?? detail.request_type : "Loading..."}
      />

      {toast && (
        <div style={{
          background: "var(--success-bg)", color: "var(--success-text)",
          border: "1px solid var(--success-border)", borderRadius: 10,
          padding: "10px 16px", margin: "16px 0",
        }}>
          {toast}
          <button onClick={() => setToast("")} style={{ marginLeft: 8, background: "none", border: "none", cursor: "pointer" }}>✕</button>
        </div>
      )}

      {req.loading && <Spinner />}
      {req.error && <p style={{ color: "var(--danger-text)" }}>Could not load request.</p>}

      {detail && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 16 }}>
          {/* Summary */}
          <Card>
            <h3 style={{ margin: "0 0 16px", fontWeight: 600, fontSize: 14 }}>
              Request Summary
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16 }}>
              {[
                { label: "Request Number",  value: detail.request_number },
                { label: "Type",             value: REQUEST_TYPE_LABELS[detail.request_type] ?? detail.request_type },
                { label: "Subject",          value: detail.subject_type?.replace(/_/g, " ") ?? "—" },
                { label: "Submitted",        value: detail.submitted_at ? new Date(detail.submitted_at).toLocaleDateString() : "—" },
                { label: "Due Date",         value: detail.due_at ? new Date(detail.due_at).toLocaleDateString() : "—" },
                { label: "Completed",        value: detail.completed_at ? new Date(detail.completed_at).toLocaleDateString() : "—" },
              ].map(({ label, value }) => (
                <div key={label}>
                  <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</p>
                  <p style={{ margin: "4px 0 0", fontWeight: 600, fontSize: 13 }}>{value}</p>
                </div>
              ))}
            </div>
            <div style={{ display: "flex", gap: 12, marginTop: 16 }}>
              <div>
                <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Status</span><br />
                <Badge variant={STATUS_COLOR[detail.status] ?? "muted"}>{detail.status_label}</Badge>
              </div>
              <div>
                <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>SLA</span><br />
                <Badge variant={SLA_COLOR[detail.sla_status] ?? "muted"}>{detail.sla_label}</Badge>
              </div>
            </div>
          </Card>

          {/* What Happens Next */}
          <Card style={{ background: "var(--info-bg)" }}>
            <h3 style={{ margin: "0 0 8px", fontWeight: 600, fontSize: 13 }}>What Happens Next</h3>
            <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)" }}>
              {WHAT_NEXT[detail.status] ?? "Our team is processing your request."}
            </p>
          </Card>

          {/* Rejection Reason */}
          {detail.rejection_reason && (
            <Card style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              <h3 style={{ margin: "0 0 8px", fontWeight: 600, fontSize: 13, color: "var(--danger-text)" }}>
                Rejection Reason
              </h3>
              <p style={{ margin: 0, fontSize: 13 }}>{detail.rejection_reason}</p>
            </Card>
          )}

          {/* Export section */}
          {EXPORT_TYPES.has(detail.request_type) && (
            <Card>
              <h3 style={{ margin: "0 0 12px", fontWeight: 600, fontSize: 14 }}>Data Export</h3>
              {!detail.export && detail.status === "approved" && (
                <div>
                  <p style={{ margin: "0 0 12px", fontSize: 13, color: "var(--text-secondary)" }}>
                    Your request is approved. Click below to generate your data export.
                  </p>
                  <Button variant="primary" loading={generateLoading} onClick={handleGenerateExport}
                    data-testid="generate-export-btn">
                    Generate Export
                  </Button>
                </div>
              )}
              {detail.export && (
                detail.export.is_expired ? (
                  <div>
                    <p style={{ color: "var(--danger-text)", margin: "0 0 12px" }}>
                      This export has expired. Please submit a new export request.
                    </p>
                    <Link href="/provider/compliance">
                      <Button variant="secondary">Back to Compliance</Button>
                    </Link>
                  </div>
                ) : detail.export.status === "processing" ? (
                  <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)" }}>
                    Export is being generated. Check back shortly.
                  </p>
                ) : (
                  <div>
                    <p style={{ margin: "0 0 12px", fontSize: 13, color: "var(--text-secondary)" }}>
                      Your export is ready.
                      {detail.export.expires_at && (
                        <> Expires: {new Date(detail.export.expires_at).toLocaleDateString()}</>
                      )}
                    </p>
                    <Button variant="primary" loading={downloadLoading}
                      onClick={() => handleDownload(detail.export!.export_id)}
                      data-testid="export-download-btn">
                      Download Business Data
                    </Button>
                  </div>
                )
              )}
              {!detail.export && detail.status !== "approved" && (
                <p style={{ margin: 0, fontSize: 13, color: "var(--text-tertiary)" }}>
                  Export will be available once your request is approved.
                </p>
              )}
            </Card>
          )}

          {/* Audit Trail */}
          {detail.audit_trail && detail.audit_trail.length > 0 && (
            <Card>
              <h3 style={{ margin: "0 0 12px", fontWeight: 600, fontSize: 14 }}>Request Timeline</h3>
              <ol style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {detail.audit_trail.map((entry, i) => (
                  <li key={i} style={{
                    display: "flex", gap: 12, paddingBottom: 12,
                    borderLeft: i < detail.audit_trail!.length - 1 ? "2px solid var(--border)" : "none",
                    paddingLeft: 12, marginLeft: 8,
                  }}>
                    <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--brand)", flexShrink: 0, marginTop: 4 }} />
                    <div>
                      <p style={{ margin: 0, fontSize: 13, fontWeight: 500 }}>
                        {entry.action.replace(/\./g, " › ").replace(/_/g, " ")}
                      </p>
                      <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>
                        {new Date(entry.created_at).toLocaleString()}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            </Card>
          )}

          {/* Actions */}
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <Link href="/provider/compliance">
              <Button variant="ghost">← Back to Compliance</Button>
            </Link>
            {["submitted", "identity_verification_pending"].includes(detail.status) && (
              <Button variant="destructive" loading={cancelAction.loading} onClick={handleCancel}
                data-testid="cancel-request-btn">
                Cancel Request
              </Button>
            )}
          </div>
        </div>
      )}
    </TenantLayout>
  );
}
