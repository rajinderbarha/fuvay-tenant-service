"use client";
import React, { useState, useCallback } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Card, Badge, Btn, StatCard, SectionHeader, Modal, Skeleton,
} from "../../../components/shared/ui";
import {
  Shield, AlertTriangle, Clock, FileDown, CheckCircle2, XCircle,
  Users, FileText, RefreshCw, Search, Filter, ChevronDown,
  Eye, UserCheck, Database, Trash2, Download, Lock,
} from "lucide-react";
import { complianceApi } from "../../../lib/api";
import type {
  ComplianceEnterpriseRequest, ComplianceRequestItem, ConsentRecord,
  ComplianceExportRecord, ComplianceAuditEntry,
  DpdpHealth, DpdpActionQueueItem, DpdpLegalHold,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

// ── Helpers ───────────────────────────────────────────────────────────────────
const STATUS_VARIANT: Record<string, "success" | "warning" | "danger" | "muted" | "info"> = {
  submitted: "info", under_review: "warning", approved: "success",
  partially_approved: "warning", rejected: "danger", processing: "info",
  completed: "success", failed: "danger", cancelled: "muted",
  sla_breached: "danger", identity_verification_pending: "warning",
  draft: "muted",
};
const SLA_VARIANT: Record<string, "success" | "warning" | "danger" | "muted"> = {
  on_track: "success", at_risk: "warning", breached: "danger",
  completed: "muted", not_applicable: "muted",
};
const REQUEST_TYPE_LABEL: Record<string, string> = {
  right_to_erasure: "Right to Erasure",
  data_export: "Data Export",
  consent_withdrawal: "Consent Withdrawal",
  consent_update: "Consent Update",
  data_correction: "Data Correction",
  processing_objection: "Processing Objection",
  grievance: "Grievance",
};
const ACTION_VARIANT: Record<string, string> = {
  delete: "var(--danger-text)", anonymize: "var(--warning-text)",
  retain: "var(--success-text)", export: "var(--info-text)",
  manual_review: "var(--text-secondary)",
};

type Tab = "action_queue" | "requests" | "consent" | "exports" | "retention" | "legal_holds" | "audit";

const HEALTH_BAND_VARIANT: Record<string, "success" | "warning" | "danger"> = {
  compliant: "success", attention_needed: "warning", at_risk: "warning", non_compliant: "danger",
};
const PRIORITY_VARIANT: Record<string, "danger" | "warning" | "info" | "muted"> = {
  critical: "danger", high: "warning", medium: "info", low: "muted",
};

// ── Request detail drawer ──────────────────────────────────────────────────────
function RequestDetailDrawer({
  request, onClose, onApprove, onReject, onScan, onProcess, onVerify,
  onEscalate, onGenerateEvidence,
}: {
  request: ComplianceEnterpriseRequest;
  onClose: () => void;
  onApprove: (id: string, notes: string) => Promise<void>;
  onReject:  (id: string, reason: string) => Promise<void>;
  onScan:    (id: string) => Promise<void>;
  onProcess: (id: string) => Promise<void>;
  onVerify:  (id: string) => Promise<void>;
  onEscalate: (id: string, reason: string) => Promise<void>;
  onGenerateEvidence: (id: string) => Promise<void>;
}) {
  const [approveNotes, setApproveNotes]   = useState("");
  const [rejectReason, setRejectReason]   = useState("");
  const [showReject,   setShowReject]     = useState(false);
  const [loading,      setLoading]        = useState<string | null>(null);

  async function handle(type: string, fn: () => Promise<void>) {
    setLoading(type);
    try { await fn(); } finally { setLoading(null); }
  }

  const items     = request.items ?? [];
  const retained  = items.filter(i => i.planned_action === "retain");
  const deletable = items.filter(i => i.planned_action !== "retain");

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 200,
      display: "flex", justifyContent: "flex-end",
    }} onClick={onClose}>
      <div style={{
        width: "min(680px,95vw)", background: "var(--surface)", overflowY: "auto",
        boxShadow: "-4px 0 32px rgba(0,0,0,0.25)", display: "flex", flexDirection: "column",
      }} onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border)",
          display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 2px",
              fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>
              DPDP Request
            </p>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
              {request.request_number}
            </h2>
          </div>
          <Btn variant="ghost" size="sm" onClick={onClose}>✕</Btn>
        </div>

        <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Status row */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Badge variant={STATUS_VARIANT[request.status] ?? "muted"}>
              {request.status.replace(/_/g, " ").toUpperCase()}
            </Badge>
            <Badge variant={SLA_VARIANT[request.sla_status] ?? "muted"}>
              SLA: {request.sla_status.replace(/_/g, " ")}
            </Badge>
            <Badge variant="muted">
              {REQUEST_TYPE_LABEL[request.request_type] ?? request.request_type}
            </Badge>
            {request.sla_overdue && (
              <Badge variant="danger">⚠ SLA OVERDUE</Badge>
            )}
          </div>

          {/* Subject info */}
          <div style={{ padding: "14px 16px", borderRadius: 10,
            background: "var(--surface-raised)", border: "1px solid var(--border)" }}>
            <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
              margin: "0 0 10px", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              Data Subject
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {[
                ["Subject ID", request.subject_id.slice(0, 16) + "…"],
                ["Type", request.subject_type],
                ["Email", request.subject_email ?? "—"],
                ["Name", request.subject_name ?? "—"],
                ["Source", request.request_source],
                ["Verification", request.verification_status.replace(/_/g, " ")],
              ].map(([label, val]) => (
                <div key={label}>
                  <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "0 0 2px",
                    textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</p>
                  <p style={{ fontSize: 12, color: "var(--text-primary)", margin: 0, fontWeight: 500 }}>
                    {val}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* SLA info */}
          {request.due_at && (
            <div style={{ padding: "10px 14px", borderRadius: 9,
              background: request.sla_overdue ? "var(--danger-bg)" : "var(--info-bg)",
              border: `1px solid ${request.sla_overdue ? "var(--danger-border)" : "var(--info-border)"}` }}>
              <p style={{ fontSize: 12, margin: 0,
                color: request.sla_overdue ? "var(--danger-text)" : "var(--info-text)" }}>
                <strong>SLA Due:</strong> {new Date(request.due_at).toLocaleString("en-IN")}
                {request.hours_until_sla != null && (
                  <span> · {Math.abs(request.hours_until_sla).toFixed(1)}h{" "}
                    {request.sla_overdue ? "overdue ⚠" : "remaining"}</span>
                )}
              </p>
            </div>
          )}

          {/* Reason */}
          {request.reason && (
            <div>
              <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                margin: "0 0 6px", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Reason
              </p>
              <p style={{ fontSize: 13, color: "var(--text-primary)", margin: 0,
                lineHeight: 1.5 }}>{request.reason}</p>
            </div>
          )}

          {/* Quick actions */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {request.verification_status === "pending" && (
              <Btn size="sm" variant="primary" loading={loading === "verify"}
                onClick={() => handle("verify", () => onVerify(request.id))}>
                <UserCheck size={13}/> Verify Identity
              </Btn>
            )}
            {items.length === 0 && (
              <Btn size="sm" variant="secondary" loading={loading === "scan"}
                onClick={() => handle("scan", () => onScan(request.id))}>
                <Database size={13}/> Scan Data Modules
              </Btn>
            )}
            {["submitted", "under_review"].includes(request.status) && (
              <>
                <Btn size="sm" variant="success" loading={loading === "approve"}
                  onClick={() => handle("approve", () => onApprove(request.id, approveNotes))}>
                  <CheckCircle2 size={13}/> Approve
                </Btn>
                <Btn size="sm" variant="danger" onClick={() => setShowReject(true)}>
                  <XCircle size={13}/> Reject
                </Btn>
              </>
            )}
            {["approved", "partially_approved"].includes(request.status) && (
              <Btn size="sm" variant="primary" loading={loading === "process"}
                onClick={() => handle("process", () => onProcess(request.id))}>
                Process Request
              </Btn>
            )}
            {!["completed", "rejected", "cancelled"].includes(request.status) && (
              <Btn size="sm" variant="secondary" loading={loading === "escalate"}
                onClick={() => handle("escalate", () => onEscalate(request.id, "Escalated by admin from request detail."))}>
                <AlertTriangle size={13}/> Escalate
              </Btn>
            )}
            <Btn size="sm" variant="ghost" loading={loading === "evidence"}
              onClick={() => handle("evidence", () => onGenerateEvidence(request.id))}>
              <FileText size={13}/> Generate Evidence Pack
            </Btn>
          </div>

          {/* Reject form */}
          {showReject && (
            <div style={{ padding: "14px 16px", borderRadius: 10,
              background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              <p style={{ fontSize: 12, fontWeight: 600, color: "var(--danger-text)",
                margin: "0 0 8px" }}>Rejection Reason (required)</p>
              <textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)}
                rows={2} placeholder="Provide reason for rejection…"
                style={{ width: "100%", padding: "8px 10px", borderRadius: 7,
                  border: "1px solid var(--danger-border)", background: "var(--surface)",
                  color: "var(--text-primary)", fontSize: 12, resize: "vertical",
                  boxSizing: "border-box" }}/>
              <div style={{ display: "flex", gap: 8, marginTop: 8, justifyContent: "flex-end" }}>
                <Btn size="xs" variant="ghost" onClick={() => setShowReject(false)}>Cancel</Btn>
                <Btn size="xs" variant="danger" loading={loading === "reject"}
                  onClick={() => handle("reject", () => onReject(request.id, rejectReason))}>
                  Confirm Reject
                </Btn>
              </div>
            </div>
          )}

          {/* Data inventory */}
          {items.length > 0 && (
            <div>
              <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                margin: "0 0 10px", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Data Inventory Scan ({items.length} modules)
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {items.map(item => (
                  <div key={item.id} style={{ display: "flex", alignItems: "center",
                    gap: 10, padding: "8px 12px", borderRadius: 8,
                    background: item.planned_action === "retain"
                      ? "var(--warning-bg)" : "var(--surface-raised)",
                    border: `1px solid ${item.planned_action === "retain"
                      ? "var(--warning-border)" : "var(--border)"}` }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: 12, fontWeight: 600,
                        color: "var(--text-primary)", margin: 0 }}>{item.module_name}</p>
                      {item.exemption_reason && (
                        <p style={{ fontSize: 10, color: "var(--warning-text)", margin: "2px 0 0" }}>
                          ⚠ {item.exemption_reason}
                        </p>
                      )}
                    </div>
                    <span style={{ fontSize: 11, fontWeight: 600,
                      color: ACTION_VARIANT[item.planned_action] ?? "var(--text-secondary)",
                      whiteSpace: "nowrap" }}>
                      {item.planned_action.toUpperCase()}
                    </span>
                    <Badge variant={item.status === "exempted" ? "warning"
                      : item.status === "processed" ? "success" : "muted"} >
                      {item.status}
                    </Badge>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 10, display: "flex", gap: 12 }}>
                <span style={{ fontSize: 11, color: "var(--success-text)" }}>
                  ✓ {deletable.length} modules will be processed
                </span>
                <span style={{ fontSize: 11, color: "var(--warning-text)" }}>
                  ⚠ {retained.length} exempt (legal retention)
                </span>
              </div>
            </div>
          )}

          {/* Audit trail */}
          {(request.audit_trail ?? []).length > 0 && (
            <div>
              <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                margin: "0 0 10px", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Audit Trail
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: 0,
                borderLeft: "2px solid var(--border)", paddingLeft: 14 }}>
                {(request.audit_trail ?? []).map((entry, i) => (
                  <div key={entry.log_id ?? i} style={{ paddingBottom: 10, position: "relative" }}>
                    <div style={{
                      position: "absolute", left: -19, top: 3, width: 8, height: 8,
                      borderRadius: "50%", background: "var(--accent)",
                    }}/>
                    <p style={{ fontSize: 11, fontWeight: 600,
                      color: "var(--text-primary)", margin: 0 }}>
                      {entry.action.replace(/\./g, " → ")}
                    </p>
                    <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                      {entry.actor_role ?? "system"} · {new Date(entry.created_at).toLocaleString("en-IN")}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Admin notes */}
          {request.admin_notes && (
            <div style={{ padding: "12px 14px", borderRadius: 9,
              background: "var(--surface-raised)", border: "1px solid var(--border)" }}>
              <p style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)",
                margin: "0 0 4px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Admin Notes
              </p>
              <p style={{ fontSize: 12, color: "var(--text-primary)", margin: 0 }}>
                {request.admin_notes}
              </p>
            </div>
          )}
          {request.rejection_reason && (
            <div style={{ padding: "12px 14px", borderRadius: 9,
              background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              <p style={{ fontSize: 11, fontWeight: 600, color: "var(--danger-text)",
                margin: "0 0 4px", textTransform: "uppercase" }}>Rejection Reason</p>
              <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>
                {request.rejection_reason}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function CompliancePage() {
  const [activeTab,    setActiveTab]    = useState<Tab>("requests");
  const [search,       setSearch]       = useState("");
  const [typeFilter,   setTypeFilter]   = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [slaFilter,    setSlaFilter]    = useState("");
  const [detailReq,    setDetailReq]    = useState<ComplianceEnterpriseRequest | null>(null);
  const [showCreate,   setShowCreate]   = useState(false);
  const [createForm,   setCreateForm]   = useState({
    subject_type: "customer", request_type: "right_to_erasure",
    subject_id: "", subject_email: "", subject_name: "", reason: "",
  });

  // ── API calls ───────────────────────────────────────────────────────────────
  const summary = useApi(useCallback(() => complianceApi.enterpriseSummary(), []));
  const requests = useApi(useCallback(() => complianceApi.listRequests({
    request_type: typeFilter || undefined,
    status: statusFilter || undefined,
    sla_status: slaFilter || undefined,
    search: search || undefined,
    limit: 50,
  }), [typeFilter, statusFilter, slaFilter, search]));
  const consents   = useApi(useCallback(() => complianceApi.listConsents({ limit: 50 }),    []));
  const exports_   = useApi(useCallback(() => complianceApi.listExports(),                  []));
  const retention  = useApi(useCallback(() => complianceApi.listRetentionPolicies(),         []));
  const auditLogs  = useApi(useCallback(() => complianceApi.listAuditTrail({ limit: 100 }), []));
  const health     = useApi(useCallback(() => complianceApi.getHealth(),                    []));
  const actionQueue= useApi(useCallback(() => complianceApi.getActionQueue(50),              []));
  const legalHolds = useApi(useCallback(() => complianceApi.listLegalHolds(),                []));

  const s = summary.data;
  const h = health.data;

  // ── Legal hold apply form ─────────────────────────────────────────────────
  const [showHoldForm, setShowHoldForm] = useState(false);
  const [holdForm, setHoldForm] = useState({ entity_type: "customer", entity_id: "", reason: "" });
  const applyHoldAction = useAction(useCallback(
    (data: typeof holdForm) => complianceApi.applyLegalHold(data), []));
  const releaseHoldAction = useAction(useCallback(
    (holdId: string, reason: string) => complianceApi.releaseLegalHold(holdId, reason), []));

  async function handleApplyHold() {
    const result = await applyHoldAction.execute(holdForm);
    if (result) {
      setShowHoldForm(false);
      setHoldForm({ entity_type: "customer", entity_id: "", reason: "" });
      legalHolds.refetch(); health.refetch();
    }
  }
  async function handleReleaseHold(holdId: string) {
    const reason = window.prompt("Reason for releasing this legal hold (required):");
    if (!reason) return;
    const result = await releaseHoldAction.execute(holdId, reason);
    if (result) { legalHolds.refetch(); health.refetch(); }
  }

  // ── Actions ─────────────────────────────────────────────────────────────────
  const runJobsAction = useAction(useCallback(() => complianceApi.runJobs(), []));
  const escalateAction = useAction(useCallback(
    (id: string, reason: string) => complianceApi.escalateRequest(id, reason), []));
  const evidenceAction = useAction(useCallback(
    (id: string) => complianceApi.generateEvidencePack(id), []));

  const approveAction = useAction(useCallback(
    (id: string, notes: string) => complianceApi.approveRequest(id, notes), []));
  const rejectAction  = useAction(useCallback(
    (id: string, reason: string) => complianceApi.rejectRequest(id, reason), []));
  const scanAction    = useAction(useCallback(
    (id: string) => complianceApi.scanData(id), []));
  const processAction = useAction(useCallback(
    (id: string) => complianceApi.processRequest(id), []));
  const verifyAction  = useAction(useCallback(
    (id: string) => complianceApi.verifyIdentity(id), []));
  const createAction  = useAction(useCallback(
    (data: typeof createForm) => complianceApi.createRequest(data), []));

  async function handleDetailAction(type: string, id: string, ...args: string[]) {
    let result: ComplianceEnterpriseRequest | null = null;
    if (type === "approve") result = await approveAction.execute(id, args[0] ?? "");
    if (type === "reject")  result = await rejectAction.execute(id, args[0] ?? "");
    if (type === "process") result = await processAction.execute(id);
    if (type === "verify")  result = await verifyAction.execute(id);
    if (type === "scan") {
      const r = await scanAction.execute(id);
      if (r && detailReq) {
        setDetailReq({ ...detailReq, items: r.items });
      }
      return;
    }
    if (result) {
      setDetailReq(result);
      requests.refetch(); summary.refetch(); health.refetch(); actionQueue.refetch();
    }
  }

  async function handleEscalate(id: string, reason: string) {
    const result = await escalateAction.execute(id, reason);
    if (result) { setDetailReq(result); actionQueue.refetch(); requests.refetch(); }
  }
  async function handleGenerateEvidence(id: string) {
    await evidenceAction.execute(id);
  }

  async function openRequest(req: ComplianceEnterpriseRequest) {
    const detail = await complianceApi.getRequest(req.id).catch(() => req);
    setDetailReq(detail as ComplianceEnterpriseRequest);
  }

  async function handleCreate() {
    const result = await createAction.execute(createForm);
    if (result) {
      setShowCreate(false);
      setCreateForm({ subject_type: "customer", request_type: "right_to_erasure",
        subject_id: "", subject_email: "", subject_name: "", reason: "" });
      requests.refetch(); summary.refetch();
    }
  }

  const statusColor = s?.compliance_status === "COMPLIANT" ? "success"
    : s?.compliance_status === "BREACH_RISK" ? "danger" : "warning";

  return (
    <AdminLayout activeNav="compliance">
      {/* Detail Drawer */}
      {detailReq && (
        <RequestDetailDrawer
          request={detailReq}
          onClose={() => setDetailReq(null)}
          onApprove={async (id, notes) => { await handleDetailAction("approve", id, notes); }}
          onReject={async (id, reason) => { await handleDetailAction("reject", id, reason); }}
          onScan={async (id) => { await handleDetailAction("scan", id); }}
          onProcess={async (id) => { await handleDetailAction("process", id); }}
          onVerify={async (id) => { await handleDetailAction("verify", id); }}
          onEscalate={handleEscalate}
          onGenerateEvidence={handleGenerateEvidence}
        />
      )}

      {/* Header */}
      <SectionHeader
        title="DPDP Compliance Command Center"
        subtitle="Manage data rights, consent, erasure, portability, retention, exemptions, evidence, and compliance audit trails."
        actions={
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <Badge variant={statusColor as "success" | "warning" | "danger"}>
              {s?.compliance_status ?? "Loading…"}
            </Badge>
            <Btn size="sm" variant="ghost" onClick={() => {
              summary.refetch(); requests.refetch(); health.refetch(); actionQueue.refetch(); legalHolds.refetch();
            }}>
              <RefreshCw size={13}/> Refresh
            </Btn>
            <Btn size="sm" variant="secondary" loading={runJobsAction.loading}
              onClick={async () => {
                await runJobsAction.execute();
                summary.refetch(); requests.refetch(); health.refetch();
              }}>
              ⚡ Run SLA Job
            </Btn>
            <Btn size="sm" variant="primary" onClick={() => setShowCreate(true)}>
              + New Request
            </Btn>
          </div>
        }
      />

      {/* Compliance Health Panel */}
      {health.loading ? (
        <Skeleton height={90} style={{ borderRadius: 12, marginBottom: 20 }}/>
      ) : h && (
        <Card style={{ padding: "16px 20px", marginBottom: 20, display: "flex",
          alignItems: "center", gap: 24, flexWrap: "wrap" }}>
          <div>
            <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
              textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 4px" }}>
              Compliance Health
            </p>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
              <span style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)" }}>{h.score}</span>
              <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>/ 100</span>
              <Badge variant={HEALTH_BAND_VARIANT[h.band] ?? "muted"}>{h.status}</Badge>
            </div>
          </div>
          <div style={{ flex: 1, minWidth: 220 }}>
            <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
              textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 4px" }}>
              Top Risks
            </p>
            {h.top_risks.length === 0 ? (
              <p style={{ fontSize: 12, color: "var(--success-text)", margin: 0 }}>No active risks.</p>
            ) : h.top_risks.map((risk, i) => (
              <p key={i} style={{ fontSize: 12, color: "var(--text-secondary)", margin: "2px 0" }}>• {risk}</p>
            ))}
          </div>
          <div>
            <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
              textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 4px" }}>
              Recommended
            </p>
            {h.recommended_actions.map((a, i) => (
              <p key={i} style={{ fontSize: 12, color: "var(--text-secondary)", margin: "2px 0" }}>{a}</p>
            ))}
          </div>
        </Card>
      )}

      {/* Summary cards */}
      {summary.loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(140px,1fr))",
          gap: 12, marginBottom: 20 }}>
          {[...Array(10)].map((_,i) => <Skeleton key={i} height={88} style={{ borderRadius: 12 }}/>)}
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(140px,1fr))",
          gap: 12, marginBottom: 20 }}>
          <StatCard label="Pending Erasure"  value={s?.pending_erasure ?? 0}
            icon={<Trash2 size={16}/>}   alert={(s?.pending_erasure ?? 0) > 0}
            onClick={() => { setTypeFilter("right_to_erasure"); setStatusFilter("submitted"); setActiveTab("requests"); }}/>
          <StatCard label="Pending Export"   value={s?.pending_export ?? 0}
            icon={<FileDown size={16}/>}
            onClick={() => { setTypeFilter("data_export"); setActiveTab("requests"); }}/>
          <StatCard label="Consent Withdrawal" value={s?.pending_consent_withdrawal ?? 0}
            icon={<XCircle size={16}/>}
            onClick={() => { setTypeFilter("consent_withdrawal"); setActiveTab("requests"); }}/>
          <StatCard label="Pending Verify"   value={s?.pending_verification ?? 0}
            icon={<UserCheck size={16}/>} alert={(s?.pending_verification ?? 0) > 0}
            onClick={() => { setStatusFilter("identity_verification_pending"); setActiveTab("requests"); }}/>
          <StatCard label="SLA Breached"     value={s?.sla_breached ?? 0}
            trend="down" icon={<AlertTriangle size={16}/>} alert={(s?.sla_breached ?? 0) > 0}
            onClick={() => { setSlaFilter("breached"); setActiveTab("requests"); }}/>
          <StatCard label="SLA At Risk"      value={s?.sla_at_risk ?? 0}
            icon={<Clock size={16}/>}     alert={(s?.sla_at_risk ?? 0) > 0}
            onClick={() => { setSlaFilter("at_risk"); setActiveTab("requests"); }}/>
          <StatCard label="Completed / Mo"   value={s?.completed_this_month ?? 0}
            trend="up"   icon={<CheckCircle2 size={16}/>}/>
          <StatCard label="Rejected"         value={s?.rejected_total ?? 0}
            icon={<XCircle size={16}/>}/>
          <StatCard label="Exemptions"       value={s?.exemptions_applied ?? 0}
            icon={<Shield size={16}/>}/>
          <StatCard label="Consent Records"  value={(s?.consent_records ?? 0).toLocaleString()}
            icon={<Lock size={16}/>}       onClick={() => setActiveTab("consent")}/>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: "flex", gap: 2, marginBottom: 16,
        borderBottom: "1px solid var(--border)" }}>
        {(["action_queue", "requests", "consent", "exports", "retention", "legal_holds", "audit"] as Tab[]).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)} style={{
            padding: "8px 16px", fontSize: 13, fontWeight: activeTab === tab ? 600 : 400,
            color: activeTab === tab ? "var(--text-primary)" : "var(--text-tertiary)",
            background: "transparent", border: "none", cursor: "pointer",
            borderBottom: activeTab === tab ? "2px solid var(--accent)" : "2px solid transparent",
            textTransform: "capitalize",
          }}>
            {tab === "action_queue" ? "Action Queue" : tab === "requests" ? "Requests" :
             tab === "legal_holds" ? "Legal Holds / Exemptions" : tab.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      {/* ── TAB: ACTION QUEUE ─────────────────────────────────────────────── */}
      {activeTab === "action_queue" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {actionQueue.loading ? (
            <Skeleton height={200} style={{ borderRadius: 12 }}/>
          ) : (actionQueue.data?.items.length ?? 0) === 0 ? (
            <Card style={{ padding: "40px 20px", textAlign: "center" }}>
              <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>
                No compliance actions pending.
              </p>
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
                All DPDP requests are currently within SLA and no admin action is required.
              </p>
            </Card>
          ) : (
            <Card style={{ padding: 0, overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "var(--surface-sunken)" }}>
                    {["Priority", "Request", "Type", "SLA", "Status", "Next Action", "Actions"].map(hh => (
                      <th key={hh} style={{ padding: "8px 16px", textAlign: "left", fontSize: 11,
                        fontWeight: 700, color: "var(--text-tertiary)" }}>{hh}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(actionQueue.data?.items ?? []).map((it: DpdpActionQueueItem, i, arr) => (
                    <tr key={it.id} style={{ borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                      <td style={{ padding: "10px 16px" }}>
                        <Badge variant={PRIORITY_VARIANT[it.priority] ?? "muted"}>{it.priority}</Badge>
                      </td>
                      <td style={{ padding: "10px 16px", fontFamily: "monospace", fontSize: 12 }}>{it.request_number}</td>
                      <td style={{ padding: "10px 16px", fontSize: 12 }}>{REQUEST_TYPE_LABEL[it.request_type] ?? it.request_type}</td>
                      <td style={{ padding: "10px 16px" }}>
                        <Badge variant={SLA_VARIANT[it.sla_status] ?? "muted"}>{it.sla_status.replace(/_/g," ")}</Badge>
                      </td>
                      <td style={{ padding: "10px 16px" }}>
                        <Badge variant={STATUS_VARIANT[it.status] ?? "muted"}>{it.status.replace(/_/g," ")}</Badge>
                      </td>
                      <td style={{ padding: "10px 16px", fontSize: 12 }}>{it.next_action}</td>
                      <td style={{ padding: "10px 16px" }}>
                        <Btn size="xs" variant="secondary" onClick={() => openRequest(it)}>Open</Btn>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
        </div>
      )}

      {/* ── TAB: LEGAL HOLDS / EXEMPTIONS ─────────────────────────────────── */}
      {activeTab === "legal_holds" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <Btn size="sm" variant="primary" onClick={() => setShowHoldForm(true)}>
              <Lock size={13}/> Apply Legal Hold
            </Btn>
          </div>
          {showHoldForm && (
            <Card style={{ padding: 16 }}>
              <p style={{ fontSize: 13, fontWeight: 600, margin: "0 0 10px" }}>New Legal Hold</p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
                <select value={holdForm.entity_type}
                  onChange={e => setHoldForm({ ...holdForm, entity_type: e.target.value })}
                  style={{ padding: "8px 10px", borderRadius: 7, border: "1px solid var(--border)",
                    background: "var(--surface)", color: "var(--text-primary)", fontSize: 12 }}>
                  <option value="customer">Customer</option>
                  <option value="tenant">Tenant</option>
                  <option value="tenant_staff">Tenant Staff</option>
                </select>
                <input placeholder="Entity ID (UUID)" value={holdForm.entity_id}
                  onChange={e => setHoldForm({ ...holdForm, entity_id: e.target.value })}
                  style={{ padding: "8px 10px", borderRadius: 7, border: "1px solid var(--border)",
                    background: "var(--surface)", color: "var(--text-primary)", fontSize: 12 }}/>
              </div>
              <textarea placeholder="Reason (required)" rows={2} value={holdForm.reason}
                onChange={e => setHoldForm({ ...holdForm, reason: e.target.value })}
                style={{ width: "100%", padding: "8px 10px", borderRadius: 7,
                  border: "1px solid var(--border)", background: "var(--surface)",
                  color: "var(--text-primary)", fontSize: 12, resize: "vertical", boxSizing: "border-box" }}/>
              <div style={{ display: "flex", gap: 8, marginTop: 10, justifyContent: "flex-end" }}>
                <Btn size="xs" variant="ghost" onClick={() => setShowHoldForm(false)}>Cancel</Btn>
                <Btn size="xs" variant="primary" loading={applyHoldAction.loading}
                  disabled={!holdForm.entity_id || !holdForm.reason}
                  onClick={handleApplyHold}>
                  Apply Hold
                </Btn>
              </div>
            </Card>
          )}
          {legalHolds.loading ? (
            <Skeleton height={200} style={{ borderRadius: 12 }}/>
          ) : (legalHolds.data?.items.length ?? 0) === 0 ? (
            <Card style={{ padding: "40px 20px", textAlign: "center" }}>
              <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
                No legal holds on record.
              </p>
            </Card>
          ) : (
            <Card style={{ padding: 0, overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "var(--surface-sunken)" }}>
                    {["Hold", "Entity", "Reason", "Status", "Applied", "Actions"].map(hh => (
                      <th key={hh} style={{ padding: "8px 16px", textAlign: "left", fontSize: 11,
                        fontWeight: 700, color: "var(--text-tertiary)" }}>{hh}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(legalHolds.data?.items ?? []).map((hold: DpdpLegalHold, i, arr) => (
                    <tr key={hold.id} style={{ borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                      <td style={{ padding: "10px 16px", fontFamily: "monospace", fontSize: 12 }}>{hold.hold_code}</td>
                      <td style={{ padding: "10px 16px", fontSize: 12 }}>{hold.entity_type} · {hold.entity_id.slice(0, 8)}…</td>
                      <td style={{ padding: "10px 16px", fontSize: 12, maxWidth: 260 }}>{hold.reason}</td>
                      <td style={{ padding: "10px 16px" }}>
                        <Badge variant={hold.status === "active" ? "warning" : "muted"}>{hold.status}</Badge>
                      </td>
                      <td style={{ padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)" }}>
                        {new Date(hold.applied_at).toLocaleDateString("en-IN")}
                      </td>
                      <td style={{ padding: "10px 16px" }}>
                        {hold.status === "active" && (
                          <Btn size="xs" variant="danger" loading={releaseHoldAction.loading}
                            onClick={() => handleReleaseHold(hold.id)}>
                            Release
                          </Btn>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
        </div>
      )}

      {/* ── TAB: REQUESTS ─────────────────────────────────────────────────── */}
      {activeTab === "requests" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* Filters toolbar */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <div style={{ position: "relative", flex: 1, minWidth: 220 }}>
              <Search size={13} style={{ position: "absolute", left: 10, top: "50%",
                transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
              <input value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Search request # / email / name…"
                style={{ width: "100%", padding: "8px 10px 8px 30px", borderRadius: 8,
                  border: "1px solid var(--border)", background: "var(--surface-raised)",
                  color: "var(--text-primary)", fontSize: 12, boxSizing: "border-box" }}/>
            </div>
            <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
              style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)",
                background: "var(--surface-raised)", color: "var(--text-primary)", fontSize: 12 }}>
              <option value="">All Types</option>
              {Object.entries(REQUEST_TYPE_LABEL).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
              style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)",
                background: "var(--surface-raised)", color: "var(--text-primary)", fontSize: 12 }}>
              <option value="">All Statuses</option>
              {["submitted","under_review","approved","partially_approved","rejected",
                "processing","completed","failed","sla_breached","cancelled"].map(s => (
                <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
              ))}
            </select>
            <select value={slaFilter} onChange={e => setSlaFilter(e.target.value)}
              style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)",
                background: "var(--surface-raised)", color: "var(--text-primary)", fontSize: 12 }}>
              <option value="">All SLA</option>
              <option value="breached">Breached</option>
              <option value="at_risk">At Risk</option>
              <option value="on_track">On Track</option>
            </select>
            {(typeFilter || statusFilter || slaFilter || search) && (
              <Btn size="sm" variant="ghost" onClick={() => {
                setTypeFilter(""); setStatusFilter(""); setSlaFilter(""); setSearch("");
              }}>Clear</Btn>
            )}
            <Btn size="sm" variant="ghost" onClick={() => requests.refetch()}>
              <RefreshCw size={13}/>
            </Btn>
          </div>

          {/* Active filter chips */}
          {(typeFilter || statusFilter || slaFilter) && (
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {typeFilter && <Badge variant="info">{REQUEST_TYPE_LABEL[typeFilter] ?? typeFilter} ×</Badge>}
              {statusFilter && <Badge variant="muted">{statusFilter.replace(/_/g, " ")} ×</Badge>}
              {slaFilter && <Badge variant={slaFilter === "breached" ? "danger" : "warning"}>
                SLA: {slaFilter} ×</Badge>}
            </div>
          )}

          {/* Request table */}
          <Card padding={0}>
            {requests.loading ? (
              <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 8 }}>
                {[...Array(5)].map((_,i) => <Skeleton key={i} height={60}/>)}
              </div>
            ) : (requests.data?.items ?? []).length === 0 ? (
              <p style={{ padding: "32px", textAlign: "center",
                color: "var(--text-tertiary)", fontSize: 13 }}>
                No compliance requests match these filters.
              </p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border)" }}>
                      {["Request #","Subject","Type","Status","SLA","Verification","Due",""].map(h => (
                        <th key={h} style={{ padding: "10px 14px", textAlign: "left",
                          fontSize: 10, fontWeight: 700, color: "var(--text-tertiary)",
                          textTransform: "uppercase", letterSpacing: "0.06em",
                          whiteSpace: "nowrap" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(requests.data?.items ?? []).map(req => (
                      <tr key={req.id} style={{ borderBottom: "1px solid var(--border)",
                        background: req.sla_overdue ? "var(--danger-bg)"
                          : req.sla_status === "at_risk" ? "var(--warning-bg)" : "transparent" }}>
                        <td style={{ padding: "10px 14px", fontWeight: 600,
                          color: "var(--text-primary)" }}>
                          <button onClick={() => openRequest(req)}
                            style={{ background: "none", border: "none", cursor: "pointer",
                              color: "var(--accent)", fontWeight: 700, fontSize: 12,
                              padding: 0, textDecoration: "underline" }}>
                            {req.request_number}
                          </button>
                        </td>
                        <td style={{ padding: "10px 14px" }}>
                          <p style={{ margin: 0, fontWeight: 500 }}>
                            {req.subject_name ?? req.subject_id.slice(0,12) + "…"}
                          </p>
                          <p style={{ margin: "2px 0 0", fontSize: 10,
                            color: "var(--text-tertiary)" }}>
                            {req.subject_type} · {req.subject_email ?? "—"}
                          </p>
                        </td>
                        <td style={{ padding: "10px 14px", whiteSpace: "nowrap" }}>
                          {REQUEST_TYPE_LABEL[req.request_type] ?? req.request_type}
                        </td>
                        <td style={{ padding: "10px 14px" }}>
                          <Badge variant={STATUS_VARIANT[req.status] ?? "muted"}>
                            {req.status.replace(/_/g, " ")}
                          </Badge>
                        </td>
                        <td style={{ padding: "10px 14px" }}>
                          <Badge variant={SLA_VARIANT[req.sla_status] ?? "muted"}>
                            {req.sla_status.replace(/_/g, " ")}
                          </Badge>
                          {req.hours_until_sla != null && (
                            <p style={{ fontSize: 10, margin: "2px 0 0",
                              color: req.sla_overdue ? "var(--danger-text)" : "var(--text-tertiary)" }}>
                              {Math.abs(req.hours_until_sla).toFixed(1)}h{" "}
                              {req.sla_overdue ? "overdue" : "left"}
                            </p>
                          )}
                        </td>
                        <td style={{ padding: "10px 14px" }}>
                          <Badge variant={
                            req.verification_status === "verified" ? "success"
                            : req.verification_status === "pending" ? "warning"
                            : req.verification_status === "failed" ? "danger" : "muted"
                          }>
                            {req.verification_status.replace(/_/g, " ")}
                          </Badge>
                        </td>
                        <td style={{ padding: "10px 14px", color: "var(--text-secondary)",
                          whiteSpace: "nowrap", fontSize: 11 }}>
                          {req.due_at ? new Date(req.due_at).toLocaleDateString("en-IN") : "—"}
                        </td>
                        <td style={{ padding: "10px 14px" }}>
                          <Btn size="xs" variant="ghost" onClick={() => openRequest(req)}>
                            <Eye size={12}/> View
                          </Btn>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {(requests.data?.meta?.total ?? 0) > 0 && (
              <div style={{ padding: "10px 14px", borderTop: "1px solid var(--border)",
                fontSize: 11, color: "var(--text-tertiary)" }}>
                {requests.data?.meta?.total} total requests
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ── TAB: CONSENT ─────────────────────────────────────────────────── */}
      {activeTab === "consent" && (
        <Card padding={0}>
          <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--border)",
            display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>
              Consent Records — Immutable Ledger
            </h3>
            <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
              {consents.data?.meta?.total ?? 0} total records
            </span>
          </div>
          {consents.loading ? (
            <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 8 }}>
              {[...Array(5)].map((_,i) => <Skeleton key={i} height={48}/>)}
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    {["Subject (User ID)","Consent Type","Action","Version","Granted At",
                      "Expires At","Source"].map(h => (
                      <th key={h} style={{ padding: "10px 14px", textAlign: "left",
                        fontSize: 10, fontWeight: 700, color: "var(--text-tertiary)",
                        textTransform: "uppercase", letterSpacing: "0.06em" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(consents.data?.items ?? []).map((c: ConsentRecord) => (
                    <tr key={c.id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 14px", fontFamily: "monospace",
                        fontSize: 11, color: "var(--text-secondary)" }}>
                        {c.user_id.slice(0, 14)}…
                      </td>
                      <td style={{ padding: "10px 14px" }}>{c.consent_type.replace(/_/g, " ")}</td>
                      <td style={{ padding: "10px 14px" }}>
                        <Badge variant={c.action === "granted" ? "success"
                          : c.action === "withdrawn" ? "danger" : "muted"}>
                          {c.action}
                        </Badge>
                      </td>
                      <td style={{ padding: "10px 14px", color: "var(--text-tertiary)" }}>
                        v{c.policy_version}
                      </td>
                      <td style={{ padding: "10px 14px", fontSize: 11,
                        color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>
                        {c.granted_at ? new Date(c.granted_at).toLocaleDateString("en-IN") : "—"}
                      </td>
                      <td style={{ padding: "10px 14px", fontSize: 11,
                        color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>
                        {c.expires_at ? new Date(c.expires_at).toLocaleDateString("en-IN") : "—"}
                      </td>
                      <td style={{ padding: "10px 14px", color: "var(--text-tertiary)" }}>
                        {c.source ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(consents.data?.items ?? []).length === 0 && (
                <p style={{ padding: "32px", textAlign: "center",
                  color: "var(--text-tertiary)", fontSize: 13 }}>No consent records.</p>
              )}
            </div>
          )}
        </Card>
      )}

      {/* ── TAB: EXPORTS ─────────────────────────────────────────────────── */}
      {activeTab === "exports" && (
        <Card padding={0}>
          <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--border)",
            display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>Data Exports</h3>
            <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
              {exports_.data?.meta?.total ?? 0} total exports
            </span>
          </div>
          {exports_.loading ? (
            <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 8 }}>
              {[...Array(3)].map((_,i) => <Skeleton key={i} height={56}/>)}
            </div>
          ) : (exports_.data?.items ?? []).length === 0 ? (
            <p style={{ padding: "32px", textAlign: "center",
              color: "var(--text-tertiary)", fontSize: 13 }}>No exports yet.</p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    {["Export ID","Subject","Format","Status","Records","Size",
                      "Generated","Expires","Actions"].map(h => (
                      <th key={h} style={{ padding: "10px 14px", textAlign: "left",
                        fontSize: 10, fontWeight: 700, color: "var(--text-tertiary)",
                        textTransform: "uppercase", letterSpacing: "0.06em" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(exports_.data?.items ?? []).map((exp: ComplianceExportRecord) => (
                    <tr key={exp.id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 14px", fontFamily: "monospace",
                        fontSize: 10, color: "var(--text-secondary)" }}>
                        {exp.id.slice(0, 12)}…
                      </td>
                      <td style={{ padding: "10px 14px", fontSize: 11 }}>
                        <p style={{ margin: 0 }}>{exp.subject_type}</p>
                        <p style={{ margin: 0, color: "var(--text-tertiary)", fontSize: 10 }}>
                          {exp.subject_id.slice(0, 12)}…
                        </p>
                      </td>
                      <td style={{ padding: "10px 14px" }}>{exp.export_format.toUpperCase()}</td>
                      <td style={{ padding: "10px 14px" }}>
                        <Badge variant={exp.status === "ready" ? "success"
                          : exp.status === "expired" ? "muted"
                          : exp.status === "failed" ? "danger" : "warning"}>
                          {exp.status}
                        </Badge>
                      </td>
                      <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>
                        {exp.record_count ?? "—"}
                      </td>
                      <td style={{ padding: "10px 14px", color: "var(--text-tertiary)",
                        fontSize: 11 }}>
                        {exp.file_size_bytes ? `${(exp.file_size_bytes/1024).toFixed(1)} KB` : "—"}
                      </td>
                      <td style={{ padding: "10px 14px", fontSize: 11,
                        color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>
                        {exp.generated_at ? new Date(exp.generated_at).toLocaleDateString("en-IN") : "—"}
                      </td>
                      <td style={{ padding: "10px 14px", fontSize: 11,
                        color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>
                        {exp.expires_at ? new Date(exp.expires_at).toLocaleDateString("en-IN") : "—"}
                      </td>
                      <td style={{ padding: "10px 14px", display: "flex", gap: 6 }}>
                        {exp.status === "ready" && exp.download_url && (
                          <Btn size="xs" variant="ghost">
                            <Download size={11}/> DL
                          </Btn>
                        )}
                        {exp.status === "ready" && (
                          <Btn size="xs" variant="ghost"
                            onClick={() => complianceApi.expireExport(exp.id).then(() => exports_.refetch())}>
                            Expire
                          </Btn>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* ── TAB: RETENTION ────────────────────────────────────────────────── */}
      {activeTab === "retention" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ padding: "12px 16px", borderRadius: 10,
            background: "var(--info-bg)", border: "1px solid var(--info-border)" }}>
            <p style={{ fontSize: 12, color: "var(--info-text)", margin: 0 }}>
              ℹ Financial records (payments, invoices, commissions, wallet ledger) are exempt from
              erasure under GST Act — 7 year statutory retention required. Each exemption is
              stored per-row in the compliance request.
            </p>
          </div>

          {retention.loading ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(240px,1fr))",
              gap: 10 }}>
              {[...Array(6)].map((_,i) => <Skeleton key={i} height={80}/>)}
            </div>
          ) : (
            <>
              {/* Exempt tables */}
              <Card padding={16}>
                <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 12px",
                  color: "var(--text-primary)" }}>Statutory Exemptions</h3>
                <div style={{ display: "grid",
                  gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 8 }}>
                  {Object.entries(retention.data?.exempt_tables ?? {}).map(([table, reason]) => (
                    <div key={table} style={{ padding: "10px 14px", borderRadius: 9,
                      background: "var(--warning-bg)", border: "1px solid var(--warning-border)" }}>
                      <p style={{ fontSize: 12, fontWeight: 700, color: "var(--warning-text)",
                        margin: "0 0 3px" }}>{table.replace(/_/g, " ")}</p>
                      <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: 0 }}>
                        {String(reason)}
                      </p>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Policies table */}
              {(retention.data?.policies ?? []).length > 0 && (
                <Card padding={0}>
                  <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
                    <h3 style={{ fontSize: 13, fontWeight: 700, margin: 0 }}>Retention Policies</h3>
                  </div>
                  <div style={{ overflowX: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                      <thead>
                        <tr style={{ borderBottom: "1px solid var(--border)" }}>
                          {["Table","Retention Days","Exempt","Legal Basis"].map(h => (
                            <th key={h} style={{ padding: "10px 14px", textAlign: "left",
                              fontSize: 10, fontWeight: 700, color: "var(--text-tertiary)",
                              textTransform: "uppercase", letterSpacing: "0.06em" }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {retention.data?.policies?.map(p => (
                          <tr key={p.table_name}
                            style={{ borderBottom: "1px solid var(--border)" }}>
                            <td style={{ padding: "10px 14px", fontWeight: 500 }}>
                              {p.table_name}
                            </td>
                            <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>
                              {p.retention_days}d
                            </td>
                            <td style={{ padding: "10px 14px" }}>
                              {p.is_exempt
                                ? <Badge variant="warning">Exempt</Badge>
                                : <Badge variant="muted">No</Badge>}
                            </td>
                            <td style={{ padding: "10px 14px", color: "var(--text-tertiary)",
                              fontSize: 11 }}>
                              {p.exemption_reason ?? "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}
            </>
          )}
        </div>
      )}

      {/* ── TAB: AUDIT ───────────────────────────────────────────────────── */}
      {activeTab === "audit" && (
        <Card padding={0}>
          <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--border)",
            display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>Compliance Audit Trail</h3>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                Append-only. Records cannot be modified or deleted.
              </p>
            </div>
            <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
              {auditLogs.data?.meta?.total ?? 0} events
            </span>
          </div>
          {auditLogs.loading ? (
            <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 6 }}>
              {[...Array(8)].map((_,i) => <Skeleton key={i} height={44}/>)}
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 0,
              padding: "16px 20px", borderLeft: "2px solid var(--border)",
              marginLeft: 20 }}>
              {(auditLogs.data?.items ?? []).map((entry: ComplianceAuditEntry, i: number) => (
                <div key={entry.log_id ?? i}
                  style={{ paddingBottom: 14, position: "relative" }}>
                  <div style={{
                    position: "absolute", left: -25, top: 4, width: 8, height: 8,
                    borderRadius: "50%",
                    background: entry.action.includes("approved") ? "var(--success-text)"
                      : entry.action.includes("reject") ? "var(--danger-text)"
                      : entry.action.includes("breach") ? "var(--danger-text)"
                      : "var(--accent)",
                  }}/>
                  <p style={{ fontSize: 12, fontWeight: 600,
                    color: "var(--text-primary)", margin: 0 }}>
                    {entry.action.replace(/\./g, " → ")}
                  </p>
                  <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                    {entry.actor_role ?? "system"}
                    {entry.reference_id && ` · ref: ${entry.reference_id.slice(0,12)}…`}
                    {" · "}
                    {new Date(entry.created_at).toLocaleString("en-IN")}
                  </p>
                </div>
              ))}
              {(auditLogs.data?.items ?? []).length === 0 && (
                <p style={{ color: "var(--text-tertiary)", fontSize: 13 }}>
                  No audit events yet.
                </p>
              )}
            </div>
          )}
        </Card>
      )}

      {/* ── Create Request Modal ──────────────────────────────────────────── */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)}
        title="Create Compliance Request">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)",
                textTransform: "uppercase" }}>Subject Type</span>
              <select value={createForm.subject_type}
                onChange={e => setCreateForm(f => ({ ...f, subject_type: e.target.value }))}
                style={{ padding: "8px 10px", borderRadius: 8,
                  border: "1px solid var(--border)", background: "var(--surface-raised)",
                  color: "var(--text-primary)", fontSize: 12 }}>
                {["customer","provider_owner","tenant_staff","platform_admin","guest_user"]
                  .map(v => <option key={v} value={v}>{v.replace(/_/g, " ")}</option>)}
              </select>
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)",
                textTransform: "uppercase" }}>Request Type</span>
              <select value={createForm.request_type}
                onChange={e => setCreateForm(f => ({ ...f, request_type: e.target.value }))}
                style={{ padding: "8px 10px", borderRadius: 8,
                  border: "1px solid var(--border)", background: "var(--surface-raised)",
                  color: "var(--text-primary)", fontSize: 12 }}>
                {Object.entries(REQUEST_TYPE_LABEL).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </label>
          </div>
          {[
            ["Subject ID (UUID) *", "subject_id", "uuid of the data subject"],
            ["Subject Email",       "subject_email", "email@example.com"],
            ["Subject Name",        "subject_name", "Full Name"],
          ].map(([label, field, placeholder]) => (
            <label key={field} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)",
                textTransform: "uppercase" }}>{label}</span>
              <input value={(createForm as Record<string, string>)[field]}
                onChange={e => setCreateForm(f => ({ ...f, [field]: e.target.value }))}
                placeholder={placeholder}
                style={{ padding: "8px 10px", borderRadius: 8,
                  border: "1px solid var(--border)", background: "var(--surface-raised)",
                  color: "var(--text-primary)", fontSize: 12 }}/>
            </label>
          ))}
          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)",
              textTransform: "uppercase" }}>Reason</span>
            <textarea value={createForm.reason} rows={3}
              onChange={e => setCreateForm(f => ({ ...f, reason: e.target.value }))}
              placeholder="Describe the request reason…"
              style={{ padding: "8px 10px", borderRadius: 8,
                border: "1px solid var(--border)", background: "var(--surface-raised)",
                color: "var(--text-primary)", fontSize: 12, resize: "vertical" }}/>
          </label>
          {createAction.error && (
            <div style={{ padding: "10px 14px", borderRadius: 8,
              background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>
                {createAction.error}
              </p>
            </div>
          )}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setShowCreate(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={createAction.loading}
              disabled={!createForm.subject_id.trim()}
              onClick={handleCreate}>
              Create Request
            </Btn>
          </div>
        </div>
      </Modal>
    </AdminLayout>
  );
}
