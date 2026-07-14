"use client";
/**
 * MODULE-L5-02 bug #36 — Admin Complaint Detail.
 *
 * The complaints list has always had a row action navigating to
 * /admin/complaints/{id} — but that page did not exist. It was a dead 404, so
 * essentially the whole admin complaint API (18 endpoints: triage, messaging,
 * resolutions, settlement, AI settlement, resolve/close) had no UI at all.
 *
 * This is also the only place the AI settlement engine — revived in bugs #37/#38
 * — can actually be driven from: start a session, watch it collect answers from
 * both sides, read the AI's recommendation/risk flags, and finalize.
 */
import React, { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import {
  Card, CardHeader, SectionHeader, Btn, Badge, Spinner, Input, Select, Modal,
} from "../../../../components/shared/ui";
import { complaintsApi } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";

type BV = "default" | "success" | "warning" | "danger" | "info" | "muted";

const STATUS_BADGE: Record<string, BV> = {
  open: "warning",
  awaiting_provider_response: "danger",
  awaiting_customer_response: "info",
  under_admin_review: "warning",
  resolution_proposed: "info",
  rework_approved: "info",
  refund_requested: "warning",
  refund_approved: "info",
  refund_recorded: "info",
  ai_settlement_started: "info",
  resolved: "success",
  settled: "success",
  closed: "muted",
  rejected: "danger",
  cancelled: "muted",
};

const SLA_BADGE: Record<string, BV> = {
  on_time: "success", at_risk: "warning", breached: "danger", escalated: "danger",
};

const PRIORITIES = [
  { value: "low", label: "Low" }, { value: "normal", label: "Normal" },
  { value: "high", label: "High" }, { value: "critical", label: "Critical" },
];

const RESOLUTION_TYPES = [
  { value: "rework", label: "Free rework" },
  { value: "refund", label: "Refund" },
  { value: "callback", label: "Callback" },
  { value: "provider_reassignment", label: "Reassign provider" },
  { value: "apology", label: "Apology" },
  { value: "no_action", label: "No action" },
];

const D = (v: unknown) => (v == null ? "" : String(v));

export default function AdminComplaintDetailPage() {
  const params = useParams();
  const id = D(params?.id);

  const [tab, setTab] = useState<"messages" | "resolutions" | "settlement" | "ai" | "timeline">("messages");
  const [reply, setReply] = useState("");
  const [priority, setPriority] = useState("");
  const [resOpen, setResOpen] = useState(false);
  const [resType, setResType] = useState("rework");
  const [resDesc, setResDesc] = useState("");
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const complaint   = useApi(useCallback(() => complaintsApi.adminGet(id), [id]), [id]);
  const messages    = useApi(useCallback(() => complaintsApi.listMessages(id), [id]), [id]);
  const resolutions = useApi(useCallback(() => complaintsApi.listResolutions(id), [id]), [id]);
  const proposals   = useApi(useCallback(() => complaintsApi.listSettlementProposals(id), [id]), [id]);
  const aiSession   = useApi(useCallback(() => complaintsApi.getAISession(id), [id]), [id]);
  const timeline    = useApi(useCallback(() => complaintsApi.getTimeline(id), [id]), [id]);

  const refresh = () => {
    complaint.refetch(); messages.refetch(); resolutions.refetch();
    proposals.refetch(); aiSession.refetch(); timeline.refetch();
  };

  // NOTE: the admin useAction takes only the action (no onSuccess option, unlike
  // the tenant portal's), so each caller refreshes explicitly after it resolves.
  const sendMessage = useAction(async (t: string) => {
    const r = await complaintsApi.addMessage(id, t); setReply(""); refresh(); return r;
  });
  const setPrio = useAction(async (p: string) => {
    const r = await complaintsApi.setPriority(id, p); refresh(); return r;
  });
  const askProvider = useAction(async () => {
    const r = await complaintsApi.requestProviderResponse(id); refresh(); return r;
  });
  const propose = useAction(async () => {
    const r = await complaintsApi.proposeResolution(id,
      { resolution_type: resType, description: resDesc });
    setResOpen(false); setResDesc(""); refresh(); return r;
  });
  const resolve  = useAction(async () => { const r = await complaintsApi.adminResolve(id); refresh(); return r; });
  const close    = useAction(async () => { const r = await complaintsApi.adminClose(id); refresh(); return r; });
  const reject   = useAction(async () => {
    const r = await complaintsApi.adminReject(id, rejectReason);
    setRejectOpen(false); setRejectReason(""); refresh(); return r;
  });
  const startAI  = useAction(async () => { const r = await complaintsApi.startAISettlement(id); refresh(); return r; });
  const finalize = useAction(async (decision: string) => {
    const r = await complaintsApi.finalizeSettlement(id, decision); refresh(); return r;
  });

  const c = (complaint.data ?? {}) as Record<string, unknown>;
  const status = D(c.status);
  const sla = D(c.sla_status);
  const ai = (aiSession.data ?? null) as Record<string, unknown> | null;
  const busy = sendMessage.loading || setPrio.loading || askProvider.loading ||
               propose.loading || resolve.loading || close.loading || reject.loading ||
               startAI.loading || finalize.loading;

  if (complaint.loading) return <AdminLayout><Spinner /></AdminLayout>;
  if (complaint.error) {
    return (
      <AdminLayout>
        <Card><p style={{ color: "var(--danger)" }}>{complaint.error}</p>
          <Link href="/admin/complaints">← Back to complaints</Link></Card>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <Link href="/admin/complaints" style={{ fontSize: 13, display: "inline-flex", gap: 4, alignItems: "center", marginBottom: 10 }}>
        <ArrowLeft size={14} /> Back to complaints
      </Link>

      <SectionHeader
        title={`${D(c.complaint_number) || "Complaint"} — ${D(c.title) || D(c.complaint_type)}`}
        subtitle={D(c.description)}
        actions={
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Btn variant="secondary" size="sm" disabled={busy} onClick={() => askProvider.execute()}>
              Request provider response
            </Btn>
            <Btn variant="secondary" size="sm" disabled={busy} onClick={() => setResOpen(true)}>
              Propose resolution
            </Btn>
            <Btn variant="secondary" size="sm" disabled={busy} onClick={() => resolve.execute()}>Resolve</Btn>
            <Btn variant="secondary" size="sm" disabled={busy} onClick={() => close.execute()}>Close</Btn>
            <Btn variant="danger" size="sm" disabled={busy} onClick={() => setRejectOpen(true)}>Reject</Btn>
          </div>
        }
      />

      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <Badge variant={STATUS_BADGE[status] ?? "default"}>{status.replace(/_/g, " ") || "—"}</Badge>
          {sla && <Badge variant={SLA_BADGE[sla] ?? "muted"}>SLA: {sla.replace(/_/g, " ")}</Badge>}
          <Badge variant="muted">{D(c.priority) || "normal"} priority</Badge>
          <Badge variant="muted">{D(c.complaint_type).replace(/_/g, " ")}</Badge>
          <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center" }}>
            <Select value={priority || D(c.priority)} onChange={v => { setPriority(v); setPrio.execute(v); }}
                    options={PRIORITIES} />
          </div>
        </div>
      </Card>

      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        {(["messages", "resolutions", "settlement", "ai", "timeline"] as const).map(t => (
          <Btn key={t} size="sm" variant={tab === t ? "primary" : "ghost"} onClick={() => setTab(t)}>
            {t === "ai" ? "AI settlement" : t[0].toUpperCase() + t.slice(1)}
          </Btn>
        ))}
      </div>

      {tab === "messages" && (
        <Card>
          <CardHeader title="Conversation" />
          {messages.loading ? <Spinner /> : (
            <div style={{ marginBottom: 14 }}>
              {(messages.data ?? []).length === 0 &&
                <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No messages.</p>}
              {(messages.data ?? []).map(m => (
                <div key={D(m.id)} style={{ padding: "10px 12px", border: "1px solid var(--border)",
                  borderRadius: 8, marginBottom: 8 }}>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>
                    {D(m.sender_type)} · {D(m.created_at).slice(0, 16).replace("T", " ")}
                  </div>
                  <div style={{ fontSize: 13 }}>{D(m.message_text)}</div>
                </div>
              ))}
            </div>
          )}
          <label style={{ fontSize: 12, fontWeight: 600 }}>Add a case message</label>
          <textarea rows={3} value={reply} onChange={e => setReply(e.target.value)}
            style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)",
                     background: "var(--surface)", color: "var(--text)" }} />
          <div style={{ marginTop: 8 }}>
            <Btn disabled={!reply.trim() || busy} onClick={() => sendMessage.execute(reply.trim())}>Send</Btn>
          </div>
        </Card>
      )}

      {tab === "resolutions" && (
        <Card>
          <CardHeader title="Resolutions"
            subtitle="An accepted rework resolution creates a rework request; the customer must accept or reject." />
          {resolutions.loading ? <Spinner /> : (
            (resolutions.data ?? []).length === 0
              ? <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No resolutions offered.</p>
              : (resolutions.data ?? []).map(r => (
                <div key={D(r.id)} style={{ padding: "10px 12px", border: "1px solid var(--border)",
                  borderRadius: 8, marginBottom: 8 }}>
                  <div style={{ display: "flex", gap: 8, marginBottom: 4 }}>
                    <Badge variant="info">{D(r.resolution_type).replace(/_/g, " ")}</Badge>
                    <Badge variant={D(r.status) === "customer_accepted" ? "success"
                                  : D(r.status) === "customer_rejected" ? "danger" : "muted"}>
                      {D(r.status).replace(/_/g, " ")}
                    </Badge>
                  </div>
                  <div style={{ fontSize: 13 }}>{D(r.description)}</div>
                </div>
              ))
          )}
        </Card>
      )}

      {tab === "settlement" && (
        <Card>
          <CardHeader title="Settlement proposals"
            subtitle="A settlement only takes effect once BOTH the customer and the provider accept it." />
          {proposals.loading ? <Spinner /> : (
            (proposals.data ?? []).length === 0
              ? <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No settlement proposals.</p>
              : (proposals.data ?? []).map(p => (
                <div key={D(p.id)} style={{ padding: "10px 12px", border: "1px solid var(--border)",
                  borderRadius: 8, marginBottom: 8 }}>
                  <div style={{ display: "flex", gap: 8, marginBottom: 4, flexWrap: "wrap" }}>
                    <Badge variant="info">{D(p.proposal_type).replace(/_/g, " ")}</Badge>
                    <Badge variant={D(p.status) === "accepted" ? "success"
                                  : D(p.status) === "rejected" ? "danger" : "muted"}>
                      {D(p.status).replace(/_/g, " ")}
                    </Badge>
                    <Badge variant={D(p.proposed_by) === "ai" ? "info" : "muted"}>
                      by {D(p.proposed_by) || "—"}
                    </Badge>
                    {p.proposal_amount != null && <Badge variant="muted">₹{D(p.proposal_amount)}</Badge>}
                  </div>
                  <div style={{ fontSize: 13, marginBottom: 4 }}>{D(p.description)}</div>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                    customer: {D(p.customer_response) || "—"} · provider: {D(p.tenant_response) || "—"}
                  </div>
                </div>
              ))
          )}
        </Card>
      )}

      {tab === "ai" && (
        <Card>
          <CardHeader
            title="AI settlement"
            subtitle="The AI asks both sides clarifying questions; once BOTH have answered it analyses the dispute and proposes a settlement."
            actions={
              <div style={{ display: "flex", gap: 8 }}>
                {!ai && <Btn size="sm" disabled={busy} onClick={() => startAI.execute()}>
                  {startAI.loading ? "Starting…" : "Start AI settlement"}
                </Btn>}
                <Btn size="sm" variant="secondary" disabled={busy}
                     onClick={() => finalize.execute("settle")}>Finalize as settled</Btn>
              </div>
            }
          />
          {aiSession.loading ? <Spinner /> : !ai ? (
            <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
              No AI settlement session yet.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Badge variant={D(ai.status) === "completed" ? "success"
                              : D(ai.status) === "failed" ? "danger" : "info"}>
                  {D(ai.status).replace(/_/g, " ")}
                </Badge>
                <Badge variant="muted">{D(ai.model_used)}</Badge>
                {ai.confidence_score != null && (
                  <Badge variant="muted">
                    confidence {Math.round(Number(ai.confidence_score) * 100)}%
                  </Badge>
                )}
              </div>

              <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                customer answered: {ai.customer_answers ? "yes" : "no"} ·
                {" "}provider answered: {ai.tenant_answers ? "yes" : "no"}
              </div>

              {ai.ai_recommendation != null && (
                <div>
                  <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase",
                              color: "var(--text-tertiary)", margin: "0 0 4px" }}>Recommendation</p>
                  <p style={{ fontSize: 13, margin: 0 }}>{D(ai.ai_recommendation)}</p>
                </div>
              )}

              {Array.isArray(ai.risk_flags) && (ai.risk_flags as unknown[]).length > 0 && (
                <div>
                  <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase",
                              color: "var(--text-tertiary)", margin: "0 0 4px" }}>Risk flags</p>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {(ai.risk_flags as unknown[]).map((f, i) => (
                      <Badge key={i} variant="warning">{D(f)}</Badge>
                    ))}
                  </div>
                </div>
              )}

              {ai.evidence_summary != null && (
                <div>
                  <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase",
                              color: "var(--text-tertiary)", margin: "0 0 4px" }}>Evidence summary</p>
                  <p style={{ fontSize: 13, margin: 0 }}>{D(ai.evidence_summary)}</p>
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      {tab === "timeline" && (
        <Card>
          <CardHeader title="Timeline" />
          {timeline.loading ? <Spinner /> : (
            (timeline.data ?? []).length === 0
              ? <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No timeline entries.</p>
              : (timeline.data ?? []).map((t, i) => (
                <div key={i} style={{ display: "flex", gap: 10, padding: "8px 0",
                  borderBottom: "1px solid var(--border)" }}>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)", minWidth: 130 }}>
                    {D(t.at).slice(0, 16).replace("T", " ")}
                  </div>
                  <div style={{ fontSize: 13 }}>
                    <strong>{D(t.event_type ?? t.type).replace(/_/g, " ")}</strong>
                    {t.reason ? ` — ${D(t.reason)}` : ""}
                  </div>
                </div>
              ))
          )}
        </Card>
      )}

      <Modal open={resOpen} onClose={() => setResOpen(false)} title="Propose a resolution">
        <Select label="Resolution type" value={resType} onChange={setResType} options={RESOLUTION_TYPES} />
        <label style={{ fontSize: 12, fontWeight: 600 }}>Description</label>
        <textarea rows={3} value={resDesc} onChange={e => setResDesc(e.target.value)} style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text)" }} />
        {propose.error && <p style={{ color: "var(--danger)", fontSize: 12 }}>{propose.error}</p>}
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <Btn disabled={!resDesc.trim() || busy} onClick={() => propose.execute()}>Propose</Btn>
          <Btn variant="ghost" onClick={() => setResOpen(false)}>Cancel</Btn>
        </div>
      </Modal>

      <Modal open={rejectOpen} onClose={() => setRejectOpen(false)} title="Reject complaint">
        <label style={{ fontSize: 12, fontWeight: 600 }}>Reason</label>
        <textarea rows={3} value={rejectReason} onChange={e => setRejectReason(e.target.value)} style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text)" }} />
        {reject.error && <p style={{ color: "var(--danger)", fontSize: 12 }}>{reject.error}</p>}
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <Btn variant="danger" disabled={!rejectReason.trim() || busy}
               onClick={() => reject.execute()}>Reject complaint</Btn>
          <Btn variant="ghost" onClick={() => setRejectOpen(false)}>Cancel</Btn>
        </div>
      </Modal>
    </AdminLayout>
  );
}
