"use client";
import React, { useState, useCallback } from "react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { Card, SectionHeader, Btn, Badge, Spinner, Modal } from "../../../../components/shared/ui";
import { providerComplianceApi, type TenantComplianceRequest } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";

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

const TENANT_ALLOWED_TYPES = [
  "business_data_export", "business_profile_erasure",
  "owner_data_export", "owner_data_erasure",
  "staff_data_export", "staff_data_erasure",
  "consent_withdrawal", "data_correction",
  "processing_objection", "grievance",
];

const ERASURE_TYPES = new Set([
  "business_profile_erasure", "owner_data_erasure", "staff_data_erasure",
]);

type TabId = "overview" | "my-requests" | "staff-requests" | "customer-requests" | "consents" | "exports" | "help";

function SummaryCards({ summary }: { summary: ReturnType<typeof providerComplianceApi.getSummary> extends Promise<infer T> ? T : never }) {
  const cards = [
    { label: "Open Requests",       value: summary.open_requests,       accent: "var(--color-info)" },
    { label: "Pending Review",       value: summary.pending_admin_review, accent: "var(--color-warning)" },
    { label: "SLA At Risk",          value: summary.sla_at_risk,          accent: summary.sla_at_risk > 0 ? "var(--color-error)" : "var(--color-success)" },
    { label: "Staff Requests",       value: summary.staff_requests,       accent: "var(--color-primary)" },
    { label: "Data Exports",         value: summary.data_exports,         accent: "var(--color-primary-muted)" },
    { label: "Completed",            value: summary.completed_requests,   accent: "var(--color-success)" },
    { label: "Rejected",             value: summary.rejected_requests,    accent: "var(--color-error)" },
  ];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "var(--space-3)", marginBottom: "var(--space-5)" }}>
      {cards.map(c => (
        <Card key={c.label} style={{ textAlign: "center", padding: "var(--space-4)" }}>
          <p style={{ margin: 0, fontSize: "var(--font-size-2xl)", fontWeight: 700, color: c.accent }}>{c.value}</p>
          <p style={{ margin: "var(--space-1) 0 0", fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", fontWeight: 500 }}>{c.label}</p>
        </Card>
      ))}
    </div>
  );
}

function RequestTable({ requests, emptyMsg }: { requests: TenantComplianceRequest[]; emptyMsg: string }) {
  if (!requests.length) {
    return <p style={{ color: "var(--color-text-muted)", padding: "var(--space-6)", textAlign: "center" }}>{emptyMsg}</p>;
  }
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--font-size-sm)" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
            {["Request #", "Type", "Status", "SLA", "Submitted", "Due"].map(h => (
              <th key={h} style={{ textAlign: "left", padding: "var(--space-2) var(--space-3)", fontWeight: 600 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {requests.map(req => (
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
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ProviderCompliancePage() {
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [toast, setToast] = useState("");

  // Summary
  const summary = useApi(useCallback(() => providerComplianceApi.getSummary(), []), []);

  // My requests
  const [reqTypeFilter, setReqTypeFilter] = useState("");
  const [reqStatusFilter, setReqStatusFilter] = useState("");
  const myRequests = useApi(
    useCallback(() => providerComplianceApi.listRequests({
      request_type: reqTypeFilter || undefined,
      status: reqStatusFilter || undefined,
    }), [reqTypeFilter, reqStatusFilter]),
    [reqTypeFilter, reqStatusFilter, activeTab]);

  // Staff requests
  const staffRequests = useApi(
    useCallback(() => providerComplianceApi.listStaffRequests(), []),
    [activeTab]);

  // Customer requests
  const customerRequests = useApi(
    useCallback(() => providerComplianceApi.listCustomerRequests(), []),
    [activeTab]);

  // Consents
  const consents = useApi(
    useCallback(() => providerComplianceApi.listConsents(), []),
    [activeTab]);

  // Exports
  const exports = useApi(
    useCallback(() => providerComplianceApi.listExports(), []),
    [activeTab]);

  // Create request modal
  const [showCreate, setShowCreate] = useState(false);
  const [formType, setFormType] = useState("business_data_export");
  const [formReason, setFormReason] = useState("");
  const [formDetails, setFormDetails] = useState("");
  const [formConfirm, setFormConfirm] = useState(false);
  const [formError, setFormError] = useState("");

  const createAction = useAction(useCallback(
    (data: Parameters<typeof providerComplianceApi.createRequest>[0]) =>
      providerComplianceApi.createRequest(data), []));

  async function handleCreate() {
    setFormError("");
    if (!formType) { setFormError("Please select a request type."); return; }
    if (!formReason.trim()) { setFormError("Reason is required."); return; }
    if (!formConfirm) { setFormError("You must confirm understanding."); return; }
    try {
      const result = await createAction.execute({
        request_type: formType, reason: formReason,
        details: formDetails, confirm_understanding: true,
      });
      setToast(`Request ${result.request_number} submitted. Due: ${result.due_at ? new Date(result.due_at).toLocaleDateString() : "72h"}`);
      setShowCreate(false);
      setFormReason(""); setFormDetails(""); setFormConfirm(false);
      summary.refetch();
      myRequests.refetch();
    } catch (e: unknown) {
      setFormError((e as { message?: string })?.message || "Failed to submit request.");
    }
  }

  // Consent withdraw modal
  const [withdrawType, setWithdrawType] = useState<string | null>(null);
  const [withdrawReason, setWithdrawReason] = useState("");
  const withdrawAction = useAction(useCallback(
    (type: string, reason: string) => providerComplianceApi.withdrawConsent(type, reason), []));

  async function handleWithdraw() {
    if (!withdrawType) return;
    try {
      await withdrawAction.execute(withdrawType, withdrawReason);
      setToast(`Consent '${withdrawType}' withdrawn.`);
      setWithdrawType(null);
      setWithdrawReason("");
      consents.refetch();
    } catch (e: unknown) {
      setToast("Error: " + ((e as { message?: string })?.message || "Failed."));
      setWithdrawType(null);
    }
  }

  const TABS: { id: TabId; label: string }[] = [
    { id: "overview",          label: "Overview" },
    { id: "my-requests",       label: "My Requests" },
    { id: "staff-requests",    label: "Staff Requests" },
    { id: "customer-requests", label: "Customer Requests" },
    { id: "consents",          label: "Consents" },
    { id: "exports",           label: "Exports" },
    { id: "help",              label: "Help & Policy" },
  ];

  return (
    <TenantLayout>
      <div style={{ padding: "var(--space-6)" }}>
        <SectionHeader
          title="Compliance Dashboard"
          subtitle="Manage DPDP Act 2023 data requests, consents, and exports for your business."
          actions={
            activeTab === "my-requests"
              ? <Btn variant="primary" onClick={() => setShowCreate(true)}>+ New Request</Btn>
              : undefined
          }
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

        {/* Tab Bar */}
        <div style={{ display: "flex", gap: "var(--space-1)", borderBottom: "1px solid var(--color-border)", marginBottom: "var(--space-5)", flexWrap: "wrap" }}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: "none", border: "none", cursor: "pointer",
                padding: "var(--space-2) var(--space-4)",
                fontWeight: activeTab === tab.id ? 700 : 400,
                color: activeTab === tab.id ? "var(--color-primary)" : "var(--color-text-secondary)",
                borderBottom: activeTab === tab.id ? "2px solid var(--color-primary)" : "2px solid transparent",
                fontSize: "var(--font-size-sm)", transition: "color 0.15s",
              }}
              data-testid={`tab-${tab.id}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Overview */}
        {activeTab === "overview" && (
          <div>
            {summary.loading && <Spinner />}
            {summary.error && <p style={{ color: "var(--color-error)" }}>Could not load summary.</p>}
            {summary.data && <SummaryCards summary={summary.data} />}
            <Card style={{ background: "var(--color-info-subtle)" }}>
              <h3 style={{ margin: "0 0 var(--space-3)", fontWeight: 600 }}>DPDP Act 2023 — Your Obligations</h3>
              <ul style={{ margin: 0, paddingLeft: "var(--space-5)", display: "flex", flexDirection: "column", gap: "var(--space-2)", fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
                <li>All data requests must be acknowledged within <strong>72 hours</strong> (SLA).</li>
                <li>Financial records (payments, invoices, GST) are retained for 7 years as required by law and cannot be erased.</li>
                <li>Records related to open disputes, pending payouts, or active bookings cannot be deleted until closure.</li>
                <li>Erasure requests affect personal data only — aggregated or anonymized data may be retained.</li>
                <li>You can withdraw optional marketing/notification consents at any time.</li>
              </ul>
            </Card>
          </div>
        )}

        {/* My Requests */}
        {activeTab === "my-requests" && (
          <div>
            <div style={{ display: "flex", gap: "var(--space-3)", marginBottom: "var(--space-4)", flexWrap: "wrap" }}>
              <select value={reqTypeFilter} onChange={e => setReqTypeFilter(e.target.value)}
                style={{ padding: "var(--space-2) var(--space-3)", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", fontSize: "var(--font-size-sm)" }}>
                <option value="">All Types</option>
                {TENANT_ALLOWED_TYPES.map(t => <option key={t} value={t}>{REQUEST_TYPE_LABELS[t] ?? t}</option>)}
              </select>
              <select value={reqStatusFilter} onChange={e => setReqStatusFilter(e.target.value)}
                style={{ padding: "var(--space-2) var(--space-3)", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", fontSize: "var(--font-size-sm)" }}>
                <option value="">All Statuses</option>
                {["submitted","under_review","approved","processing","completed","rejected","cancelled"].map(s => (
                  <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
            <Card>
              {myRequests.loading && <Spinner />}
              {myRequests.error && <p style={{ color: "var(--color-error)" }}>Could not load requests.</p>}
              {!myRequests.loading && (
                <RequestTable
                  requests={myRequests.data?.requests ?? []}
                  emptyMsg="No compliance requests yet. Use '+ New Request' to get started."
                />
              )}
            </Card>
          </div>
        )}

        {/* Staff Requests */}
        {activeTab === "staff-requests" && (
          <Card>
            {staffRequests.loading && <Spinner />}
            {staffRequests.error && <p style={{ color: "var(--color-error)" }}>Could not load staff requests.</p>}
            {!staffRequests.loading && (
              <RequestTable
                requests={staffRequests.data?.requests ?? []}
                emptyMsg="No staff compliance requests found for your organization."
              />
            )}
            <p style={{ margin: "var(--space-4) 0 0", fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
              Staff members' compliance requests (e.g. data access, erasure) that are associated with your business are shown here.
            </p>
          </Card>
        )}

        {/* Customer Requests */}
        {activeTab === "customer-requests" && (
          <Card>
            {customerRequests.loading && <Spinner />}
            {customerRequests.error && <p style={{ color: "var(--color-error)" }}>Could not load customer requests.</p>}
            {!customerRequests.loading && (
              <RequestTable
                requests={customerRequests.data?.requests ?? []}
                emptyMsg="No customer compliance requests are currently linked to your business."
              />
            )}
            <p style={{ margin: "var(--space-4) 0 0", fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
              Only limited status information is shown. Customer names and personal data are not disclosed.
              Requests are linked when a customer's booking is associated with your business.
            </p>
          </Card>
        )}

        {/* Consents */}
        {activeTab === "consents" && (
          <Card>
            {consents.loading && <Spinner />}
            {consents.error && <p style={{ color: "var(--color-error)" }}>Could not load consent records.</p>}
            {!consents.loading && consents.data && (
              <div>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--font-size-sm)" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                        {["Consent Type", "Action", "Legal Basis", "Date", ""].map(h => (
                          <th key={h} style={{ textAlign: "left", padding: "var(--space-2) var(--space-3)", fontWeight: 600 }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(consents.data.records ?? []).map(rec => (
                        <tr key={rec.record_id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                          <td style={{ padding: "var(--space-2) var(--space-3)" }}>{rec.consent_type.replace(/_/g, " ")}</td>
                          <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                            <Badge variant={rec.action === "granted" ? "success" : rec.action === "revoked" ? "danger" : "muted"}>
                              {rec.action}
                            </Badge>
                          </td>
                          <td style={{ padding: "var(--space-2) var(--space-3)", color: "var(--color-text-muted)" }}>
                            {rec.legal_basis ?? "—"}
                          </td>
                          <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                            {new Date(rec.created_at).toLocaleDateString()}
                          </td>
                          <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                            {rec.action === "granted" && (
                              <Btn size="sm" variant="ghost"
                                onClick={() => setWithdrawType(rec.consent_type)}>
                                Withdraw
                              </Btn>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {!consents.data.records?.length && (
                  <p style={{ textAlign: "center", padding: "var(--space-6)", color: "var(--color-text-muted)" }}>
                    No consent records found.
                  </p>
                )}
              </div>
            )}
          </Card>
        )}

        {/* Exports */}
        {activeTab === "exports" && (
          <Card>
            {exports.loading && <Spinner />}
            {exports.error && <p style={{ color: "var(--color-error)" }}>Could not load exports.</p>}
            {!exports.loading && exports.data && (
              <div>
                {exports.data.exports.length === 0 ? (
                  <p style={{ textAlign: "center", padding: "var(--space-6)", color: "var(--color-text-muted)" }}>
                    No data exports yet. Submit a data export request from My Requests tab.
                  </p>
                ) : (
                  <div style={{ overflowX: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--font-size-sm)" }}>
                      <thead>
                        <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                          {["Export ID", "Status", "Generated", "Expires", "Downloaded", "Action"].map(h => (
                            <th key={h} style={{ textAlign: "left", padding: "var(--space-2) var(--space-3)", fontWeight: 600 }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {exports.data.exports.map(exp => (
                          <tr key={exp.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                            <td style={{ padding: "var(--space-2) var(--space-3)", fontFamily: "monospace", fontSize: "var(--font-size-xs)" }}>
                              {exp.id.slice(0, 8)}...
                            </td>
                            <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                              <Badge variant={
                                exp.status === "ready" ? "success" :
                                exp.status === "processing" ? "info" :
                                exp.status === "downloaded" ? "muted" :
                                exp.status === "expired" ? "danger" : "default"
                              }>{exp.status}</Badge>
                            </td>
                            <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                              {exp.generated_at ? new Date(exp.generated_at).toLocaleDateString() : "—"}
                            </td>
                            <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                              {exp.expires_at ? new Date(exp.expires_at).toLocaleDateString() : "—"}
                            </td>
                            <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                              {exp.downloaded_at ? new Date(exp.downloaded_at).toLocaleDateString() : "—"}
                            </td>
                            <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                              {exp.status === "ready" && (
                                <Btn size="sm" variant="primary"
                                  onClick={() => providerComplianceApi.downloadExport(exp.id)
                                    .then(r => { if (r?.download_url) window.open(r.download_url, "_blank"); exports.refetch(); })
                                    .catch(() => setToast("Download failed."))
                                  }>
                                  Download
                                </Btn>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </Card>
        )}

        {/* Help */}
        {activeTab === "help" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
            {[
              {
                title: "What is the DPDP Act 2023?",
                body: "The Digital Personal Data Protection Act 2023 (India) grants individuals rights over their personal data including the right to access, correct, and erase their data. As a service provider you are a 'Data Fiduciary' and must process requests within 72 hours.",
              },
              {
                title: "What data can and cannot be erased?",
                body: "Personal data not required for regulatory compliance may be erased on valid request. Financial records (GST Act: 7 years), security investigation data, active booking/dispute records, and insurance-required data cannot be erased before their retention period ends.",
              },
              {
                title: "What happens after I submit a request?",
                body: "Your request is reviewed by our compliance team within 72 hours. You will receive an email notification at each stage change. If approved, data export downloads are available for 7 days. Erasure requests are logged and audited.",
              },
              {
                title: "How do I withdraw a consent?",
                body: "Go to the Consents tab and click 'Withdraw' next to any optional consent. Marketing, notifications, location processing, and AI processing consents can be withdrawn. Core data processing consents required for service delivery cannot be withdrawn while you have an active subscription.",
              },
              {
                title: "Who can I contact for compliance queries?",
                body: "For escalations, email compliance@serviceos.in or file a Grievance request from the My Requests tab. Our Data Protection Officer responds within 24 hours.",
              },
            ].map(({ title, body }) => (
              <Card key={title}>
                <h3 style={{ margin: "0 0 var(--space-2)", fontWeight: 600, fontSize: "var(--font-size-base)" }}>{title}</h3>
                <p style={{ margin: 0, fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)", lineHeight: 1.6 }}>{body}</p>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Create Request Modal */}
      <Modal open={showCreate} title="New Compliance Request" onClose={() => setShowCreate(false)}>
        {showCreate && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            <div>
              <label style={{ fontSize: "var(--font-size-sm)", fontWeight: 500 }}>Request Type *</label>
              <select value={formType} onChange={e => { setFormType(e.target.value); setFormError(""); }}
                style={{ display: "block", width: "100%", marginTop: "var(--space-1)",
                  padding: "var(--space-2) var(--space-3)", borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)", fontSize: "var(--font-size-sm)" }}>
                {TENANT_ALLOWED_TYPES.map(t => <option key={t} value={t}>{REQUEST_TYPE_LABELS[t] ?? t}</option>)}
              </select>
            </div>

            {ERASURE_TYPES.has(formType) && (
              <div style={{ background: "var(--color-warning-subtle)", border: "1px solid var(--color-warning)", borderRadius: "var(--radius-sm)", padding: "var(--space-3)", fontSize: "var(--font-size-sm)" }}>
                <strong>Important:</strong> Erasure requests are reviewed by our compliance team.
                Financial records (7 years), active bookings, and open disputes cannot be erased.
                You will be notified of the outcome within 72 hours.
              </div>
            )}

            <div>
              <label style={{ fontSize: "var(--font-size-sm)", fontWeight: 500 }}>Reason *</label>
              <textarea value={formReason} onChange={e => setFormReason(e.target.value)}
                placeholder="Describe your request..."
                rows={3}
                style={{ display: "block", width: "100%", marginTop: "var(--space-1)",
                  padding: "var(--space-2) var(--space-3)", borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)", fontSize: "var(--font-size-sm)", resize: "vertical" }}
              />
            </div>

            <div>
              <label style={{ fontSize: "var(--font-size-sm)", fontWeight: 500 }}>Additional Details (optional)</label>
              <textarea value={formDetails} onChange={e => setFormDetails(e.target.value)}
                placeholder="Any additional context..."
                rows={2}
                style={{ display: "block", width: "100%", marginTop: "var(--space-1)",
                  padding: "var(--space-2) var(--space-3)", borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)", fontSize: "var(--font-size-sm)", resize: "vertical" }}
              />
            </div>

            <label style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-start", cursor: "pointer", fontSize: "var(--font-size-sm)" }}>
              <input type="checkbox" checked={formConfirm} onChange={e => setFormConfirm(e.target.checked)} style={{ marginTop: 2 }} />
              <span>I understand this request will be processed within 72 hours and some data may be legally exempt from deletion or export.</span>
            </label>

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
        )}
      </Modal>

      {/* Withdraw Consent Modal */}
      <Modal open={withdrawType !== null} title="Withdraw Consent" onClose={() => { setWithdrawType(null); setWithdrawReason(""); }}>
        {withdrawType !== null && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            <p style={{ margin: 0, fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
              You are withdrawing consent for: <strong>{withdrawType.replace(/_/g, " ")}</strong>
            </p>
            <div>
              <label style={{ fontSize: "var(--font-size-sm)", fontWeight: 500 }}>Reason (optional)</label>
              <textarea value={withdrawReason} onChange={e => setWithdrawReason(e.target.value)}
                placeholder="Optional reason for withdrawal..."
                rows={2}
                style={{ display: "block", width: "100%", marginTop: "var(--space-1)",
                  padding: "var(--space-2) var(--space-3)", borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)", fontSize: "var(--font-size-sm)", resize: "vertical" }}
              />
            </div>
            <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "flex-end" }}>
              <Btn variant="ghost" onClick={() => { setWithdrawType(null); setWithdrawReason(""); }}>Cancel</Btn>
              <Btn variant="danger" loading={withdrawAction.loading} onClick={handleWithdraw}>Withdraw Consent</Btn>
            </div>
          </div>
        )}
      </Modal>
    </TenantLayout>
  );
}
