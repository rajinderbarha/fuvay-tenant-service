"use client";
/**
 * MODULE-L5-02 — Provider Complaint Detail.
 *
 * The complaints list page has always had a "View & Respond" row action linking
 * to /provider/complaints/{id}, but that page did not exist — it was a dead 404.
 * So the provider-facing complaint workflow (respond, offer a resolution, and
 * the settlement-proposal exchange) had no UI at all, even though every endpoint
 * behind it exists.
 *
 * Backs: GET  /v1/provider/complaints/{id}
 *        GET  /v1/provider/complaints/{id}/messages
 *        POST /v1/provider/complaints/{id}/respond
 *        GET  /v1/provider/complaints/{id}/resolutions
 *        POST /v1/provider/complaints/{id}/offer-resolution
 *        GET  /v1/provider/complaints/{id}/settlement-proposals
 *        POST /v1/provider/complaints/{id}/settlement-proposals
 *        POST /v1/provider/complaints/{id}/settlement-proposals/{pid}/respond
 */
import React, { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { TenantLayout } from "../../../../../components/layout/TenantLayout";
import { Card, PageHeader, Button, Spinner, Modal, Select, Input, Textarea } from "@serviceos/design-system";
import { Badge } from "../../../../../components/shared/ui";
import { apiFetch } from "../../../../../lib/api";
import { useApi, useAction } from "../../../../../hooks/useApi";

type BV = "default" | "success" | "warning" | "danger" | "info" | "muted";

const STATUS_COLOR: Record<string, BV> = {
  open:                       "warning",
  awaiting_provider_response: "danger",
  awaiting_customer_response: "info",
  under_admin_review:         "warning",
  resolution_proposed:        "info",
  rework_approved:            "info",
  refund_requested:           "warning",
  refund_approved:            "info",
  refund_recorded:            "info",
  resolved:                   "success",
  settled:                    "success",
  closed:                     "muted",
  rejected:                   "danger",
  cancelled:                  "muted",
};

const SLA_COLOR: Record<string, BV> = {
  on_time:   "success",
  at_risk:   "warning",
  breached:  "danger",
  escalated: "danger",
};

const RESOLUTION_TYPES = [
  { value: "rework",                label: "Free rework visit" },
  { value: "refund",                label: "Refund" },
  { value: "callback",              label: "Callback" },
  { value: "provider_reassignment", label: "Reassign provider" },
  { value: "apology",               label: "Apology" },
  { value: "no_action",             label: "No action" },
];

const PROPOSAL_TYPES = [
  { value: "partial_refund", label: "Partial refund" },
  { value: "full_refund",    label: "Full refund" },
  { value: "free_rework",    label: "Free rework" },
  { value: "credit",         label: "Account credit" },
  { value: "no_action",      label: "No action" },
];

type Dict = Record<string, unknown>;
const s = (v: unknown) => (v == null ? "" : String(v));

export default function ProviderComplaintDetailPage() {
  const params = useParams();
  const id = String(params?.complaint_id ?? "");

  const [tab, setTab] = useState<"messages" | "resolutions" | "settlement" | "ai">("messages");
  const [reply, setReply] = useState("");
  const [aiAnswers, setAiAnswers] = useState<string[]>([]);
  const [resOpen, setResOpen] = useState(false);
  const [resType, setResType] = useState("rework");
  const [resDesc, setResDesc] = useState("");
  const [propOpen, setPropOpen] = useState(false);
  const [propType, setPropType] = useState("partial_refund");
  const [propDesc, setPropDesc] = useState("");
  const [propAmt, setPropAmt] = useState("");

  const complaint = useApi<Dict>(
    useCallback(() => apiFetch<Dict>(`/v1/provider/complaints/${id}`), [id]), [id]);
  const messages = useApi<Dict[]>(
    useCallback(() => apiFetch<Dict[]>(`/v1/provider/complaints/${id}/messages`), [id]), [id]);
  const resolutions = useApi<Dict[]>(
    useCallback(() => apiFetch<Dict[]>(`/v1/provider/complaints/${id}/resolutions`), [id]), [id]);
  const proposals = useApi<Dict[]>(
    useCallback(() => apiFetch<Dict[]>(`/v1/provider/complaints/${id}/settlement-proposals`), [id]), [id]);
  const aiSession = useApi<Dict | null>(
    useCallback(() => apiFetch<Dict | null>(`/v1/provider/complaints/${id}/ai-session`), [id]), [id]);

  const refreshAll = () => {
    complaint.refetch(); messages.refetch(); resolutions.refetch(); proposals.refetch(); aiSession.refetch();
  };

  // seed the answer boxes from the AI's tenant questions once they load
  React.useEffect(() => {
    const qs = (aiSession.data as Dict | null)?.tenant_questions as string[] | undefined;
    if (qs && aiAnswers.length === 0) setAiAnswers(qs.map(() => ""));
  }, [aiSession.data]); // eslint-disable-line react-hooks/exhaustive-deps

  const submitAiAnswers = useAction(
    async (answers: string[]) =>
      apiFetch(`/v1/provider/complaints/${id}/ai-session/answers`, {
        method: "POST", body: JSON.stringify({ answers }),
      }),
    { onSuccess: refreshAll },
  );

  const respond = useAction(
    async (text: string) =>
      apiFetch(`/v1/provider/complaints/${id}/respond`, {
        method: "POST", body: JSON.stringify({ message_text: text }),
      }),
    { onSuccess: () => { setReply(""); refreshAll(); } },
  );

  const offerResolution = useAction(
    async () =>
      apiFetch(`/v1/provider/complaints/${id}/offer-resolution`, {
        method: "POST",
        body: JSON.stringify({ resolution_type: resType, description: resDesc }),
      }),
    { onSuccess: () => { setResOpen(false); setResDesc(""); refreshAll(); } },
  );

  const createProposal = useAction(
    async () =>
      apiFetch(`/v1/provider/complaints/${id}/settlement-proposals`, {
        method: "POST",
        body: JSON.stringify({
          proposal_type: propType,
          description: propDesc,
          ...(propAmt ? { proposal_amount: Number(propAmt) } : {}),
        }),
      }),
    { onSuccess: () => { setPropOpen(false); setPropDesc(""); setPropAmt(""); refreshAll(); } },
  );

  const respondProposal = useAction(
    async (pid: string, response: string) =>
      apiFetch(`/v1/provider/complaints/${id}/settlement-proposals/${pid}/respond`, {
        method: "POST", body: JSON.stringify({ response }),
      }),
    { onSuccess: refreshAll },
  );

  const c = complaint.data ?? {};
  const status = s(c.status);
  const sla = s(c.sla_status);

  if (complaint.loading) {
    return <TenantLayout activeNav="provider"><Spinner /></TenantLayout>;
  }
  if (complaint.error) {
    return (
      <TenantLayout activeNav="provider">
        <Card><p style={{ color: "var(--danger-text)" }}>{complaint.error}</p>
          <Link href="/provider/complaints">← Back to complaints</Link>
        </Card>
      </TenantLayout>
    );
  }

  return (
    <TenantLayout activeNav="provider">
      <div style={{ marginBottom: 12 }}>
        <Link href="/provider/complaints" style={{ fontSize: 13 }}>← Back to complaints</Link>
      </div>

      <PageHeader
        title={`${s(c.complaint_number) || "Complaint"} — ${s(c.title) || s(c.complaint_type)}`}
        description={s(c.description)}
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Button variant="secondary" size="sm" onClick={() => setPropOpen(true)}>Propose settlement</Button>
            <Button variant="primary" size="sm" onClick={() => setResOpen(true)}>Offer resolution</Button>
          </div>
        }
      />

      <Card style={{ margin: "16px 0" }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <Badge variant={STATUS_COLOR[status] ?? "default"}>{status.replace(/_/g, " ") || "—"}</Badge>
          {sla && <Badge variant={SLA_COLOR[sla] ?? "muted"}>SLA: {sla.replace(/_/g, " ")}</Badge>}
          <Badge variant="muted">{s(c.priority) || "normal"} priority</Badge>
          <Badge variant="muted">{s(c.complaint_type).replace(/_/g, " ")}</Badge>
          <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
            Opened {s(c.created_at).slice(0, 10)}
            {c.resolved_at ? ` · Resolved ${s(c.resolved_at).slice(0, 10)}` : ""}
          </span>
        </div>
      </Card>

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        {(["messages", "resolutions", "settlement", "ai"] as const).map(t => (
          <Button key={t} variant={tab === t ? "primary" : "ghost"} size="sm" onClick={() => setTab(t)}>
            {t === "messages" ? "Messages" : t === "resolutions" ? "Resolutions"
              : t === "settlement" ? "Settlement" : "AI settlement"}
          </Button>
        ))}
      </div>

      {tab === "messages" && (
        <Card>
          <h3 style={{ margin: "0 0 4px", fontSize: 14, fontWeight: 600 }}>Conversation</h3>
          <p style={{ margin: "0 0 12px", fontSize: 12, color: "var(--text-tertiary)" }}>Replying marks your first response for SLA purposes.</p>
          {messages.loading ? <Spinner /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
              {(messages.data ?? []).length === 0 && (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No messages yet.</p>
              )}
              {(messages.data ?? []).map(m => (
                <div key={s(m.id)} style={{
                  padding: "10px 12px", borderRadius: 8,
                  background: s(m.sender_type) === "provider" ? "var(--surface-sunken)" : "var(--surface)",
                  border: "1px solid var(--border)",
                }}>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>
                    {s(m.sender_type)} · {s(m.created_at).slice(0, 16).replace("T", " ")}
                  </div>
                  <div style={{ fontSize: 13 }}>{s(m.message_text)}</div>
                </div>
              ))}
            </div>
          )}
          <Textarea label="Reply to customer" rows={3} value={reply} onChange={e => setReply(e.target.value)}
                 placeholder="Explain what you will do to resolve this…" />
          {respond.error && <p style={{ color: "var(--danger-text)", fontSize: 12 }}>{respond.error}</p>}
          <div style={{ marginTop: 10 }}>
            <Button disabled={!reply.trim() || respond.loading} loading={respond.loading}
                 onClick={() => respond.execute(reply.trim())}>
              Send reply
            </Button>
          </div>
        </Card>
      )}

      {tab === "resolutions" && (
        <Card>
          <h3 style={{ margin: "0 0 4px", fontSize: 14, fontWeight: 600 }}>Resolutions offered</h3>
          <p style={{ margin: "0 0 12px", fontSize: 12, color: "var(--text-tertiary)" }}>
            A rework resolution, once the customer accepts it, creates a rework request.
          </p>
          {resolutions.loading ? <Spinner /> : (
            (resolutions.data ?? []).length === 0
              ? <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No resolution offered yet.</p>
              : (resolutions.data ?? []).map(r => (
                <div key={s(r.id)} style={{
                  padding: "10px 12px", border: "1px solid var(--border)",
                  borderRadius: 8, marginBottom: 8,
                }}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                    <Badge variant="info">{s(r.resolution_type).replace(/_/g, " ")}</Badge>
                    <Badge variant={s(r.status) === "customer_accepted" ? "success"
                                  : s(r.status) === "customer_rejected" ? "danger" : "muted"}>
                      {s(r.status).replace(/_/g, " ")}
                    </Badge>
                  </div>
                  <div style={{ fontSize: 13 }}>{s(r.description)}</div>
                </div>
              ))
          )}
        </Card>
      )}

      {tab === "settlement" && (
        <Card>
          <h3 style={{ margin: "0 0 4px", fontSize: 14, fontWeight: 600 }}>Settlement proposals</h3>
          <p style={{ margin: "0 0 12px", fontSize: 12, color: "var(--text-tertiary)" }}>
            A settlement only takes effect once BOTH you and the customer accept it.
          </p>
          {proposals.loading ? <Spinner /> : (
            (proposals.data ?? []).length === 0
              ? <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No settlement proposals yet.</p>
              : (proposals.data ?? []).map(p => {
                const pstatus = s(p.status);
                const mine = s(p.proposed_by) === "provider";
                const awaitingMe = pstatus === "proposed" && !p.tenant_response;
                return (
                  <div key={s(p.id)} style={{
                    padding: "10px 12px", border: "1px solid var(--border)",
                    borderRadius: 8, marginBottom: 8,
                  }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                      <Badge variant="info">{s(p.proposal_type).replace(/_/g, " ")}</Badge>
                      <Badge variant={pstatus === "accepted" ? "success"
                                    : pstatus === "rejected" ? "danger" : "muted"}>
                        {pstatus.replace(/_/g, " ")}
                      </Badge>
                      <Badge variant="muted">by {s(p.proposed_by) || "—"}</Badge>
                      {p.proposal_amount != null && (
                        <Badge variant="muted">₹{s(p.proposal_amount)}</Badge>
                      )}
                    </div>
                    <div style={{ fontSize: 13, marginBottom: 6 }}>{s(p.description)}</div>
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                      customer: {s(p.customer_response) || "—"} · you: {s(p.tenant_response) || "—"}
                    </div>
                    {awaitingMe && !mine && (
                      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                        <Button size="sm" disabled={respondProposal.loading}
                             onClick={() => respondProposal.execute(s(p.id), "accept")}>Accept</Button>
                        <Button size="sm" variant="secondary" disabled={respondProposal.loading}
                             onClick={() => respondProposal.execute(s(p.id), "reject")}>Reject</Button>
                      </div>
                    )}
                  </div>
                );
              })
          )}
          {respondProposal.error && (
            <p style={{ color: "var(--danger-text)", fontSize: 12 }}>{respondProposal.error}</p>
          )}
        </Card>
      )}

      {tab === "ai" && (
        <Card>
          <h3 style={{ margin: "0 0 4px", fontSize: 14, fontWeight: 600 }}>AI settlement</h3>
          <p style={{ margin: "0 0 12px", fontSize: 12, color: "var(--text-tertiary)" }}>
            If the customer's issue reaches AI mediation, answer these so it can weigh both sides. Running AI settlement is charged to your account.
          </p>
          {aiSession.loading ? <Spinner /> : !aiSession.data ? (
            <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
              No AI settlement session for this complaint.
            </p>
          ) : (() => {
            const ai = aiSession.data as Dict;
            const qs = (ai.tenant_questions as string[]) ?? [];
            const awaiting = Boolean(ai.awaiting_your_answers);
            return (
              <div>
                <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
                  <Badge variant={s(ai.status) === "completed" ? "success"
                                : s(ai.status) === "failed" ? "danger" : "info"}>
                    {s(ai.status).replace(/_/g, " ")}
                  </Badge>
                </div>
                {awaiting ? (
                  <>
                    {qs.map((q, i) => (
                      <div key={i} style={{ marginBottom: 12 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{q}</div>
                        <Textarea rows={2} value={aiAnswers[i] ?? ""}
                          onChange={e => setAiAnswers(a => { const n = [...a]; n[i] = e.target.value; return n; })}
                          placeholder="Your response…" />
                      </div>
                    ))}
                    {submitAiAnswers.error && (
                      <p style={{ color: "var(--danger-text)", fontSize: 12 }}>{submitAiAnswers.error}</p>
                    )}
                    <Button disabled={submitAiAnswers.loading ||
                                   qs.length === 0 ||
                                   qs.some((_, i) => !(aiAnswers[i] ?? "").trim())}
                         loading={submitAiAnswers.loading}
                         onClick={() => submitAiAnswers.execute(qs.map((_, i) => aiAnswers[i] ?? ""))}>
                      Submit answers
                    </Button>
                  </>
                ) : (
                  <p style={{ fontSize: 13, color: "var(--success-text)" }}>
                    ✓ Your answers are recorded. The AI will propose an outcome once both sides have responded.
                  </p>
                )}
              </div>
            );
          })()}
        </Card>
      )}

      <Modal
        open={resOpen}
        onClose={() => setResOpen(false)}
        title="Offer a resolution"
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => setResOpen(false)}>Cancel</Button>
          <Button variant="primary" size="sm" disabled={!resDesc.trim()} loading={offerResolution.loading}
               onClick={() => offerResolution.execute()}>
            Offer resolution
          </Button>
        </>}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Select label="Resolution type" value={resType} onChange={e => setResType(e.target.value)} options={RESOLUTION_TYPES} />
          <Textarea label="Description" rows={3} value={resDesc} onChange={e => setResDesc(e.target.value)}
                 placeholder="What are you offering the customer?" />
          {offerResolution.error && (
            <p style={{ color: "var(--danger-text)", fontSize: 12 }}>{offerResolution.error}</p>
          )}
        </div>
      </Modal>

      <Modal
        open={propOpen}
        onClose={() => setPropOpen(false)}
        title="Propose a settlement"
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => setPropOpen(false)}>Cancel</Button>
          <Button variant="primary" size="sm" disabled={!propDesc.trim()} loading={createProposal.loading}
               onClick={() => createProposal.execute()}>
            Propose settlement
          </Button>
        </>}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Select label="Proposal type" value={propType} onChange={e => setPropType(e.target.value)} options={PROPOSAL_TYPES} />
          <Input label="Amount (optional)" value={propAmt} onChange={e => setPropAmt(e.target.value)} placeholder="e.g. 75" />
          <Textarea label="Description" rows={3} value={propDesc} onChange={e => setPropDesc(e.target.value)}
                 placeholder="Describe the settlement you are proposing…" />
          {createProposal.error && (
            <p style={{ color: "var(--danger-text)", fontSize: 12 }}>{createProposal.error}</p>
          )}
        </div>
      </Modal>
    </TenantLayout>
  );
}
