"use client";
import React, { useState, useCallback } from "react";
import { TenantLayout } from "../../../../../components/layout/TenantLayout";
import { Card, SectionHeader, Btn, Badge, Spinner, Modal, Input } from "../../../../../components/shared/ui";
import { customerComplianceApi, type CustomerComplianceRequest } from "../../../../../lib/api";
import { useApi, useAction } from "../../../../../hooks/useApi";
import Link from "next/link";

const REQUEST_TYPE_LABELS: Record<string, string> = {
  right_to_erasure:     "Right to Erasure",
  data_export:          "Data Export",
  consent_withdrawal:   "Consent Withdrawal",
  consent_update:       "Consent Update",
  data_correction:      "Data Correction",
  processing_objection: "Processing Objection",
  grievance:            "Grievance",
};

type BV = "default" | "success" | "warning" | "danger" | "info" | "muted" | "golden" | "terra";

const SLA_COLOR: Record<string, BV> = {
  on_track:  "success",
  at_risk:   "warning",
  breached:  "danger",
  completed: "muted",
};

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

const ALLOWED_TYPES = [
  "right_to_erasure", "data_export", "consent_withdrawal",
  "consent_update", "data_correction", "processing_objection", "grievance",
];
const REASON_REQUIRED = new Set(["right_to_erasure", "data_correction", "grievance"]);

export default function DataRequestsPage() {
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const requests = useApi(
    useCallback(() => customerComplianceApi.listRequests({
      request_type: typeFilter || undefined,
      status: statusFilter || undefined,
    }), [typeFilter, statusFilter]),
    [typeFilter, statusFilter]);

  // Create modal
  const [showCreate, setShowCreate] = useState(false);
  const [formType, setFormType] = useState("data_export");
  const [formReason, setFormReason] = useState("");
  const [formDetails, setFormDetails] = useState("");
  const [formConfirm, setFormConfirm] = useState(false);
  const [formError, setFormError] = useState("");
  const [toast, setToast] = useState("");

  const createAction = useAction(useCallback(
    (data: Parameters<typeof customerComplianceApi.createRequest>[0]) =>
      customerComplianceApi.createRequest(data), []));

  async function handleCreate() {
    setFormError("");
    if (!formType) { setFormError("Please select a request type."); return; }
    if (!formConfirm) { setFormError("You must confirm understanding."); return; }
    if (REASON_REQUIRED.has(formType) && !formReason.trim()) {
      setFormError("Reason is required for this request type."); return;
    }
    try {
      const result = await createAction.execute({
        request_type: formType, reason: formReason, details: formDetails, confirm_understanding: true,
      });
      setToast(`Request ${result.request_number} submitted. Due: ${result.due_at ? new Date(result.due_at).toLocaleDateString() : "72h"}`);
      setShowCreate(false);
      setFormReason(""); setFormDetails(""); setFormConfirm(false);
      requests.refetch();
    } catch (e: unknown) {
      const msg = (e as { message?: string })?.message || "Failed to submit request.";
      setFormError(msg);
    }
  }

  const items: CustomerComplianceRequest[] = requests.data?.requests ?? [];

  return (
    <TenantLayout>
      <div style={{ padding: "var(--space-6)" }}>
        <SectionHeader
          title="My Data Requests"
          subtitle="Track your DPDP Act 2023 data requests."
          actions={<Btn variant="primary" onClick={() => setShowCreate(true)}>+ New Request</Btn>}
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

        {/* Filters */}
        <div style={{ display: "flex", gap: "var(--space-3)", marginBottom: "var(--space-4)", flexWrap: "wrap", alignItems: "center" }}>
          <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
            style={{ padding: "var(--space-2) var(--space-3)", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", fontSize: "var(--font-size-sm)" }}>
            <option value="">All Types</option>
            {ALLOWED_TYPES.map(t => <option key={t} value={t}>{REQUEST_TYPE_LABELS[t] ?? t}</option>)}
          </select>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            style={{ padding: "var(--space-2) var(--space-3)", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", fontSize: "var(--font-size-sm)" }}>
            <option value="">All Statuses</option>
            {["submitted","under_review","approved","processing","completed","rejected","cancelled"].map(s => (
              <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
            ))}
          </select>
          {(typeFilter || statusFilter) && (
            <Btn size="sm" variant="ghost" onClick={() => { setTypeFilter(""); setStatusFilter(""); }}>
              Clear
            </Btn>
          )}
        </div>

        <Card>
          {requests.loading && <Spinner />}
          {requests.error && <p style={{ color: "var(--color-error)" }}>Could not load requests.</p>}
          {!requests.loading && items.length === 0 && (
            <div style={{ textAlign: "center", padding: "var(--space-8)", color: "var(--color-text-muted)" }}>
              <p>No data requests found.</p>
              <Btn variant="secondary" onClick={() => setShowCreate(true)} style={{ marginTop: "var(--space-3)" }}>
                Submit Your First Request
              </Btn>
            </div>
          )}

          {items.length > 0 && (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--font-size-sm)" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                    {["Request #", "Type", "Status", "SLA", "Submitted", "Due", "Action"].map(h => (
                      <th key={h} style={{ textAlign: "left", padding: "var(--space-2) var(--space-3)", fontWeight: 600 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {items.map(req => (
                    <tr key={req.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                      <td style={{ padding: "var(--space-2) var(--space-3)", fontWeight: 500 }}>{req.request_number}</td>
                      <td style={{ padding: "var(--space-2) var(--space-3)" }}>{REQUEST_TYPE_LABELS[req.request_type] ?? req.request_type}</td>
                      <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                        <Badge variant={STATUS_COLOR[req.status] ?? "muted"}>{req.status_label}</Badge>
                      </td>
                      <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                        <Badge variant={SLA_COLOR[req.sla_status] ?? "muted"}>{req.sla_label}</Badge>
                      </td>
                      <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                        {req.submitted_at ? new Date(req.submitted_at).toLocaleDateString() : "—"}
                      </td>
                      <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                        {req.due_at ? new Date(req.due_at).toLocaleDateString() : "—"}
                      </td>
                      <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                        <Link href={`/account/privacy/requests/${req.id}`}>
                          <Btn size="sm" variant="ghost">View</Btn>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <p style={{ marginTop: "var(--space-4)", fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
          <Link href="/account/privacy" style={{ color: "var(--color-link)" }}>← Back to Privacy & Data</Link>
        </p>
      </div>

      {/* Create Request Modal */}
      <Modal open={showCreate} title="New Data Request" onClose={() => setShowCreate(false)}>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            <div>
              <label style={{ fontSize: "var(--font-size-sm)", fontWeight: 500 }}>Request Type *</label>
              <select value={formType} onChange={e => { setFormType(e.target.value); setFormError(""); }}
                style={{ display: "block", width: "100%", marginTop: "var(--space-1)",
                  padding: "var(--space-2) var(--space-3)", borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)", fontSize: "var(--font-size-sm)" }}>
                {ALLOWED_TYPES.map(t => <option key={t} value={t}>{REQUEST_TYPE_LABELS[t] ?? t}</option>)}
              </select>
            </div>

            <div>
              <label style={{ fontSize: "var(--font-size-sm)", fontWeight: 500 }}>
                Reason {REASON_REQUIRED.has(formType) ? "*" : "(optional)"}
              </label>
              <textarea value={formReason} onChange={e => setFormReason(e.target.value)}
                placeholder="Describe your request..."
                rows={3}
                style={{ display: "block", width: "100%", marginTop: "var(--space-1)",
                  padding: "var(--space-2) var(--space-3)", borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)", fontSize: "var(--font-size-sm)", resize: "vertical" }}
              />
            </div>

            <div>
              <label style={{ display: "flex", gap: "var(--space-2)", alignItems: "center", cursor: "pointer", fontSize: "var(--font-size-sm)" }}>
                <input type="checkbox" checked={formConfirm} onChange={e => setFormConfirm(e.target.checked)} />
                I understand this request will be processed within 72 hours and some data may be legally exempt from deletion.
              </label>
            </div>

            {formError && (
              <p style={{ color: "var(--color-error)", fontSize: "var(--font-size-sm)", margin: 0 }}>
                {formError}
              </p>
            )}

            <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "flex-end" }}>
              <Btn variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Btn>
              <Btn variant="primary" loading={createAction.loading} onClick={handleCreate}>Submit Request</Btn>
            </div>
          </div>
      </Modal>
    </TenantLayout>
  );
}
