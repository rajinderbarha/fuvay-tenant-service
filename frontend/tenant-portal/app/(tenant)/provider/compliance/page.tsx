"use client";
import React, { useState, useCallback } from "react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { Card, PageHeader, Button, Modal, Select, Textarea, Spinner } from "@serviceos/design-system";
import { Badge } from "../../../../components/shared/ui";
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
    { label: "Open Requests",  value: summary.open_requests,        accent: "var(--info)" },
    { label: "Pending Review", value: summary.pending_admin_review,  accent: "var(--warning)" },
    { label: "SLA At Risk",    value: summary.sla_at_risk,           accent: summary.sla_at_risk > 0 ? "var(--danger)" : "var(--success)" },
    { label: "Staff Requests", value: summary.staff_requests,        accent: "var(--brand)" },
    { label: "Data Exports",   value: summary.data_exports,          accent: "var(--accent)" },
    { label: "Completed",     value: summary.completed_requests,     accent: "var(--success)" },
    { label: "Rejected",      value: summary.rejected_requests,      accent: "var(--danger)" },
  ];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, marginBottom: 16 }}>
      {cards.map(c => (
        <Card key={c.label} padding="md" style={{ textAlign: "center" }}>
          <p style={{ margin: 0, fontSize: 22, fontWeight: 700, color: c.accent }}>{c.value}</p>
          <p style={{ margin: "4px 0 0", fontSize: 11, color: "var(--text-tertiary)", fontWeight: 500 }}>{c.label}</p>
        </Card>
      ))}
    </div>
  );
}

function RequestTable({ requests, emptyMsg }: { requests: TenantComplianceRequest[]; emptyMsg: string }) {
  if (!requests.length) {
    return <p style={{ color: "var(--text-tertiary)", padding: 24, textAlign: "center" }}>{emptyMsg}</p>;
  }
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            {["Request #", "Type", "Status", "SLA", "Submitted", "Due"].map(h => (
              <th key={h} style={{ textAlign: "left", padding: "8px 12px", fontWeight: 600 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {requests.map(req => (
            <tr key={req.id} style={{ borderBottom: "1px solid var(--border)" }}>
              <td style={{ padding: "8px 12px", fontWeight: 500 }}>{req.request_number}</td>
              <td style={{ padding: "8px 12px" }}>{REQUEST_TYPE_LABELS[req.request_type] ?? req.request_type}</td>
              <td style={{ padding: "8px 12px" }}>
                <Badge variant={STATUS_COLOR[req.status] ?? "muted"}>{req.status_label}</Badge>
              </td>
              <td style={{ padding: "8px 12px" }}>
                <Badge variant={SLA_COLOR[req.sla_status] ?? "muted"}>{req.sla_label}</Badge>
              </td>
              <td style={{ padding: "8px 12px" }}>
                {req.submitted_at ? new Date(req.submitted_at).toLocaleDateString() : "—"}
              </td>
              <td style={{ padding: "8px 12px" }}>
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
      <PageHeader
        title="Compliance Dashboard"
        description="Manage DPDP Act 2023 data requests, consents, and exports for your business."
        actions={
          activeTab === "my-requests"
            ? <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>+ New Request</Button>
            : undefined
        }
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

      <div style={{ display: "flex", gap: 4, padding: 4, background: "var(--bg-muted)",
        borderRadius:"var(--radius-lg)", border: "1px solid var(--border)", margin: "16px 0", flexWrap: "wrap" }}>
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            data-testid={`tab-${tab.id}`}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "7px 14px", borderRadius: 9, border: "none",
              background: activeTab === tab.id ? "var(--surface)" : "transparent",
              color: activeTab === tab.id ? "var(--text-primary)" : "var(--text-secondary)",
              fontWeight: activeTab === tab.id ? 600 : 400, fontSize: 13,
              cursor: "pointer", transition: "all 0.15s ease",
              boxShadow: activeTab === tab.id ? "var(--shadow-sm)" : "none",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeTab === "overview" && (
        <div>
          {summary.loading && <Spinner />}
          {summary.error && <p style={{ color: "var(--danger-text)" }}>Could not load summary.</p>}
          {summary.data && <SummaryCards summary={summary.data} />}
          <Card style={{ background: "var(--info-bg)" }}>
            <h3 style={{ margin: "0 0 12px", fontWeight: 600 }}>DPDP Act 2023 — Your Obligations</h3>
            <ul style={{ margin: 0, paddingLeft: 20, display: "flex", flexDirection: "column", gap: 8, fontSize: 13, color: "var(--text-secondary)" }}>
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
          <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
            <Select value={reqTypeFilter} onChange={e => setReqTypeFilter(e.target.value)}
              placeholder="All Types"
              options={TENANT_ALLOWED_TYPES.map(t => ({ value: t, label: REQUEST_TYPE_LABELS[t] ?? t }))}
              style={{ minWidth: 200 }} />
            <Select value={reqStatusFilter} onChange={e => setReqStatusFilter(e.target.value)}
              placeholder="All Statuses"
              options={["submitted","under_review","approved","processing","completed","rejected","cancelled"]
                .map(s => ({ value: s, label: s.replace(/_/g, " ") }))}
              style={{ minWidth: 200 }} />
          </div>
          <Card padding="none">
            {myRequests.loading && <Spinner />}
            {myRequests.error && <p style={{ color: "var(--danger-text)", padding: 16 }}>Could not load requests.</p>}
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
        <Card padding="none">
          {staffRequests.loading && <Spinner />}
          {staffRequests.error && <p style={{ color: "var(--danger-text)", padding: 16 }}>Could not load staff requests.</p>}
          {!staffRequests.loading && (
            <RequestTable
              requests={staffRequests.data?.requests ?? []}
              emptyMsg="No staff compliance requests found for your organization."
            />
          )}
          <p style={{ margin: 0, padding: 16, fontSize: 11, color: "var(--text-tertiary)" }}>
            Staff members' compliance requests (e.g. data access, erasure) that are associated with your business are shown here.
          </p>
        </Card>
      )}

      {/* Customer Requests */}
      {activeTab === "customer-requests" && (
        <Card padding="none">
          {customerRequests.loading && <Spinner />}
          {customerRequests.error && <p style={{ color: "var(--danger-text)", padding: 16 }}>Could not load customer requests.</p>}
          {!customerRequests.loading && (
            <RequestTable
              requests={customerRequests.data?.requests ?? []}
              emptyMsg="No customer compliance requests are currently linked to your business."
            />
          )}
          <p style={{ margin: 0, padding: 16, fontSize: 11, color: "var(--text-tertiary)" }}>
            Only limited status information is shown. Customer names and personal data are not disclosed.
            Requests are linked when a customer's booking is associated with your business.
          </p>
        </Card>
      )}

      {/* Consents */}
      {activeTab === "consents" && (
        <Card padding="none">
          {consents.loading && <Spinner />}
          {consents.error && <p style={{ color: "var(--danger-text)", padding: 16 }}>Could not load consent records.</p>}
          {!consents.loading && consents.data && (
            <div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border)" }}>
                      {["Consent Type", "Action", "Legal Basis", "Date", ""].map(h => (
                        <th key={h} style={{ textAlign: "left", padding: "8px 12px", fontWeight: 600 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(consents.data.records ?? []).map(rec => (
                      <tr key={rec.record_id} style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: "8px 12px" }}>{rec.consent_type.replace(/_/g, " ")}</td>
                        <td style={{ padding: "8px 12px" }}>
                          <Badge variant={rec.action === "granted" ? "success" : rec.action === "revoked" ? "danger" : "muted"}>
                            {rec.action}
                          </Badge>
                        </td>
                        <td style={{ padding: "8px 12px", color: "var(--text-tertiary)" }}>
                          {rec.legal_basis ?? "—"}
                        </td>
                        <td style={{ padding: "8px 12px" }}>
                          {new Date(rec.created_at).toLocaleDateString()}
                        </td>
                        <td style={{ padding: "8px 12px" }}>
                          {rec.action === "granted" && (
                            <Button size="sm" variant="ghost"
                              onClick={() => setWithdrawType(rec.consent_type)}>
                              Withdraw
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {!consents.data.records?.length && (
                <p style={{ textAlign: "center", padding: 24, color: "var(--text-tertiary)" }}>
                  No consent records found.
                </p>
              )}
            </div>
          )}
        </Card>
      )}

      {/* Exports */}
      {activeTab === "exports" && (
        <Card padding="none">
          {exports.loading && <Spinner />}
          {exports.error && <p style={{ color: "var(--danger-text)", padding: 16 }}>Could not load exports.</p>}
          {!exports.loading && exports.data && (
            <div>
              {exports.data.exports.length === 0 ? (
                <p style={{ textAlign: "center", padding: 24, color: "var(--text-tertiary)" }}>
                  No data exports yet. Submit a data export request from My Requests tab.
                </p>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--border)" }}>
                        {["Export ID", "Status", "Generated", "Expires", "Downloaded", "Action"].map(h => (
                          <th key={h} style={{ textAlign: "left", padding: "8px 12px", fontWeight: 600 }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {exports.data.exports.map(exp => (
                        <tr key={exp.id} style={{ borderBottom: "1px solid var(--border)" }}>
                          <td style={{ padding: "8px 12px", fontFamily: "monospace", fontSize: 11 }}>
                            {exp.id.slice(0, 8)}...
                          </td>
                          <td style={{ padding: "8px 12px" }}>
                            <Badge variant={
                              exp.status === "ready" ? "success" :
                              exp.status === "processing" ? "info" :
                              exp.status === "downloaded" ? "muted" :
                              exp.status === "expired" ? "danger" : "default"
                            }>{exp.status}</Badge>
                          </td>
                          <td style={{ padding: "8px 12px" }}>
                            {exp.generated_at ? new Date(exp.generated_at).toLocaleDateString() : "—"}
                          </td>
                          <td style={{ padding: "8px 12px" }}>
                            {exp.expires_at ? new Date(exp.expires_at).toLocaleDateString() : "—"}
                          </td>
                          <td style={{ padding: "8px 12px" }}>
                            {exp.downloaded_at ? new Date(exp.downloaded_at).toLocaleDateString() : "—"}
                          </td>
                          <td style={{ padding: "8px 12px" }}>
                            {exp.status === "ready" && (
                              <Button size="sm" variant="primary"
                                onClick={() => providerComplianceApi.downloadExport(exp.id)
                                  .then(r => { if (r?.download_url) window.open(r.download_url, "_blank"); exports.refetch(); })
                                  .catch(() => setToast("Download failed."))
                                }>
                                Download
                              </Button>
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
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
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
              <h3 style={{ margin: "0 0 8px", fontWeight: 600, fontSize: 14 }}>{title}</h3>
              <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>{body}</p>
            </Card>
          ))}
        </div>
      )}

      {/* Create Request Modal */}
      <Modal
        open={showCreate}
        title="New Compliance Request"
        onClose={() => setShowCreate(false)}
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => setShowCreate(false)}>Cancel</Button>
          <Button variant="primary" size="sm" loading={createAction.loading} onClick={handleCreate}>Submit Request</Button>
        </>}
      >
        {showCreate && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <Select label="Request Type" required value={formType}
              onChange={e => { setFormType(e.target.value); setFormError(""); }}
              options={TENANT_ALLOWED_TYPES.map(t => ({ value: t, label: REQUEST_TYPE_LABELS[t] ?? t }))} />

            {ERASURE_TYPES.has(formType) && (
              <div style={{ background: "var(--warning-bg)", border: "1px solid var(--warning-border)", borderRadius:"var(--radius-md)", padding: 12, fontSize: 13 }}>
                <strong>Important:</strong> Erasure requests are reviewed by our compliance team.
                Financial records (7 years), active bookings, and open disputes cannot be erased.
                You will be notified of the outcome within 72 hours.
              </div>
            )}

            <Textarea label="Reason" required value={formReason} onChange={e => setFormReason(e.target.value)}
              placeholder="Describe your request..." rows={3} />

            <Textarea label="Additional Details (optional)" value={formDetails} onChange={e => setFormDetails(e.target.value)}
              placeholder="Any additional context..." rows={2} />

            <label style={{ display: "flex", gap: 8, alignItems: "flex-start", cursor: "pointer", fontSize: 13 }}>
              <input type="checkbox" checked={formConfirm} onChange={e => setFormConfirm(e.target.checked)} style={{ marginTop: 2 }} />
              <span>I understand this request will be processed within 72 hours and some data may be legally exempt from deletion or export.</span>
            </label>

            {formError && (
              <p style={{ color: "var(--danger-text)", fontSize: 13, margin: 0 }}>
                {formError}
              </p>
            )}
          </div>
        )}
      </Modal>

      {/* Withdraw Consent Modal */}
      <Modal
        open={withdrawType !== null}
        title="Withdraw Consent"
        onClose={() => { setWithdrawType(null); setWithdrawReason(""); }}
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => { setWithdrawType(null); setWithdrawReason(""); }}>Cancel</Button>
          <Button variant="destructive" size="sm" loading={withdrawAction.loading} onClick={handleWithdraw}>Withdraw Consent</Button>
        </>}
      >
        {withdrawType !== null && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)" }}>
              You are withdrawing consent for: <strong>{withdrawType.replace(/_/g, " ")}</strong>
            </p>
            <Textarea label="Reason (optional)" value={withdrawReason} onChange={e => setWithdrawReason(e.target.value)}
              placeholder="Optional reason for withdrawal..." rows={2} />
          </div>
        )}
      </Modal>
    </TenantLayout>
  );
}
